from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.notion.notion_client import update_client_stage, get_client_name
from core.notion.notion_top import (
    get_all_top_clients,
    get_top_client_card,
    add_top_payment,
    add_top_extension,
    update_top_stage,
)
from core.utils.push import push_message

router = Router()

ANASTASIA_ID = 7553118544
ANDREY_ID = 8151289930
ALEXANDR_ID = 6503850751
EGOR_ID = 7585439289
IRA_ID = 7925207619

class CuratorFSM(StatesGroup):
    main_menu = State()
    top_menu = State()
    top_view_client = State()
    top_wait_payment_select = State()
    top_wait_payment_sum = State()
    top_wait_extension_select = State()
    top_wait_extension_sum = State()
    top_wait_status_select = State()
    top_wait_status_final = State()

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вывод в ТОП")],
            [KeyboardButton(text="Мои задачи")],
            [KeyboardButton(text="Выйти")],
        ],
        resize_keyboard=True
    )

def top_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Клиенты ТОП"), KeyboardButton(text="Добавить оплату ТОП")],
            [KeyboardButton(text="Продлить ТОП"), KeyboardButton(text="Изменить статус ТОП")],
            [KeyboardButton(text="Назад в главное меню")]
        ],
        resize_keyboard=True
    )

# --- Главное меню ---
@router.message(F.text.in_({"/start", "Старт"}))
async def anastasia_start(message: Message, state: FSMContext):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await state.set_state(CuratorFSM.main_menu)

@router.message(CuratorFSM.main_menu, F.text == "Вывод в ТОП")
async def top_entry(message: Message, state: FSMContext):
    await message.answer("Меню ТОП:", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_menu)

@router.message(CuratorFSM.main_menu, F.text == "Мои задачи")
async def my_tasks(message: Message, state: FSMContext):
    await message.answer("📝 Раздел в разработке.", reply_markup=main_menu_keyboard())

@router.message(CuratorFSM.main_menu, F.text == "Выйти")
async def exit_handler(message: Message, state: FSMContext):
    await message.answer("Вы вышли из меню. Для возврата — /start", reply_markup=ReplyKeyboardMarkup(keyboard=[[]], resize_keyboard=True))
    await state.clear()

# --- Назад в меню ---
@router.message(CuratorFSM.top_menu, F.text == "Назад в главное меню")
@router.message(F.text == "Назад в главное меню")
async def back_to_main(message: Message, state: FSMContext):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await state.set_state(CuratorFSM.main_menu)

# --- КЛИЕНТЫ ТОП (инлайн-кнопки) ---
@router.message(CuratorFSM.top_menu, F.text == "Клиенты ТОП")
async def top_show_clients(message: Message, state: FSMContext):
    clients = get_all_top_clients()
    if not clients:
        await message.answer("Нет клиентов в работе по ТОП.", reply_markup=top_menu_keyboard())
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['name']} | {c['status']}",
            callback_data=f"topclient_{c['id']}"
        )] for c in clients
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите клиента:", reply_markup=markup)
    await state.set_state(CuratorFSM.top_view_client)

@router.callback_query(CuratorFSM.top_view_client, F.data.startswith("topclient_"))
async def top_view_one_client(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 1)[1]
    card = get_top_client_card(client_id)
    text = f"Карточка клиента {card['name']}:\n"
    text += f"Статус: {card['status']}\n"
    text += f"Ответственный: {card.get('manager', '—')}\n"
    text += f"Дата добавления: {card['date']}\n"
    text += f"Услуги: {card['services']}\n"
    text += f"Бюджет: {card.get('budget', '—')}\n"
    text += f"Продления: {card.get('extensions', 0)}\n"
    text += f"Комментарий: {card.get('comment', '')}\n"
    await callback.message.answer(text, reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_menu)
    await callback.answer()

# --- ДОБАВИТЬ ОПЛАТУ ТОП (инлайн-кнопки) ---
@router.message(CuratorFSM.top_menu, F.text == "Добавить оплату ТОП")
async def top_wait_payment_select(message: Message, state: FSMContext):
    clients = get_all_top_clients()
    if not clients:
        await message.answer("Нет клиентов для оплаты.", reply_markup=top_menu_keyboard())
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['name']} | {c['status']}",
            callback_data=f"payclient_{c['id']}"
        )] for c in clients
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите клиента для оплаты:", reply_markup=markup)
    await state.set_state(CuratorFSM.top_wait_payment_select)

@router.callback_query(CuratorFSM.top_wait_payment_select, F.data.startswith("payclient_"))
async def top_payment_amount(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 1)[1]
    await state.update_data(top_pay_client=client_id)
    await callback.message.answer("Введите сумму оплаты (число):", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_wait_payment_sum)
    await callback.answer()

@router.message(CuratorFSM.top_wait_payment_sum)
async def top_payment_sum_final(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("top_pay_client")
    try:
        amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Введите корректное число.", reply_markup=top_menu_keyboard())
        return
    add_top_payment(client_id, amount)
    name = get_client_name(client_id)
    await message.answer(f"Оплата {amount}₽ успешно добавлена клиенту {name}.", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_menu)

# --- ПРОДЛИТЬ ТОП (инлайн-кнопки) ---
@router.message(CuratorFSM.top_menu, F.text == "Продлить ТОП")
async def top_wait_extension_select(message: Message, state: FSMContext):
    clients = get_all_top_clients()
    if not clients:
        await message.answer("Нет клиентов для продления.", reply_markup=top_menu_keyboard())
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['name']} | {c['status']}",
            callback_data=f"extendclient_{c['id']}"
        )] for c in clients
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите клиента для продления:", reply_markup=markup)
    await state.set_state(CuratorFSM.top_wait_extension_select)

@router.callback_query(CuratorFSM.top_wait_extension_select, F.data.startswith("extendclient_"))
async def top_extension_sum(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 1)[1]
    await state.update_data(top_extension_client=client_id)
    await callback.message.answer("Введите сумму продления (число):", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_wait_extension_sum)
    await callback.answer()

@router.message(CuratorFSM.top_wait_extension_sum)
async def top_extension_sum_final(message: Message, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("top_extension_client")
    try:
        amount = float(message.text.replace(",", "."))
    except Exception:
        await message.answer("Введите корректное число.", reply_markup=top_menu_keyboard())
        return
    add_top_extension(client_id, amount)
    name = get_client_name(client_id)
    await message.answer(f"Продление на {amount}₽ успешно добавлено клиенту {name}.", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_menu)

# --- ИЗМЕНИТЬ СТАТУС ТОП (инлайн-кнопки) ---
@router.message(CuratorFSM.top_menu, F.text == "Изменить статус ТОП")
async def top_wait_status_select(message: Message, state: FSMContext):
    clients = get_all_top_clients()
    if not clients:
        await message.answer("Нет клиентов для смены статуса.", reply_markup=top_menu_keyboard())
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['name']} | {c['status']}",
            callback_data=f"statusclient_{c['id']}"
        )] for c in clients
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите клиента для смены статуса:", reply_markup=markup)
    await state.set_state(CuratorFSM.top_wait_status_select)

@router.callback_query(CuratorFSM.top_wait_status_select, F.data.startswith("statusclient_"))
async def top_status_final(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 1)[1]
    await state.update_data(top_status_client=client_id)
    await callback.message.answer("Введите новый статус (например: В ТОПе, Продлен, Не в ТОПе):", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_wait_status_final)
    await callback.answer()

@router.message(CuratorFSM.top_wait_status_final)
async def top_status_final_set(message: Message, state: FSMContext):
    new_status = message.text.strip()
    data = await state.get_data()
    client_id = data.get("top_status_client")
    update_top_stage(client_id, new_status)
    name = get_client_name(client_id)
    await message.answer(f"Статус клиента {name} обновлён на: {new_status}.", reply_markup=top_menu_keyboard())
    await state.set_state(CuratorFSM.top_menu)

# --- ВОЗВРАТ В ЛЮБОЙ МОМЕНТ ---
@router.message(F.text == "Назад в главное меню")
async def any_back_to_main(message: Message, state: FSMContext):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await state.set_state(CuratorFSM.main_menu)

# ========== Важно ==========
# --- Callbacks для инвойса и оплаты ---
@router.callback_query(F.data.startswith("invoice_done_"))
async def invoice_done(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_")[-1]
    update_client_stage(client_id, "Выставлен счёт", callback.from_user.id)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Счёт оплачен", callback_data=f"paid_{client_id}")]
        ]
    )
    await callback.message.answer("💸 Когда получишь оплату — нажми кнопку ниже", reply_markup=markup)
    await state.set_state(CuratorFSM.main_menu)

@router.callback_query(F.data.startswith("paid_"))
async def payment_received(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_")[-1]
    update_client_stage(client_id, "Оплачено", callback.from_user.id)
    client_name = get_client_name(client_id)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔘 Приступить к упаковке", callback_data=f"ira_start:{client_id}")]
        ]
    )
    await push_message(IRA_ID, f"✅ Клиент оплатил, можно приступать к работе!\nКлиент: {client_name}\nНажми кнопку, чтобы начать упаковку.", markup)
    # Дополнительные уведомления (если нужно)
    notify_text = "💸 Счёт оплачен"
    for uid in [ALEXANDR_ID, ANDREY_ID, EGOR_ID]:
        await push_message(uid, notify_text)
    await callback.message.answer("✅ Оплата подтверждена. Уведомления отправлены.")
    await state.set_state(CuratorFSM.main_menu)