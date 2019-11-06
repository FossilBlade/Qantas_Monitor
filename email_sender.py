import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import glob



def send_mail(receiver_email,job_id,folder_path):

    sender_email = "qantasscrapper@gmail.com"
    password = "scrapper@123"

    subject = "[Job:{}] Qantas Flight Data".format(job_id)
    body = "Please find attached the latest qantas data report for Job Id: {}".format(job_id)

    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message["Bcc"] = receiver_email  # Recommended for mass emails



    files = glob.glob("{}/*.xlsx".format(folder_path))

    if(len(files)==0):
        body = "No Files found for Job Id: {}".format(job_id)
        subject = "[Job:{}] Qantas Report: No Files Found".format(job_id)
        message["Subject"] = subject
    else:
        for f in files:
            # Open PDF file in binary mode
            with open(f, "rb") as attachment:
                # Add file as application/octet-stream
                # Email client can usually download this automatically as attachment
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(f)}",
            )

            # Add attachment to message and convert message to string
            message.attach(part)

    # Add body to email
    message.attach(MIMEText(body, "plain"))
    text = message.as_string()

    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)