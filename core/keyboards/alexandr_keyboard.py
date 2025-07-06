from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

alexandr_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Админ-панель")]
    ],
    resize_keyboard=True
)