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
from datetime import datetime

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

# ======= Tables =======
class User(SQLModel, table=True):
    """
    User table, user_id = PK
    """
    __tablename__ = "User"
    user_id: Optional[int] = Field(default=None, primary_key=True)    
    username_db: str = Field(index=True)     #uniqueness is restricted by register api
    password_hash: str
    public_key_db: str = Field(default="")

class UserSession(SQLModel, table=True):
    """
    Login session and state table
    """
    __tablename__ = "UserSession"
    token: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="User.user_id")
    expires_at: datetime

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
    is_delivered: bool = Field(default=False)

#=======Utility Functions=======
#for establishing database connection
def get_session():
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
    except Exception as e:
        session.rollback()
        logger.error(f"Error getting valid user id: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: {e}")

def get_valid_session_from_db(
    token: str, 
    session: Session = Depends(get_session)
    ) -> Session:
    """get valid session from database"""
    try:
        session = session.exec(select(UserSession).where(UserSession.token == token)).first()
        if session.expires_at < datetime.now():
            raise HTTPException(status_code=401, detail="Session expired")
        return session
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error getting valid session by token: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")


def check_password(password: str):
    """check if password is valid"""
    if len(password) < 8:
        return False
    return True
