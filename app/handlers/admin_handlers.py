import asyncio
import time
import logging
from aiogram import Router, F, types
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest

from config import Config
import database
from app.keyboards.admin_keyboards import admin_main_keyboard, channels_list_keyboard, back_to_admin_keyboard

class IsAdmin(BaseFilter):
    async def __call__(self, event: types.TelegramObject) -> bool:
        user = getattr(event, 'from_user', None)
        if not user:
            return False
        return user.id in Config.ADMIN_IDS

router = Router()
# Butun router bo'yicha faqat adminlarga ruxsat berish
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()
    waiting_for_channel_url = State()
    waiting_for_caption = State()
    waiting_for_start_msg = State()

@router.message(Command("admin", "panel"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 <b>Admin panelga xush kelibsiz:</b>", parse_mode="HTML", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 <b>Admin panelga xush kelibsiz:</b>", parse_mode="HTML", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    stats = await database.get_stats_summary()
    text = (
        "📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b> ta\n"
        f"🟢 Faol foydalanuvchilar: <b>{stats['active_users']}</b> ta\n"
        f"📥 Jami yuklab olishlar: <b>{stats['total_downloads']}</b> ta"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring:\n\n"
        "<i>(Bekor qilish uchun '⬅️ Orqaga' tugmasini bosing)</i>",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

async def execute_broadcast(bot, admin_chat_id: int, message: types.Message, users: list, wait_msg_id: int):
    sent = 0
    failed = 0
    total = len(users)
    last_update_time = time.time()
    
    for idx, user_id in enumerate(users):
        try:
            await message.copy_to(chat_id=user_id, reply_markup=message.reply_markup)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
            try:
                await message.copy_to(chat_id=user_id, reply_markup=message.reply_markup)
                sent += 1
            except Exception:
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            failed += 1
            err_str = str(e).lower()
            if "blocked" in err_str or "forbidden" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                await database.set_user_active(user_id, False)
        except Exception as e:
            logging.warning(f"Broadcast failed for user {user_id}: {e}")
            failed += 1

        # Har 4 soniyada xabarni yangilash (Telegram Flood limitiga tushmaslik uchun)
        if time.time() - last_update_time > 4.0:
            last_update_time = time.time()
            try:
                percent = int((idx + 1) / total * 100)
                await bot.edit_message_text(
                    f"📢 <b>Xabar tarqatilmoqda...</b> ({percent}%)\n\n"
                    f"👥 Jami: <b>{total}</b> ta\n"
                    f"✅ Yetkazildi: <b>{sent}</b> ta\n"
                    f"🚫 Yetib bormadi: <b>{failed}</b> ta",
                    chat_id=admin_chat_id,
                    message_id=wait_msg_id,
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.04) # Sekundiga ~25 ta xabar yuborish (Telegram tavsiyasi)

    await asyncio.sleep(1.0)
    report = (
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"👥 Jami qabul qiluvchilar: <b>{total}</b> ta\n"
        f"✅ Muvaffaqiyatli yetkazildi: <b>{sent}</b> ta\n"
        f"🚫 Yetib bormadi (bloklagan): <b>{failed}</b> ta"
    )
    try:
        await bot.edit_message_text(
            report,
            chat_id=admin_chat_id,
            message_id=wait_msg_id,
            parse_mode="HTML",
            reply_markup=back_to_admin_keyboard()
        )
    except Exception:
        try:
            await bot.send_message(
                admin_chat_id,
                report,
                parse_mode="HTML",
                reply_markup=back_to_admin_keyboard()
            )
        except Exception:
            pass

@router.message(AdminStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    users = await database.get_all_users(only_active=True)
    valid_users = [u for u in users if u > 0]
    total = len(valid_users)
    
    if total == 0:
        return await message.answer(
            "❌ <b>Bazada faol foydalanuvchilar topilmadi!</b>\n\n"
            "<i>Foydalanuvchilar botga /start bosishi yoki media yuborishi bilan bazaga avtomatik qo'shiladi.</i>",
            parse_mode="HTML",
            reply_markup=back_to_admin_keyboard()
        )

    wait_msg = await message.answer(
        f"🚀 <b>Xabar tarqatish boshlandi...</b>\n\n"
        f"👥 Qabul qiluvchilar: <b>{total}</b> ta\n"
        f"⏳ Jarayon ketmoqda, iltimos kuting...",
        parse_mode="HTML"
    )
    
    # Bot qotib qolmasligi uchun orqa fonda ishga tushirish
    asyncio.create_task(
        execute_broadcast(
            bot=message.bot,
            admin_chat_id=message.chat.id,
            message=message,
            users=valid_users,
            wait_msg_id=wait_msg.message_id
        )
    )

@router.callback_query(F.data == "admin_caption")
async def start_caption_set(callback: types.CallbackQuery, state: FSMContext):
    current = await database.get_setting('custom_caption', "")
    display_text = current if current else "<i>O'rnatilmagan</i>"
    await callback.message.edit_text(
        f"✍️ <b>Hozirgi qo'shimcha izoh (caption):</b>\n\n{display_text}\n\n"
        "Yangi izohni yuboring (o'chirish uchun <b>0</b> deb yozing):",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_caption)

@router.message(AdminStates.waiting_for_caption)
async def set_caption(message: types.Message, state: FSMContext):
    await state.clear()
    val = "" if message.text.strip() == "0" else message.text.strip()
    await database.set_setting('custom_caption', val)
    await message.answer("✅ Izoh muvaffaqiyatli saqlandi!", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_start_msg")
async def start_msg_settings(callback: types.CallbackQuery, state: FSMContext):
    current = await database.get_setting('start_message', "")
    display = current if current else "<i>Standart xabar ishlatilmoqda</i>"
    await callback.message.edit_text(
        f"💬 <b>Hozirgi Start xabari:</b>\n\n{display}\n\n"
        "Yangi Start xabarini yuboring (standart holatga qaytarish uchun <b>0</b> deb yozing):\n\n"
        "<i>Eslatma: HTML teglaridan (<b>, <i>, <code>) foydalanishingiz mumkin.</i>",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_start_msg)

@router.message(AdminStates.waiting_for_start_msg)
async def set_start_msg(message: types.Message, state: FSMContext):
    await state.clear()
    val = "" if message.text.strip() == "0" else message.text.strip()
    await database.set_setting('start_message', val)
    await message.answer("✅ Start xabari muvaffaqiyatli saqlandi!", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_channels")
async def list_channels(callback: types.CallbackQuery):
    channels = await database.get_channels()
    await callback.message.edit_text("📢 <b>Majburiy obuna kanallari:</b>", parse_mode="HTML", reply_markup=channels_list_keyboard(channels))

@router.callback_query(F.data == "add_channel")
async def add_ch_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📢 <b>Kanal qo'shish:</b>\n\n"
        "1. Kanalning <code>@username</code>ini yuboring (masalan: <code>@mening_kanalim</code>),\n"
        "2. Kanal ID'sini kiriting (masalan: <code>-1001234567890</code>),\n"
        "3. Yoki kanaldan biror xabarni shu yerga <b>Forward (uzatish)</b> qiling:\n\n"
        "<i>⚠️ Eslatma: Bot ushbu kanalda ADMIN qilingan bo'lishi shart!</i>",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_channel_id)

@router.message(AdminStates.waiting_for_channel_id)
async def add_ch_id(message: types.Message, state: FSMContext):
    chat_id = None
    suggested_title = None

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        suggested_title = message.forward_from_chat.title
    elif message.text:
        raw = message.text.strip()
        try:
            # @username yoki ID orqali kanalni topish
            chat = await message.bot.get_chat(raw)
            chat_id = chat.id
            suggested_title = chat.title
        except Exception:
            try:
                chat_id = int(raw)
            except ValueError:
                pass

    if not chat_id:
        return await message.answer(
            "❌ <b>Kanal aniqlanmadi!</b>\n\n"
            "Iltimos, kanalning <code>@username</code>ini to'g'ri yozing, ID'sini kiriting yoki kanaldan biror xabarni Forward qiling:",
            parse_mode="HTML"
        )

    # Bot kanalda adminligini tekshirish
    try:
        bot_info = await message.bot.get_me()
        member = await message.bot.get_chat_member(chat_id, bot_info.id)
        if member.status not in ['administrator', 'creator']:
            return await message.answer(
                "⚠️ <b>Bot ushbu kanalda ADMIN emas!</b>\n\n"
                "Iltimos, avval botni kanalingizga admin qilib tayinlang, so'ng qayta yuboring.",
                parse_mode="HTML"
            )
    except Exception as e:
        return await message.answer(
            f"⚠️ <b>Kanal bilan bog'lanishda xatolik:</b>\n{e}\n\n"
            "Bot kanalda admin qilinganligiga ishonch hosil qiling.",
            parse_mode="HTML"
        )

    await state.update_data(id=chat_id)
    if suggested_title:
        await state.update_data(title=suggested_title)
        await message.answer(
            f"✅ Kanal muvaffaqiyatli aniqlandi: <b>{suggested_title}</b>\n\n"
            f"Endi ushbu kanalga ulanish havolasini (link) yuboring (masalan: <code>https://t.me/...</code>):",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_channel_url)
    else:
        await message.answer("2. Kanalning nomini yuboring (tugmada chiqadigan matn):")
        await state.set_state(AdminStates.waiting_for_channel_title)

@router.message(AdminStates.waiting_for_channel_title)
async def add_ch_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        return await message.answer("❌ Kanal nomi bo'sh bo'lishi mumkin emas!")
    await state.update_data(title=title)
    await message.answer("3. Kanalga havolani (link) yuboring (masalan: <code>https://t.me/kanal_nomi</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_channel_url)

@router.message(AdminStates.waiting_for_channel_url)
async def add_ch_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("t.me/")):
        return await message.answer("❌ Noto'g'ri havola formati! https://t.me/... ko'rinishida yuboring.")
    
    if url.startswith("t.me/"):
        url = "https://" + url

    data = await state.get_data()
    await database.add_or_update_channel(data['id'], data['title'], url)
    await state.clear()
    await message.answer("✅ Kanal muvaffaqiyatli saqlandi!", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data.startswith("del_ch:"))
async def del_ch(callback: types.CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    await database.delete_channel(chat_id)
    await callback.answer("❌ Kanal o'chirildi")
    channels = await database.get_channels()
    await callback.message.edit_text("📢 <b>Majburiy obuna kanallari:</b>", parse_mode="HTML", reply_markup=channels_list_keyboard(channels))
