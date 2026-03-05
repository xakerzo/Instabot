import os
import telebot
import yt_dlp
import re
import uuid

# Atrof-muhit o'zgaruvchilari (Railway) dan token va owner_id ni olamiz
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', 'SIZNING_BOT_TOKENINGIZNI_SHU_YERGA_YOZING')
OWNER_ID = os.getenv('OWNER_ID')

bot = telebot.TeleBot(BOT_TOKEN)

# URL naqshlari (Regex)
PATTERNS = {
    'instagram': r'(https?://(?:www\.)?instagram\.com/(?:reel|reels|p)/[\w-]+/?.*)',
    'tiktok': r'(https?://(?:www\.|vt\.|vm\.)?tiktok\.com/.*)',
    'youtube_shorts': r'(https?://(?:www\.)?youtube\.com/shorts/[\w-]+/?.*)',
    'pinterest': r'(https?://(?:www\.)?pinterest\.com/pin/\d+/?.*|https?://pin\.it/[\w]+)'
}

def is_supported_url(url):
    for platform, pattern in PATTERNS.items():
        if re.match(pattern, url):
            return platform
    return None

def download_video(url, output_path):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"Xatolik: {e}")
        return False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "Men quyidagi platformalardan video yuklab bera olaman:\n"
        "📱 <b>Instagram</b> (Reels, Post)\n"
        "🎵 <b>TikTok</b>\n"
        "▶️ <b>YouTube</b> (faqat Shorts)\n"
        "📌 <b>Pinterest</b>\n\n"
        "👇 Menga video havolasini yuboring!"
    )
    bot.reply_to(message, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    platform = is_supported_url(url)
    
    if platform:
        wait_msg = bot.reply_to(message, "⏳ <b>Video yuklanmoqda...</b> Iltimos, kuting.", parse_mode='HTML')
        
        file_id = str(uuid.uuid4())
        output_file = f"{file_id}.mp4"
        
        success = download_video(url, output_file)
        
        bot.delete_message(message.chat.id, wait_msg.message_id)

        if success and os.path.exists(output_file):
            try:
                with open(output_file, 'rb') as video:
                    bot.send_video(
                        chat_id=message.chat.id,
                        video=video,
                        caption="✅ Sizning videongiz tayyor!",
                        reply_to_message_id=message.message_id
                    )
            except Exception as e:
                bot.reply_to(message, "❌ Videoni Telegramga yuklashda xatolik yuz berdi. (Hajmi juda katta bo'lishi mumkin)")
            finally:
                if os.path.exists(output_file):
                    os.remove(output_file)
        else:
            bot.reply_to(message, "❌ <b>Kechirasiz, videoni yuklab olib bo'lmadi.</b>\nLink to'g'riligini va ochiq hisobdagi video ekanligini tekshiring.", parse_mode='HTML')
            if os.path.exists(output_file):
                os.remove(output_file)
    else:
        error_text = (
            "⚠️ <b>Kechirasiz, bu link noto'g'ri yoki men bunday havolalardan yuklamayman!</b>\n\n"
            "Faqat quyidagilarni yuboring:\n"
            "➥ <code>instagram.com/reel/...</code>\n"
            "➥ <code>tiktok.com/...</code>\n"
            "➥ <code>youtube.com/shorts/...</code>\n"
            "➥ <code>pinterest.com/pin/...</code>"
        )
        bot.reply_to(message, error_text, parse_mode='HTML')

if __name__ == '__main__':
    print("🚀 Bot dasturi ishga tushdi...")
    try:
        bot.remove_webhook()
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Bot ishida xatolik: {e}")
