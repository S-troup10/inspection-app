"""Background report-email jobs with persisted state.

Each job's PDF/Excel and status are saved to Supabase storage under
jobs/<id>/ so a failed or interrupted send can be retried (or re-sent
from a button) even after the server restarts.
"""
import json
import logging
import re
import threading
import time
import uuid
from io import BytesIO

import Email
import local

logger = logging.getLogger("inspection.jobs")

_JOBS = {}      # job_id -> meta dict (in memory cache)
_BLOBS = {}     # job_id -> (pdf, xlsx) kept only if persisting to storage failed
_lock = threading.Lock()
_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def valid_id(job_id):
    return bool(job_id and _ID_RE.match(job_id))


def _path(job_id, name):
    return f"jobs/{job_id}/{name}"


def _set(job_id, **fields):
    with _lock:
        meta = _JOBS.setdefault(job_id, {})
        meta.update(fields, updated=time.time())
        snapshot = dict(meta)
    try:
        local.storage_put(_path(job_id, "job.json"),
                          json.dumps(snapshot).encode(), "application/json")
    except Exception:
        logger.warning("Could not persist status for job %s", job_id)
    return snapshot


def create_job(email, customer, pdf, xlsx):
    """Register a job, persist its files, and start sending in the background."""
    job_id = uuid.uuid4().hex
    with _lock:
        _JOBS[job_id] = {"id": job_id, "email": email, "customer": customer,
                         "status": "queued", "error": None, "attempts": 0,
                         "updated": time.time()}
    _start(job_id, pdf, xlsx)
    return job_id


def _start(job_id, pdf, xlsx):
    threading.Thread(target=_run, args=(job_id, pdf, xlsx), daemon=True).start()


def _run(job_id, pdf, xlsx):
    try:
        meta = _JOBS.get(job_id, {})
        persisted = True
        try:
            if pdf is not None:
                local.storage_put(_path(job_id, "report.pdf"), pdf, "application/pdf")
            if xlsx is not None:
                local.storage_put(_path(job_id, "report.xlsx"), xlsx,
                                  "application/octet-stream")
        except Exception:
            persisted = False
            logger.exception("Could not persist files for job %s; keeping in memory", job_id)
            _BLOBS[job_id] = (pdf, xlsx)

        _set(job_id, status="sending", attempts=meta.get("attempts", 0) + 1,
             persisted=persisted)
        ok, err = Email.send_Email(pdf, BytesIO(xlsx) if xlsx is not None else None,
                                   meta.get("email"), meta.get("customer"))
        if ok:
            _set(job_id, status="sent", error=None)
            _BLOBS.pop(job_id, None)
        else:
            _set(job_id, status="failed", error=err)
    except Exception as e:
        logger.exception("Job %s crashed", job_id)
        _set(job_id, status="failed", error=str(e))
        Email.send_alert_async(f"Email job crashed ({job_id})", repr(e))


def get_status(job_id):
    """Return the job's meta dict, or None if unknown."""
    with _lock:
        meta = _JOBS.get(job_id)
    if meta:
        return dict(meta)
    try:  # after a restart
        return json.loads(local.storage_get(_path(job_id, "job.json")))
    except Exception:
        return None


def resend(job_id):
    """Re-send a failed job. Returns (ok, message)."""
    meta = get_status(job_id)
    if not meta:
        return False, "Unknown job"
    if meta.get("status") in ("queued", "sending"):
        return False, "Already sending"
    with _lock:
        _JOBS[job_id] = dict(meta)
    if job_id in _BLOBS:
        pdf, xlsx = _BLOBS[job_id]
    else:
        try:
            pdf = local.storage_get(_path(job_id, "report.pdf"))
        except Exception:
            return False, "Saved report not found - please regenerate it"
        try:
            xlsx = local.storage_get(_path(job_id, "report.xlsx"))
        except Exception:
            xlsx = None
    _set(job_id, status="queued", error=None)
    _start(job_id, pdf, xlsx)
    return True, "Resending"
