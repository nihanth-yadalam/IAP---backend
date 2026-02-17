"""
Email service — sends emails via SMTP (Gmail).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send a password reset email with the reset token/link."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. Token for {to_email}: {token}")
        return False

    reset_link = f"http://localhost:3000/reset-password?token={token}"

    subject = f"{settings.EMAILS_FROM_NAME} — Password Reset"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Password Reset Request</h2>
        <p>Hello,</p>
        <p>We received a request to reset your password. Click the button below to set a new password:</p>
        <p style="margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #4CAF50; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 4px; font-size: 16px;">
                Reset Password
            </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="color: #666; word-break: break-all;">{reset_link}</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">
            If you didn't request a password reset, you can safely ignore this email.
            This link expires in 1 hour.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email

    # Plain text fallback
    text_body = (
        f"Password Reset\n\n"
        f"Click this link to reset your password:\n{reset_link}\n\n"
        f"This link expires in 1 hour.\n"
        f"If you didn't request this, ignore this email."
    )

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL] Password reset email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email to {to_email}: {e}")
        return False