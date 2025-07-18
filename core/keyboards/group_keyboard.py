from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

group_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Позвать человека", callback_data="call_human_group")]
    ]
)