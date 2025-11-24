import requests
import time
import re
import sqlite3
import json

BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
OWNER_ID = 1373647
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- SQLite tayyorlash ----------
conn = sqlite3.connect("bot_data.db")
cursor = conn.cursor()

# Foydalanuvchilar
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY
                 )""")

# Majburiy kanallar
cursor.execute("""CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT UNIQUE
                 )""")

# Settings (caption va state)
cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                 )""")

# Tasdiqlangan foydalanuvchilar
cursor.execute("""CREATE TABLE IF NOT EXISTS subscribed_users (
                    user_id INTEGER PRIMARY KEY
                 )""")

conn.commit()

# ---------- Telegram funktsiyalari ----------
def get_updates(offset=None):
    try:
        url = f"{BASE_URL}/getUpdates"
        params = {"offset": offset, "timeout": 60}
        response = requests.get(url, params=params, timeout=65)
        return response.json()
    except Exception as e:
        print(f"Xatolik yangiliklarni olishda: {e}")
        return {"result": []}

def send_message(chat_id, text, reply_markup=None):
    try:
        url = f"{BASE_URL}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        requests.post(url, data=data)
    except Exception as e:
        print(f"Xatolik xabar yuborishda: {e}")

# ---------- Instagram funktsiyalari ----------
def is_instagram_url(url):
    patterns = [
        r'https?://(www\.)?instagram\.com/\S+',
        r'https?://(www\.)?instagr\.am/\S+',
        r'https?://(www\.)?kkinstagram\.com/\S+'
    ]
    return any(re.match(p, url) for p in patterns)

def modify_instagram_url(url):
    replacements = [
        ("www.instagram.com", "kkinstagram.com"),
        ("instagram.com", "kkinstagram.com"),
        ("instagr.am", "kkinstagram.com"),
        ("www.instagr.am", "kkinstagram.com"),
    ]
    for old, new in replacements:
        if old in url:
            return url.replace(old, new)
    return url

# ---------- User & Caption & Channel funktsiyalari ----------
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

def check_subscription(user_id):
    channels = get_channels()
    for channel in channels:
        try:
            url = f"{BASE_URL}/getChatMember"
            params = {"chat_id": channel, "user_id": user_id}
            res = requests.get(url, params=params).json()
            status = res.get("result", {}).get("status", "")
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            print(f"Xato kanal tekshiruvda: {channel}")
            return False
    return True

def mark_subscribed(user_id):
    cursor.execute("INSERT OR IGNORE INTO subscribed_users (user_id) VALUES (?)", (user_id,))
    conn.commit()

def is_subscribed(user_id):
    cursor.execute("SELECT user_id FROM subscribed_users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

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

# ---------- Owner tugmalarini boshqarish ----------
def handle_owner_buttons(data):
    chat_id = data["message"]["chat"]["id"]
    button = data["data"]
    if button == "broadcast":
        set_state("broadcast")
        send_message(chat_id, "Matn yuboring (bu barcha foydalanuvchilarga jo‘natiladi):")
    elif button == "caption_add":
        set_state("caption")
        send_message(chat_id, "Iltimos, video caption matnini yuboring:")
    elif button == "caption_view":
        cap = get_caption()
        msg = cap if cap else "Hozircha caption yo'q."
        send_message(chat_id, msg)
    elif button == "caption_delete":
        delete_caption()
        send_message(chat_id, "Caption o‘chirildi ✅")
    elif button == "channel_add":
        set_state("channel_add")
        send_message(chat_id, "Kanal username yuboring (misol: @SizningKanal)")
    elif button == "channel_delete":
        channels = get_channels()
        msg = "Kanallar:\n" + "\n".join(channels) if channels else "Hozircha kanal yo'q."
        set_state("channel_delete")
        send_message(chat_id, msg + "\nO‘chirish uchun kanal username yuboring:")
    elif button == "channel_check":
        channels = get_channels()
        msg = "Kanallar:\n" + "\n".join(channels) if channels else "Hozircha kanal yo'q."
        send_message(chat_id, msg)
    elif button == "user_count":
        count = len(get_users())
        send_message(chat_id, f"Botdagi foydalanuvchilar soni: {count}")
    elif button == "confirm_subscription":
        if check_subscription(chat_id):
            mark_subscribed(chat_id)
            send_message(chat_id, "✅ Siz barcha majburiy kanallarga obuna bo‘ldingiz. Endi botni ishlatishingiz mumkin!")
        else:
            send_message(chat_id, "❌ Siz hali barcha kanallarga obuna bo‘lmadingiz! Iltimos, barcha kanallarga obuna bo‘ling va qayta tasdiqlang.")

# ---------- Main Loop ----------
def main():
    print("🤖 Bot ishga tushdi...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)
            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1

                    # Callback tugma bosilishi
                    if "callback_query" in update:
                        handle_owner_buttons(update["callback_query"])
                        continue

                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip()

                        # Foydalanuvchilar ro'yxatiga qo'shish
                        if chat_id != OWNER_ID:
                            add_user(chat_id)

                        # Owner xabarlarini state bo‘yicha boshqarish
                        if chat_id == OWNER_ID:
                            state = get_state()
                            if state == "broadcast":
                                for uid in get_users():
                                    if uid != OWNER_ID:
                                        send_message(uid, text)
                                send_message(chat_id, "Broadcast yuborildi ✅")
                                clear_state()
                                continue
                            elif state == "caption":
                                set_caption(text)
                                send_message(chat_id, f"Caption saqlandi ✅\n{text}")
                                clear_state()
                                continue
                            elif state == "channel_add":
                                add_channel(text)
                                send_message(chat_id, f"Kanal qo'shildi: {text}")
                                clear_state()
                                continue
                            elif state == "channel_delete":
                                delete_channel(text)
                                send_message(chat_id, f"Kanal o‘chirildi: {text}")
                                clear_state()
                                continue

                            # /start owner
                            if text == "/start":
                                keyboard = {
                                    "inline_keyboard": [
                                        [{"text":"Broadcast","callback_data":"broadcast"}],
                                        [{"text":"Caption Qo‘shish","callback_data":"caption_add"},
                                         {"text":"Caption Ko‘rish","callback_data":"caption_view"},
                                         {"text":"Caption O‘chirish","callback_data":"caption_delete"}],
                                        [{"text":"Kanal Qo‘shish","callback_data":"channel_add"},
                                         {"text":"Kanal O‘chirish","callback_data":"channel_delete"},
                                         {"text":"Kanal Tekshirish","callback_data":"channel_check"}],
                                        [{"text":"Foydalanuvchilar soni","callback_data":"user_count"}]
                                    ]
                                }
                                send_message(chat_id, "Owner paneli:", keyboard)
                                continue

                        # ---------- Majburiy kanal tekshiruvi ----------
                        if chat_id != OWNER_ID:
                            channels = get_channels()
                            if channels and not is_subscribed(chat_id):
                                if not check_subscription(chat_id):
                                    buttons = [[{"text": ch, "url": f"https://t.me/{ch.replace('@','')}"}] for ch in channels]
                                    buttons.append([{"text": "✅ Tasdiqladim", "callback_data": "confirm_subscription"}])
                                    reply_markup = {"inline_keyboard": buttons}
                                    send_message(chat_id, "Iltimos, barcha majburiy kanallarga obuna bo‘ling va tasdiqlang!", reply_markup)
                                    continue
                                else:
                                    mark_subscribed(chat_id)

                        # /start foydalanuvchi
                        if text == "/start":
                            send_message(chat_id, "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING!")
                            continue

                        # Instagram link
                        if is_instagram_url(text):
                            if channels and not is_subscribed(chat_id):
                                continue
                            modified_url = modify_instagram_url(text)
                            caption = get_caption()
                            msg_text = f"VIDEO YUKLANDI ✅\n\n{modified_url}"
                            if caption:
                                msg_text += f"\n\n{caption}"
                            send_message(chat_id, msg_text)
                            continue

                        # Boshqa xabar
                        send_message(chat_id, "Iltimos, faqat Instagram video linkini yuboring!")

            time.sleep(1)
        except Exception as e:
            print(f"❌ Xatolik: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
