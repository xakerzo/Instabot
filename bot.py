import requests
import time
import re

BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
OWNER_ID = 1373647  # Sizning Telegram ID
CHANNEL_USERNAME = "@SizningKanal"  # Majburiy obuna bo'lishi kerak bo'lgan kanal
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


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
            data["reply_markup"] = reply_markup
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Xatolik xabar yuborishda: {e}")


def is_instagram_url(url):
    """Instagram linki ekanligini tekshirish"""
    instagram_patterns = [
        r'https?://(www\.)?instagram\.com/\S+',
        r'https?://(www\.)?instagr\.am/\S+',
        r'https?://(www\.)?kkinstagram\.com/\S+'
    ]
    for pattern in instagram_patterns:
        if re.match(pattern, url):
            return True
    return False


def modify_instagram_url(original_url):
    """Instagram URL ni o'zgartirish"""
    try:
        modified_url = original_url
        replacements = [
            ("www.instagram.com", "kkinstagram.com"),
            ("instagram.com", "kkinstagram.com"),
            ("instagr.am", "kkinstagram.com"),
            ("www.instagr.am", "kkinstagram.com"),
        ]
        for old_domain, new_domain in replacements:
            if old_domain in modified_url:
                modified_url = modified_url.replace(old_domain, new_domain)
                break
        return modified_url
    except Exception as e:
        print(f"URL o'zgartirish xatosi: {e}")
        return original_url


def check_subscription(user_id):
    """Foydalanuvchi kanalga obuna bo'lganligini tekshirish"""
    try:
        url = f"{BASE_URL}/getChatMember"
        params = {"chat_id": CHANNEL_USERNAME, "user_id": user_id}
        response = requests.get(url, params=params).json()
        status = response.get("result", {}).get("status", "")
        return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Obuna tekshirish xatolik: {e}")
        return False


def main():
    print("🤖 Instagram Link Converter Bot ishga tushdi...")
    last_update_id = None

    while True:
        try:
            updates = get_updates(last_update_id)

            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1

                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "").strip()

                        print(f"📨 Yangi xabar: {chat_id} - {text}")

                        # Majburiy kanalga obuna bo'lmagan foydalanuvchilar uchun
                        if chat_id != OWNER_ID and not check_subscription(chat_id):
                            subscribe_text = f"Iltimos, botdan foydalanishdan oldin {CHANNEL_USERNAME} kanaliga obuna bo'ling!"
                            send_message(chat_id, subscribe_text)
                            continue

                        # /start komandasi
                        if text.startswith('/start'):
                            welcome_text = "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!"
                            send_message(chat_id, welcome_text)
                            print(f"✅ Start xabari yuborildi: {chat_id}")

                        # /help komandasi
                        elif text.startswith('/help'):
                            help_text = "Instagram video linkini yuboring, men sizga video tayyorlab beraman!"
                            send_message(chat_id, help_text)

                        # Owner uchun broadcast tugmasi
                        elif chat_id == OWNER_ID and text.startswith('/broadcast'):
                            msg = text.replace('/broadcast', '').strip()
                            if msg:
                                # Broadcast qilinadi
                                send_message(chat_id, f"Broadcast yuborildi: {msg}")
                                # Foydalanuvchilarga yuborish
                                print(f"📢 Owner broadcast: {msg}")
                                # Real foydalanuvchilar ro'yxatini saqlash kerak bo'ladi, bu yerda demo
                            else:
                                send_message(chat_id, "Broadcast matnini kiriting: /broadcast Xabar matni")

                        # Instagram link tekshirish
                        elif is_instagram_url(text):
                            print(f"📥 Instagram link topildi: {text}")

                            # Linkni o'zgartirish
                            modified_url = modify_instagram_url(text)

                            # VIDEO YUKLANDI xabarini yuborish + qo'shimcha caption
                            extra_caption = "\n\n📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price"
                            result_message = f"VIDEO YUKLANDI ✅\n\n{modified_url}{extra_caption}"
                            send_message(chat_id, result_message)

                            print(f"✅ Link o'zgartirildi: {modified_url}")

                        # Boshqa xabarlar
                        elif text and not text.startswith('/'):
                            error_message = "Iltimos, faqat Instagram video linkini yuboring!"
                            send_message(chat_id, error_message)
                            print(f"❌ Noto'g'ri xabar: {text}")

            time.sleep(1)

        except Exception as e:
            print(f"❌ Xatolik: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
