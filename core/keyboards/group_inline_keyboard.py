from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

print("[LOG] Импортирована клавиатура group_inline_keyboard!")

group_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Позвать человека", callback_data="call_human_group")]
    ]
)