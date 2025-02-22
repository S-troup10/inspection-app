import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import local
from email.mime.text import MIMEText




def send_Email(pdf, excel, recipient_email, customer):
    try:
        # Email configuration
        sender_email = "enquiries@HVengineers.com.au"  # Replace with your email
        sender_password = "rant xdhh onjr tehc"  # Replace with your email app password
        subject = f"Inspection Report for {customer}"

        # Create the email message
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = subject

        # Format customer name for filename
        current_date = datetime.now()
        file_name = f"inspection_report-{customer.replace(' ', '-')}-{current_date}.pdf"
        file_name = file_name.replace(' ', '')

        # Handle PDF (upload if too large)
        pdf_link = None
        if pdf is not None:
            pdf_result = handle_pdf_upload(pdf, file_name)

            if isinstance(pdf_result, bytes):  # If it's small enough, attach directly
                pdf_attachment = MIMEBase('application', 'pdf')
                pdf_attachment.set_payload(pdf_result)
                encoders.encode_base64(pdf_attachment)
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
                message.attach(pdf_attachment)
            else:  # If it's a URL, store it for the email body
                pdf_link = pdf_result

        # Attach Excel file if provided
        if excel is not None:
            excel_attachment = MIMEBase('application', 'octet-stream')
            excel_attachment.set_payload(excel.read())
            encoders.encode_base64(excel_attachment)
            excel_attachment.add_header('Content-Disposition', 'attachment', filename='inspection_report.xlsx')
            message.attach(excel_attachment)

        # Create a professional HTML email body
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #004085;">Inspection Report</h2>
            <p>Dear {customer},</p>
            <p>Please find the attached inspection report.</p>
        """

        if pdf_link:
            email_body += f"""
            <p>The report is too large to attach. You can download it by clicking the link below:</p>
            <p><a href="{pdf_link}" style="color: #007bff; text-decoration: none; font-weight: bold;">Click here</a> to download your report.</p>
            """

        email_body += """
            <p>Best regards</p>

        </body>
        </html>
        """

        # Attach the email body as HTML
        message.attach(MIMEText(email_body, 'html'))

        # Send the email using SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)

        print("Email sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")



def handle_pdf_upload(pdf_bytes: bytes, filename: str) -> str:
    """
    Handle the process of checking the size of the PDF and uploading it to Supabase if necessary.

    Args:
        pdf_bytes (bytes): The generated PDF in bytes.
        filename (str): The filename to use when uploading the PDF.

    Returns:
        str: The URL of the uploaded PDF if it's too large, or the PDF in bytes if it's small enough.
    """
    MAX_PDF_SIZE = 10 * 1024 * 1024  # 23 MB

    try:
        # Step 1: Get the size of the PDF
        pdf_size = len(pdf_bytes)

        # Step 2: Check if the PDF exceeds 23 MB
        if pdf_size > MAX_PDF_SIZE:
            # If the PDF is too big, upload it to Supabase
            pdf_url = local.upload_pdf_to_supabase(pdf_bytes, filename)
            pdf_url = pdf_url.rstrip('?')
            #pdf_url = f"{pdf_url}?download=true"

            return pdf_url  # Return the URL if uploaded to Supabase
        
        else:
            # If the PDF is small enough, return the bytes
            return pdf_bytes

    except Exception as e:
        print(f"Error during PDF handling: {e}")
        return f"Error during PDF handling: {str(e)}"
