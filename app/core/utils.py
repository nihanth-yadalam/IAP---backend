from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from app.core.config import settings

<<<<<<< HEAD

=======
>>>>>>> main
def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=1)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = int(expires.timestamp())
    encoded_jwt = jwt.encode(
<<<<<<< HEAD
        {"exp": exp, "sub": email},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


=======
        {"exp": exp, "sub": email}, settings.SECRET_KEY, algorithm="HS256",
    )
    return encoded_jwt

>>>>>>> main
def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return decoded_token["sub"]
    except jwt.JWTError as e:
        print(f"JWT Verification Error: {e}")
        return None
