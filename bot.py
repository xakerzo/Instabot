import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Logger sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Tokenni bu yerga qo'yamiz
TOKEN = "8294906702:AAHkYE73B6m5NokLedyUBsUTXib4XdLQ2BE"

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "SALOM! MENGA INSTAGRAM VIDEO LINKINI YUBORING, SIZGA VIDEO QILIB YUBORAMAN!"
    )

# Linklarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "www.instagram.com" in text:
        new_link = text.replace("www.instagram.com", "kkinstagram.com")
        await update.message.reply_text(
            f"Link: {new_link}\n📢 PUBG MOBILE uchun eng arzon UC‑servis: @ZakirShaX_Price"
        )
    else:
        await update.message.reply_text(
            "Bu link xususiy emas yoki boshqa saytga tegishli."
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
