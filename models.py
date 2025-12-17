from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    public_key = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    avatar_frame = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    birthdate = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_admin = Column(Boolean, default=False, nullable=False)

    avatar_visibility = Column(String, default="all", nullable=False)
    avatar_visibility_exceptions = Column(Text, nullable=True)
    show_read_receipts = Column(Boolean, default=True, nullable=False)
    show_last_seen = Column(Boolean, default=True, nullable=False)
    show_online_status = Column(Boolean, default=True, nullable=False)

    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    encrypted_content = Column(Text, nullable=False)
    message_type = Column(String, default="text", nullable=False)
    media_url = Column(String, nullable=True)
    reply_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")


class UserTheme(Base):
    __tablename__ = "user_themes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    primary_color = Column(String, nullable=False)
    background_color = Column(String, nullable=False)
    bubble_color_me = Column(String, nullable=False)
    bubble_color_other = Column(String, nullable=False)
    text_color = Column(String, nullable=False)
    secondary_text_color = Column(String, nullable=False)
    brightness = Column(String, nullable=False)
    wallpaper_url = Column(String, nullable=True)
    wallpaper_blur = Column(String, nullable=True, default="0.0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    local_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", foreign_keys=[owner_id])
    contact = relationship("User", foreign_keys=[contact_id])

    __table_args__ = (
        UniqueConstraint('owner_id', 'contact_id', name='uq_owner_contact'),
    )

