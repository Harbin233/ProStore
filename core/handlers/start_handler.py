from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

from core.keyboards.employee_keyboards import employee_keyboards  # <-- новый импорт!

router = Router()

# Telegram ID сотрудников + их клавиатуры
ID_MAP = {
    7585439289: ("Егор", employee_keyboards[7585439289]),
    7925207619: ("Ира", employee_keyboards[7925207619]),
    7553118544: ("Анастасия", employee_keyboards[7553118544]),
    8151289930: ("Андрей", employee_keyboards[8151289930]),
    6503850751: ("Александр", employee_keyboards[6503850751]),
    7714773957: ("Ирина Горшкова", employee_keyboards[7714773957]),
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