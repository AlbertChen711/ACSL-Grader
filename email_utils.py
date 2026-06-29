"""
Email utilities for sending verification codes via Gmail SMTP
"""
import smtplib
import os
from email.message import EmailMessage


def send_verification_code(email, code):
    """Sends a 6-digit verification code to the given email via Gmail SMTP."""
    username = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")

    msg = EmailMessage()
    msg.set_content(
        f"Your ACSL Grader verification code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you did not create an account, please ignore this email."
    )
    msg["Subject"] = "Verify your ACSL Grader account"
    msg["From"] = username
    msg["To"] = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send to {email}: {e}")
        return False
