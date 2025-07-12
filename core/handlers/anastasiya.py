from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.notion.notion_client import get_services_for_client, update_client_stage
from core.utils.push import push_message

router = Router()

ANASTASIA_ID = 7553118544
ANDREY_ID = 8151289930
ALEXANDR_ID = 6503850751
EGOR_ID = 7585439289
IRA_ID = 7925207619

class CuratorFSM(StatesGroup):
    waiting_for_start = State()
    showing_services = State()
    waiting_invoice_confirmation = State()
    waiting_payment_confirmation = State()

@router.message(F.text == "Я готова")
async def curator_start(message: Message, state: FSMContext):
    await message.answer("🔔 Ожидается клиент. Как только появится задача — ты получишь уведомление.")
    await state.set_state(CuratorFSM.waiting_for_start)

async def notify_curator_new_client(name: str, client_id: str):
    services = get_services_for_client(client_id)
    text = f"🧾 Нужно выставить счёт клиенту {name}.\nУслуги:\n" + "\n".join([f"• {s['name']} — {s['price']}₽" for s in services])
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Выставлен счёт", callback_data=f"invoice_done_{client_id}")]
    ])
    await push_message(ANASTASIA_ID, text, markup)

@router.callback_query(F.data.startswith("invoice_done_"))
async def invoice_done(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_")[-1]
    await state.update_data(client_id=client_id)
    # Смена этапа на "Счёт выставлен" + время этапа
    update_client_stage(client_id, "Счёт выставлен", user_id=callback.from_user.id)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Счёт оплачен", callback_data=f"paid_{client_id}")]
    ])
    await callback.message.answer("💸 Когда получишь оплату — нажми кнопку ниже", reply_markup=markup)
    await state.set_state(CuratorFSM.waiting_payment_confirmation)

@router.callback_query(CuratorFSM.waiting_payment_confirmation, F.data.startswith("paid_"))
async def payment_received(callback: CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_")[-1]
    # Смена этапа на "Счёт оплачен" + время этапа
    update_client_stage(client_id, "Счёт оплачен", user_id=callback.from_user.id)

    # Уведомления
    await push_message(IRA_ID, "✅ Клиент оплатил, можно приступать к работе")
    notify_text = "💸 Счёт оплачен"
    for uid in [ALEXANDR_ID, ANDREY_ID, EGOR_ID]:
        await push_message(uid, notify_text)

    await callback.message.answer("✅ Оплата подтверждена. Уведомления отправлены.")
    await state.clear()