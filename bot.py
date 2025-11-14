import requests
import time
import json

BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"  # @BotFather dan olingan tokenni qo'ying
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

def send_video(chat_id, video_url, caption=""):
    """Video yuborish"""
    try:
        url = f"{BASE_URL}/sendVideo"
        data = {"chat_id": chat_id, "video": video_url, "caption": caption}
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Xatolik video yuborishda: {e}")

def download_instagram_video(url):
    """
    Instagram video yuklab olish (DEMO)
    Haqiqiy loyiha uchun instaloader yoki API ishlating
    """
    try:
        # DEMO: Haqiqiy yuklab olish o'rniga test video
        # Bu yerda o'zingizning yuklab olish logikangizni qo'shing
        demo_video = "https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4"
        return demo_video
    except Exception as e:
        print(f"Yuklab olish xatosi: {e}")
        return None

def main():
    print("🤖 Bot ishga tushdi...")
    last_update_id = None
    
    while True:
        try:
            # Yangiliklarni olish
            updates = get_updates(last_update_id)
            
            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    last_update_id = update["update_id"] + 1
                    
                    if "message" in update:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "")
                        
                        print(f"📨 Yangi xabar: {text}")
                        
                        # /start komandasi
                        if text.startswith('/start'):
                            welcome_text = "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!"
                            send_message(chat_id, welcome_text)
                            print(f"✅ Start xabari yuborildi: {chat_id}")
                        
                        # Instagram link tekshirish
                        elif "instagram.com" in text.lower():
                            print(f"📥 Instagram link topildi: {text}")
                            send_message(chat_id, "📥 Video yuklanmoqda...")
                            
                            # Domen nomini o'zgartirish
                            modified_url = text.replace("www.instagram.com", "kkinstagram.com")
                            modified_url = modified_url.replace("instagram.com", "kkinstagram.com")
                            
                            print(f"🔗 O'zgartirilgan URL: {modified_url}")
                            
                            # Video yuklab olish
                            video_url = download_instagram_video(modified_url)
                            
                            if video_url:
                                send_video(chat_id, video_url, "🎥 Sizning video")
                                send_message(chat_id, "📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakazUz_Price")
                                print(f"✅ Video yuborildi: {chat_id}")
                            else:
                                send_message(chat_id, "❌ Video yuklab olishda xatolik yuz berdi")
                                print(f"❌ Video yuklab olish xatosi: {chat_id}")
                        
                        # Boshqa xabarlar
                        elif text:
                            send_message(chat_id, "Iltimos, faqat Instagram video linkini yuboring!")
                            print(f"❌ Noto'g'ri xabar: {text}")
            
            # Kichik tanaffus
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Asosiy tsikl xatosi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
