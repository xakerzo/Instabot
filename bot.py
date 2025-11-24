import requests
import time
import re
import sqlite3
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------- BOT TOKEN VA OWNER ----------
BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
OWNER_ID = 1373647

# ---------- Log sozlash ----------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- SQLite tayyorlash ----------
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT UNIQUE)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS subscribed_users (user_id INTEGER PRIMARY KEY)""")
conn.commit()

# ---------- Funktsiyalar ----------
def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()

def get_users():
    cursor.execute("SELECT id FROM users")
    return [u[0] for u in cursor.fetchall()]

def get_channels():
    cursor.execute("SELECT channel FROM channels")
    return [c[0] for c in cursor.fetchall()]

def check_subscription(user_id):
    channels = get_channels()
    if not channels:
        return True
    for channel in channels:
        try:
            res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
                               params={"chat_id": channel, "user_id": user_id}).json()
            status = res.get("result", {}).get("status", "")
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def mark_subscribed(user_id):
    cursor.execute("INSERT OR IGNORE INTO subscribed_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def is_subscribed(user_id):
    cursor.execute("SELECT user_id FROM subscribed_users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ---------- Instagram helper ----------
def is_instagram_url(url):
    patterns = [r'https?://(www\.)?instagram\.com/\S+', r'https?://(www\.)?instagr\.am/\S+']
    return any(re.match(p, url) for p in patterns)

def modify_instagram_url(url):
    replacements = [("www.instagram.com", "kkinstagram.com"), ("instagram.com", "kkinstagram.com"),
                    ("instagr.am", "kkinstagram.com"), ("www.instagr.am", "kkinstagram.com")]
    for old, new in replacements:
        if old in url:
            return url.replace(old, new)
    return url

# ---------- TikTok helper ----------
def is_tiktok_url(url):
    patterns = [r'https?://(?:www\.)?tiktok\.com/[@\w./-]+', r'https?://vm\.tiktok\.com/[\w+/]+']
    return any(re.match(p, url) for p in patterns)

def get_tiktok_video_url(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    try:
        response = requests.get(api_url)
        data = response.json()
        if data.get('code') == 0:
            return data['data']['play']
    except:
        return None
    return None

# ---------- Pinterest helper ----------
class PinterestDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}
    def clean_url(self, text):
        patterns = [r'https://pin\.it/[^\s]+', r'https://pinterest\.com/pin/[^\s]+']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match: return match.group()
        return None
    def download_content(self, url):
        try:
            response = self.session.get(url, timeout=20)
            html_content = response.text
            images = re.findall(r'src="(https://i\.pinimg\.com/[^"]+)"', html_content)
            videos = re.findall(r'"video_url":"([^"]+)"', html_content)
            return images[:10], videos[:5]
        except:
            return [], []

pinterest_downloader = PinterestDownloader()

# ---------- User subscription check ----------
async def check_user_sub(update: Update):
    user_id = update.effective_user.id
    if is_subscribed(user_id):
        return True
    if check_subscription(user_id):
        mark_subscribed(user_id)
        return True
    buttons = [[InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}")] for ch in get_channels()]
    buttons.append([InlineKeyboardButton("✅ Tasdiqladim", callback_data="confirm_subscription")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "❌ Siz hali barcha kanallarga obuna bo‘lmadingiz! Iltimos, obuna bo‘ling va qayta tasdiqlang.",
        reply_markup=reply_markup
    )
    return False

# ---------- Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data="instagram")],
        [InlineKeyboardButton("🎵 TikTok", callback_data="tiktok")],
        [InlineKeyboardButton("📌 Pinterest", callback_data="pinterest")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Salom! 3-in-1 Downloader botga xush kelibsiz.\n\n"
        "Quyidagidan birini tanlang yoki link yuboring:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "confirm_subscription":
        if check_subscription(query.from_user.id):
            mark_subscribed(query.from_user.id)
            await query.edit_message_text("✅ Endi botni ishlatishingiz mumkin!")
        else:
            await query.edit_message_text("❌ Hali barcha kanallarga obuna bo‘lmadingiz.")
    else:
        await query.edit_message_text(f"Tanlangan: {query.data}\nIltimos, link yuboring.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_user_sub(update):
        return
    text = update.message.text
    if is_instagram_url(text):
        url = modify_instagram_url(text)
        await update.message.reply_text(f"Instagram video tayyor ✅\n{url}")
    elif is_tiktok_url(text):
        url = get_tiktok_video_url(text)
        if url:
            await update.message.reply_video(url, caption="TikTok video yuklandi ✅")
        else:
            await update.message.reply_text("❌ TikTok video yuklab bo‘lmadi!")
    else:
        url = pinterest_downloader.clean_url(text)
        if url:
            images, videos = pinterest_downloader.download_content(url)
            msg = f"Pinterest topildi!\nRasmlar: {len(images)}, Videolar: {len(videos)}"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("❌ Link aniqlanmadi! Instagram/TikTok/Pinterest linkini yuboring.")

# ---------- Main ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🤖 3-in-1 Downloader Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
