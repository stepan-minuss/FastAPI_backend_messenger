from datetime import datetime, timedelta
from typing import Optional
import hashlib
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from models import User
from database import get_db

SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def _preprocess_password(password: str) -> bytes:
    if password is None:
        raise ValueError("Password cannot be None")
    
    password_bytes = str(password).encode('utf-8')
    
    if len(password_bytes) > 72:
        sha256_hash = hashlib.sha256(password_bytes).digest()
        return sha256_hash
    
    return password_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    
    processed_password_bytes = _preprocess_password(plain_password)
    
    try:
        return bcrypt.checkpw(processed_password_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    if password is None:
        raise ValueError("Password cannot be None")
    
    processed_password_bytes = _preprocess_password(str(password))
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(processed_password_bytes, salt)
    
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def normalize_phone(phone: str) -> str:
    import re
    normalized = re.sub(r'[^\d]', '', phone)
    return normalized


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        normalized_phone = normalize_phone(username)
        user = db.query(User).filter(User.phone == normalized_phone).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == subject).first()
    if not user:
        try:
            user_id = int(subject)
            user = db.query(User).filter(User.id == user_id).first()
        except (ValueError, TypeError):
            pass
    
    if user is None:
        raise credentials_exception
    return user


def get_user_from_token(token: str, db: Session) -> Optional[User]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject: str = payload.get("sub")
        if subject is None:
            return None
        
        user = db.query(User).filter(User.username == subject).first()
        if not user:
            try:
                user_id = int(subject)
                user = db.query(User).filter(User.id == user_id).first()
            except (ValueError, TypeError):
                pass
        
        return user
    except JWTError:
        return None

