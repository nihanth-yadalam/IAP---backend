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

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    reset_link = f"{frontend_url}/reset-password?token={token}"

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


def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Generic SMTP send helper."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured for {to_email}")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email to {to_email}: {e}")
        return False


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send a 6-digit OTP code for login verification."""
    subject = f"{settings.EMAILS_FROM_NAME} — Your sign-in code"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Your Sign-In Code</h2>
        <p>Hello,</p>
        <p>Use the code below to complete your sign-in:</p>
        <p style="margin: 30px 0; text-align: center;">
            <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                         background: #f4f4f4; padding: 16px 32px; border-radius: 8px;
                         display: inline-block; color: #333;">
                {otp_code}
            </span>
        </p>
        <p style="color: #666;">This code expires in <strong>10 minutes</strong>.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">
            If you didn't try to sign in, you can safely ignore this email.
        </p>
    </body>
    </html>
    """
    text_body = (
        f"Your sign-in code: {otp_code}\n\n"
        f"This code expires in 10 minutes.\n"
        f"If you didn't request this, ignore this email."
    )
    sent = _send_email(to_email, subject, html_body, text_body)
    if sent:
        print(f"[EMAIL] OTP sent to {to_email}")
    else:
        print(f"[EMAIL] OTP for {to_email}: {otp_code}")
    return sent


def send_email_confirmation(to_email: str, token: str) -> bool:
    """Send an email confirmation link to a newly registered user."""
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    confirm_link = f"{frontend_url}/confirm-email?token={token}"

    subject = f"{settings.EMAILS_FROM_NAME} — Confirm your email"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Confirm Your Email Address</h2>
        <p>Hello,</p>
        <p>Thanks for signing up! Please confirm your email address by clicking the button below:</p>
        <p style="margin: 30px 0;">
            <a href="{confirm_link}"
               style="background-color: #6366f1; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 4px; font-size: 16px;">
                Confirm Email
            </a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="color: #666; word-break: break-all;">{confirm_link}</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">
            If you didn't create an account, you can safely ignore this email.
            This link expires in 24 hours.
        </p>
    </body>
    </html>
    """
    text_body = (
        f"Confirm your email\n\n"
        f"Click this link to confirm your email:\n{confirm_link}\n\n"
        f"This link expires in 24 hours.\n"
        f"If you didn't sign up, ignore this email."
    )
    sent = _send_email(to_email, subject, html_body, text_body)
    if sent:
        print(f"[EMAIL] Confirmation email sent to {to_email}")
    else:
        print(f"[EMAIL] Confirmation link for {to_email}: {confirm_link}")
    return sent