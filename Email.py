import base64
import html
import logging
import os
import smtplib
import socket
import threading
import time
import traceback
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

import local

logger = logging.getLogger("inspection.email")

# ---- Configuration (set these as environment variables on Render) ----
# SENDER_EMAIL / SENDER_PASSWORD : Gmail address + app password (SMTP)
# RESEND_API_KEY                 : if set, mail is sent over HTTPS via Resend
#                                  (use this if your Render plan blocks SMTP)
# RESEND_FROM                    : "From" address for Resend (verified domain)
# ALERT_EMAIL                    : where error alerts get sent
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "enquiries@HVengineers.com.au")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "rant xdhh onjr tehc")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM = os.environ.get("RESEND_FROM", SENDER_EMAIL)
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "simontroup27@gmail.com")

MAX_ATTACH_BYTES = 15 * 1024 * 1024
RETRIES = 3
TIMEOUT = 30


class EmailError(Exception):
    pass


# ----------------------------------------------------------------------
# Transports
# ----------------------------------------------------------------------
def _send_resend(to, subject, html_body, attachments):
    payload = {
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html_body,
        "attachments": [
            {"filename": n, "content": base64.b64encode(b).decode()}
            for n, b in attachments
        ],
    }
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json=payload,
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise EmailError(f"Resend API {r.status_code}: {r.text[:500]}")


def _build_mime(to, subject, html_body, attachments):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    for name, data in attachments:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=name)
        msg.attach(part)
    return msg


def _send_smtp(to, subject, html_body, attachments):
    msg = _build_mime(to, subject, html_body, attachments)
    errors = []
    # Try implicit SSL (465) then STARTTLS (587)
    for label, opener in (
        ("465/SSL", lambda: smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=TIMEOUT)),
        ("587/STARTTLS", lambda: _starttls()),
    ):
        try:
            with opener() as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            return
        except smtplib.SMTPAuthenticationError as e:
            # Bad credentials: no point trying another port
            raise EmailError(f"SMTP authentication failed (check app password): {e}")
        except (OSError, smtplib.SMTPException, socket.timeout) as e:
            errors.append(f"{label}: {type(e).__name__}: {e}")
            logger.warning("SMTP via %s failed: %s", label, e)
    raise EmailError(
        "All SMTP attempts failed (Render free instances block SMTP; "
        "set RESEND_API_KEY to send over HTTPS instead). " + " | ".join(errors)
    )


def _starttls():
    s = smtplib.SMTP("smtp.gmail.com", 587, timeout=TIMEOUT)
    s.ehlo()
    s.starttls()
    s.ehlo()
    return s


def _deliver(to, subject, html_body, attachments):
    """Send with retries. Raises EmailError after all attempts fail."""
    transport = _send_resend if RESEND_API_KEY else _send_smtp
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            logger.info("Sending '%s' to %s via %s (attempt %d/%d)",
                        subject, to, transport.__name__, attempt, RETRIES)
            transport(to, subject, html_body, attachments)
            logger.info("Email sent to %s", to)
            return
        except EmailError as e:
            last = e
            if "authentication failed" in str(e):
                break
        except Exception as e:  # network errors etc.
            last = EmailError(f"{type(e).__name__}: {e}")
        logger.error("Attempt %d failed: %s", attempt, last)
        if attempt < RETRIES:
            time.sleep(2 ** attempt)
    raise last


# ----------------------------------------------------------------------
# Error alerts
# ----------------------------------------------------------------------
_alert_lock = threading.Lock()
_alert_times = {}      # title -> last sent (monotonic)
_alert_window = []     # recent send times, for the global cap
ALERT_COOLDOWN = 600   # same alert at most once per 10 minutes
ALERT_MAX_PER_HOUR = 10


def _alert_allowed(title):
    now = time.monotonic()
    with _alert_lock:
        if now - _alert_times.get(title, -1e9) < ALERT_COOLDOWN:
            return False
        _alert_window[:] = [t for t in _alert_window if now - t < 3600]
        if len(_alert_window) >= ALERT_MAX_PER_HOUR:
            return False
        _alert_times[title] = now
        _alert_window.append(now)
        return True


def send_alert(title, details):
    """Email the admin about a failure (rate limited). Never raises."""
    try:
        if not _alert_allowed(title):
            logger.info("Alert suppressed (rate limit): %s", title)
            return
        body = (
            f"<h3>{html.escape(title)}</h3>"
            f"<p>{datetime.now():%Y-%m-%d %H:%M:%S}</p>"
            f"<pre style='white-space:pre-wrap'>{html.escape(str(details))}</pre>"
        )
        _deliver(ALERT_EMAIL, f"[Inspection App] {title}", body, [])
    except Exception:
        logger.exception("Could not send alert email (%s)", title)


def send_alert_async(title, details):
    """Fire-and-forget alert so request handlers never wait on SMTP."""
    threading.Thread(target=send_alert, args=(title, details), daemon=True).start()


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def send_Email(pdf, excel, recipient_email, customer):
    """Send the report. Logs every step and alerts the admin on failure.
    Returns (True, None) on success, (False, error_message) on failure."""
    try:
        if not recipient_email:
            raise EmailError("No recipient email address was provided")

        subject = f"Inspection Report for {customer}"
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"inspection_report-{str(customer).replace(' ', '-')}-{stamp}.pdf"
        logger.info("Preparing report for %s -> %s (pdf=%s bytes)",
                    customer, recipient_email, len(pdf) if pdf else 0)

        attachments = []
        links = []  # (label, url) for files too big to attach
        xlsx_bytes = excel.read() if excel is not None else None
        pdf_len = len(pdf) if pdf else 0
        xlsx_len = len(xlsx_bytes) if xlsx_bytes else 0
        logger.info("Attachment sizes: pdf=%d bytes, xlsx=%d bytes", pdf_len, xlsx_len)

        # Gmail's limit is 25MB *after* base64 (~+33%), so keep raw total under ~15MB.
        # If too big, upload the largest file(s) and send links instead.
        files = []
        if pdf is not None:
            files.append(["PDF report", file_name, pdf, "application/pdf"])
        if xlsx_bytes is not None:
            files.append(["Excel report", "inspection_report-%s-%s.xlsx" % (
                str(customer).replace(' ', '-'), stamp), xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"])
        files.sort(key=lambda f: len(f[2]))
        total = 0
        for label, name, data, ctype in files:
            if total + len(data) <= MAX_ATTACH_BYTES:
                attachments.append((name, data))
                total += len(data)
            else:
                logger.info("%s is %d bytes, uploading to storage", label, len(data))
                url = local.upload_pdf_to_supabase(data, name, ctype)
                if not str(url).startswith("http"):
                    raise EmailError(f"{label} upload failed: {url}")
                links.append((label, url))

        safe_customer = html.escape(str(customer))
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #004085;">Inspection Report</h2>
            <p>Dear {safe_customer},</p>
            <p>Please find the attached inspection report.</p>
        """
        if links:
            email_body += "<p>Some files are too large to attach directly. Download them using the links below:</p>"
            for label, url in links:
                email_body += f'''
            <p><a href="{url}" style="color: #007bff; text-decoration: underline; font-weight: bold;">Download {label}</a></p>
            <p style="word-break: break-all;">{url}</p>'''
        email_body += """
            <p>Best regards</p>

        </body>
        </html>
        """

        _deliver(recipient_email, subject, email_body, attachments)
        return True, None

    except Exception as e:
        logger.error("Failed to send report email: %s", e)
        send_alert(
            f"Report email FAILED for {customer}",
            f"Recipient: {recipient_email}\nError: {e}\n\n{traceback.format_exc()}",
        )
        return False
