import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Token config.py yoki Railway Variables dan olinadi
TOKEN = os.getenv("TOKEN")

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Instagramdan video link yuboring! Men uni yuklab beraman!"
    )

# Instagram videoni olish funksiyasi
def get_instagram_video(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    response = requests.get(url, headers=headers)
    if "login" in response.url or "private" in response.text.lower():
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    video_tag = soup.find("meta", property="og:video")

    if video_tag and video_tag.get("content"):
        return video_tag["content"]
    return None

# Asosiy xabarni qayta ishlovchi funksiya
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "instagram.com" not in url:
        await update.message.reply_text("Iltimos, to‘g‘ri Instagram link yuboring.")
        return

    # Video olishga harakat
    video_url = get_instagram_video(url)

    if video_url:
        # Ochiq akkauntdagi video topildi
        await update.message.reply_video(video_url)
        await update.message.reply_text("🎥 VIDEO YUKLANDI, KO‘CHIRIB OLISHINGIZ MUMKIN ✅\n\nPUBG MOBILE uchun eng arzon UC servis 👉 @ZakirShaX_Price")
    else:
        # Privat yoki login talab qiladigan akkaunt
        new_link = re.sub(r"www\.instagram\.com", "kkinstagram.com", url)
        await update.message.reply_text(
            f"🎥 VIDEO YUKLANDI, KO‘CHIRIB OLISHINGIZ MUMKIN ✅\n\nPUBG MOBILE uchun eng arzon UC servis 👉 @ZakirShaX_Price\n\n🔗 {new_link}"
        )

# Asosiy ishga tushirish funksiyasi
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
