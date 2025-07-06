from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

irina_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✍️ Начать оформление ТапБлога")],
        [KeyboardButton(text="🤖 Настроить чат-бота")]
    ],
    resize_keyboard=True
)