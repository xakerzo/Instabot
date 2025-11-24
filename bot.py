import re
import time
import requests
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- Config ---
BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
OWNER_ID = 1373647

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DB Setup ---
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)""")
conn.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()

# --- Utility Functions ---
def is_instagram_url(url):
    return any(re.match(p, url) for p in [
        r'https?://(www\.)?instagram\.com/\S+',
        r'https?://(www\.)?instagr\.am/\S+',
        r'https?://(www\.)?kkinstagram\.com/\S+'
    ])

def modify_instagram_url(url):
    for old, new in [("www.instagram.com","kkinstagram.com"),
                     ("instagram.com","kkinstagram.com"),
                     ("instagr.am","kkinstagram.com"),
                     ("www.instagr.am","kkinstagram.com")]:
        if old in url:
            return url.replace(old,new)
    return url

def is_tiktok_url(url):
    return any(re.match(p, url) for p in [
        r'https?://(?:www\.)?tiktok\.com/[@\w./-]+',
        r'https?://vm\.tiktok\.com/[\w+/]+',
        r'https?://vt\.tiktok\.com/[\w+/]+'
    ])

def is_pinterest_url(url):
    return re.search(r'https?://(www\.)?(pinterest\.com|pin\.it)/', url) is not None

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.message.from_user.id)
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

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Siz tanladingiz: {query.data}\nIltimos, link yuboring.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat.id

    if is_instagram_url(text):
        modified_url = modify_instagram_url(text)
        await update.message.reply_text(f"Instagram video tayyor ✅\n{modified_url}")
    elif is_tiktok_url(text):
        api_url = f"https://www.tikwm.com/api/?url={text}"
        try:
            res = requests.get(api_url).json()
            if res.get('code') == 0:
                video_url = res['data']['play']
                await update.message.reply_video(video=video_url, caption="🎵 TikTok video yuklandi!")
            else:
                await update.message.reply_text("❌ TikTok video yuklanmadi. Linkni tekshiring!")
        except:
            await update.message.reply_text("❌ TikTok video yuklanmadi. Xatolik yuz berdi!")
    elif is_pinterest_url(text):
        await update.message.reply_text(f"Pinterest link qabul qilindi: {text}\nRasmlar va videolar yuklanmoqda...")
        # Pinterest downloader kodini shu yerga qo'shish mumkin
    else:
        await update.message.reply_text("❌ Iltimos, faqat Instagram, TikTok yoki Pinterest linkini yuboring!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
