from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📢 Xabar tarqatish (Broadcast)", callback_data="admin_broadcast"))
    builder.row(types.InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="admin_channels"))
    builder.row(types.InlineKeyboardButton(text="💬 Start xabarini sozlash", callback_data="admin_start_msg"))
    builder.row(types.InlineKeyboardButton(text="✍️ Video izohi (Caption)", callback_data="admin_caption"))
    builder.row(types.InlineKeyboardButton(text="📊 Bot statistikasi", callback_data="admin_stats"))
    return builder.as_markup()

def channels_list_keyboard(channels):
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(types.InlineKeyboardButton(text=f"❌ {ch.title}", callback_data=f"del_ch:{ch.chat_id}"))
    builder.row(types.InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel"))
    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def back_to_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_back"))
    return builder.as_markup()
