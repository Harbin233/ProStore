from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()

class IrinaFSM(StatesGroup):
    choosing_service = State()
    collecting_info = State()
    revising = State()
    confirming = State()

@router.message(Command("ирина"))
async def start_irina(message: Message, state: FSMContext):
    await message.answer(
        "Привет, Ирина. Выбери услугу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ТапБлог", callback_data="irina_tapblog")],
            [InlineKeyboardButton(text="Чат-бот", callback_data="irina_bot")]
        ])
    )
    await state.set_state(IrinaFSM.choosing_service)

@router.callback_query(IrinaFSM.choosing_service)
async def select_service(callback: CallbackQuery, state: FSMContext):
    service = "ТапБлог" if callback.data == "irina_tapblog" else "Чат-бот"
    await state.update_data(service=service)
    await callback.message.answer(f"✅ Выбрано: {service}. Собери информацию от методолога и клиента.")
    await state.set_state(IrinaFSM.collecting_info)

@router.message(IrinaFSM.collecting_info, F.text.lower().contains("готово"))
async def collected_info(message: Message, state: FSMContext):
    await message.answer(
        "Проверь всё ещё раз. Всё точно готово?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отправить дальше", callback_data="irina_confirm")],
            [InlineKeyboardButton(text="🔁 На доработку", callback_data="irina_revise")]
        ])
    )
    await state.set_state(IrinaFSM.confirming)

@router.callback_query(IrinaFSM.confirming)
async def confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service = data.get("service", "услуга не указана")

    if callback.data == "irina_confirm":
        await callback.message.answer(f"✅ Материалы по услуге {service} переданы на следующий этап.")
        # Здесь можно добавить запись в Notion или другой лог при необходимости
    else:
        await callback.message.answer("🔁 Отправлено на доработку. Ждём обновлений.")

    await state.clear()