from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast"))
    builder.row(types.InlineKeyboardButton(text="📊 Obunachilar soni", callback_data="admin_stats"))
    builder.row(types.InlineKeyboardButton(text="📢 Kanallarni boshqarish", callback_data="admin_channels"))
    builder.row(types.InlineKeyboardButton(text="✍️ Caption sozlash", callback_data="admin_caption"))
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
