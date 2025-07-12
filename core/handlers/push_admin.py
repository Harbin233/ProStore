from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.notion.notion_client import update_push_interval_notion

# ID тех, кто может управлять пушами
PUSH_ADMINS = [8151289930, 6503850751]  # Андрей, Александр

# Список сотрудников (id: имя)
EMPLOYEES = {
    7585439289: "Егор",
    7925207619: "Ира",
    7553118544: "Анастасия",
    8151289930: "Андрей",
    6503850751: "Александр",
    7714773957: "Ирина Горшкова"
}

router = Router()

class PushFSM(StatesGroup):
    choosing_employee = State()
    choosing_interval = State()

# 1. Обработка нажатия "Пуш сотрудников" (Reply)
@router.message(F.text == "Пуш сотрудников")
async def push_staff_menu(message: Message, state: FSMContext):
    if message.from_user.id not in PUSH_ADMINS:
        await message.answer("Нет доступа.")
        return

    # Формируем инлайн-кнопки сотрудников (только для обычных сотрудников)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=name, callback_data=f"push_choose:{emp_id}")]
            for emp_id, name in EMPLOYEES.items() if emp_id not in PUSH_ADMINS
        ]
    )
    await message.answer(
        "Выбери сотрудника, для которого хочешь изменить частоту пушей:",
        reply_markup=keyboard
    )
    await state.set_state(PushFSM.choosing_employee)

# 2. Обработка выбора сотрудника
@router.callback_query(PushFSM.choosing_employee, F.data.startswith("push_choose:"))
async def push_choose_employee(callback: CallbackQuery, state: FSMContext):
    emp_id = int(callback.data.split(":")[1])
    await state.update_data(target_emp=emp_id)
    # Даем выбор интервала пуша (например, от 1 до 12 часов)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{h} ч.", callback_data=f"push_interval:{h}")
                for h in range(1, 7)
            ],
            [
                InlineKeyboardButton(text=f"{h} ч.", callback_data=f"push_interval:{h}")
                for h in range(7, 13)
            ]
        ]
    )
    await callback.message.edit_text(
        f"Выбран: <b>{EMPLOYEES.get(emp_id, '—')}</b>\n\nВыбери интервал пуша:",
        reply_markup=keyboard
    )
    await state.set_state(PushFSM.choosing_interval)
    await callback.answer()

# 3. Обработка выбора интервала
@router.callback_query(PushFSM.choosing_interval, F.data.startswith("push_interval:"))
async def push_set_interval(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    emp_id = data.get("target_emp")
    interval = int(callback.data.split(":")[1])

    # -- Обновляем интервал в Notion:
    ok = update_push_interval_notion(emp_id, interval)

    if ok:
        text = f"✅ Для сотрудника <b>{EMPLOYEES.get(emp_id, '—')}</b> установлен интервал пушей: <b>{interval} ч.</b>"
    else:
        text = f"❗️ Не удалось обновить интервал в Notion для {EMPLOYEES.get(emp_id, '—')}!"

    await callback.message.edit_text(text)
    await state.clear()
    await callback.answer()