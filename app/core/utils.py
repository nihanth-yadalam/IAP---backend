from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from app.core.config import settings


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=1)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = int(expires.timestamp())
    encoded_jwt = jwt.encode(
        {"exp": exp, "sub": email},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return decoded_token["sub"]
    except jwt.JWTError as e:
        print(f"JWT Verification Error: {e}")
        return None


def generate_email_confirmation_token(email: str) -> str:
    delta = timedelta(hours=24)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = int(expires.timestamp())
    encoded_jwt = jwt.encode(
        {"exp": exp, "sub": email, "purpose": "email_confirmation"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_email_confirmation_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if decoded_token.get("purpose") != "email_confirmation":
            return None
        return decoded_token["sub"]
    except jwt.JWTError as e:
        print(f"Email confirmation JWT error: {e}")
        return None


def generate_otp_code() -> str:
    """Generate a cryptographically secure 6-digit OTP code."""
    import secrets
    return f"{secrets.randbelow(900000) + 100000}"
