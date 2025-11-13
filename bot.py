# bot.py
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from config import TOKEN  # TOKEN ni config.py dan oladi

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sizning video yuklash funksiyangiz (placeholder)
def download_instagram_video(url):
    """
    Bu funksiya ochiq videolarni yuklash uchun ishlatiladi.
    Agar video topilsa, video fayl yoki URL qaytaradi.
    Agar private bo'lsa, None qaytaradi.
    """
    # Hozirgi kodda faqat simulyatsiya qilamiz
    if "instagram.com" in url and "private" not in url:
        return url  # Ochiq video uchun URL yoki fayl
    else:
        return None  # Private yoki xato

# Linkni tekshirish va qayta ishlash
def process_instagram_link(url):
    try:
        video_data = download_instagram_video(url)
        if video_data:
            return {"type": "video", "data": video_data}
        else:
            modified_link = url.replace("www.instagram.com", "kkinstagram.com")
            return {"type": "link", "data": modified_link}
    except Exception:
        modified_link = url.replace("www.instagram.com", "kkinstagram.com")
        return {"type": "link", "data": modified_link}

# Xabar handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    url = message.text.strip()
    
    result = process_instagram_link(url)
    if result["type"] == "video":
        await message.reply_video(result["data"])
        # Qo'shimcha xabar
        await message.reply_text(
            "PUBG MOBILE uchun eng arzon UC SERVIC @ZakirShaX_Price"
        )
    else:
        await message.reply_text(
            f"*VIDEO YUKLANDI! KO'CHIRIB OLISHINGIZ MUMKIN*\nLink: {result['data']}",
            parse_mode="Markdown",
        )
        # Qo'shimcha xabar
        await message.reply_text(
            "PUBG MOBILE uchun eng arzon UC SERVIC @ZakirShaX_Price"
        )

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Instagramdan video link yuboring! Men uni yuklab beraman!"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start))

    # Botni ishga tushirish
    logger.info("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
