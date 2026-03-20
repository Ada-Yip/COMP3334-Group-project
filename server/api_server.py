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
from .security_service import (
    get_current_user,
    hash_password, 
    verify_password,
    create_user_session,
    )
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
    except Exception:
        session.rollback()
        logger.exception("Error registering user")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    logger.info(f"User {username_input} registered successfully")
    return {
        "message": f"User {username_input} registered successfully",
        "data": {"user_id": new_user.user_id, "username": username_input},
    }

class LoginReq(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(
        login_req: LoginReq,
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

        token = create_user_session(current_user.user_id, session)
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Error logging in")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    return {"message": "Login successful", 
            "data": {
                "token": token, 
                "user_id": current_user.user_id, 
                "username": current_user.username_db
                }
            }

@app.post("/logout")
def logout(
        authorization: str = Header(None),
        session: Session = Depends(get_session),
):
    """logout user from database, invalidate session token"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ")[1]
        logged_in_session = get_valid_session_from_db(token, session)
        if logged_in_session:
            session.delete(logged_in_session)
            session.commit()
            logger.info(f"Session {token} invalidated successfully")
            logger.info(f"User {logged_in_session.user_id} logged out successfully")
        return {"message": "Logout successful"}
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Error logging out")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/users/{user_id}/public_key")
def get_user_public_key(
        user: User = Depends(get_current_user),
):
    """get user public key from database(for current user)"""
    return {"public_key": user.public_key_db}  #TODO: add validation to key changes?


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
    except HTTPException:
        raise
    except Exception:
        session.rollback()
        logger.exception("Error sending message")
        raise HTTPException(status_code=500, detail="Internal Server Error")


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
        logger.exception("Error fetching messages")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
