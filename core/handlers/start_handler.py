from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from core.keyboards.egor_keyboard import egor_kb
from core.keyboards.ira_keyboard import ira_kb
from core.keyboards.anastasiya_keyboard import anastasiya_kb
from core.keyboards.andrey_keyboard import andrey_kb
from core.keyboards.alexandr_keyboard import alexandr_kb
from core.keyboards.irina_keyboard import irina_kb

router = Router()

# Telegram ID сотрудников + их клавиатуры
ID_MAP = {
    7585439289: ("Егор", egor_kb),
    7925207619: ("Ира", ira_kb),
    7553118544: ("Анастасия", anastasiya_kb),
    8151289930: ("Андрей", andrey_kb),
    6503850751: ("Александр", alexandr_kb),
    7714773957: ("Ирина Горшкова", irina_kb),
}

@router.message(CommandStart())
async def start_command(message: Message):
    user_id = message.from_user.id
    user = ID_MAP.get(user_id)

    if user:
        name, keyboard = user
        await message.answer(
            f"Привет, {name}! Выбери действие из меню ниже ⬇️",
            reply_markup=keyboard
        )
    else:
        await message.answer("Здравствуйте! Вы не администратор.")