from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime, timezone


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    password: str
    public_key: Optional[str] = None


class UserLogin(BaseModel):
    phone: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    public_key: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_frame: Optional[str] = None
    bio: Optional[str] = None
    birthdate: Optional[str] = None
    last_seen: Optional[datetime] = None
    is_online: Optional[bool] = None
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    last_message_sender_id: Optional[int] = None
    last_message_type: Optional[str] = None
    local_name: Optional[str] = None

    @field_serializer('last_seen', 'last_message_time')
    def serialize_datetime_utc(self, value: Optional[datetime], _info) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            dt_utc = value.replace(tzinfo=timezone.utc)
        else:
            dt_utc = value.astimezone(timezone.utc)
        return dt_utc.isoformat().replace('+00:00', 'Z')

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class KeyExchangeRequest(BaseModel):
    user_id: int


class KeyExchangeResponse(BaseModel):
    user_id: int
    public_key: str


class UserThemeCreate(BaseModel):
    name: str
    primary_color: str
    background_color: str
    bubble_color_me: str
    bubble_color_other: str
    text_color: str
    secondary_text_color: str
    brightness: str
    wallpaper_url: str | None = None
    wallpaper_blur: str | None = "0.0"


class UserThemeResponse(BaseModel):
    id: int
    name: str
    primary_color: str
    background_color: str
    bubble_color_me: str
    bubble_color_other: str
    text_color: str
    secondary_text_color: str
    brightness: str
    wallpaper_url: str | None
    wallpaper_blur: str | None
    created_at: datetime

    class Config:
        from_attributes = True

