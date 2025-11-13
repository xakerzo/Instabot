import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# TOKEN Railway Environment Variable dan olinadi
TOKEN = os.environ.get("TOKEN")

def is_private_instagram(url: str) -> bool:
    """Instagram post public yoki private ekanini tekshiradi"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return True
        if "login" in response.url:
            return True
        return False
    except Exception:
        return True

def modify_private_link(url: str) -> str:
    """Private post linkni kk-instagram variantiga o‘zgartiradi"""
    modified = url.replace("www.instagram.com", "kkinstagram.com")
    modified = modified.replace("kkinstagram..com", "kkinstagram.com")
    return modified

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋 Instagramdan video link yuboring — men uni yuklab beraman!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.search(r"(https?://(www\.)?instagram\.com/[^\s]+)", text)

    if not match:
        await update.message.reply_text("⚠️ Iltimos, to‘g‘ri Instagram link yuboring.")
        return

    url = match.group(0)

    if is_private_instagram(url):
        modified = modify_private_link(url)
        await update.message.reply_text(
            f"🔒 Bu post private hisobga tegishli.\n\n👉 Shu linkdan kirib ko‘rishingiz mumkin:\n{modified}"
        )
        await update.message.reply_text(
            "🎮 PUBG MOBILE uchun eng arzon UC SERVIC — @ZakirShaX_Price"
        )
    else:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            video_tag = soup.find('meta', property='og:video')

            if video_tag:
                video_url = video_tag.get("content")
                await update.message.reply_video(video_url)
                await update.message.reply_text(
                    "🎮 PUBG MOBILE uchun eng arzon UC SERVIC — @ZakirShaX_Price"
                )
            else:
                modified = modify_private_link(url)
                await update.message.reply_text(
                    f"❌ Video topilmadi, lekin linkni o‘zgartirdim:\n{modified}"
                )
                await update.message.reply_text(
                    "🎮 PUBG MOBILE uchun eng arzon UC SERVIC — @ZakirShaX_Price"
                )
        except Exception as e:
            await update.message.reply_text(f"Xatolik yuz berdi: {str(e)}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
