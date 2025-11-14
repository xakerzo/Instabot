from aiogram import Bot, Dispatcher, executor, types
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(content_types=['text'])
async def change_instagram_domain(message: types.Message):
    text = message.text.strip()

    # faqat instagram linklarini tekshiramiz
    if "instagram.com" in text:
        # domenni kkinstagram.com ga almashtiramiz
        new_link = text.replace("www.instagram.com", "kkinstagram.com")
        new_link = new_link.replace("instagram.com", "kkinstagram.com")

        await message.answer(f"Mana o'zgartirilgan link:\n{new_link}")
    else:
        await message.answer("Iltimos, Instagram videosi linkini yuboring!")

if __name__ == "__main__":
    executor.start_polling(dp)
