"""
Email service — sends emails via SMTP (Gmail).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def _send(msg: MIMEMultipart, to_email: str, label: str) -> bool:
    """Internal helper — opens one SMTP connection and sends msg."""
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL] {label} sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send {label} to {to_email}: {e}")
        return False


def send_signup_confirmation_email(to_email: str, username: str) -> bool:
    """Send a welcome email after a new account is created."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. Skipping signup confirmation for {to_email}")
        return False

    subject = f"Welcome to {settings.EMAILS_FROM_NAME}!"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
        <h2 style="color: #4f46e5;">Welcome, {username}! 🎓</h2>
        <p>Your account has been created successfully on <strong>{settings.EMAILS_FROM_NAME}</strong>.</p>
        <p>You can now log in and start planning your academic schedule.</p>
        <p style="margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/login"
               style="background-color: #4f46e5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 8px; font-size: 15px;">
                Go to Login
            </a>
        </p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">If you did not create this account, please ignore this email.</p>
    </body>
    </html>
    """
    text_body = (
        f"Welcome to {settings.EMAILS_FROM_NAME}, {username}!\n\n"
        f"Your account has been created. Log in at: {settings.FRONTEND_URL}/login\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return _send(msg, to_email, "signup confirmation")


def send_otp_email(to_email: str, username: str, otp: str) -> bool:
    """Send a 6-digit OTP for login verification."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. OTP for {to_email}: {otp}")
        return False

    subject = f"{settings.EMAILS_FROM_NAME} — Your login code: {otp}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; max-width: 600px;">
        <h2>Your One-Time Login Code</h2>
        <p>Hi {username},</p>
        <p>Use the code below to complete your sign-in. It expires in <strong>10 minutes</strong>.</p>
        <div style="margin: 30px 0; text-align: center;">
            <span style="font-size: 40px; font-weight: bold; letter-spacing: 12px;
                         color: #4f46e5; background: #f0f0ff; padding: 16px 28px;
                         border-radius: 12px; display: inline-block;">
                {otp}
            </span>
        </div>
        <p>If you did not request this code, someone may be trying to access your account.
           Please <a href="{settings.FRONTEND_URL}/forgot">reset your password</a> immediately.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">This code is valid for one use only.</p>
    </body>
    </html>
    """
    text_body = (
        f"Hi {username},\n\n"
        f"Your login verification code is: {otp}\n"
        f"It expires in 10 minutes.\n\n"
        f"If you did not request this, reset your password at: {settings.FRONTEND_URL}/forgot\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return _send(msg, to_email, "OTP")


def send_login_confirmation_email(to_email: str, username: str) -> bool:
    """Send a login notification email after a successful password-based login."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"[EMAIL] SMTP not configured. Skipping login confirmation for {to_email}")
        return False

    subject = f"{settings.EMAILS_FROM_NAME} — New Sign-in Detected"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>New Sign-in to Your Account</h2>
        <p>Hi {username},</p>
        <p>We detected a new sign-in to your {settings.EMAILS_FROM_NAME} account.</p>
        <p>If this was you, no action is needed.</p>
        <p>If you did not sign in, please <a href="{settings.FRONTEND_URL}/forgot">reset your password</a> immediately.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #999; font-size: 12px;">This is an automated security notification.</p>
    </body>
    </html>
    """
    text_body = (
        f"Hi {username},\n\n"
        f"We detected a new sign-in to your {settings.EMAILS_FROM_NAME} account.\n"
        f"If this was not you, reset your password at: {settings.FRONTEND_URL}/forgot\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return _send(msg, to_email, "login confirmation")


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
    return _send(msg, to_email, "password reset")