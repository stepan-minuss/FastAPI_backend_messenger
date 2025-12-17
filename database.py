from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./chat.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_database()


def _migrate_database():
    import sqlite3
    import os
    
    db_path = "./chat.db"
    
    if not os.path.exists(db_path):
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'avatar_frame' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_frame TEXT")
        
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'reply_to_message_id' not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN reply_to_message_id INTEGER")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка миграции (можно игнорировать): {e}")

