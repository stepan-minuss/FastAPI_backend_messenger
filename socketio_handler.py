import logging
from typing import Dict
from sqlalchemy.orm import Session
from socketio import AsyncNamespace
from socketio.exceptions import ConnectionRefusedError
from database import SessionLocal
from models import User, Message
from datetime import datetime, timezone
from auth import get_user_from_token

logger = logging.getLogger(__name__)

user_socket_map: Dict[int, set] = {}


class ChatNamespace(AsyncNamespace):
    
    async def on_connect(self, sid, environ, auth=None):
        logger.info(f"Connection attempt from socket {sid}")
        
        logger.debug(f"Environ keys: {list(environ.keys())}")
        if auth:
            logger.debug(f"Auth data received: {auth}")
        else:
            logger.debug("No auth data received directly")

        token = None
        
        if auth and isinstance(auth, dict):
            token = auth.get("token")
            if token:
                logger.debug("Token found in auth dictionary")
        
        if not token:
            auth_header = environ.get("HTTP_AUTHORIZATION")
            
            if not auth_header and "headers" in environ:
                headers = environ["headers"]
                if isinstance(headers, list):
                    for key, value in headers:
                        if key.lower() == b"authorization":
                            auth_header = value.decode("utf-8")
                            break
                elif isinstance(headers, dict):
                    auth_header = headers.get("authorization") or headers.get("Authorization")

            if auth_header:
                if isinstance(auth_header, (list, tuple)) and len(auth_header) > 0:
                    auth_header = auth_header[0]
                if isinstance(auth_header, str) and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    logger.debug("Token found in Authorization header")

        if not token and environ.get("QUERY_STRING"):
            query_string = environ["QUERY_STRING"]
            if isinstance(query_string, bytes):
                query_string = query_string.decode("utf-8")
            
            logger.debug(f"Checking query string for token")
            
            import urllib.parse
            params = urllib.parse.parse_qs(query_string)
            if "token" in params:
                token_list = params["token"]
                if token_list:
                    token = token_list[0]
                    logger.debug("Token found in query string")

        if not token:
            logger.warning(f"Connection refused: No token provided for socket {sid}")
            raise ConnectionRefusedError("Authentication required: No token provided")
        
        logger.debug(f"Token extracted: {token[:20]}... (length: {len(token)})")
        
        db: Session = SessionLocal()
        try:
            user = get_user_from_token(token, db)
            if not user:
                logger.warning(f"Connection refused: Invalid token for socket {sid} (token: {token[:30]}...)")
                try:
                    from jose import jwt
                    from auth import SECRET_KEY, ALGORITHM
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    logger.debug(f"Token payload: {payload}")
                    logger.warning(f"Token decoded successfully but user not found. Subject: {payload.get('sub')}")
                except Exception as decode_error:
                    logger.error(f"Failed to decode token: {decode_error}")
                raise ConnectionRefusedError("Authentication failed: Invalid token")
            
            await self.save_session(sid, {"user_id": user.id, "username": user.username})
            
            if user.id not in user_socket_map:
                user_socket_map[user.id] = set()
            user_socket_map[user.id].add(sid)
            
            logger.info(f"User {user.username} (ID: {user.id}) connected via socket {sid}")
            
        except Exception as e:
            logger.error(f"Error during connection handling: {e}")
            raise ConnectionRefusedError("Internal server error during authentication")
        finally:
            db.close()
    
    async def on_disconnect(self, sid):
        session = await self.get_session(sid)
        if session and "user_id" in session:
            user_id = session["user_id"]
            username = session.get("username", "Unknown")
            
            if user_id in user_socket_map:
                user_socket_map[user_id].discard(sid)
                if not user_socket_map[user_id]:
                    del user_socket_map[user_id]
            
            db: Session = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user.last_seen = datetime.now(timezone.utc)
                    db.commit()
                    logger.info(f"Updated last_seen for user {username} (ID: {user_id})")
            except Exception as e:
                logger.error(f"Error updating last_seen for user {user_id}: {e}")
                db.rollback()
            finally:
                db.close()
            
            logger.info(f"User {username} (ID: {user_id}) disconnected from socket {sid}")
    
    async def on_send_message(self, sid, data):
        session = await self.get_session(sid)
        if not session or "user_id" not in session:
            logger.error(f"Unauthorized send_message attempt from socket {sid}")
            await self.emit("error", {"message": "Unauthorized"}, room=sid)
            return
        
        sender_id_raw = session["user_id"]
        receiver_id_raw = data.get("receiver_id")
        encrypted_content = data.get("encrypted_content")
        message_type = data.get("message_type", "text")
        media_url = data.get("media_url")
        reply_to_message_id = data.get("reply_to_message_id")
        
        if not receiver_id_raw or not encrypted_content:
            logger.warning(f"Invalid send_message data from user {sender_id_raw}: missing receiver_id or encrypted_content")
            await self.emit("error", {"message": "Missing receiver_id or encrypted_content"}, room=sid)
            return
        
        try:
            sender_id = int(sender_id_raw)
            receiver_id = int(receiver_id_raw)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid user ID format: sender_id={sender_id_raw} (type: {type(sender_id_raw)}), receiver_id={receiver_id_raw} (type: {type(receiver_id_raw)}): {e}")
            await self.emit("error", {"message": "Invalid user ID format"}, room=sid)
            return
        
        logger.info(f"📤 Message send attempt: sender_id={sender_id} (raw: {sender_id_raw}, type: {type(sender_id_raw)}), receiver_id={receiver_id} (raw: {receiver_id_raw}, type: {type(receiver_id_raw)})")
        
        if sender_id == receiver_id:
            logger.warning(f"⚠️ User {sender_id} attempted to send message to self (receiver_id={receiver_id})")
            await self.emit("error", {"message": "Cannot send message to yourself"}, room=sid)
            return
        
        db: Session = SessionLocal()
        try:
            receiver = db.query(User).filter(User.id == receiver_id).first()
            if not receiver:
                logger.warning(f"User {sender_id} attempted to send message to non-existent user {receiver_id}")
                await self.emit("error", {"message": "Receiver not found"}, room=sid)
                return
            
            now_utc = datetime.now(timezone.utc)
            if reply_to_message_id:
                reply_message = db.query(Message).filter(Message.id == reply_to_message_id).first()
                if not reply_message:
                    logger.warning(f"User {sender_id} attempted to reply to non-existent message {reply_to_message_id}")
                    await self.emit("error", {"message": "Reply message not found"}, room=sid)
                    return
            
            message = Message(
                sender_id=sender_id,
                receiver_id=receiver_id,
                encrypted_content=encrypted_content,
                message_type=message_type,
                media_url=media_url,
                reply_to_message_id=reply_to_message_id,
                timestamp=now_utc
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            
            logger.info(
                f"Message saved: sender_id={sender_id}, receiver_id={receiver_id}, "
                f"message_id={message.id}, timestamp={message.timestamp}. "
                f"[PRIVACY: Content is encrypted (E2EE) and unreadable by server/admin]"
            )
            
            message_data = {
                "id": message.id,
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "encrypted_content": encrypted_content,
                "message_type": message_type,
                "media_url": media_url,
                "reply_to_message_id": message.reply_to_message_id,
                "timestamp": message.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "is_read": message.is_read
            }
            
            receiver_sockets = user_socket_map.get(receiver_id, set())
            logger.info(f"Receiver {receiver_id} has {len(receiver_sockets)} active socket(s)")
            
            if not receiver_sockets:
                logger.warning(f"Receiver {receiver_id} is not connected - message saved but not delivered in real-time")
            
            for receiver_sid in receiver_sockets:
                await self.emit("new_message", message_data, room=receiver_sid)
                logger.info(
                    f"✅ Emitted new_message to receiver {receiver_id} (socket {receiver_sid}). "
                    f"[PRIVACY: Content is encrypted and unreadable by server]"
                )
            
            sender_sockets = user_socket_map.get(sender_id, set())
            for sender_sid in sender_sockets:
                if sender_sid != sid:
                    await self.emit("new_message", message_data, room=sender_sid)
                    logger.info(
                        f"Emitted new_message to sender {sender_id} (socket {sender_sid}) for sync. "
                        f"[PRIVACY: Content is encrypted and unreadable by server]"
                    )
            
            await self.emit("message_sent", {"message_id": message.id}, room=sid)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error sending message from user {sender_id}: {str(e)}")
            await self.emit("error", {"message": "Failed to send message"}, room=sid)
        finally:
            db.close()
    
    async def on_typing(self, sid, data):
        session = await self.get_session(sid)
        if not session or "user_id" not in session:
            logger.warning(f"Unauthorized typing event from socket {sid}")
            return
        
        sender_id = session["user_id"]
        receiver_id = data.get("receiver_id")
        is_typing = data.get("is_typing", False)
        
        if not receiver_id:
            return
        
        db: Session = SessionLocal()
        try:
            receiver = db.query(User).filter(User.id == receiver_id).first()
            if not receiver:
                return
        finally:
            db.close()
        
        typing_data = {
            "sender_id": sender_id,
            "is_typing": is_typing
        }
        
        receiver_sockets = user_socket_map.get(receiver_id, set())
        for receiver_sid in receiver_sockets:
            await self.emit("typing", typing_data, room=receiver_sid)
            logger.debug(f"Relayed typing status from user {sender_id} to user {receiver_id}")


_sio_server = None

def set_sio_server(sio):
    global _sio_server
    _sio_server = sio

async def notify_messages_read(sender_id: int, message_ids: list, reader_id: int):
    if _sio_server is None:
        logger.warning("Socket.IO server not initialized, cannot send read receipt")
        return
    
    sender_sockets = user_socket_map.get(sender_id, set())
    if sender_sockets:
        read_data = {
            "message_ids": message_ids,
            "reader_id": reader_id
        }
        for sender_sid in sender_sockets:
            await _sio_server.emit("messages_read", read_data, room=sender_sid)
        logger.info(f"Sent read receipt notification to sender {sender_id} for messages {message_ids}")

