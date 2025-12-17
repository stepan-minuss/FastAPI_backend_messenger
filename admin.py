from sqladmin import Admin, ModelView
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import User, Message
from database import engine
from datetime import datetime, timezone


class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.username,
        User.avatar_url,
        User.bio,
        User.birthdate,
        User.last_seen,
        User.is_admin,
    ]
    
    column_searchable_list = [User.username, User.bio]
    
    column_sortable_list = [User.id, User.username, User.last_seen, User.is_admin]
    
    form_columns = [
        User.username,
        User.bio,
        User.birthdate,
        User.avatar_url,
        User.is_admin,
    ]
    
    column_labels = {
        User.id: "ID",
        User.username: "Имя пользователя",
        User.avatar_url: "Аватар",
        User.bio: "О себе",
        User.birthdate: "Дата рождения",
        User.last_seen: "Последний вход",
        User.is_admin: "Администратор",
    }
    
    column_formatters = {
        User.last_seen: lambda m, a: m.last_seen.strftime("%d.%m.%Y %H:%M") if m.last_seen else "Никогда",
        User.avatar_url: lambda m, a: "🖼️ Есть" if m.avatar_url else "❌ Нет",
        User.is_admin: lambda m, a: "👑 Администратор" if m.is_admin else "👤 Пользователь",
        User.bio: lambda m, a: (m.bio[:50] + "...") if m.bio and len(m.bio) > 50 else (m.bio or "—"),
        User.birthdate: lambda m, a: m.birthdate or "—",
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    
    name = "👤 Пользователь"
    name_plural = "👥 Пользователи"
    icon = "fa-solid fa-users"
    
    column_default_sort = (User.id, True)
    
    page_size = 50
    page_size_options = [25, 50, 100, 200]


class MessageAdmin(ModelView, model=Message):
    column_list = [
        Message.id,
        Message.sender_id,
        Message.receiver_id,
        Message.message_type,
        Message.timestamp,
        Message.is_read,
        Message.media_url,
    ]
    
    column_details_list = [
        Message.id,
        Message.sender_id,
        Message.receiver_id,
        Message.encrypted_content,
        Message.message_type,
        Message.media_url,
        Message.timestamp,
        Message.is_read,
    ]
    
    column_searchable_list = [Message.sender_id, Message.receiver_id]
    
    column_sortable_list = [Message.id, Message.timestamp, Message.is_read, Message.message_type]
    
    form_columns = [
        Message.sender_id,
        Message.receiver_id,
        Message.encrypted_content,
        Message.message_type,
        Message.media_url,
        Message.is_read,
    ]
    
    column_labels = {
        Message.id: "ID",
        Message.sender_id: "Отправитель",
        Message.receiver_id: "Получатель",
        Message.encrypted_content: "Содержимое (зашифровано)",
        Message.message_type: "Тип",
        Message.media_url: "Медиа URL",
        Message.timestamp: "Время отправки",
        Message.is_read: "Прочитано",
    }
    
    column_formatters = {
        Message.timestamp: lambda m, a: m.timestamp.strftime("%d.%m.%Y %H:%M:%S") if m.timestamp else "N/A",
        Message.message_type: lambda m, a: "📷 Изображение" if m.message_type == "image" else "💬 Текст",
        Message.is_read: lambda m, a: "✅ Прочитано" if m.is_read else "⏳ Отправлено",
        Message.encrypted_content: lambda m, a: f"🔒 {m.encrypted_content[:40]}..." if len(m.encrypted_content) > 40 else f"🔒 {m.encrypted_content}",
        Message.media_url: lambda m, a: "📎 Медиа" if m.media_url else "—",
        Message.sender_id: lambda m, a: f"👤 ID: {m.sender_id}",
        Message.receiver_id: lambda m, a: f"👤 ID: {m.receiver_id}",
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    
    name = "💬 Сообщение"
    name_plural = "💬 Сообщения"
    icon = "fa-solid fa-message"
    
    column_default_sort = (Message.timestamp, False)
    
    page_size = 50
    page_size_options = [25, 50, 100, 200]

