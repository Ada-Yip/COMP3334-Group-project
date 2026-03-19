"""
api and enter point
"""

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlmodel import Session, select
from .database import (
    User, 
    Message, 
    init_db, 
    get_session, 
    get_valid_user_by_id, 
    check_password,
    get_valid_session_from_db
)
from pydantic import BaseModel
from contextlib import asynccontextmanager
from .security_service import get_current_user, hash_password, verify_password
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
        password_hashed = hash_password(password_input)
        new_user = User(username_db=username_input, password_hash=password_hashed, public_key_db=public_key_input)

        #check if user already exists
        existing_user = session.exec(select(User).where(User.username_db == username_input)).first()
        if existing_user is not None:
            logger.error(f"User {username_input} already exists")
            session.rollback()
            raise HTTPException(status_code=400, detail="User already exists")
        
        #check if password is valid
        if not check_password(password_input):
            logger.error(f"Password requirement not satisfied for user {username_input}")
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
    session.refresh(new_user)
    logger.info(f"User {username_input} registered successfully")
    return {
        "message": f"User {username_input} registered successfully",
        "data": {"user_id": new_user.user_id, "username": username_input},
    }

@app.post("/login")
def login(
        login_req: RegisterReq,
        session: Session = Depends(get_session)
    ):
    try:
        username_input = login_req.username.strip()
        password_input = login_req.password.strip()

        current_user = session.exec(select(User).where(User.username_db == username_input)).first()
        if current_user is None:
            logger.error(f"Username or Password incorrect.")
            session.rollback()
            raise HTTPException(status_code=400, detail="Username or Password incorrect.")

        # verify password using bcrypt
        if not verify_password(password_input, current_user.password_hash):
            logger.error(f"Username or Password incorrect.")
            session.rollback()
            raise HTTPException(status_code=400, detail="Username or Password incorrect.")

        # TODO: issue session token and return to client in future step
    except Exception as e:
        session.rollback()
        logger.error(f"Error logging in: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"message": "Login successful"}
#  TODO: Yeah I still need time to figure out how to code "login status".



@app.get("/users/{user_id}/public_key")
def get_user_public_key(
    user: User = Depends(get_current_user), 
    ):
    """get user public key from database(for current user)"""
    return {"public_key": user.public_key_db}      #TODO: add validation to key changes?

#=======Message API=======

# Send Message Request
class SendMsgReq(BaseModel):
    receiver_username: str
    ciphertext: str
    nonce: str

@app.post("/messages/send")
def send_message(
    req: SendMsgReq,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
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
            sender_id=user.user_id, sender_username_db=user.username_db,
            receiver_id=receiver.user_id, receiver_username_db=receiver.username_db,
            ciphertext=req.ciphertext, 
            nonce=req.nonce)
        session.add(msg)
        session.commit()
        logger.info(f"Message from {user.username_db} to {req.receiver_username} queued successfully")
        return {"message": f"Message from {user.username_db} to {req.receiver_username} queued successfully"}
    except Exception as e:
        session.rollback()
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=400, detail=f"Bad Request: {e}")

@app.post("/messages/fetch")
def fetch_messages(
    unseen_only: bool = False,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    ):
    """
    Current user fetch messages from database.
    If unseen_only is True, only fetch unseen messages.
    """
    try:
        if unseen_only:
            msgs = session.exec(select(Message).where(
                Message.receiver_id == user.user_id, 
                Message.is_delivered == False)
                ).all()
        else:
            msgs = session.exec(select(Message).where(
                Message.receiver_id == user.user_id)
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

