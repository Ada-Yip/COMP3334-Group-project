"""
api and enter point
"""
from datetime import datetime, timezone #JJ
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlmodel import Session, select
from .database import (
    User,
    Message,
    FriendRequest,  #JJ
    Friend,         
    BlockedUser,     #JJ
    init_db,
    get_session,
    get_valid_user_by_id,
    get_valid_user_by_username,
    check_password,
    get_valid_session_from_db, remove_expired_messages,
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
import time

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
        user_id: int,
        session: Session = Depends(get_session),
):
    """get user public key from database(for current user)"""
    target_user = get_valid_user_by_id(user_id, session=session)
    return {"public_key": target_user.public_key_db}  #TODO: add validation to key changes?


#=======Message API=======

# Send Message Request
class SendMsgReq(BaseModel):
    receiver_username: str
    ciphertext: str
    nonce: str
    age: int


@app.post("/messages/send")      ### JJ added frd/block check ###
def send_message(
        req: SendMsgReq,
        user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
)->dict:
    """send message to database"""
    try:
        #check if receiver exists
        receiver = req.receiver_username.strip()
        receiver = get_valid_user_by_username(username=receiver, session=session)
        
        # ========== FRIEND AND BLOCK CHECKS ==========
        # Check if receiver has blocked the sender
        block_check = session.exec(
            select(BlockedUser).where(
                BlockedUser.user_id == receiver.user_id,
                BlockedUser.blocked_user_id == user.user_id
            )
        ).first()
        if block_check:
            raise HTTPException(status_code=403, detail="You are blocked by this user")
        
        # Check if sender and receiver are friends (accepted request)
        friend_check = session.exec(select(Friend).where(
            Friend.user_id == user.user_id,
            Friend.friend_id == receiver.user_id
        )).first()
        if not friend_check:
            raise HTTPException(status_code=403, detail="You are not friends with this user")
        # ========== END CHECKS ==========
        
        msg = Message(
            sender_id=user.user_id, sender_username_db=user.username_db,
            receiver_id=receiver.user_id, receiver_username_db=receiver.username_db,
            ciphertext=req.ciphertext,
            nonce=req.nonce,
            timestamp=int(time.time()),
            age=req.age,
            )
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
        #=========unseen_only=true=========
        unseen_msgs = session.exec(
            select(Message).where(
                Message.receiver_id == user.user_id,
                Message.is_delivered == False
            )
        ).all()

        unseen_messages_count = len(unseen_msgs)
        for m in unseen_msgs:
            m.is_delivered = True

        messages_list_unseen = [
            {
                "sender_username": m.sender_username_db,
                "receiver_username": m.receiver_username_db,
                "ciphertext": m.ciphertext if m.age == 0 or m.age - (int(time.time()) - m.timestamp) >= 0 else "0",
                "nonce": m.nonce,
                "timestamp": m.timestamp,
                "age": m.age - (int(time.time()) - m.timestamp) if m.age > 0 else 0,
            }
            for m in unseen_msgs
        ]

        if unseen_only:
            remove_expired_messages(session)
            session.commit()
            return {
                "data": {
                    "messages": messages_list_unseen,
                    "unseen_count": unseen_messages_count,
                }
            }

        #=========unseen_only=false=========
        msgs_all = session.exec(
            select(Message).where(Message.receiver_id == user.user_id)
        ).all()

        messages_list_all = [
            {
                "sender_username": m.sender_username_db,
                "receiver_username": m.receiver_username_db,
                "ciphertext": m.ciphertext if m.age == 0 or m.age - (int(time.time()) - m.timestamp) >= 0 else "0",
                "nonce": m.nonce,
                "timestamp": m.timestamp,
                "age": m.age - (int(time.time()) - m.timestamp) if m.age > 0 else 0,
            }
            for m in msgs_all
        ]

        remove_expired_messages(session)
        session.commit()
        return {
            "data": {
                "messages": messages_list_all,
                "unseen_count": unseen_messages_count,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.exception("Error fetching messages")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# JJ friend
class FriendRequestReq(BaseModel):
    to_username: str

class FriendRequestActionReq(BaseModel):
    request_id: int
    action: str #accept, decline

class RemoveFriendReq(BaseModel):
    friend_username: str

class BlockUserReq(BaseModel):
    block_username: str

# edited friend request logic ###
@app.post("/friend-requests/respond")
def respond_friend_request(
    req: FriendRequestActionReq,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Respond to a pending friend request."""
    friend_req = session.get(FriendRequest, req.request_id)
    if not friend_req or friend_req.to_user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Request not found or not authorized")
    if friend_req.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    if req.action == "accept":
        friend_req.status = "accepted"
        link1 = Friend(user_id=current_user.user_id, friend_id=friend_req.from_user_id)
        link2 = Friend(user_id=friend_req.from_user_id, friend_id=current_user.user_id)
        session.add(link1)
        session.add(link2)
        message = "Friend request accepted"

    elif req.action == "decline":
        friend_req.status = "declined"
        message = "Friend request declined"
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    friend_req.updated_at = int(time.time())
    session.add(friend_req)
    session.commit()
    return {"message": message}

############ JJ Send friend request ################
@app.post("/friend-requests/send")
def send_friend_request(
    req: FriendRequestReq,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Send a friend request to another user."""
    # Find target user
    target = get_valid_user_by_username(req.to_username.strip(), session)
    if target.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check if already friends 
    friend_check = session.exec(select(Friend).where(
        Friend.user_id == current_user.user_id,
        Friend.friend_id == target.user_id
    )).first()
    if friend_check:
        raise HTTPException(status_code=400, detail="Already friends")

    existing_pending = session.exec(select(FriendRequest).where(
        ((FriendRequest.from_user_id == current_user.user_id) & (FriendRequest.to_user_id == target.user_id)) |
        ((FriendRequest.from_user_id == target.user_id) & (FriendRequest.to_user_id == current_user.user_id)),
        FriendRequest.status == "pending"
    )).first()
    if existing_pending:
        raise HTTPException(status_code=400, detail="Friend request already pending")

    # Check if blocked
    block_check = session.exec(
        select(BlockedUser).where(
            (BlockedUser.user_id == target.user_id) & (BlockedUser.blocked_user_id == current_user.user_id)
        )
    ).first()
    if block_check:
        raise HTTPException(status_code=403, detail="You are blocked by this user")
    
    # Create request
    new_req = FriendRequest(
        from_user_id=current_user.user_id,
        to_user_id=target.user_id,
        status="pending"
    )
    session.add(new_req)
    session.commit()
    return {"message": "Friend request sent"}

############ JJ List recieved friend request ################
@app.get("/friend-requests/received")
def get_received_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List pending friend requests sent to current user."""
    requests = session.exec(
        select(FriendRequest).where(
            FriendRequest.to_user_id == current_user.user_id,
            FriendRequest.status == "pending"
        )
    ).all()
    
    result = []
    for r in requests:
        from_user = session.exec(select(User).where(User.user_id == r.from_user_id)).first()
        if from_user:
            result.append({
                "id": r.id,
                "from_username": from_user.username_db,
                "created_at": r.created_at  ###
            })
    
    return {"requests": result}

############ JJ List sent friend request ################
@app.get("/friend-requests/sent")
def get_sent_requests(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List pending friend requests sent by current user."""
    requests = session.exec(
        select(FriendRequest).where(
            FriendRequest.from_user_id == current_user.user_id,
            FriendRequest.status == "pending"
        )
    ).all()
    
    result = []
    for r in requests:
        to_user = session.exec(select(User).where(User.user_id == r.to_user_id)).first()
        if to_user:
            result.append({
                "id": r.id,
                "to_username": to_user.username_db,
                "created_at": r.created_at.isoformat()
            })
    
    return {"requests": result}

############ JJ List friend accepeted ################
@app.get("/friends")
def get_friends(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List all accepted friends."""
    # Get all accepted requests where current_user is either sender or receiver
    friends = session.exec(
        select(Friend).where(Friend.user_id == current_user.user_id)
    ).all()
    result = []
    for r in friends:
        friend = session.get(User, r.friend_id)
        result.append({
            "user_id": friend.user_id,
            "username": friend.username_db
        })
    return {"friends": result}

############ JJ Remove friend  ################
@app.post("/friends/remove")
def remove_friend(
    req: RemoveFriendReq,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Remove an existing friend (delete the accepted friend request)."""
    target = get_valid_user_by_username(req.friend_username.strip(), session)
    
    #link1 for current user, link2 for target user
    link1 = session.exec(select(Friend).where(Friend.user_id == current_user.user_id, Friend.friend_id == target.user_id)).first()
    link2 = session.exec(select(Friend).where(Friend.user_id == target.user_id, Friend.friend_id == current_user.user_id)).first()

    if not link1 or not link2:
        raise HTTPException(status_code=404, detail="Friend not found")
    session.delete(link1)
    session.delete(link2)
    session.commit()
    return {"message": "Friend removed"}

############ JJ Block user  ################
@app.post("/users/block")
def block_user(
    req: BlockUserReq,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Block another user."""
    target = get_valid_user_by_username(req.block_username.strip(), session)
    if target.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    
    # Check if already blocked
    existing = session.exec(
        select(BlockedUser).where(
            BlockedUser.user_id == current_user.user_id,
            BlockedUser.blocked_user_id == target.user_id
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already blocked")
    
    try:
        # Remove friend link
        link1 = session.exec(select(Friend).where(Friend.user_id == current_user.user_id, Friend.friend_id == target.user_id)).first()
        link2 = session.exec(select(Friend).where(Friend.user_id == target.user_id, Friend.friend_id == current_user.user_id)).first()
        if link1:
            session.delete(link1)
        if link2:
            session.delete(link2)
    except Exception:
        session.rollback()
        logger.exception("Error removing friend when blocking user")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    # Change pending friend requests to declined
    friend_req = session.exec(select(FriendRequest).where(
        ((FriendRequest.from_user_id == current_user.user_id) & (FriendRequest.to_user_id == target.user_id)) |
        ((FriendRequest.from_user_id == target.user_id) & (FriendRequest.to_user_id == current_user.user_id)),
        FriendRequest.status == "pending"
    )).first()
    if friend_req:
        friend_req.status = "declined"
        friend_req.updated_at = int(time.time())
        session.add(friend_req)
    
    # Add block
    block = BlockedUser(user_id=current_user.user_id, blocked_user_id=target.user_id)
    session.add(block)
    session.commit()
    return {"message": "User blocked"}

############ JJ Unblock user  ################
@app.post("/users/unblock")
def unblock_user(
    req: BlockUserReq,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Unblock a previously blocked user."""
    target = get_valid_user_by_username(req.block_username.strip(), session)
    block = session.exec(
        select(BlockedUser).where(
            BlockedUser.user_id == current_user.user_id,
            BlockedUser.blocked_user_id == target.user_id
        )
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="User not blocked")
    session.delete(block)
    session.commit()
    return {"message": "User unblocked"}