import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import re
import requests

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Instagram linkni tekshirish
def is_private_instagram_link(url):
    return "instagram.com" in url and not any([
        "reel" in url,
        "p/" in url,
        "tv/" in url
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Salom! Menga Instagram video link yuboring.")

async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" not in text:
        await update.message.reply_text("❌ Iltimos, Instagram link yuboring.")
        return

    # Privat hisobni tekshirish
    if "www.instagram.com" in text:
        if "reel" not in text and "p/" not in text and "tv/" not in text:
            new_link = text.replace("www.instagram.com", "kk.instagram.com")
            await update.message.reply_text(
                f"🔒 Bu privat hisobdagi post ko‘rinmaydi.\n"
                f"🔁 Shu linkni sinab ko‘ring:\n{new_link}"
            )
            return

    # Public video yuklash
    try:
        api_url = f"https://api.sssinstagram.com/api/instagram/video?url={text}"
        r = requests.get(api_url)
        data = r.json()
        if "video" in data and data["video"]:
            await update.message.reply_video(video=data["video"][0])
        else:
            await update.message.reply_text("❌ Video topilmadi.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Xatolik yuz berdi: {e}")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Buyruq noma’lum. Faqat /start yoki Instagram link yuboring.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
