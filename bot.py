import os
import requests
import json
from urllib.parse import urlparse

# Telegram Bot API dan to'g'ridan-to'g'ri foydalanish
BOT_TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, data=data)

def send_video(chat_id, video_url, caption=""):
    url = f"{BASE_URL}/sendVideo"
    data = {"chat_id": chat_id, "video": video_url, "caption": caption}
    requests.post(url, data=data)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    response = requests.get(url, params=params)
    return response.json()

def handle_updates():
    last_update_id = None
    
    while True:
        updates = get_updates(last_update_id)
        
        if "result" in updates:
            for update in updates["result"]:
                last_update_id = update["update_id"] + 1
                
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")
                    
                    # Start komandasi
                    if text.startswith('/start'):
                        send_message(chat_id, "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!")
                    
                    # Instagram linklarini tekshirish
                    elif "instagram.com" in text or "kkinstagram.com" in text:
                        send_message(chat_id, "📥 Video yuklanmoqda...")
                        
                        try:
                            # Domen nomini o'zgartirish
                            modified_url = text.replace("www.instagram.com", "kkinstagram.com")
                            
                            # Video yuklab olish (sizning logikangiz)
                            video_url = download_instagram_video(modified_url)
                            
                            if video_url:
                                send_video(chat_id, video_url, "🎥 Sizning video")
                                send_message(chat_id, "📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price")
                            else:
                                send_message(chat_id, "❌ Video yuklab olishda xatolik yuz berdi")
                                
                        except Exception as e:
                            send_message(chat_id, f"❌ Xatolik: {str(e)}")
                    
                    else:
                        send_message(chat_id, "Iltimos, faqat Instagram video linkini yuboring!")

def download_instagram_video(url):
    """
    Instagram videoni yuklab olish funksiyasi
    Bu yerda siz o'zingizning yuklab olish logikangizni qo'shing
    """
    try:
        # DEMO: Haqiqiy yuklab olish logikasi o'rniga demo URL
        # Haqiqiy loyiha uchun instaloader yoki API ishlating
        
        # Misol demo video
        demo_video_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
        
        return demo_video_url
        
    except Exception as e:
        print(f"Download error: {e}")
        return None

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    handle_updates()
