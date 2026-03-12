import sqlite3
import threading

class Database:
    def __init__(self, db_file="bot.db"):
        self.db_file = db_file
        self._local = threading.local()
        self._init_conn()
        self.create_tables()

    def _init_conn(self):
        """Har bir thread uchun alohida connection yaratadi."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_file, check_same_thread=False)

    def _execute(self, query, params=()):
        """Query bajaradi va cursor qaytaradi (thread-safe)."""
        self._init_conn()
        cursor = self._local.conn.cursor()
        cursor.execute(query, params)
        self._local.conn.commit()
        return cursor

    def create_tables(self):
        self._execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
        self._execute("CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, url TEXT)")
        self._execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self._execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ('start_text', '📥 Downloader Bot\n\nPlatformalar:\n📸 Instagram\n🎵 TikTok\n📌 Pinterest\n🎬 YouTube Shorts\n\nLink yuboring.')
        )
        # Extra caption uchun default bo'sh qiymat
        self._execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ('extra_caption', '')
        )

    def add_user(self, user_id):
        self._execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

    def get_all_users(self):
        cursor = self._execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

    def count_users(self):
        cursor = self._execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]

    def add_channel(self, channel_id, url):
        self._execute("REPLACE INTO channels (channel_id, url) VALUES (?, ?)", (channel_id, url))

    def delete_channel(self, channel_id):
        self._execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))

    def get_channels(self):
        cursor = self._execute("SELECT channel_id, url FROM channels")
        return cursor.fetchall()

    def set_start_text(self, text):
        self._execute("REPLACE INTO settings (key, value) VALUES ('start_text', ?)", (text,))

    def get_start_text(self):
        cursor = self._execute("SELECT value FROM settings WHERE key='start_text'")
        row = cursor.fetchone()
        return row[0] if row else "Xush kelibsiz!"

    def set_extra_caption(self, text):
        """Video captioniga qo'shimcha matnni saqlaydi."""
        self._execute("REPLACE INTO settings (key, value) VALUES ('extra_caption', ?)", (text,))

    def get_extra_caption(self):
        """Video captioniga qo'shimcha matnni oladi."""
        cursor = self._execute("SELECT value FROM settings WHERE key='extra_caption'")
        row = cursor.fetchone()
        return row[0] if row else ""
