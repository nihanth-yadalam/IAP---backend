"""
Google OAuth service — from System B.
Handles authorization URL generation, code exchange, and credential refresh.
Adapted to work with the merged async User model.
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from app.core.config import settings


class GoogleOAuthService:
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    LOGIN_SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    settings.OAUTH_REDIRECT_URI,
                    settings.GOOGLE_LOGIN_REDIRECT_URI,
                ],
            }
        }

    def get_authorization_url(self, state: str = "random_state") -> str:
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=self.client_config["web"]["redirect_uris"][0],
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=state,
        )
        return auth_url

    def exchange_code_for_tokens(self, code: str) -> dict:
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=self.client_config["web"]["redirect_uris"][0],
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user email from Google Calendar
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=credentials)
        calendar = service.calendars().get(calendarId="primary").execute()
        email = calendar.get("id", "unknown@example.com")

        return {
            "refresh_token": credentials.refresh_token,
            "access_token": credentials.token,
            "email": email,
        }

    def get_login_authorization_url(self, state: str = "login") -> str:
        """Generate a Google OAuth URL for sign-in (no prior login required)."""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.LOGIN_SCOPES,
            redirect_uri=settings.GOOGLE_LOGIN_REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="select_account",
            state=state,
        )
        return auth_url

    def exchange_login_code_for_user_info(self, code: str) -> dict:
        """Exchange authorization code for Google user profile (email + name)."""
        import requests as _requests

        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.LOGIN_SCOPES,
            redirect_uri=settings.GOOGLE_LOGIN_REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials

        resp = _requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"},
            timeout=10,
        )
        resp.raise_for_status()
        info = resp.json()
        return {
            "email": info.get("email"),
            "name": info.get("name", ""),
        }

    def get_valid_credentials(self, refresh_token: str) -> Credentials:
        """Build valid Google credentials from a refresh token."""
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_config["web"]["client_id"],
            client_secret=self.client_config["web"]["client_secret"],
            scopes=self.SCOPES,
        )
        if not creds.valid:
            creds.refresh(Request())
        return creds
