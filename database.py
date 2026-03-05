import sqlite3

class Database:
    def __init__(self, db_file="bot.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Foydalanuvchilar
        self.cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        # Kanallar (majburiy obuna uchun)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, url TEXT)")
        # Sozlamalar (start matni va hakazo)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        
        # Boshlang'ich start matnini kiritib qo'yamiz (agar mavjud bo'lmasa)
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                            ('start_text', '📥 Downloader Bot\n\nPlatformalar:\n📸 Instagram\n🎵 TikTok\n📌 Pinterest\n🎬 YouTube Shorts\n\nLink yuboring.'))
        self.conn.commit()

    def add_user(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    def count_users(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        return self.cursor.fetchone()[0]

    def add_channel(self, channel_id, url):
        self.cursor.execute("REPLACE INTO channels (channel_id, url) VALUES (?, ?)", (channel_id, url))
        self.conn.commit()

    def delete_channel(self, channel_id):
        self.cursor.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
        self.conn.commit()

    def get_channels(self):
        self.cursor.execute("SELECT channel_id, url FROM channels")
        return self.cursor.fetchall()

    def set_start_text(self, text):
        self.cursor.execute("REPLACE INTO settings (key, value) VALUES ('start_text', ?)", (text,))
        self.conn.commit()

    def get_start_text(self):
        self.cursor.execute("SELECT value FROM settings WHERE key='start_text'")
        return self.cursor.fetchone()[0]
