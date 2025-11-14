from aiogram import Bot, Dispatcher, executor, types
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    text = """SALOM! 👋
MENGA *INSTAGRAM VIDEO LINKINI* YUBORING, SIZGA VIDEO QILIB YUBORAMAN!

Sizga bular ham kerak bo‘lsa:
📌 TikTok VIDEO yuklab beruvchi bot: @tiktokdan_yuklabot
📌 Pinterest RASM & VIDEO yuklab beruvchi bot: @pinterest_yuklabot
"""
    await msg.answer(text, parse_mode="Markdown")


@dp.message_handler()
async def handle_instagram(msg: types.Message):
    text = msg.text.strip()

    if "instagram.com" in text:
        # domenni almashtirish
        new_link = text.replace("www.instagram.com", "kkinstagram.com")
        new_link = new_link.replace("instagram.com", "kkinstagram.com")

        await msg.answer("VIDEO TAYYOR YUKLAB OLISHINGIZ MUMKIN! 👇")
        await msg.answer(new_link)
    else:
        await msg.answer("Iltimos Instagram video link yuboring!")
        

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
