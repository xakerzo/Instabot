import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
from database import Database
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
# Agar OWNER_ID ichida vergullar bilan bir nechta admin bo'lsa ularni array (list) ga aylantirib olamiz:
admin_env = os.getenv("OWNER_ID", "")
ADMIN_IDS = [int(i.strip()) for i in admin_env.split(',') if i.strip().isdigit()]

bot = telebot.TeleBot(TOKEN)
db = Database()

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Majburiy obunani tekshirish (faqat kanallarni qaytaradi, qaysikiga a'zo bo'lmasa)
def check_join(user_id):
    channels = db.get_channels()
    not_joined = []
    
    # Agar admin bo'lsa teksirmaydi
    if user_id in ADMIN_IDS:
        return []

    for ch_id, ch_url in channels:
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append((ch_id, ch_url))
        except Exception as e:
            # Agar bot kanalga admin qilinmagan bo'lsa yoki kanal yo'q bo'lsa tekshira olmaydi
            pass
    return not_joined

def send_join_request(chat_id, not_joined_channels):
    markup = InlineKeyboardMarkup()
    for i, (ch_id, ch_url) in enumerate(not_joined_channels, start=1):
        markup.add(InlineKeyboardButton(text=f"📢 {i}-kanalga qo'shilish", url=ch_url))
    markup.add(InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_join"))
    bot.send_message(chat_id, "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz kerak!</b>", parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    not_joined = check_join(call.from_user.id)
    if not_joined:
        bot.answer_callback_query(call.id, "❌ Siz hali kanallarga a'zo bo'lmadingiz!", show_alert=True)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ <b>Obuna tasdiqlandi! Endi menga video linkini yuborishingiz mumkin.</b>", parse_mode="HTML")

# --- ADMIN PANEL TUGMALARI ---
ADMIN_BUTTONS = ["📊 Statistika", "📢 Broadcast", "➕ Kanal qo'shish", "➖ Kanalni o'chirish", "📝 Start matnini o'zgartirish"]

def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton(ADMIN_BUTTONS[0]), KeyboardButton(ADMIN_BUTTONS[1]))
    markup.add(KeyboardButton(ADMIN_BUTTONS[2]), KeyboardButton(ADMIN_BUTTONS[3]))
    markup.add(KeyboardButton(ADMIN_BUTTONS[4]))
    return markup


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
        # Userlarga oddiy menyusiz jo'natish (agar hohlasangiz userlarga ham menyu qo'shsa bo'ladi)
        bot.send_message(message.chat.id, text, reply_markup=telebot.types.ReplyKeyboardRemove())


# --- ADMIN FUNKSIYALAR ---
@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.chat.id in ADMIN_IDS)
def stat_handler(message):
    count = db.count_users()
    bot.reply_to(message, f"📊 <b>Bot foydalanuvchilari soni:</b> {count} ta", parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text == "➕ Kanal qo'shish" and m.chat.id in ADMIN_IDS)
def add_channel_step(message):
    msg = bot.reply_to(message, "📝 Kanal ma'lumotlarini quyidagi formatda yuboring:\n<code>@kanal_useri https://t.me/kanal_linki</code>\n\nYoki maxfiy kanallar uchun (bot kanalda admin bo'lishi shart!):\n<code>-100123456789 https://t.me/link</code>", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    if message.text in ADMIN_BUTTONS:
         # Agar admin boshqa tugma bossa bekor bo'ladi
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
     bot.reply_to(message, f"✅ Kanal {message.text} ochiirilgan bo'lsa bas, endi bu kanal tekshirilmaydi.")

@bot.message_handler(func=lambda m: m.text == "📝 Start matnini o'zgartirish" and m.chat.id in ADMIN_IDS)
def start_text_step(message):
    msg = bot.reply_to(message, f"Hozirgi matn:\n\n<code>{db.get_start_text()}</code>\n\n📝 Yangi matnni yuboring:", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_start_text)

def process_start_text(message):
    if message.text in ADMIN_BUTTONS: return
    db.set_start_text(message.text)
    bot.reply_to(message, "✅ Start matni almashtirildi!")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.chat.id in ADMIN_IDS)
def broadcast_step(message):
    msg = bot.reply_to(message, "Yuza barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing (rasm, video va h.k):", reply_markup=telebot.types.ReplyKeyboardRemove())
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
    bot.send_message(message.chat.id, f"✅ <b>Xabar yetkazildi!</b>\n✔️ Muvaffaqiyatli: {succ}\n❌ Yetkazilmadi (bloklangan): {fail}", parse_mode="HTML", reply_markup=admin_keyboard())


# --- YUKLAB OLISH (DOWNLOADER) QISMI ---
def download_video(url):
    ydl_opts = {
        "outtmpl": f"{DOWNLOAD_FOLDER}/%(id)s.%(ext)s",
        "format": "best",
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
    return file_path

@bot.message_handler(func=lambda m: True)
def downloader(message):
    # Oddiy matnlarni ushlab qolmasligi uchun.
    if message.text in ADMIN_BUTTONS:
        return

    # Avval kanallarga a'zolik tekshiriladi
    not_joined = check_join(message.from_user.id)
    if not_joined:
        send_join_request(message.chat.id, not_joined)
        return

    url = message.text

    if "youtube.com" in url and "shorts" not in url:
        bot.reply_to(message, "❌ Faqat YouTube Shorts ishlaydi")
        return

    if not ("instagram.com" in url or "tiktok.com" in url or "youtube.com/shorts" in url or "pinterest.com" in url or "pin.it" in url):
        bot.reply_to(message, "❌ Menga faqat Instagram (Reels), TikTok, YouTube Shorts yoki Pinterest dan video havolasini yuboring.")
        return

    msg = bot.reply_to(message, "⏳ Yuklanmoqda...")

    try:
        file_path = download_video(url)
        with open(file_path, "rb") as video:
            bot.send_video(message.chat.id, video)
        
        # Kesib olgandan kegin o'chirib tashlaymiz
        os.remove(file_path)
        bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        bot.reply_to(message, f"❌ Yuklab bo‘lmadi. Yuborgan linkingiz ochiq (public) ekanligini tekshiring.")
        print("Xatolik: ", e)


print("Bot ishga tushdi...")
try:
    bot.remove_webhook()
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
except Exception as e:
    print(e)