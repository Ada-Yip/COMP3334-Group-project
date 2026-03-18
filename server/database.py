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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ======= Database =======
# Keep DB path stable regardless of current working directory.
# I changed the path of database.db into a dir under server/
# Now it should be always in server/database/database.db
# Todo: I think it's kinda crazy to put message and user into same database, we skip it? or we make it separate?
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

#for establishing database connection
def get_session():
    with Session(engine) as session:
        yield session

#=======Utility Functions=======

def get_valid_user_id(user_id: int, session: Session = Depends(get_session)):
    """
    get valid user id from database
    """
    try:
        user = session.exec(select(User).where(User.user_id == user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.user_id
    except Exception as e:
        session.rollback()
        logger.error(f"Error getting valid user id: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: {e}")

def check_password(password: str):
    """
    check if password is valid
    """
    if len(password) < 8:
        return False
    return True

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
