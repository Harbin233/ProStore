from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from core.storage.client_storage import create_client, log
from core.utils.push import push_message
from core.notion.notion_client import add_service_entry, update_client_stage, set_username_for_client
from core.notion.notion_top import add_top_client, get_top_services, get_service_ids_by_names
from datetime import datetime
from core.utils.notifications import notify_curator_new_client

router = Router()

TEAM_CHAT_ID = -1002671503187
ANASTASIA_ID = 7553118544
FOUNDERS = [ANASTASIA_ID, 6503850751, 7585439289]

services_dict = {
    "top": "Вывод в ТОП",
    "ads": "ADS",
    "pack": "Упаковка",
    "chatbot": "Чат-бот",
    "tapblog": "ТапБлог",
    "seeding": "Посевы"
}

class EgovFSM(StatesGroup):
    waiting_name = State()
    waiting_username = State()
    waiting_services = State()
    entering_price = State()

@router.message(F.text == "Добавить клиента")
async def start_add_client(message: Message, state: FSMContext):
    await message.answer("Введи имя клиента:")
    await state.set_state(EgovFSM.waiting_name)

@router.message(EgovFSM.waiting_name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text, services=[], prices={}, price_index=0)
    await message.answer("Введи username клиента (через @, например: @username):")
    await state.set_state(EgovFSM.waiting_username)

@router.message(EgovFSM.waiting_username)
async def get_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith('@') or len(username) < 2:
        await message.answer("Пожалуйста, введи корректный username (пример: @username)")
        return
    await state.update_data(username=username)
    await message.answer(
        "Выбери одну или несколько услуг:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вывод в ТОП", callback_data="service_top")],
            [InlineKeyboardButton(text="ADS", callback_data="service_ads")],
            [InlineKeyboardButton(text="Упаковка", callback_data="service_pack")],
            [InlineKeyboardButton(text="Чат-бот", callback_data="service_chatbot")],
            [InlineKeyboardButton(text="ТапБлог", callback_data="service_tapblog")],
            [InlineKeyboardButton(text="Посевы", callback_data="service_seeding")],
            [InlineKeyboardButton(text="✅ Завершить выбор", callback_data="confirm_services")]
        ])
    )
    await state.set_state(EgovFSM.waiting_services)

@router.callback_query(EgovFSM.waiting_services, F.data.startswith("service_"))
async def select_service(callback: CallbackQuery, state: FSMContext):
    service_key = callback.data.split("_")[1]
    data = await state.get_data()
    services = data.get("services", [])
    if service_key not in services:
        services.append(service_key)
        await state.update_data(services=services)
    selected_names = [services_dict[s] for s in services]
    await callback.message.edit_text(
        f"Выбрано: {', '.join(selected_names)}\n\nДобавлено: {services_dict[service_key]}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Вывод в ТОП", callback_data="service_top")],
            [InlineKeyboardButton(text="ADS", callback_data="service_ads")],
            [InlineKeyboardButton(text="Упаковка", callback_data="service_pack")],
            [InlineKeyboardButton(text="Чат-бот", callback_data="service_chatbot")],
            [InlineKeyboardButton(text="ТапБлог", callback_data="service_tapblog")],
            [InlineKeyboardButton(text="Посевы", callback_data="service_seeding")],
            [InlineKeyboardButton(text="✅ Завершить выбор", callback_data="confirm_services")]
        ])
    )
    await callback.answer()

@router.callback_query(EgovFSM.waiting_services, F.data == "confirm_services")
async def confirm_services(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    services = data.get("services", [])
    if not services:
        await callback.message.answer("Выбери хотя бы одну услугу.")
        return
    await state.update_data(price_index=0, prices={})
    service_key = services[0]
    await callback.message.answer(f"Укажи цену для услуги: {services_dict[service_key]} (в ₽)")
    await state.set_state(EgovFSM.entering_price)

@router.message(EgovFSM.entering_price)
async def enter_price(message: Message, state: FSMContext):
    data = await state.get_data()
    services = data.get("services", [])
    prices = data.get("prices", {})
    price_index = data.get("price_index", 0)

    try:
        amount = int(message.text.replace(" ", "").replace("₽", ""))
    except ValueError:
        await message.answer("Пожалуйста, укажи цену числом (например, 30000 или 30 000).")
        return

    service_key = services[price_index]
    prices[service_key] = amount
    await state.update_data(prices=prices)

    price_index += 1
    if price_index < len(services):
        next_service = services[price_index]
        await state.update_data(price_index=price_index)
        await message.answer(f"Укажи цену для услуги: {services_dict[next_service]} (в ₽)")
        return

    # --- СОЗДАЁМ КЛИЕНТА ---
    name = data.get("name")
    username = data.get("username")   # с @
    comment_parts = [f"{services_dict[k]} ({v}₽)" for k, v in prices.items()]
    comment = f"Создан Егором с услугами: {', '.join(comment_parts)}"
    client_id = create_client(name, comment)

    # --- Сохраняем username в основную таблицу ---
    try:
        set_username_for_client(client_id, username)
    except Exception as e:
        print(f"[WARN] Не удалось записать username в основную таблицу: {e}")

    log(client_id, "Егор", "Создание", f"Услуги: {', '.join(comment_parts)}")
    for key, price in prices.items():
        add_service_entry(service_name=services_dict[key], price=price, client_page_id=client_id)
    update_client_stage(client_id, "Ожидает счёт")
    total_sum = sum(prices.values())
    text_for_admins = (
        f"🆕 Новый клиент: {name}\n"
        f"🧩 Услуги: {', '.join(comment_parts)}\n"
        f"💰 Общая сумма: {total_sum}₽"
    )
    text_for_team = (
        f"🆕 Новый клиент: {name}\n"
        f"🧩 Услуги: {', '.join([services_dict[k] for k in services])}"
    )
    for admin_id in FOUNDERS:
        await push_message(admin_id, text_for_admins)
    await push_message(TEAM_CHAT_ID, text_for_team)

    # --- Добавление в ТОП таблицу если выбрано ТОП ---
    if "top" in services:
        try:
            service_names = [services_dict[k] for k in services]
            service_ids = get_service_ids_by_names(service_names)
            budget = prices.get("top", None)
            add_top_client(
                main_client_id=client_id,
                name=name,
                status="Ожидает счёт",
                date=datetime.now().strftime("%Y-%m-%d"),
                comment=comment,
                services=service_ids,
                budget=budget
            )
        except Exception as e:
            await message.answer(f"⚠️ Не удалось добавить клиента в ТОП-таблицу: {e}")

    await notify_curator_new_client(client_id)
    await message.answer(f"✅ Клиент {name} создан с username и услугами.")
    await state.clear()