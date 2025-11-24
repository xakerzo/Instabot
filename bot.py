import requests
import re
import sqlite3
import json
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ---------- Sozlamalar ----------
BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
OWNER_ID = 1373647

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

# ---------- Foydalanuvchi va kanal funksiyalari ----------
def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()

def get_users():
    cursor.execute("SELECT id FROM users")
    return [u[0] for u in cursor.fetchall()]

def add_channel(channel):
    if not channel.startswith("@"):
        channel = "@" + channel
    cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (channel,))
    conn.commit()

def delete_channel(channel):
    if not channel.startswith("@"):
        channel = "@" + channel
    cursor.execute("DELETE FROM channels WHERE channel=?", (channel,))
    conn.commit()

def get_channels():
    cursor.execute("SELECT channel FROM channels")
    return [c[0] for c in cursor.fetchall()]

def set_caption(text):
    cursor.execute("REPLACE INTO settings (key,value) VALUES ('caption',?)", (text,))
    conn.commit()

def get_caption():
    cursor.execute("SELECT value FROM settings WHERE key='caption'")
    row = cursor.fetchone()
    return row[0] if row else ""

def delete_caption():
    cursor.execute("DELETE FROM settings WHERE key='caption'")
    conn.commit()

def set_state(state):
    cursor.execute("REPLACE INTO settings (key,value) VALUES ('state',?)", (state,))
    conn.commit()

def get_state():
    cursor.execute("SELECT value FROM settings WHERE key='state'")
    row = cursor.fetchone()
    return row[0] if row else ""

def clear_state():
    cursor.execute("DELETE FROM settings WHERE key='state'")
    conn.commit()

def mark_subscribed(user_id):
    cursor.execute("INSERT OR IGNORE INTO subscribed_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def is_subscribed(user_id):
    cursor.execute("SELECT user_id FROM subscribed_users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ---------- Owner start xabarini saqlash/olish/o'chirish ----------
def set_owner_message(text):
    cursor.execute("REPLACE INTO settings (key,value) VALUES ('owner_message',?)", (text,))
    conn.commit()

def get_owner_message():
    cursor.execute("SELECT value FROM settings WHERE key='owner_message'")
    row = cursor.fetchone()
    return row[0] if row else None

def delete_owner_message():
    cursor.execute("DELETE FROM settings WHERE key='owner_message'")
    conn.commit()

# ---------- Majburiy kanal tekshiruvi ----------
async def check_subscription(user_id, app):
    channels = get_channels()
    if not channels:
        return True

    if is_subscribed(user_id):
        return True

    for ch in channels:
        try:
            res = await app.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if res.status not in ["member", "administrator", "creator"]:
                break
        except:
            break
    else:
        mark_subscribed(user_id)
        return True

    buttons = [[InlineKeyboardButton(ch, url=f"https://t.me/{ch.replace('@','')}")] for ch in channels]
    buttons.append([InlineKeyboardButton("✅ Tasdiqladim", callback_data="confirm_subscription")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await app.bot.send_message(user_id, "❌ Siz hali barcha kanallarga obuna bo‘lmadingiz! Iltimos, obuna bo‘lib qayta tasdiqlang:", reply_markup=reply_markup)
    return False

# ---------- Instagram link funksiyalari ----------
def is_instagram_url(url):
    patterns = [r'https?://(www\.)?instagram\.com/\S+', r'https?://(www\.)?instagr\.am/\S+', r'https?://(www\.)?kkinstagram\.com/\S+']
    return any(re.match(p, url) for p in patterns)

def modify_instagram_url(url):
    replacements = [("www.instagram.com", "kkinstagram.com"), ("instagram.com", "kkinstagram.com"), ("instagr.am", "kkinstagram.com"), ("www.instagr.am", "kkinstagram.com")]
    for old,new in replacements:
        if old in url:
            return url.replace(old,new)
    return url

# ---------- TikTok download ----------
def is_tiktok_url(url):
    patterns = [r'https?://(?:www\.)?tiktok\.com/[@\w./-]+', r'https?://vm\.tiktok\.com/[\w+/]+', r'https?://vt\.tiktok\.com/[\w+/]+']
    return any(re.match(p, url) for p in patterns)

def get_tiktok_video(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"
    try:
        res = requests.get(api_url).json()
        if res.get("code")==0:
            return res['data']['play']
    except:
        return None
    return None

# ---------- Pinterest download ----------
class PinterestDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {'User-Agent':'Mozilla/5.0'}
    def clean_url(self, text):
        patterns = [r'https://pin\.it/[^\s]+', r'https://pinterest\.com/pin/[^\s]+', r'https://www\.pinterest\.com/pin/[^\s]+']
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return None
    def download_content(self, url):
        try:
            resp = self.session.get(url, timeout=15)
            html = resp.text
            images = re.findall(r'"url":"(https://i\.pinimg\.com/[^"]+)"', html)
            videos = re.findall(r'"video_url":"([^"]+)"', html)
            return images[:10], videos[:5]
        except:
            return [],[]

pinterest = PinterestDownloader()

# ---------- Owner tugmalarini boshqarish ----------
async def handle_owner_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == "broadcast":
        set_state("broadcast")
        await context.bot.send_message(user_id, "Matn yuboring (bu barcha foydalanuvchilarga jo'natiladi):")
    elif data == "caption_add":
        set_state("caption")
        await context.bot.send_message(user_id, "Iltimos, video caption matnini yuboring:")
    elif data == "caption_view":
        cap = get_caption()
        await context.bot.send_message(user_id, cap if cap else "Hozircha caption yo'q.")
    elif data == "caption_delete":
        delete_caption()
        await context.bot.send_message(user_id, "Caption o'chirildi ✅")
    elif data == "channel_add":
        set_state("channel_add")
        await context.bot.send_message(user_id, "Kanal username yuboring (misol: @SizningKanal)")
    elif data == "channel_delete":
        set_state("channel_delete")
        chs = get_channels()
        msg = "Kanallar:\n" + "\n".join(chs) if chs else "Hozircha kanal yo'q."
        await context.bot.send_message(user_id, msg + "\nO'chirish uchun kanal username yuboring:")
    elif data == "channel_check":
        chs = get_channels()
        msg = "Kanallar:\n" + "\n".join(chs) if chs else "Hozircha kanal yo'q."
        await context.bot.send_message(user_id, msg)
    elif data == "user_count":
        count = len(get_users())
        await context.bot.send_message(user_id, f"Botdagi foydalanuvchilar soni: {count}")
    
    # ---------- Owner start matni boshqaruvi ----------
    elif data == "start_add":
        set_state("start_add")
        await context.bot.send_message(user_id, "Iltimos, foydalanuvchilarga ko'rsatadigan start matnini yuboring:")
    elif data == "start_view":
        msg = get_owner_message()
        await context.bot.send_message(user_id, msg if msg else "Hozircha start matni yo'q.")
    elif data == "start_delete":
        delete_owner_message()
        await context.bot.send_message(user_id, "Start matni o'chirildi ✅")

    elif data == "confirm_subscription":
        if await check_subscription(user_id, context):
            mark_subscribed(user_id)
            await context.bot.send_message(user_id, "✅ Siz barcha majburiy kanallarga obuna bo'ldingiz. Endi botni ishlatishingiz mumkin!")

# ---------- /start komandasi ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    add_user(user_id)
    
    if user_id == OWNER_ID:
        buttons = [
            [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
            [InlineKeyboardButton("✏️ Caption qo'shish", callback_data="caption_add")],
            [InlineKeyboardButton("📝 Captionni ko'rish", callback_data="caption_view")],
            [InlineKeyboardButton("❌ Captionni o'chirish", callback_data="caption_delete")],
            [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="channel_add")],
            [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="channel_delete")],
            [InlineKeyboardButton("📃 Kanallarni tekshirish", callback_data="channel_check")],
            [InlineKeyboardButton("👥 Foydalanuvchilar soni", callback_data="user_count")],
            [InlineKeyboardButton("📝 Start matnini qo'shish", callback_data="start_add")],
            [InlineKeyboardButton("👁 Start matnini ko'rish", callback_data="start_view")],
            [InlineKeyboardButton("❌ Start matnini o'chirish", callback_data="start_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(user_id, "👋 Salom Owner!\nBu sizning maxsus boshqaruv panelingiz:", reply_markup=reply_markup)
    else:
        owner_msg = get_owner_message()
        if owner_msg:
            text = owner_msg
        else:
            text = "👋 Salom! \n\n✅ Instagram downloader\n✅ TikTok downloader\n✅ Pinterest downloader\n\n📌 Iltimos, birinchi navbatda link yuboring!"
        await context.bot.send_message(user_id, text)

# ---------- Xabarlarni qayta ishlash ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    text = update.message.text.strip()
    add_user(chat_id)

    # ---------- Owner start matni saqlash uchun state tekshirish ----------
    if get_state() == "start_add" and chat_id == OWNER_ID:
        set_owner_message(text)
        clear_state()
        await context.bot.send_message(chat_id, "✅ Start matni saqlandi!")
        return

    if not await check_subscription(chat_id, context):
        return

    # Instagram
    if is_instagram_url(text):
        url = modify_instagram_url(text)
        cap = get_caption()
        msg_text = f"📥 Instagram video tayyor!\n{url}"
        if cap:
            msg_text += f"\n\n{cap}"
        await context.bot.send_message(chat_id, msg_text)
        return

    # TikTok
    if is_tiktok_url(text):
        video = get_tiktok_video(text)
        if video:
            cap = get_caption() or ""
            await context.bot.send_video(chat_id, video, caption=f"📥 TikTok video\n{cap}")
        else:
            await context.bot.send_message(chat_id, "❌ TikTok video yuklab bo'lmadi!")
        return

    # Pinterest
    url = pinterest.clean_url(text)
    if url:
        images, videos = pinterest.download_content(url)
        if images:
            for i,img in enumerate(images):
                await context.bot.send_photo(chat_id, img, caption=f"📸 Rasm {i+1}/{len(images)}")
        if videos:
            for i,vid in enumerate(videos):
                await context.bot.send_video(chat_id, vid, caption=f"🎥 Video {i+1}/{len(videos)}")
        return

    await context.bot.send_message(chat_id, "❌ Iltimos, faqat Instagram, TikTok yoki Pinterest linkini yuboring!")

# ---------- Main function ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_owner_buttons))
    logger.info("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
