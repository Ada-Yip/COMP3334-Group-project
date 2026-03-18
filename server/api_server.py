"""
api and enter point
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from .database import (
    User, 
    Message, 
    init_db, 
    get_session, 
    get_valid_user_id, 
    check_password
)
from pydantic import BaseModel
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


#FastAPI instance
app = FastAPI(title="EE2E Server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up server")
    init_db()
    logger.info("server started")
    yield
    logger.info("shutting down server")

app = FastAPI(lifespan=lifespan)

# --- API 端點 ---
#  TODO: add function to generate public key
#  Sam: for client-server encryption? We can leave it in next phase.


# Register Request, using pydantic
class RegisterReq(BaseModel):
    username: str
    password: str
    public_key: str

@app.post("/register")
def register(
    req: RegisterReq, 
    session: Session = Depends(get_session)
    ):
    """register user to database"""
    try:
        username_input = req.username.strip()
        password_input = req.password.strip()
        public_key_input = req.public_key.strip()
        new_user = User(username_db=username_input, password_hash=password_input, public_key_db=public_key_input)

        #check if user already exists
        existing_user = session.exec(select(User).where(User.username_db == username_input)).first()
        if existing_user is not None:
            logger.error(f"User {username_input} already exists")
            session.rollback()
            raise HTTPException(status_code=400, detail="User already exists")
        
        #check if password is valid
        if not check_password(password_input):
            logger.error(f"Password requiement not satisfied for user {username_input}")
            session.rollback()
            raise HTTPException(status_code=400, detail="Password requirement not satisfied")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    session.add(new_user)
    session.commit()
    logger.info(f"User {username_input} registered successfully")
    return {"message":f"User {username_input} registered successfully"}

@app.get("/users/{user_id}/public_key")
def get_user_public_key(
    user_id: int = Depends(get_valid_user_id), 
    session: Session = Depends(get_session)
    ):
    """get user public key from database"""
    user = session.get(User, user_id)
    return {"public_key": user.public_key_db}      #TODO: add validation to key changes?

#=======Message API=======

# Send Message Request
class SendMsgReq(BaseModel):
    sender_id: int
    sender_username: str
    receiver_username: str
    ciphertext: str
    nonce: str

@app.post("/messages/send")
def send_message(
    req: SendMsgReq, 
    session: Session = Depends(get_session)
    ):
    """send message to database"""
    try:
        #check if receiver exists
        receiver = session.exec(select(User).where(User.username_db == req.receiver_username)).first()
        if not receiver:
            logger.error(f"Receiver {req.receiver_username} not found")
            session.rollback()
            raise HTTPException(status_code=400, detail="Receiver not found")

        msg = Message(
            sender_id=req.sender_id, sender_username_db=req.sender_username,
            receiver_id=receiver.user_id, receiver_username_db=receiver.username_db,
            ciphertext=req.ciphertext, 
            nonce=req.nonce)
        session.add(msg)
        session.commit()
        logger.info(f"Message from {req.sender_username} to {req.receiver_username} queued successfully")
        return {"message": f"Message from {req.sender_username} to {req.receiver_username} queued successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: {e}")

class FetchMsgCond(BaseModel):
    user_id: int
    unseen_only: bool

@app.post("/messages/fetch")
def fetch_messages(
    request: FetchMsgCond, 
    session: Session = Depends(get_session)
    ):
    """
    user fetch messages from database
    if unseen_only is True, only fetch unseen messages
    """
    try:
        user_id = request.user_id
        unseen_only = request.unseen_only

        if unseen_only:
            msgs = session.exec(select(Message).where(
                Message.receiver_id == user_id, 
                Message.is_delivered == False)
                ).all()
        else:
            msgs = session.exec(select(Message).where(
                Message.receiver_id == user_id)
                ).all()

        if not msgs:
            return {"messages": []}

        for received_msgs in msgs:
            received_msgs.is_delivered = True
            session.add(received_msgs)
        session.commit()
        return {"messages": f"Message fetched: {len(msgs)}"}
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
