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

# Request Acc, using pydantic
class RegisterReq(BaseModel):
    username: str
    password: str

# Send Message Request
class SendMsgReq(BaseModel):
    sender_id: int
    sender_username: str
    receiver_id: int
    receiver_username: str
    receiver: str
    ciphertext: str
    nonce: str

# --- API 端點 ---
<<<<<<< HEAD
#TODO: add function to generate public key, hash pw
=======
#  TODO: add function to generate public key
#  Sam: for client-server encryption? We can leave it in next phase.
>>>>>>> a36b31aaa89006cb07e9477f4481b62e8ba49e03
@app.post("/register")
def register(
    req: RegisterReq, 
    session: Session = Depends(get_session)
    ):
    """register user to database"""
    try:
        username_input = req.username.strip()
        password_input = req.password.strip()
        new_user = User(username_db=username_input, password_hash=password_input, public_key_db="dummy_key")

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
    except Exception as e:
        session.rollback()
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: {e}")
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

@app.post("/messages/send")
def send_message(
    req: SendMsgReq, 
    session: Session = Depends(get_session)
    ):
    """send message to database"""
    try:
        msg = Message(
            sender_id=req.sender_id, sender_username_db=req.sender_username,
            receiver_id=req.receiver_id, receiver_username_db=req.receiver_username,
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

@app.get("/messages/fetch/{user_id}")
def fetch_messages(
    user_id: int = Depends(get_valid_user_id), 
    session: Session = Depends(get_session)
    ):
    """user fetch messages from database"""
    msgs = session.exec(select(Message).where(
        Message.receiver_id == user_id, 
        Message.is_delivered == False)
        ).all()

    # Return a stable response shape that client code can parse reliably.
    if not msgs:
        return {"messages": []}

    #  Sam: Now the server should return message body when client use fetch_message().

    serialized_messages = [
        {
            "message_id": msg.message_id,
            "sender_id": msg.sender_id,
            "sender_username": msg.sender_username,
            "receiver_id": msg.receiver_id,
            "receiver_username": msg.receiver_username,
            "ciphertext": msg.ciphertext,
            "nonce": msg.nonce,
            "is_delivered": msg.is_delivered,
        }
        for msg in msgs
    ]

    for received_msgs in msgs:
        received_msgs.is_delivered = True
        session.add(received_msgs)
    session.commit()
    return {"messages": serialized_messages}
