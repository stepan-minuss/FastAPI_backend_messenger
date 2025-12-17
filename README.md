# Messenger Backend

Backend API для мессенджера с поддержкой End-to-End Encryption (E2EE).

## Технологии

- **FastAPI** - веб-фреймворк для создания API
- **SQLAlchemy** - ORM для работы с базой данных
- **SQLite** - база данных
- **Socket.IO** - WebSocket для real-time коммуникации
- **JWT** - аутентификация
- **bcrypt** - хеширование паролей

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите миграцию базы данных (опционально):
```bash
python migrate_db.py
```

3. Запустите сервер:
```bash
python main.py
```

Или используйте uvicorn напрямую:
```bash
uvicorn main:asgi_app --host 0.0.0.0 --port 5000
```

## Структура проекта

- `main.py` - точка входа, настройка FastAPI и Socket.IO
- `database.py` - настройка базы данных и миграции
- `models.py` - модели данных (User, Message, UserTheme, Contact)
- `schemas.py` - Pydantic схемы для валидации данных
- `routes.py` - API endpoints
- `auth.py` - аутентификация и авторизация
- `socketio_handler.py` - обработка Socket.IO событий
- `admin.py` - админ-панель SQLAdmin
- `migrate_db.py` - скрипт миграции базы данных

## API Endpoints

### Аутентификация
- `POST /auth/register` - регистрация нового пользователя
- `POST /auth/login` - вход в систему

### Пользователи
- `GET /me` - получить информацию о текущем пользователе
- `PUT /users/me/username` - обновить username
- `PUT /users/me/profile` - обновить профиль
- `PUT /users/me/bio` - обновить биографию
- `PUT /users/me/birthdate` - обновить дату рождения
- `POST /users/me/avatar` - загрузить аватар
- `PUT /users/me/avatar-frame` - установить рамку аватара
- `PUT /users/me/preset-avatar` - установить предустановленный аватар
- `GET /users/search` - поиск пользователей
- `GET /users` - получить список всех пользователей
- `GET /users/{user_id}/profile` - получить профиль пользователя
- `DELETE /users/me` - удалить аккаунт

### Сообщения
- `GET /chats/{target_user_id}/messages` - получить историю сообщений
- `DELETE /chats/{target_user_id}/messages` - очистить чат
- `DELETE /messages/{message_id}` - удалить сообщение
- `POST /chats/{target_user_id}/mark-read` - отметить сообщения как прочитанные
- `GET /chats/{target_user_id}/media` - получить медиа из чата

### Темы
- `POST /users/me/themes` - создать пользовательскую тему
- `GET /users/me/themes` - получить все темы пользователя
- `PUT /users/me/themes/{theme_id}` - обновить тему
- `DELETE /users/me/themes/{theme_id}` - удалить тему

### Контакты
- `PUT /contacts/{contact_id}/local-name` - установить локальное имя контакта
- `DELETE /contacts/{contact_id}/local-name` - удалить локальное имя

### Приватность
- `GET /users/me/privacy` - получить настройки приватности
- `PUT /users/me/privacy` - обновить настройки приватности

### Файлы
- `POST /upload` - загрузить файл (изображение)

### Другое
- `GET /test` - тестовый endpoint
- `GET /health` - проверка здоровья сервера
- `GET /avatars/list` - список предустановленных аватаров
- `GET /avatar-frames/list` - список доступных рамок аватаров

## Socket.IO Events

### Клиент -> Сервер
- `send_message` - отправить сообщение
- `typing` - статус печати

### Сервер -> Клиент
- `new_message` - новое сообщение
- `message_sent` - подтверждение отправки
- `messages_read` - сообщения прочитаны
- `typing` - статус печати от другого пользователя
- `error` - ошибка

## Админ-панель

Доступна по адресу `/admin` после запуска сервера.

## База данных

База данных SQLite создается автоматически при первом запуске. Файл базы данных: `chat.db`

## Конфигурация

- `SECRET_KEY` - секретный ключ для JWT (измените в production!)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - время жизни токена (24 часа)
- `SQLALCHEMY_DATABASE_URL` - URL базы данных

## Безопасность

- Пароли хешируются с помощью bcrypt
- JWT токены для аутентификации
- End-to-End Encryption для сообщений (E2EE)
- CORS настройки (в production укажите конкретные origins)

