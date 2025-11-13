import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Bot Tokeningiz
TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"

# Foydalanuvchi xabarini qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "www.instagram.com" in text:
        # www.instagram.com ni kkinstagram.com ga o'zgartirish
        new_link = text.replace("www.instagram.com", "kkinstagram.com")
        await update.message.reply_text(
            f"SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING SIZGA VIDEO QILIB YUBORAMAN!\n\n"
            f'LINK: <a href="{new_link}">LINK</a>\n'
            f'📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price',
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Kechirasiz, bu linkni qayta ishlay olmayman yoki xususiy hisob bo‘lishi mumkin."
        )

def main():
    # Botni ishga tushirish
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("🚀 Bot ishga tushdi...")
    # Shu yerda oddiy run_polling() ishlatamiz
    app.run_polling()

if __name__ == "__main__":
    main()
