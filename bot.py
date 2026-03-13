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

# Instagram uchun shunchaki kkinstagram linkiga aylantirib beramiz
# Instagram uchun kkinstagram orqali videoni ko'chirib olamiz
def download_instagram(url):
    """Instagram videosini kkinstagram.com orqali botga ko'chirib oladi."""
    try:
        # Linkni fixerga o'zgartiramiz
        fixer_url = url.replace("instagram.com", "kkinstagram.com")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }
        
        # Saytni ochib, ichidagi video manzilini qidiramiz
        res = requests.get(fixer_url, headers=headers, timeout=15)
        if res.status_code == 200:
            import re
            html = res.text
            # Video linkini qidiramiz
            match = re.search(r'property="og:video" content="([^"]+)"', html)
            if not match:
                match = re.search(r'name="twitter:player:stream" content="([^"]+)"', html)
            
            # Captionni qidiramiz
            c_match = re.search(r'property="og:description" content="([^"]+)"', html)
            original_caption = c_match.group(1) if c_match else None
            
            if match:
                video_url = match.group(1).replace("&amp;", "&")
                file_name = f"{DOWNLOAD_FOLDER}/insta_{int(time.time())}.mp4"
                
                # Videoni botga yuklab olamiz
                v_res = requests.get(video_url, stream=True, timeout=30)
                if v_res.status_code == 200:
                    with open(file_name, 'wb') as f:
                        for chunk in v_res.iter_content(chunk_size=1024*1024):
                            if chunk: f.write(chunk)
                    
                    if os.path.exists(file_name) and os.path.getsize(file_name) > 10000:
                        return file_name, original_caption

        return "LINK_ONLY", fixer_url
    except Exception:
        return "LINK_ONLY", url.replace("instagram.com", "kkinstagram.com")


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
        if is_instagram_url(url):
            # Instagram uchun link rejimini tekshiramiz
            file_path, link_or_caption = download_instagram(url)
            
            if file_path == "LINK_ONLY":
                bot.delete_message(chat_id, msg.message_id) # "Yuklanmoqda"ni o'chiramiz
                # KK-Link rejimi uchun xabar formatlash
                text = (
                    f"📩 <b>SIZNING VIDEOYINGIZ TAYYOR!</b>\n\n"
                    f"{link_or_caption}\n\n"
                    f"🤖 @{BOT_USERNAME}"
                )
                bot.send_message(chat_id, text, parse_mode="HTML", reply_to_message_id=reply_to_msg_id)
                return
            
            caption = link_or_caption
        else:
            file_path = download_video(url)
            caption = None

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
        
        # Agat post private bo'lsa
        if "private" in err_msg.lower():
            try:
                bot.edit_message_text(
                    "❌ Bu post <b>yopiq (private)</b> profilga tegishli. "
                    "Iltimos, ochiq (public) profil linkini yuboring.",
                    chat_id, msg.message_id, parse_mode="HTML"
                )
            except: pass
            return

        # AGAR YUKLAB BO'LMASA -> KKINSTAGRAM FALLBACK
        # Bu usulda Telegramning o'zi videoni ko'rsatib beradi
        try:
            fixer_link = url.replace("instagram.com", "kkinstagram.com")
            bot.delete_message(chat_id, msg.message_id) # "Yuklanmoqda"ni o'chiramiz
            
            fallback_text = (
                "⚠️ <b>To'g'ridan-to'g'ri yuklab bo'lmadi.</b>\n"
                "Lekin ushbu havola orqali videoni ko'rishingiz mumkin:\n\n"
                f"{fixer_link}"
            )
            bot.send_message(chat_id, fallback_text, parse_mode="HTML", reply_to_message_id=reply_to_msg_id)
        except Exception as fe:
            print(f"Fallback xatosi: {fe}")
            try:
                bot.edit_message_text("❌ Yuklab bo'lmadi. Havola vaqtincha bloklangan.", chat_id, msg.message_id)
            except: pass


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
