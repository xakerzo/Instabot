import requests
import time
import re

BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
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

def send_message(chat_id, text):
    """Xabar yuborish"""
    try:
        url = f"{BASE_URL}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
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
        
        # Barcha Instagram domainlarini o'zgartirish
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
                        
                        # /start komandasi
                        if text.startswith('/start'):
                            welcome_text = "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!"
                            send_message(chat_id, welcome_text)
                            print(f"✅ Start xabari yuborildi: {chat_id}")
                        
                        # /help komandasi
                        elif text.startswith('/help'):
                            help_text = "Instagram video linkini yuboring, men sizga video tayyorlab beraman!"
                            send_message(chat_id, help_text)
                        
                        # Instagram link tekshirish
                        elif is_instagram_url(text):
                            print(f"📥 Instagram link topildi: {text}")
                            
                            # Linkni o'zgartirish
                            modified_url = modify_instagram_url(text)
                            
                            # VIDEO YUKLANDI xabarini yuborish
                            result_message = "VIDEO YUKLANDI\n\n" + modified_url + "\n\n📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price"
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
