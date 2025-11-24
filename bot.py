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
cursor.execute("""CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT UNIQUE
                 )""")
cursor.execute("""CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                 )""")
conn.commit()


def get_updates(offset=None):
    """Yangiliklarni olish"""
    try:
        url = f"{BASE_URL}/getUpdates"
        params = {"offset": offset, "timeout": 60}
        response = requests.get(url, params=params, timeout=65)
        return response.json()
    except Exception as e:
        print(f"Xatolik yangiliklarni olishda: {e}")
        return {"result": []}


def send_message(chat_id, text, reply_markup=None):
    """Xabar yuborish"""
    try:
        url = f"{BASE_URL}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Xatolik xabar yuborishda: {e}")


def is_instagram_url(url):
    """Instagram linki ekanligini tekshirish"""
    patterns = [
        r'https?://(www\.)?instagram\.com/\S+',
        r'https?://(www\.)?instagr\.am/\S+',
        r'https?://(www\.)?kkinstagram\.com/\S+'
    ]
    return any(re.match(p, url) for p in patterns)


def modify_instagram_url(url):
    """Instagram URL ni o'zgartirish"""
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


def check_subscription(user_id):
    """Foydalanuvchi barcha kanallarga obuna bo'lganligini tekshirish"""
    cursor.execute("SELECT channel FROM channels")
    channels = cursor.fetchall()
    for (channel,) in channels:
        try:
            url = f"{BASE_URL}/getChatMember"
            params = {"chat_id": channel, "user_id": user_id}
            res = requests.get(url, params=params).json()
            status = res.get("result", {}).get("status", "")
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


def get_caption():
    cursor.execute("SELECT value FROM settings WHERE key='caption'")
    row = cursor.fetchone()
    return row[0] if row else ""


def set_caption(text):
    cursor.execute("REPLACE INTO settings (key,value) VALUES ('caption',?)", (text,))
    conn.commit()


def add_channel(channel):
    cursor.execute("INSERT OR IGNORE INTO channels (channel) VALUES (?)", (channel,))
    conn.commit()


def handle_owner_buttons(data):
    chat_id = data["message"]["chat"]["id"]
    text = data["data"]
    if text == "add_channel":
        send_message(chat_id, "Iltimos, kanal usernameini yuboring (misol: @SizningKanal)")
    elif text == "set_caption":
        send_message(chat_id, "Iltimos, video caption matnini yuboring:")


def main():
    print("🤖 Bot ishga tushdi...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)
            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1

                    # Inline tugma bosilishi
                    if "callback_query" in update:
                        handle_owner_buttons(update["callback_query"])
                        continue

                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip()

                        # Owner paneli tugmalari
                        if chat_id == OWNER_ID and text == "/owner":
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "Add Channel", "callback_data": "add_channel"}],
                                    [{"text": "Set Caption", "callback_data": "set_caption"}]
                                ]
                            }
                            send_message(chat_id, "Owner paneli:", keyboard)
                            continue

                        # Owner javoblari (kanal qo'shish)
                        if chat_id == OWNER_ID and text.startswith("@"):
                            add_channel(text)
                            send_message(chat_id, f"Kanal qo'shildi: {text}")
                            continue

                        # Owner caption qo'shish
                        if chat_id == OWNER_ID and text.startswith("caption:"):
                            cap = text.replace("caption:", "").strip()
                            set_caption(cap)
                            send_message(chat_id, f"Caption o'zgartirildi:\n{cap}")
                            continue

                        # Majburiy kanal obunasi
                        if chat_id != OWNER_ID and not check_subscription(chat_id):
                            send_message(chat_id, "Iltimos, barcha majburiy kanallarga obuna bo'ling!")
                            continue

                        # /start
                        if text == "/start":
                            send_message(chat_id, "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING!")
                            continue

                        # Instagram link tekshirish
                        if is_instagram_url(text):
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
