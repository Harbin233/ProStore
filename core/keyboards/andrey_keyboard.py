from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

andrey_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Получить карточку на проверку")]
    ],
    resize_keyboard=True
)