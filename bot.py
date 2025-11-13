import os
import re
import logging
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram TOKENni environment variable dan olish
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    logger.error("❌ TOKEN topilmadi! Environment variable TOKEN ni tekshiring.")
    exit(1)

# Public/Private Instagram linkni aniqlash uchun regex
INSTAGRAM_URL_REGEX = r"(https?://(?:www\.)?instagram\.com/[\w/?=&.-]+)"

# Xabarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text.strip()
    match = re.search(INSTAGRAM_URL_REGEX, msg_text)

    if not match:
        await update.message.reply_text("❌ Iltimos, haqiqiy Instagram link yuboring.")
        return

    url = match.group(0)

    try:
        # Public videolarni API orqali olish (bu misol uchun sssinstagram API)
        api_url = f"https://api.sssinstagram.com/api/instagram/video?url={url}"
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=15.0)
            if response.status_code == 200 and "video_url" in response.json():
                video_url = response.json()["video_url"]
                await update.message.reply_video(video_url)
            else:
                # Public video topilmasa private linkni o'zgartirib qaytarish
                private_url = url.replace("www.instagram.com", "kkinstagram.com")
                await update.message.reply_text(
                    f"❌ Bu ehtimol *xususiy (private)* hisobdagi video.\n\n"
                    f"Sizga linkni qaytardim: {private_url}\n\n"
                    "PUBG MOBILE uchun eng arzon UC SERVIC: @ZakirShaX_Price",
                    parse_mode="Markdown"
                )
    except Exception as e:
        logger.error(f"Xatolik yuz berdi: {e}")
        await update.message.reply_text(
            "❌ Kechirasiz, videoni yuklab bo‘lmadi.\n"
            "Bu ehtimol *xususiy (private)* hisobdagi video bo‘lishi mumkin."
        )

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Instagram video bot ishga tushdi ✅\n"
                                    "Link yuboring va video yuklab oling.")

def main():
    # Botni ishga tushirish
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
