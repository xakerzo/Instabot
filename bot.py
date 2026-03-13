import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import re
import time
from database import Database
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
admin_env = os.getenv("OWNER_ID", "")
ADMIN_IDS = [int(i.strip()) for i in admin_env.split(',') if i.strip().isdigit()]

bot = telebot.TeleBot(TOKEN)
db = Database()

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Bot username ni bir marta olamiz
def get_bot_username():
    try:
        return bot.get_me().username
    except:
        return None

BOT_USERNAME = None  # ishga tushganda to'ldiriladi


# ---- YORDAMCHI FUNKSIYALAR ----

def is_instagram_url(text):
    return text and "instagram.com" in text

def is_supported_url(text):
    return text and (
        "instagram.com" in text or
        "tiktok.com" in text or
        "youtube.com/shorts" in text or
        "pinterest.com" in text or
        "pin.it" in text
    )

def check_join(user_id):
    channels = db.get_channels()
    not_joined = []
    if user_id in ADMIN_IDS:
        return []
    for ch_id, ch_url in channels:
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append((ch_id, ch_url))
        except:
            pass
    return not_joined

def send_join_request(chat_id, not_joined_channels):
    markup = InlineKeyboardMarkup()
    for i, (ch_id, ch_url) in enumerate(not_joined_channels, start=1):
        markup.add(InlineKeyboardButton(text=f"📢 {i}-kanalga qo'shilish", url=ch_url))
    markup.add(InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_join"))
    bot.send_message(chat_id, "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz kerak!</b>",
                     parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

def build_video_markup():
    """Video tagidagi inline tugma: Botni guruhga qo'shish."""
    markup = InlineKeyboardMarkup()
    if BOT_USERNAME:
        markup.add(InlineKeyboardButton(
            text="➕ Botni guruhga qo'shish",
            url=f"https://t.me/{BOT_USERNAME}?startgroup=1"
        ))
    return markup

def build_full_caption(caption, bot_username):
    """Instagram caption + extra admin matni + bot manzili."""
    extra = db.get_extra_caption()
    parts = []
    if caption:
        parts.append(caption)
    if extra:
        parts.append(f"<b><i>{extra}</i></b>")
    if bot_username:
        parts.append(f"🤖 @{bot_username}")
    full = "\n\n".join(parts) if parts else None
    if full and len(full) > 1024:
        full = full[:1020] + "..."
    return full


# ---- ADMIN PANEL ----
ADMIN_BUTTONS = ["📊 Statistika", "📢 Broadcast", "➕ Kanal qo'shish", "➖ Kanalni o'chirish",
                 "📝 Start matnini o'zgartirish", "🖊 Caption matni"]

def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton(ADMIN_BUTTONS[0]), KeyboardButton(ADMIN_BUTTONS[1]))
    markup.add(KeyboardButton(ADMIN_BUTTONS[2]), KeyboardButton(ADMIN_BUTTONS[3]))
    markup.add(KeyboardButton(ADMIN_BUTTONS[4]), KeyboardButton(ADMIN_BUTTONS[5]))
    return markup


@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    not_joined = check_join(call.from_user.id)
    if not_joined:
        bot.answer_callback_query(call.id, "❌ Siz hali kanallarga a'zo bo'lmadingiz!", show_alert=True)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id,
                         "✅ <b>Obuna tasdiqlandi! Endi menga video linkini yuborishingiz mumkin.</b>",
                         parse_mode="HTML")


@bot.message_handler(commands=['start'])
def start(message):
    db.add_user(message.chat.id)
    not_joined = check_join(message.from_user.id)
    if not_joined:
        send_join_request(message.chat.id, not_joined)
        return
    text = db.get_start_text()
    if message.chat.id in ADMIN_IDS:
        bot.send_message(message.chat.id, text, reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, text, reply_markup=telebot.types.ReplyKeyboardRemove())


# --- ADMIN FUNKSIYALAR ---
@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.chat.id in ADMIN_IDS)
def stat_handler(message):
    count = db.count_users()
    bot.reply_to(message, f"📊 <b>Bot foydalanuvchilari soni:</b> {count} ta", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "➕ Kanal qo'shish" and m.chat.id in ADMIN_IDS)
def add_channel_step(message):
    msg = bot.reply_to(message,
        "📝 Kanal ma'lumotlarini quyidagi formatda yuboring:\n<code>@kanal_useri https://t.me/kanal_linki</code>\n\n"
        "Yoki maxfiy kanallar uchun (bot kanalda admin bo'lishi shart!):\n<code>-100123456789 https://t.me/link</code>",
        parse_mode="HTML")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    if message.text in ADMIN_BUTTONS:
        return
    try:
        parts = message.text.split()
        if len(parts) >= 2:
            ch_id = parts[0]
            url = parts[1]
            db.add_channel(ch_id, url)
            bot.reply_to(message, f"✅ Kanal muvaffaqiyatli saqlandi!\nID: {ch_id}")
        else:
            bot.reply_to(message, "❌ Noto'g'ri format! Iltimos qaytadan urinib ko'ring.")
    except Exception as e:
        bot.reply_to(message, f"❌ Xato yuz berdi: {e}")

@bot.message_handler(func=lambda m: m.text == "➖ Kanalni o'chirish" and m.chat.id in ADMIN_IDS)
def del_channel_step(message):
    channels = db.get_channels()
    if not channels:
        bot.reply_to(message, "❌ Baza bo'sh. Hech qanday kanal qo'shilmagan.")
        return
    text = "Hozirgi kanallar ro'yxati:\n"
    for idx, (ch_id, url) in enumerate(channels, 1):
        text += f"{idx}. {ch_id} - {url}\n"
    text += "\nO'chirmoqchi bo'lgan <b>kanal ID</b> (yoki useri) ni yozib yuboring:"
    msg = bot.reply_to(message, text, parse_mode="HTML")
    bot.register_next_step_handler(msg, process_del_channel)

def process_del_channel(message):
    if message.text in ADMIN_BUTTONS: return
    db.delete_channel(message.text.strip())
    bot.reply_to(message, f"✅ Kanal {message.text} o'chirildi.")

@bot.message_handler(func=lambda m: m.text == "📝 Start matnini o'zgartirish" and m.chat.id in ADMIN_IDS)
def start_text_step(message):
    msg = bot.reply_to(message,
        f"Hozirgi matn:\n\n<code>{db.get_start_text()}</code>\n\n📝 Yangi matnni yuboring:",
        parse_mode="HTML")
    bot.register_next_step_handler(msg, process_start_text)

def process_start_text(message):
    if message.text in ADMIN_BUTTONS: return
    db.set_start_text(message.text)
    bot.reply_to(message, "✅ Start matni almashtirildi!", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🖊 Caption matni" and m.chat.id in ADMIN_IDS)
def caption_extra_step(message):
    current = db.get_extra_caption()
    current_show = f"<b><i>{current}</i></b>" if current else "<i>(bo'sh)</i>"
    msg = bot.reply_to(
        message,
        f"Hozirgi qo'shimcha caption:\n{current_show}\n\n"
        "📝 Yangi matnni yuboring (barcha videolarga <b>qalin egri</b> formatda qo'shiladi).\n"
        "O'chirish uchun <code>-</code> yuboring:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_caption_extra)

def process_caption_extra(message):
    if message.text in ADMIN_BUTTONS: return
    text = "" if message.text.strip() == "-" else message.text.strip()
    db.set_extra_caption(text)
    if text:
        bot.reply_to(message, f"✅ Qo'shimcha caption saqlandi:\n<b><i>{text}</i></b>",
                     parse_mode="HTML", reply_markup=admin_keyboard())
    else:
        bot.reply_to(message, "✅ Qo'shimcha caption o'chirildi.", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.chat.id in ADMIN_IDS)
def broadcast_step(message):
    msg = bot.reply_to(message,
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing (rasm, video va h.k):",
        reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.text in ADMIN_BUTTONS: return
    users = db.get_all_users()
    succ = 0
    fail = 0
    wait = bot.reply_to(message, "⏳ Xabar tarqatilmoqda...")
    for u in set(users):
        try:
            bot.copy_message(chat_id=u, from_chat_id=message.chat.id, message_id=message.message_id)
            succ += 1
        except Exception:
            fail += 1
    bot.delete_message(message.chat.id, wait.message_id)
    bot.send_message(message.chat.id,
                     f"✅ <b>Xabar yetkazildi!</b>\n✔️ Muvaffaqiyatli: {succ}\n❌ Yetkazilmadi: {fail}",
                     parse_mode="HTML", reply_markup=admin_keyboard())


# ---- YUKLAB OLISH FUNKSIYALARI ----

import requests
import random

# ---- PROXY VA STRATEGIYA SOZLAMALARI ----

FREE_PROXIES = []
LAST_PROXY_UPDATE = 0

def update_proxies():
    """ProxyScrape dan bepul proksilar ro'yxatini yangilaydi."""
    global FREE_PROXIES, LAST_PROXY_UPDATE
    # Har 10 daqiqada bir marta yangilaymiz
    if time.time() - LAST_PROXY_UPDATE < 600 and FREE_PROXIES:
        return
    
    try:
        url = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            proxies = response.text.split('\r\n')
            FREE_PROXIES = [p.strip() for p in proxies if p.strip()]
            LAST_PROXY_UPDATE = time.time()
            print(f"Yangilangan proksilar soni: {len(FREE_PROXIES)}")
    except Exception as e:
        print(f"Proksi olishda xato: {e}")

# Instagram yuklash strategiyalari
INSTAGRAM_STRATEGIES = [
    {"app_id": "936619743392459", "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"},
    {"app_id": "1217981644879628", "ua": "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36"},
    {"app_id": "350685531728", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
]

def download_instagram_cobalt(url):
    """Cobalt API orqali Instagram videosini yuklab olish (No-Login)."""
    try:
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        data = {
            "url": url,
            "vQuality": "720",
            "filenameStyle": "basic"
        }
        response = requests.post(api_url, json=data, headers=headers, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            video_url = res_json.get("url")
            if video_url:
                # Videoni vaqtincha faylga yuklab olamiz
                file_name = f"{DOWNLOAD_FOLDER}/{int(time.time())}.mp4"
                v_res = requests.get(video_url, stream=True, timeout=30)
                if v_res.status_code == 200:
                    with open(file_name, 'wb') as f:
                        for chunk in v_res.iter_content(chunk_size=1024*1024):
                            f.write(chunk)
                    return file_name, "" # Cobalt odatda caption qaytarmaydi
        return None, None
    except Exception as e:
        print(f"Cobalt xatosi: {e}")
        return None, None

def download_instagram(url):
    """Instagram videosini bir necha usul bilan yuklash: Cobalt -> Oddiy -> Proksi."""
    
    # 1. Cobalt API orqali urinib ko'rish (Eng yaxshisi)
    file_path, caption = download_instagram_cobalt(url)
    if file_path:
        return file_path, caption

    # 2. Agar Cobalt ish bermasa, yt-dlp oddiy usul
    update_proxies()
    last_error = ""
    
    for strategy in INSTAGRAM_STRATEGIES:
        ydl_opts = {
            "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "http_headers": {
                "User-Agent": strategy["ua"]
            },
            "extractor_args": {"instagram": {"app_id": strategy["app_id"]}},
            "socket_timeout": 10,
        }
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info), (info.get("description") or info.get("title") or "")
        except Exception as e:
            last_error = str(e)
            if "private" in last_error.lower(): break
            continue

    # 3. Oxirgi chora: Tasodifiy proksilar
    if FREE_PROXIES and "private" not in last_error.lower():
        test_proxies = random.sample(FREE_PROXIES, min(10, len(FREE_PROXIES)))
        for proxy_addr in test_proxies:
            try:
                ydl_opts = {
                    "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
                    "format": "best",
                    "quiet": True,
                    "proxy": f"http://{proxy_addr}",
                    "socket_timeout": 8,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info), (info.get("description") or info.get("title") or "")
            except:
                continue

    raise Exception(last_error)


def download_video(url):
    """yt-dlp bilan video yuklab oladi (TikTok, YouTube Shorts, Pinterest)."""
    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
        "format": "best",
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
    return file_path


def process_video_url(chat_id, url, reply_to_msg_id=None):
    """URL ni yuklab, videoni yuboradi. Guruh va shaxsiy chat uchun umumiy funksiya."""
    try:
        msg = bot.send_message(chat_id, "⏳ Yuklanmoqda...",
                               reply_to_message_id=reply_to_msg_id)
    except:
        msg = bot.send_message(chat_id, "⏳ Yuklanmoqda...")

    try:
        caption = None
        if is_instagram_url(url):
            file_path, caption = download_instagram(url)
        else:
            file_path = download_video(url)

        full_caption = build_full_caption(caption, BOT_USERNAME)
        markup = build_video_markup()

        with open(file_path, "rb") as video:
            bot.send_video(
                chat_id, video,
                caption=full_caption,
                parse_mode="HTML" if full_caption else None,
                reply_markup=markup
            )

        os.remove(file_path)
        bot.delete_message(chat_id, msg.message_id)

    except Exception as e:
        err_msg = str(e)
        print("Xatolik:", err_msg)
        if "private" in err_msg.lower():
            try:
                bot.edit_message_text(
                    "❌ Bu post <b>yopiq (private)</b> profilga tegishli. "
                    "Iltimos, ochiq (public) profil linkini yuboring.",
                    chat_id, msg.message_id, parse_mode="HTML"
                )
            except:
                pass
        elif "login" in err_msg.lower() or "confirm your identity" in err_msg.lower():
            try:
                bot.edit_message_text(
                    "⚠️ Instagram vaqtincha cheklov qo'ydi (Login talab qilinmoqda). "
                    "Birozdan so'ng qayta urinib ko'ring yoki boshqa link yuboring.",
                    chat_id, msg.message_id
                )
            except:
                pass
        else:
            try:
                bot.edit_message_text(
                    "❌ Yuklab bo'lmadi. Havola noto'g'ri yoki Instagramda texnik nosozlik. "
                    "Iltimos, qayta urinib ko'ring.",
                    chat_id, msg.message_id
                )
            except:
                pass


# ---- GURUH HANDLERI (faqat Instagram link) ----

def extract_instagram_url(message):
    """Xabardagi Instagram URL ni topib qaytaradi (text yoki entities dan)."""
    # Oddiy matndan qidirish
    if message.text:
        urls = re.findall(r'https?://(?:www\.)?instagram\.com/\S+', message.text)
        if urls:
            return urls[0]
    # Entities dan URL qidirish (Telegram URL entity sifatida yuborsa)
    if message.entities:
        for entity in message.entities:
            if entity.type == "url":
                url = message.text[entity.offset: entity.offset + entity.length]
                if "instagram.com" in url:
                    return url
    return None

@bot.message_handler(
    func=lambda m: m.chat.type in ["group", "supergroup"] and (
        (m.text and "instagram.com" in m.text) or
        (m.entities and any(
            "instagram.com" in (m.text[e.offset:e.offset+e.length] if m.text else "")
            for e in m.entities if e.type == "url"
        ))
    )
)
def group_instagram_handler(message):
    """Guruhda faqat Instagram linkiga javob beradi."""
    url = extract_instagram_url(message)
    if url:
        process_video_url(message.chat.id, url, reply_to_msg_id=message.message_id)


# ---- SHAXSIY CHAT HANDLERI ----
@bot.message_handler(func=lambda m: m.chat.type == "private")
def downloader(message):
    if not message.text:
        return
    if message.text in ADMIN_BUTTONS:
        return

    # Kanalga a'zolik tekshiruvi
    not_joined = check_join(message.from_user.id)
    if not_joined:
        send_join_request(message.chat.id, not_joined)
        return

    url = message.text

    if "youtube.com" in url and "shorts" not in url:
        bot.reply_to(message, "❌ Faqat YouTube Shorts ishlaydi")
        return

    if not is_supported_url(url):
        bot.reply_to(message, "❌ Menga faqat Instagram (Reels), TikTok, YouTube Shorts yoki Pinterest dan video havolasini yuboring.")
        return

    process_video_url(message.chat.id, url, reply_to_msg_id=message.message_id)


# ---- BOT ISHGA TUSHISHI ----
print("Bot ishga tushdi...")
BOT_USERNAME = get_bot_username()
print(f"Bot username: @{BOT_USERNAME}")

while True:
    try:
        bot.remove_webhook()
        time.sleep(3)  # Telegram'ga eski session'ni yopish uchun vaqt
        bot.infinity_polling(
            timeout=20,
            long_polling_timeout=25,
            allowed_updates=None,
            restart_on_change=False,
        )
    except Exception as e:
        err = str(e)
        print("Bot xato:", err)
        if "409" in err or "Conflict" in err:
            # Telegram long poll timeout 30s — shuning uchun 35s kutamiz
            print("409 Conflict: eski instance to'xtaguncha 35 soniya kutiladi...")
            try:
                bot.stop_polling()
            except:
                pass
            time.sleep(35)
        else:
            time.sleep(3)
