import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


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

        # Add email body
        body = "Please find the attached inspection report."
        message.attach(MIMEText(body, 'plain'))

        # Attach the PDF file
        if pdf is not None:
                
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(pdf)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment; filename=inspection_report.pdf')
            message.attach(attachment)
            
        if excel is not None:
            attachment_excel = MIMEBase('application', 'octet-stream')
            attachment_excel.set_payload(excel.read())
            encoders.encode_base64(attachment_excel)
            attachment_excel.add_header('Content-Disposition', 'attachment; filename="inspection_report.xlsx"')
            message.attach(attachment_excel)

        # Send the email using SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        
