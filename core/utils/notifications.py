# core/utils/notifications.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.utils.push import push_message
from core.notion.notion_client import get_services_for_client, get_client_name

# --- Telegram ID сотрудников ---
ANASTASIA_ID = 7553118544
ANDREY_ID = 8151289930
ALEXANDR_ID = 6503850751
EGOR_ID = 7585439289
IRA_ID = 7925207619

# --- Уведомление для Анастасии о новом клиенте ---
async def notify_curator_new_client(client_id: str) -> None:
    services = get_services_for_client(client_id)
    client_name = get_client_name(client_id)
    text = (
        f"🧾 Нужно выставить счёт клиенту {client_name}.\nУслуги:\n" +
        "\n".join([f"• {s['name']} — {s['price']}₽" for s in services])
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Выставлен счёт", callback_data=f"invoice_done_{client_id}")]
        ]
    )
    await push_message(ANASTASIA_ID, text, markup)

# --- Уведомление для Иры о старте упаковки ---
async def notify_ira_start_pack(client_id: str) -> None:
    client_name = get_client_name(client_id)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать упаковку", callback_data=f"ira_start:{client_id}")]
        ]
    )
    await push_message(IRA_ID, f"✅ Клиент готов к упаковке: {client_name}", markup)

# --- PUSH всем админам о поступлении оплаты ---
async def notify_admins_payment(client_id: str) -> None:
    notify_text = "💸 Счёт оплачен"
    for uid in [ALEXANDR_ID, ANDREY_ID, EGOR_ID]:
        await push_message(uid, notify_text)

# --- PUSH для Иры: возврат на доработку от Андрея ---
async def notify_ira_pack_reject(client_id: str, resource: str, comment: str) -> None:
    client_name = get_client_name(client_id)
    text = (
        f"❗️ Карточка по {resource} клиента {client_name} отправлена на доработку от Андрея.\n"
        f"Комментарий: {comment}"
    )
    await push_message(IRA_ID, text)

# --- Можно добавить другие кастомные уведомления по аналогии ---