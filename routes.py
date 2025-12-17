from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, String
from typing import List, Optional
from datetime import datetime, timezone
from models import User, Message, UserTheme, Contact
from database import get_db
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from schemas import UserCreate, UserLogin, UserResponse, Token, KeyExchangeRequest, KeyExchangeResponse, UserThemeCreate, UserThemeResponse
from socketio_handler import user_socket_map
from datetime import timedelta
import shutil
import os
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def isoformat_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


@router.get("/test")
async def test_connection():
    return {"status": "ok", "message": "Backend is running"}


import re


def normalize_phone(phone: str) -> str:
    normalized = re.sub(r'[^\d]', '', phone)
    return normalized


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    normalized_phone = normalize_phone(user_data.phone)
    
    existing_user = db.query(User).filter(User.phone == normalized_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=normalized_phone,
        username=None,
        password_hash=hashed_password,
        public_key=user_data.public_key
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token_expires = timedelta(days=1)
    token_subject = new_user.username if new_user.username else str(new_user.id)
    access_token = create_access_token(
        data={"sub": token_subject}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    normalized_phone = normalize_phone(user_credentials.phone)
    user = authenticate_user(db, normalized_phone, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Логин или пароль неверен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(days=1)
    token_subject = user.username if user.username else str(user.id)
    access_token = create_access_token(
        data={"sub": token_subject}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=current_user.id, 
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        public_key=current_user.public_key,
        avatar_url=current_user.avatar_url,
        avatar_frame=current_user.avatar_frame,
        bio=current_user.bio,
        birthdate=current_user.birthdate
    )


@router.put("/users/me/username", response_model=UserResponse)
async def update_username(
    new_username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.username == new_username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    current_user.username = new_username
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id, 
        username=current_user.username, 
        public_key=current_user.public_key,
        avatar_url=current_user.avatar_url,
        avatar_frame=current_user.avatar_frame,
        bio=current_user.bio,
        birthdate=current_user.birthdate,
        last_seen=current_user.last_seen
    )


@router.put("/users/me/profile", response_model=UserResponse)
async def update_profile(
    bio: Optional[str] = None,
    birthdate: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if bio is not None:
        current_user.bio = bio if bio.strip() else None
    if birthdate is not None:
        current_user.birthdate = birthdate if birthdate.strip() else None
    
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        public_key=current_user.public_key,
        avatar_url=current_user.avatar_url,
        avatar_frame=current_user.avatar_frame,
        bio=current_user.bio,
        birthdate=current_user.birthdate,
        last_seen=current_user.last_seen
    )


@router.put("/users/me/bio", response_model=UserResponse)
async def update_bio(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        body = await request.json()
        bio = body.get('bio', '')
        current_user.bio = bio.strip() if bio and bio.strip() else None
        db.commit()
        db.refresh(current_user)
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            public_key=current_user.public_key,
            avatar_url=current_user.avatar_url,
            avatar_frame=current_user.avatar_frame,
            bio=current_user.bio,
            birthdate=current_user.birthdate,
            last_seen=current_user.last_seen
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/me/birthdate", response_model=UserResponse)
async def update_birthdate(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        body = await request.json()
        birthdate = body.get('birthdate', '')
        current_user.birthdate = birthdate.strip() if birthdate and birthdate.strip() else None
        db.commit()
        db.refresh(current_user)
        return UserResponse(
            id=current_user.id,
            username=current_user.username,
            public_key=current_user.public_key,
            avatar_url=current_user.avatar_url,
            avatar_frame=current_user.avatar_frame,
            bio=current_user.bio,
            birthdate=current_user.birthdate,
            last_seen=current_user.last_seen
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Avatar upload: user_id={current_user.id}, filename={file.filename}, content_type={file.content_type}")
    
    is_valid_image = (
        file.content_type and file.content_type.startswith('image/')
    ) or (
        file.filename and any(file.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
    )
    
    if not is_valid_image:
        logger.warning(f"Invalid file: {file.content_type}, filename={file.filename}")
        raise HTTPException(400, detail=f"File must be an image")
    
    extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4()}.{extension}"
    file_path = f"static/avatars/{filename}"
    
    logger.info(f"Saving to: {file_path}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved successfully: {file_path}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(500, detail=f"Error saving file: {str(e)}")
    
    base_url = str(request.base_url).rstrip("/")
    full_url = f"{base_url}/{file_path}"
    
    logger.info(f"Avatar URL: {full_url}")
    
    current_user.avatar_url = full_url
    db.commit()
    
    logger.info(f"Avatar updated in DB for user {current_user.id}")
    
    return {"avatar_url": full_url}


@router.put("/users/me/avatar-frame")
async def set_avatar_frame(
    frame: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    valid_frames = [
        "none", "fire", "rainbow", "purple"
    ]
    if frame not in valid_frames:
        raise HTTPException(400, detail=f"Invalid frame. Must be one of: {', '.join(valid_frames)}")
    
    current_user.avatar_frame = frame if frame != "none" else None
    db.commit()
    db.refresh(current_user)
    
    return {"avatar_frame": current_user.avatar_frame}


@router.get("/avatars/list")
async def get_avatars_list():
    avatars = [
        {"id": "1", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=1"},
        {"id": "2", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=2"},
        {"id": "3", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=3"},
        {"id": "4", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=4"},
        {"id": "5", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=5"},
        {"id": "6", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=6"},
        {"id": "7", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=7"},
        {"id": "8", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=8"},
        {"id": "9", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=9"},
        {"id": "10", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=10"},
        {"id": "11", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=11"},
        {"id": "12", "url": "https://api.dicebear.com/7.x/avataaars/svg?seed=12"},
    ]
    return {"avatars": avatars}


@router.get("/avatar-frames/list")
async def get_avatar_frames_list():
    frames = [
        {"id": "none", "name": "Без рамки", "color": "#000000"},
        {"id": "fire", "name": "Огненная", "color": "#FF4500"},
        {"id": "rainbow", "name": "Радужная", "color": "#FF0000"},
        {"id": "purple", "name": "Фиолетовая", "color": "#800080"},
    ]
    return {"frames": frames}


@router.put("/users/me/preset-avatar")
async def set_preset_avatar(
    avatar_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    avatars_response = await get_avatars_list()
    avatar = next((a for a in avatars_response["avatars"] if a["id"] == avatar_id), None)
    
    if not avatar:
        raise HTTPException(400, detail="Invalid avatar ID")
    
    current_user.avatar_url = avatar["url"]
    db.commit()
    db.refresh(current_user)
    
    return {"avatar_url": current_user.avatar_url}


@router.get("/users/search", response_model=List[UserResponse])
async def search_users(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if len(query) < 2:
        return []
    
    from sqlalchemy import or_, func
    
    search_conditions = [
        User.username.ilike(f"%{query}%"),
        User.first_name.ilike(f"%{query}%"),
        User.last_name.ilike(f"%{query}%"),
    ]
    
    full_name_search = func.lower(
        func.coalesce(User.first_name, '') + ' ' + func.coalesce(User.last_name, '')
    ).like(f"%{query.lower()}%")
    search_conditions.append(full_name_search)
        
    users = db.query(User).filter(
        or_(*search_conditions),
        User.id != current_user.id
    ).limit(20).all()
    
    query_lower = query.lower()
    filtered_users = []
    for user in users:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip().lower()
        if (user.username and query_lower in (user.username or '').lower()) or \
           (user.first_name and query_lower in (user.first_name or '').lower()) or \
           (user.last_name and query_lower in (user.last_name or '').lower()) or \
           query_lower in full_name:
            filtered_users.append(user)
    
    users = filtered_users[:20]
    
    return [
        UserResponse(
            id=user.id, 
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            public_key=user.public_key,
            avatar_url=user.avatar_url,
            avatar_frame=user.avatar_frame,
            bio=user.bio,
            birthdate=user.birthdate,
            last_seen=user.last_seen,
            is_online=user.id in user_socket_map and len(user_socket_map[user.id]) > 0
        ) for user in users
    ]


@router.get("/users/check_availability")
async def check_availability(
    username: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    return {"available": user is None}


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.id != current_user.id).all()
    return [
        UserResponse(
            id=user.id, 
            username=user.username, 
            public_key=user.public_key,
            avatar_url=user.avatar_url,
            avatar_frame=user.avatar_frame,
            phone=user.phone
        ) for user in users
    ]


@router.post("/keys/exchange", response_model=KeyExchangeResponse)
async def exchange_key(
    key_request: KeyExchangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == key_request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.public_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have a public key"
        )
    
    return KeyExchangeResponse(user_id=user.id, public_key=user.public_key)


@router.get("/chats/active", response_model=List[UserResponse])
async def get_active_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sent_to = db.query(Message.receiver_id).filter(
        and_(
            Message.sender_id == current_user.id,
            Message.receiver_id != current_user.id
        )
    ).distinct()
    received_from = db.query(Message.sender_id).filter(
        and_(
            Message.receiver_id == current_user.id,
            Message.sender_id != current_user.id
        )
    ).distinct()
    
    chat_user_ids = set()
    for row in sent_to:
        if row[0] != current_user.id:
            chat_user_ids.add(row[0])
    for row in received_from:
        if row[0] != current_user.id:
            chat_user_ids.add(row[0])
    
    if not chat_user_ids:
        return []
    
    users = db.query(User).filter(
        and_(
            User.id.in_(chat_user_ids),
            User.id != current_user.id
        )
    ).all()
    
    contacts = db.query(Contact).filter(Contact.owner_id == current_user.id).all()
    contact_names = {contact.contact_id: contact.local_name for contact in contacts}
    
    result = []
    for user in users:
        last_message = db.query(Message).filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user.id),
                and_(Message.sender_id == user.id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.timestamp.desc()).first()
        
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            public_key=user.public_key,
            avatar_url=user.avatar_url,
            avatar_frame=user.avatar_frame,
            bio=user.bio,
            birthdate=user.birthdate,
            last_seen=user.last_seen,
            is_online=user.id in user_socket_map and len(user_socket_map[user.id]) > 0,
            last_message=last_message.encrypted_content if last_message else None,
            last_message_time=last_message.timestamp if last_message else None,
            last_message_sender_id=last_message.sender_id if last_message else None,
            last_message_type=last_message.message_type if last_message else None,
            local_name=contact_names.get(user.id)
        ))
    
    return result


@router.get("/users/{user_id}/profile", response_model=UserResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, detail="User not found")
    
    is_online = user_id in user_socket_map and len(user_socket_map[user_id]) > 0
    
    avatar_url = None
    if hasattr(user, 'avatar_visibility'):
        avatar_visibility = user.avatar_visibility or 'all'
        if avatar_visibility == 'all':
            avatar_url = user.avatar_url
        elif avatar_visibility == 'contacts':
            has_messages = db.query(Message).filter(
                or_(
                    and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
                    and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
                )
            ).first() is not None
            if has_messages:
                avatar_url = user.avatar_url
        elif avatar_visibility == 'except':
            import json
            exceptions = []
            if hasattr(user, 'avatar_visibility_exceptions') and user.avatar_visibility_exceptions:
                try:
                    exceptions = json.loads(user.avatar_visibility_exceptions)
                except:
                    exceptions = []
            if current_user.id not in exceptions:
                avatar_url = user.avatar_url
    else:
        avatar_url = user.avatar_url
    
    show_last_seen = True
    show_online_status = True
    if hasattr(user, 'show_last_seen'):
        show_last_seen = user.show_last_seen if user.show_last_seen is not None else True
    if hasattr(user, 'show_online_status'):
        show_online_status = user.show_online_status if user.show_online_status is not None else True
    
    local_name = None
    contact = db.query(Contact).filter(
        and_(Contact.owner_id == current_user.id, Contact.contact_id == user_id)
    ).first()
    if contact:
        local_name = contact.local_name
    
    return UserResponse(
        id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        local_name=local_name,
        public_key=user.public_key,
        avatar_url=avatar_url,
        avatar_frame=user.avatar_frame,
        bio=user.bio,
        birthdate=user.birthdate,
        last_seen=user.last_seen if show_last_seen else None,
        is_online=is_online if show_online_status else None
    )


@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"File upload: user_id={current_user.id}, filename={file.filename}, content_type={file.content_type}")
    
    is_valid_image = (
        file.content_type and file.content_type.startswith('image/')
    ) or (
        file.filename and any(file.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
    )
    
    if not is_valid_image:
        raise HTTPException(400, detail="File must be an image")
    
    extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{extension}"
    file_path = f"static/uploads/{filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved: {file_path}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        raise HTTPException(500, detail=f"Error saving file: {str(e)}")
    
    base_url = str(request.base_url).rstrip("/")
    full_url = f"{base_url}/{file_path}"
    
    return {"url": full_url, "filename": filename}


@router.get("/chats/{target_user_id}/messages")
async def get_chat_history(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == target_user_id),
            and_(Message.sender_id == target_user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    
    return [
        {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "encrypted_content": msg.encrypted_content,
            "message_type": msg.message_type,
            "media_url": msg.media_url,
            "reply_to_message_id": msg.reply_to_message_id,
            "timestamp": isoformat_utc(msg.timestamp),
            "is_read": msg.is_read
        } for msg in messages
    ]


@router.delete("/chats/{target_user_id}/messages")
async def clear_chat(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deleted_count = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == target_user_id),
            and_(Message.sender_id == target_user_id, Message.receiver_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    
    db.commit()
    
    logger.info(f"User {current_user.id} cleared chat with user {target_user_id}. Deleted {deleted_count} messages.")
    
    return {"deleted_count": deleted_count, "message": "Chat cleared successfully"}


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"🗑️ Delete request: message_id={message_id} (type: {type(message_id)}), user_id={current_user.id}")
    
    if message_id is None or message_id <= 0:
        logger.warning(f"Invalid message_id: {message_id}")
        raise HTTPException(400, detail="Invalid message ID")
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        logger.warning(f"Message {message_id} not found in database")
        raise HTTPException(404, detail="Message not found")
    
    if message.sender_id != current_user.id:
        logger.warning(f"User {current_user.id} attempted to delete message {message_id} from user {message.sender_id}")
        raise HTTPException(403, detail="You can only delete your own messages")
    
    if message.media_url:
        try:
            import os
            if message.media_url.startswith('/static/'):
                file_path = message.media_url.replace('/static/', 'static/')
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted media file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete media file: {e}")
    
    db.delete(message)
    db.commit()
    
    logger.info(f"✅ User {current_user.id} deleted message {message_id}")
    
    return {"message": "Message deleted successfully"}


@router.put("/users/me/privacy")
async def update_privacy_settings(
    avatar_visibility: Optional[str] = None,
    avatar_visibility_exceptions: Optional[str] = None,
    show_read_receipts: Optional[bool] = None,
    show_last_seen: Optional[bool] = None,
    show_online_status: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import json
    
    if avatar_visibility is not None:
        if avatar_visibility not in ['all', 'contacts', 'nobody', 'except']:
            raise HTTPException(400, detail="Invalid avatar_visibility value")
        current_user.avatar_visibility = avatar_visibility
    
    if avatar_visibility_exceptions is not None:
        try:
            exceptions_list = json.loads(avatar_visibility_exceptions)
            if isinstance(exceptions_list, list):
                current_user.avatar_visibility_exceptions = avatar_visibility_exceptions
        except json.JSONDecodeError:
            raise HTTPException(400, detail="Invalid avatar_visibility_exceptions format")
    
    if show_read_receipts is not None:
        current_user.show_read_receipts = show_read_receipts
    
    if show_last_seen is not None:
        current_user.show_last_seen = show_last_seen
    
    if show_online_status is not None:
        current_user.show_online_status = show_online_status
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "avatar_visibility": current_user.avatar_visibility,
        "avatar_visibility_exceptions": current_user.avatar_visibility_exceptions,
        "show_read_receipts": current_user.show_read_receipts,
        "show_last_seen": current_user.show_last_seen,
        "show_online_status": current_user.show_online_status,
    }


@router.get("/users/me/privacy")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "avatar_visibility": current_user.avatar_visibility or "all",
        "avatar_visibility_exceptions": current_user.avatar_visibility_exceptions,
        "show_read_receipts": current_user.show_read_receipts if current_user.show_read_receipts is not None else True,
        "show_last_seen": current_user.show_last_seen if current_user.show_last_seen is not None else True,
        "show_online_status": current_user.show_online_status if current_user.show_online_status is not None else True,
    }


@router.post("/chats/{target_user_id}/mark-read")
async def mark_messages_as_read(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from socketio_handler import user_socket_map, notify_messages_read
    
    messages_to_update = db.query(Message).filter(
        and_(
            Message.sender_id == target_user_id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        )
    ).all()
    
    updated_count = len(messages_to_update)
    
    if updated_count > 0:
        for msg in messages_to_update:
            msg.is_read = True
        
        db.commit()
        
        message_ids = [msg.id for msg in messages_to_update]
        await notify_messages_read(target_user_id, message_ids, current_user.id)
    
    logger.info(f"User {current_user.id} marked {updated_count} messages from user {target_user_id} as read")
    
    return {"marked_count": updated_count, "message": "Messages marked as read"}


@router.get("/chats/{target_user_id}/media")
async def get_chat_media(
    target_user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        Message.message_type == "image",
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == target_user_id),
            and_(Message.sender_id == target_user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.timestamp.desc()).all()
    
    return [
        {
            "id": msg.id,
            "media_url": msg.media_url,
            "timestamp": isoformat_utc(msg.timestamp),
            "sender_id": msg.sender_id
        } for msg in messages
    ]


@router.post("/users/me/themes", response_model=UserThemeResponse, status_code=status.HTTP_201_CREATED)
async def create_user_theme(
    theme_data: UserThemeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_theme = UserTheme(
        user_id=current_user.id,
        name=theme_data.name,
        primary_color=theme_data.primary_color,
        background_color=theme_data.background_color,
        bubble_color_me=theme_data.bubble_color_me,
        bubble_color_other=theme_data.bubble_color_other,
        text_color=theme_data.text_color,
        secondary_text_color=theme_data.secondary_text_color,
        brightness=theme_data.brightness,
        wallpaper_url=theme_data.wallpaper_url,
        wallpaper_blur=theme_data.wallpaper_blur,
    )
    db.add(new_theme)
    db.commit()
    db.refresh(new_theme)
    return new_theme


@router.get("/users/me/themes", response_model=List[UserThemeResponse])
async def get_user_themes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    themes = db.query(UserTheme).filter(UserTheme.user_id == current_user.id).order_by(UserTheme.created_at.desc()).all()
    return themes


@router.put("/users/me/themes/{theme_id}", response_model=UserThemeResponse)
async def update_user_theme(
    theme_id: int,
    theme_data: UserThemeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    theme = db.query(UserTheme).filter(
        UserTheme.id == theme_id,
        UserTheme.user_id == current_user.id
    ).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    theme.name = theme_data.name
    theme.primary_color = theme_data.primary_color
    theme.background_color = theme_data.background_color
    theme.bubble_color_me = theme_data.bubble_color_me
    theme.bubble_color_other = theme_data.bubble_color_other
    theme.text_color = theme_data.text_color
    theme.secondary_text_color = theme_data.secondary_text_color
    theme.brightness = theme_data.brightness
    theme.wallpaper_url = theme_data.wallpaper_url
    theme.wallpaper_blur = theme_data.wallpaper_blur
    
    db.commit()
    db.refresh(theme)
    return theme


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        db.query(Message).filter(
            or_(Message.sender_id == current_user.id, Message.receiver_id == current_user.id)
        ).delete()
        
        db.query(UserTheme).filter(UserTheme.user_id == current_user.id).delete()
        
        if current_user.avatar_url:
            import os
            avatar_filename = os.path.basename(current_user.avatar_url)
            avatar_path = os.path.join("static", "avatars", avatar_filename)
            if os.path.exists(avatar_path):
                try:
                    os.remove(avatar_path)
                except Exception as e:
                    logger.warning(f"Failed to delete avatar file {avatar_path}: {e}")
        
        db.delete(current_user)
        db.commit()
        
        logger.info(f"User account {current_user.id} ({current_user.username}) deleted successfully")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user account {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")


@router.delete("/users/me/themes/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_theme(
    theme_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    theme = db.query(UserTheme).filter(
        UserTheme.id == theme_id,
        UserTheme.user_id == current_user.id
    ).first()
    
    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found"
        )
    
    db.delete(theme)
    db.commit()
    return None


@router.put("/contacts/{contact_id}/local-name")
async def set_contact_local_name(
    contact_id: int,
    local_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contact_user = db.query(User).filter(User.id == contact_id).first()
    if not contact_user:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    if contact_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot set local name for yourself")
    
    contact = db.query(Contact).filter(
        and_(Contact.owner_id == current_user.id, Contact.contact_id == contact_id)
    ).first()
    
    if contact:
        contact.local_name = local_name.strip() if local_name.strip() else None
        contact.updated_at = datetime.now(timezone.utc)
    else:
        contact = Contact(
            owner_id=current_user.id,
            contact_id=contact_id,
            local_name=local_name.strip() if local_name.strip() else None
        )
        db.add(contact)
    
    db.commit()
    db.refresh(contact)
    
    return {"contact_id": contact_id, "local_name": contact.local_name}


@router.delete("/contacts/{contact_id}/local-name")
async def delete_contact_local_name(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contact = db.query(Contact).filter(
        and_(Contact.owner_id == current_user.id, Contact.contact_id == contact_id)
    ).first()
    
    if contact:
        db.delete(contact)
        db.commit()
    
    return {"message": "Local name deleted"}

