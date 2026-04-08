from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import Config
import database
from app.keyboards.admin_keyboards import admin_main_keyboard, channels_list_keyboard, back_to_admin_keyboard
import asyncio

router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_channel_id = State()
    waiting_for_channel_title = State()
    waiting_for_channel_url = State()
    waiting_for_caption = State()

def is_admin(user_id: int):
    return user_id in Config.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id): return
    await message.answer("🛠 Admin panelga xush kelibsiz:", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 Admin panelga xush kelibsiz:", reply_markup=admin_main_keyboard())

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    count = await database.get_users_count()
    await callback.message.edit_text(f"📊 Jami obunachilar: {count} ta", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📢 Menga userlarga tarqatmoqchi bo'lgan xabaringizni yuboring:", 
                                     reply_markup=back_to_admin_keyboard())
    await state.set_state(AdminStates.waiting_for_broadcast)

@router.message(AdminStates.waiting_for_broadcast)
async def perform_broadcast(message: types.Message, state: FSMContext):
    await state.clear()
    users = await database.get_all_users()
    sent = 0
    failed = 0
    wait_msg = await message.answer(f"⏳ Tarqatish boshlandi (0/{len(users)})...")
    
    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            sent += 1
            if sent % 10 == 0:
                await wait_msg.edit_text(f"⏳ Tarqatilmoqda ({sent}/{len(users)})...")
            await asyncio.sleep(0.05)
        except:
            failed += 1
            
    await wait_msg.edit_text(f"✅ Tarqatish yakunlandi!\n\nSizga: {sent} kishiga bordi.\nO'chirilgan akkauntlar: {failed}", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_caption")
async def start_caption_set(callback: types.CallbackQuery, state: FSMContext):
    current = await database.get_setting('custom_caption')
    display_text = current if current else "Hozircha yo'q" # "Yo'q" dagi xato olib tashlandi
    await callback.message.edit_text(
        f"✍️ Hozirgi qo'shimcha caption:\n\n{display_text}\n\nYangi matnni yuboring (o'chirish uchun '0' deb yozing):", 
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_caption)

@router.message(AdminStates.waiting_for_caption)
async def set_caption(message: types.Message, state: FSMContext):
    await state.clear()
    val = "" if message.text == "0" else message.text
    await database.set_setting('custom_caption', val)
    await message.answer("✅ Caption muvaffaqiyatli saqlandi!", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data == "admin_channels")
async def list_channels(callback: types.CallbackQuery):
    channels = await database.get_channels()
    await callback.message.edit_text("📢 Majburiy obuna kanallari:", reply_markup=channels_list_keyboard(channels))

@router.callback_query(F.data == "add_channel")
async def add_ch_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("1. Menga kanalning ID'sini yuboring (masalan: -100123456):")
    await state.set_state(AdminStates.waiting_for_channel_id)

@router.message(AdminStates.waiting_for_channel_id)
async def add_ch_id(message: types.Message, state: FSMContext):
    try:
        chat_id = int(message.text)
        await state.update_data(id=chat_id)
        await message.answer("2. Kanalning nomini yuboring (tugmada chiqadigan matn):")
        await state.set_state(AdminStates.waiting_for_channel_title)
    except:
        await message.answer("❌ Xato ID. Raqam bo'lishi kerak!")

@router.message(AdminStates.waiting_for_channel_title)
async def add_ch_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("3. Kanalga havola (link) yuboring:")
    await state.set_state(AdminStates.waiting_for_channel_url)

@router.message(AdminStates.waiting_for_channel_url)
async def add_ch_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await database.add_channel(data['id'], data['title'], message.text)
    await state.clear()
    await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!", reply_markup=back_to_admin_keyboard())

@router.callback_query(F.data.startswith("del_ch:"))
async def del_ch(callback: types.CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    await database.delete_channel(chat_id)
    await callback.answer("❌ Kanal o'chirildi")
    channels = await database.get_channels()
    await callback.message.edit_text("📢 Majburiy obuna kanallari:", reply_markup=channels_list_keyboard(channels))
