from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.notion.notion_client import update_client_stage

router = Router()

class TopFSM(StatesGroup):
    select_type = State()
    wait_pack = State()
    wait_resource = State()
    wait_top = State()
    retention = State()
    final = State()

@router.message(F.text.lower() == "топ старт")
async def start_top(message: Message, state: FSMContext):
    # ⚠️ Здесь временно client_id задаётся вручную — нужно будет получать его из данных клиента
    client_id = "example-client-id"
    await state.update_data(client_id=client_id)

    await message.answer("\ud83d\udccc Какой тип ресурса? Выберите:",
                         reply_markup=InlineKeyboardMarkup(
                             inline_keyboard=[
                                 [InlineKeyboardButton(text="Канал", callback_data="type_channel")],
                                 [InlineKeyboardButton(text="Бот", callback_data="type_bot")]
                             ]
                         ))
    await state.set_state(TopFSM.select_type)

@router.callback_query(TopFSM.select_type, F.data.startswith("type_"))
async def type_selected(callback: CallbackQuery, state: FSMContext):
    resource_type = callback.data.split("_")[1]
    await state.update_data(resource_type=resource_type)

    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Упаковка")

    await callback.message.edit_text(f"Тип ресурса: {resource_type.upper()}.\n\nСледующий шаг: упаковка.")
    await state.set_state(TopFSM.wait_pack)

@router.message(TopFSM.wait_pack)
async def packaging_done(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Подготовка ресурса")

    await message.answer("\u2705 Упаковка завершена. Готовим ресурс.")
    await state.set_state(TopFSM.wait_resource)

@router.message(TopFSM.wait_resource)
async def resource_ready(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Выведен в ТОП")

    await message.answer("\u2705 Ресурс готов. Запускаем вывод в ТОП.")
    await state.set_state(TopFSM.wait_top)

@router.message(TopFSM.wait_top)
async def confirm_top(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Удержание в ТОПе")

    await message.answer("\ud83d\udcc8 ТОП достигнут. Начинаем удержание.")
    await state.set_state(TopFSM.retention)

@router.message(TopFSM.retention)
async def end_or_extend(message: Message, state: FSMContext):
    await message.answer("\u23f3 Подходит к завершению. Продлить?", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\ud83d\udd01 Продлить", callback_data="top_extend")],
            [InlineKeyboardButton(text="\u2705 Завершить", callback_data="top_done")]
        ]
    ))

@router.callback_query(TopFSM.retention, F.data == "top_extend")
async def extended(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Продление или завершение")

    await callback.message.edit_text("\ud83d\udd01 ТОП продлён. Снова отслеживаем выдачу.")
    await state.set_state(TopFSM.final)

@router.callback_query(TopFSM.retention, F.data == "top_done")
async def finished(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Завершено")

    await callback.message.edit_text("\u2705 Работа по ТОП завершена.")
    await state.clear()