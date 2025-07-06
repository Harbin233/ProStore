from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

egor_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить клиента")]
    ],
    resize_keyboard=True
)