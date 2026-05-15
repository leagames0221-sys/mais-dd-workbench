"""Session + OAuth provider hooks.

PoC = mock OAuth、 real OAuth (Google / LinkedIn) は OAuth key を .env で provision 後 active 化。
移植 = Authlib + fastapi-users + JWT RS256 + MFA。
"""
from __future__ import annotations

import os
import secrets
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)

ProviderName = Literal["mock", "google", "linkedin"]

OAUTH_PROVIDERS = {
    "google": {
        "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "linkedin": {
        "client_id": os.environ.get("LINKEDIN_OAUTH_CLIENT_ID", ""),
        "client_secret": os.environ.get("LINKEDIN_OAUTH_CLIENT_SECRET", ""),
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "userinfo_url": "https://api.linkedin.com/v2/userinfo",
        "scope": "openid email profile",
    },
}


def is_provider_configured(name: ProviderName) -> bool:
    if name == "mock":
        return True
    cfg = OAUTH_PROVIDERS.get(name)
    return bool(cfg and cfg["client_id"] and cfg["client_secret"])
