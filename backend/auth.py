"""Firebase Authentication middleware for FastAPI."""

import logging
from typing import Optional

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import get_firebase_credentials
from .db import get_db
from .models import User

logger = logging.getLogger(__name__)

# --- Initialize Firebase Admin SDK ---
_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK if credentials are available."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    creds_dict = get_firebase_credentials()
    if creds_dict:
        try:
            cred = credentials.Certificate(creds_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully.")
        except Exception as exc:
            logger.error("Failed to initialize Firebase: %s", exc)
            _firebase_app = None
    else:
        # Initialize without credentials (allows token verification using project ID from env)
        try:
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized without explicit credentials.")
        except Exception:
            logger.warning(
                "Firebase Admin SDK not initialized. Auth will be disabled. "
                "Set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH."
            )
            _firebase_app = None

    return _firebase_app


# Initialize on module load
_init_firebase()


def _extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None


def get_or_create_user(db: Session, firebase_uid: str, email: str, display_name: str, photo_url: str | None) -> User:
    """Find existing user by Firebase UID or create a new one."""
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user:
        # Update profile info if changed
        changed = False
        if user.email != email:
            user.email = email
            changed = True
        if user.display_name != display_name:
            user.display_name = display_name
            changed = True
        if user.photo_url != photo_url:
            user.photo_url = photo_url
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user

    user = User(
        firebase_uid=firebase_uid,
        email=email,
        display_name=display_name or email.split("@")[0],
        photo_url=photo_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """
    Dependency that extracts and verifies Firebase ID token.
    Returns the User object if authenticated, None if no token or Firebase not configured.
    """
    token = _extract_token(request)
    if not token:
        return None

    if _firebase_app is None:
        # Firebase not configured — skip verification but still return None
        return None

    try:
        decoded = firebase_auth.verify_id_token(token)
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Authentication token has expired.")
    except Exception as exc:
        logger.error("Token verification error: %s", exc)
        raise HTTPException(status_code=401, detail="Authentication failed.")

    firebase_uid = decoded.get("uid", "")
    email = decoded.get("email", "unknown@unknown.com")
    display_name = decoded.get("name", "") or email.split("@")[0]
    photo_url = decoded.get("picture")

    user = get_or_create_user(db, firebase_uid, email, display_name, photo_url)
    return user


async def require_auth(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Strict auth dependency — raises 401 if not authenticated.
    Use for endpoints that MUST have a logged-in user.
    """
    user = await get_current_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user
