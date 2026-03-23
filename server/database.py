"""
database connection, 
the suffix "_db" indicates the variables are from database to reduce confusion
"""

from sqlmodel import Field, SQLModel, create_engine, Session
from typing import Optional
import logging
from pathlib import Path
from fastapi import HTTPException, Depends
from sqlmodel import select
import time
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ======= Database =======
server_dir = Path(__file__).resolve().parent
database_dir = server_dir / "database"
database_dir.mkdir(parents=True, exist_ok=True)

sqlite_file_name = database_dir / "database.db"
DATABASE_URL = f"sqlite:///{sqlite_file_name.as_posix()}"
engine = create_engine(
    DATABASE_URL,
    echo=False
)


def init_db():
    SQLModel.metadata.create_all(engine)
    normalize_session_expiry_storage()


def normalize_session_expiry_storage() -> None:
    """Best-effort migration to keep expires_at persisted as Unix seconds."""
    try:
        with Session(engine) as session:
            session.exec(text(
                """
                UPDATE UserSession
                SET expires_at = CAST(expires_at AS INTEGER)
                WHERE typeof(expires_at) = 'text' AND trim(expires_at) GLOB '[0-9]*'
                """
            ))
            session.exec(text(
                """
                UPDATE UserSession
                SET expires_at = CAST(strftime('%s', expires_at) AS INTEGER)
                WHERE typeof(expires_at) = 'text'
                  AND trim(expires_at) LIKE '____-__-__%'
                  AND strftime('%s', expires_at) IS NOT NULL
                """
            ))
            session.commit()
    except Exception as e:
        logger.warning(f"Session expiry migration skipped: {e}")


# ======= Tables =======
class User(SQLModel, table=True):
    """
    User table, user_id = PK
    """
    __tablename__ = "User"
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username_db: str = Field(index=True)  #uniqueness is restricted by register api
    password_hash: str
    public_key_db: str = Field(default="")


class UserSession(SQLModel, table=True):
    """
    Login session and state table
    """
    __tablename__ = "UserSession"
    token: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="User.user_id")
    expires_at: int


class Message(SQLModel, table=True):
    """
    Message table, message_id = PK
    """
    __tablename__ = "Message"
    message_id: int = Field(default=None, primary_key=True)
    sender_id: int = Field(default=None)
    sender_username_db: str
    receiver_id: int = Field(default=None)
    receiver_username_db: str
    ciphertext: str
    nonce: str
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    is_delivered: bool = Field(default=False)
    age: int = Field(default=0)

#JJ friend 
class FriendRequest(SQLModel, table=True):
    __tablename__ = "FriendRequest"
    id: Optional[int] = Field(default=None, primary_key=True)
    from_user_id: int = Field(foreign_key="User.user_id")
    to_user_id: int = Field(foreign_key="User.user_id")
    status: str = Field(default="pending")   # pending, accepted, declined
    created_at: int = Field(default_factory=lambda: int(time.time()))  # Unix timestamp
    updated_at: int = Field(default_factory=lambda: int(time.time()))  # Unix timestamp

class Friend(SQLModel, table=True):
    __tablename__ = "Friend"
    user_id: int = Field(foreign_key="User.user_id", primary_key=True)
    friend_id: int = Field(foreign_key="User.user_id", primary_key=True)

class BlockedUser(SQLModel, table=True):
    __tablename__ = "BlockedUser"
    user_id: int = Field(foreign_key="User.user_id", primary_key=True)
    blocked_user_id: int = Field(foreign_key="User.user_id", primary_key=True)

#======= User Session Utilities =======

def compute_session_expires_at(ttl_seconds: int, now: Optional[int] = None) -> int:
    """
    Compute the expires_at unix timestamp for a session, given a TTL in seconds.
    """
    if now != None:
        base_time = now
    else:
        base_time = int(time.time())
    return base_time + ttl_seconds


def refresh_user_session(
        db_session: Session,
        user_session: UserSession,
        ttl_seconds: int,
        now: Optional[int] = None
) -> UserSession:
    """
    Refresh an existing UserSession's expires_at by extending it from 'now' by ttl_seconds.
    The caller is responsible for committing the transaction.
    """
    try:
        new_expires_at = compute_session_expires_at(ttl_seconds=ttl_seconds, now=now)
        user_session.expires_at = new_expires_at
        db_session.add(user_session)
        db_session.commit()
        logger.info(f"User session refreshed successfully")
        return user_session
    except Exception as e:
        db_session.rollback()
        logger.exception("Error refreshing user session")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


def coerce_epoch_seconds(value: object) -> Optional[int]:
    """Best-effort conversion for persisted session expiry values."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


#=======Utility Functions=======

def get_session():
    """for establishing database connection"""
    with Session(engine) as session:
        yield session


def get_valid_user_by_id(
        user_id: int,
        session: Session = Depends(get_session)
) -> User:
    """get valid user from database"""
    try:
        user = session.exec(select(User).where(User.user_id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("Error getting valid user id")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


def get_valid_user_by_username(
        username: str,
        session: Session = Depends(get_session)
) -> User:
    """get valid user from database"""
    try:
        user = session.exec(select(User).where(User.username_db == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("Error getting valid user by username")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


def get_valid_session_from_db(
        token: str,
        session: Session = Depends(get_session)
) -> UserSession:
    """get and check valid session from database"""
    try:
        user_session = session.exec(select(UserSession).where(UserSession.token == token)).first()
        if not user_session:
            raise HTTPException(status_code=401, detail="Session not found")

        expires_at_checked = coerce_epoch_seconds(user_session.expires_at)
        if expires_at_checked is None:
            raise HTTPException(status_code=401, detail="Session invalid")

        if expires_at_checked < int(time.time()):
            raise HTTPException(status_code=401, detail="Session expired")

        if user_session.expires_at != expires_at_checked:
            user_session.expires_at = expires_at_checked
            session.add(user_session)
            session.commit()

        return user_session
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("Error getting valid session by token")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


def check_password(password: str):
    """check if password is valid"""
    if len(password) < 8:
        return False
    return True

def get_expired_messages(session: Session) -> list[Message]:
    """get expired messages from database"""
    try:
        current_time = int(time.time())
        expired_msgs = session.exec(
            select(Message).where(
                (Message.age > 0) & (Message.timestamp + Message.age < current_time)
            )
        ).all()
        return expired_msgs
    except Exception as e:
        logger.exception("Error getting expired messages")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

def remove_expired_messages(session: Session) -> None:
    """remove expired messages from database"""
    try:
        expired_msgs = get_expired_messages(session)
        for msg in expired_msgs:
            session.delete(msg)
        session.commit()
        logger.info(f"Expired messages removed successfully, count: {len(expired_msgs)}")
    except Exception as e:
        session.rollback()
        logger.exception("Error removing expired messages")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")