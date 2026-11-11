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

@router.message(AdminStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    users = await database.get_all_users(only_active=True)
    total = len(users)
    
    if total == 0:
        return await message.answer("❌ Bazada foydalanuvchilar topilmadi.", reply_markup=back_to_admin_keyboard())

    sent = 0
    failed = 0
    last_update_time = time.time()
    wait_msg = await message.answer(f"⏳ Tarqatish boshlandi (0/{total})...")
    
    for idx, user_id in enumerate(users):
        try:
            await message.copy_to(chat_id=user_id)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await message.copy_to(chat_id=user_id)
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            failed += 1
            await database.set_user_active(user_id, False)
        except Exception as e:
            logging.debug(f"Broadcast failed for user {user_id}: {e}")
            failed += 1

        # Har 3 soniyada xabarni yangilash (Flood control chekloviga tushmaslik uchun)
        if time.time() - last_update_time > 3.0 or idx == total - 1:
            last_update_time = time.time()
            try:
                await wait_msg.edit_text(
                    f"⏳ Tarqatilmoqda... ({idx + 1}/{total})\n\n"
                    f"✅ Yetkazildi: {sent}\n"
                    f"❌ Xatolik / Bloklagan: {failed}"
                )
            except Exception:
                pass
        
        await asyncio.sleep(0.04) # Sekundiga ~25-30 ta xabar yuborish
        
    await wait_msg.edit_text(
        f"✅ <b>Tarqatish yakunlandi!</b>\n\n"
        f"👥 Jami: {total}\n"
        f"✅ Muvaffaqiyatli bordi: <b>{sent}</b>\n"
        f"🚫 Yetib bormadi (bloklagan): <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
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
        "1. Menga kanalning ID'sini yuboring (masalan: <code>-1001234567890</code>):\n\n"
        "<i>Eslatma: Bot ushbu kanalda ADMIN bo'lishi shart!</i>",
        parse_mode="HTML",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_channel_id)

@router.message(AdminStates.waiting_for_channel_id)
async def add_ch_id(message: types.Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
        await state.update_data(id=chat_id)
        await message.answer("2. Kanalning nomini yuboring (tugmada chiqadigan matn):")
        await state.set_state(AdminStates.waiting_for_channel_title)
    except ValueError:
        await message.answer("❌ Noto'g'ri ID! Faqat butun son bo'lishi kerak (masalan: -1001234567890):")

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
