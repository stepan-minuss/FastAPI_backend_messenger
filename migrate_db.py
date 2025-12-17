import sqlite3
import os

def migrate_database():
    db_path = "chat.db"
    
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена. Создайте её сначала через init_db.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'first_name' not in columns:
            print("Добавляем колонку first_name в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
            print("Колонка first_name добавлена")
        else:
            print("Колонка first_name уже существует")
        
        if 'last_name' not in columns:
            print("Добавляем колонку last_name в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
            print(" Колонка last_name добавлена")
        else:
            print(" Колонка last_name уже существует")
        
        if 'phone' not in columns:
            print("Добавляем колонку phone в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT UNIQUE")
            print(" Колонка phone добавлена")
        else:
            print(" Колонка phone уже существует")
        
        if 'avatar_frame' not in columns:
            print("Добавляем колонку avatar_frame в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_frame TEXT")
            print(" Колонка avatar_frame добавлена")
        else:
            print(" Колонка avatar_frame уже существует")
        
        if 'avatar_visibility' not in columns:
            print("Добавляем колонку avatar_visibility в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_visibility TEXT DEFAULT 'all'")
            print(" Колонка avatar_visibility добавлена")
        else:
            print(" Колонка avatar_visibility уже существует")
        
        if 'avatar_visibility_exceptions' not in columns:
            print("Добавляем колонку avatar_visibility_exceptions в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_visibility_exceptions TEXT")
            print(" Колонка avatar_visibility_exceptions добавлена")
        else:
            print(" Колонка avatar_visibility_exceptions уже существует")
        
        if 'show_read_receipts' not in columns:
            print("Добавляем колонку show_read_receipts в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN show_read_receipts INTEGER DEFAULT 1")
            print(" Колонка show_read_receipts добавлена")
        else:
            print(" Колонка show_read_receipts уже существует")
        
        if 'show_last_seen' not in columns:
            print("Добавляем колонку show_last_seen в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN show_last_seen INTEGER DEFAULT 1")
            print(" Колонка show_last_seen добавлена")
        else:
            print(" Колонка show_last_seen уже существует")
        
        if 'show_online_status' not in columns:
            print("Добавляем колонку show_online_status в таблицу users...")
            cursor.execute("ALTER TABLE users ADD COLUMN show_online_status INTEGER DEFAULT 1")
            print(" Колонка show_online_status добавлена")
        else:
            print(" Колонка show_online_status уже существует")
        
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'reply_to_message_id' not in columns:
            print("Добавляем колонку reply_to_message_id в таблицу messages...")
            cursor.execute("ALTER TABLE messages ADD COLUMN reply_to_message_id INTEGER")
            print(" Колонка reply_to_message_id добавлена")
        else:
            print(" Колонка reply_to_message_id уже существует")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                primary_color TEXT NOT NULL,
                background_color TEXT NOT NULL,
                bubble_color_me TEXT NOT NULL,
                bubble_color_other TEXT NOT NULL,
                text_color TEXT NOT NULL,
                secondary_text_color TEXT NOT NULL,
                brightness TEXT NOT NULL,
                wallpaper_url TEXT,
                wallpaper_blur TEXT DEFAULT '0.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_themes_user_id ON user_themes(user_id)")
        print(" Таблица user_themes создана или уже существует")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL,
                local_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id),
                FOREIGN KEY (contact_id) REFERENCES users(id),
                UNIQUE(owner_id, contact_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_owner_id ON contacts(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_contact_id ON contacts(contact_id)")
        print(" Таблица contacts создана или уже существует")
        
        conn.commit()
        print("\n Миграция завершена успешно!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()

