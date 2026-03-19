"""
login/ registration/ authentication
"""
from sqlmodel import Session, select
from datetime import datetime
from .database import UserSession, User, get_session
from fastapi import Depends, HTTPException, Header
from .database import get_valid_user_by_id, get_valid_session_from_db
from .database import refresh_user_session
from config import TOKEN_TTL_SECONDS
import bcrypt

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def hash_password(plain_password: str) -> str:
    """hash password using bcrypt"""
    try:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """verify password using bcrypt"""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_current_user(
    authorization: str = Header(None),
    session: Session = Depends(get_session)
) -> User:
    """get current user from database, and refresh session expiry (sliding)."""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ")[1]

        #check if the session is valid and try to refresh
        user_session = get_valid_session_from_db(token, session)
        try:
            refresh_user_session(session, user_session, ttl_seconds=TOKEN_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Session refresh failed, continue with current session: {e}")

        #get current user after it is checked and refreshed
        user = get_valid_user_by_id(user_session.user_id, session=session)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

