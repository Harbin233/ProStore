from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

ira_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Начать карточку клиента")]
    ],
    resize_keyboard=True
)