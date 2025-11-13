import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!"
    )

# Xabarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "www.instagram.com" in text:
        new_link = text.replace("www.instagram.com", "kkinstagram.com")
        await update.message.reply_text(
            f'LINK: <a href="{new_link}">LINK</a>\n'
            f'📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price',
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Kechirasiz, bu linkni qayta ishlay olmayman yoki xususiy hisob bo‘lishi mumkin."
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # /start komandasi
    app.add_handler(CommandHandler("start", start))
    
    # Foydalanuvchi matni
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
