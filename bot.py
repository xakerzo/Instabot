import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests
<<<<<<< HEAD

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

=======
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# TOKEN .env yoki Railway Variables ichidan olinadi
TOKEN = os.getenv("TOKEN")

# --- Instagram videoni yuklab olish funksiyasi ---
def download_instagram_video(insta_url):
    try:
        # Yangi, barqaror API
        api_url = f"https://api.instavideosave.net/allinone?url={insta_url}"
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Agar video topilgan bo‘lsa
        if "url" in data and len(data["url"]) > 0:
            video_url = data["url"][0]["url"]
            return video_url
        else:
            return None

    except Exception as e:
        print(f"Xatolik: {e}")
        return None


# --- /start buyrug‘i ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\n"
        "📥 Menga *Instagram video link* yuboring — men sizga videoni yuklab beraman.\n\n"
        "⚠️ Eslatma: faqat *ommaviy (public)* postlardan video yuklab olinadi.",
        parse_mode="Markdown"
    )


# --- Asosiy xabarlarni qayta ishlovchi funksiya ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # faqat Instagram linklarini qayta ishlaymiz
    if "instagram.com" not in text:
        await update.message.reply_text("⚠️ Iltimos, faqat Instagram video havolasini yuboring.")
        return

    # Privat akkauntni aniqlash
    if "instagram.com" in text and "?" not in text:
        # privat hisoblarda faqat linkni almashtiramiz
        new_link = text.replace("www.instagram.com", "kk.instagram.com")
        await update.message.reply_text(
            f"🔒 Bu video privat hisobdan bo‘lishi mumkin.\n"
            f"Mana sizga yangilangan link:\n{new_link}"
        )
        return

    await update.message.reply_text("⏳ Video yuklab olinmoqda, biroz kuting...")

    video_url = download_instagram_video(text)

    if video_url:
        try:
            await update.message.reply_video(video_url)
            await update.message.reply_text(
                "🎯 Video muvaffaqiyatli yuklab olindi!\n\n"
                "🔥 PUBG MOBILE uchun eng arzon UC servis — @ZakirShaX_Price"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Xatolik yuz berdi: {e}")
    else:
        await update.message.reply_text(
            "❌ Kechirasiz, videoni yuklab bo‘lmadi.\n"
            "Bu ehtimol *xususiy (private)* hisobdagi video bo‘lishi mumkin."
        )


# --- Asosiy funksiya ---
>>>>>>> 7545121 (Yangilangan kod: ApplicationBuilder polling va video yuklash tuzatildi)
def main():
    print("🚀 Bot ishga tushdi...")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instagram))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("Bu yangi kod")

if __name__ == "__main__":
    main()
