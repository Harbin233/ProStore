# core/handlers/status.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from core.notion.notion_client import (
    get_all_clients,
    get_client_stage,
    get_packagings_for_client,
    get_client_name
)

router = Router()
CLIENTS_PER_PAGE = 5

def build_clients_keyboard(clients, page=0):
    """
    Формирует инлайн-клавиатуру для страницы клиентов с навигацией и подписью имени клиента.
    """
    total = len(clients)
    total_pages = (total - 1) // CLIENTS_PER_PAGE + 1
    start = page * CLIENTS_PER_PAGE
    end = start + CLIENTS_PER_PAGE
    chunk = clients[start:end]

    # Кнопки "Подробнее: Имя"
    buttons = [
        [InlineKeyboardButton(
            text=f"Подробнее: {client.get('name') or '(Без имени)'}",
            callback_data=f"client_details:{client.get('id', '')}:{page}"
        )]
        for client in chunk
    ]

    # Кнопки для навигации по страницам (и нумерация)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"clients_page:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"Стр {page+1} из {total_pages}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"clients_page:{page+1}"))
    if nav:
        buttons.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text == "Статус клиентов")
async def status_clients_list(message: Message):
    # Сообщаем пользователю о загрузке
    loading = await message.answer("⏳ Загружаю список клиентов...")
    clients = get_all_clients()
    if not clients:
        await loading.edit_text("Пока нет клиентов.")
        return

    client_lines = []
    for c in clients:
        name = c.get("name") or "(Без имени)"
        try:
            stage = get_client_stage(c["id"]) or "—"
        except Exception:
            stage = "—"
        client_lines.append(f"• {name} — {stage}")

    page = 0
    text = "\n".join(client_lines)
    keyboard = build_clients_keyboard(clients, page=page)
    await loading.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("clients_page:"))
async def clients_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    # Сообщаем пользователю о загрузке
    await callback.message.edit_text("⏳ Загружаю список клиентов...")
    clients = get_all_clients()
    if not clients:
        await callback.message.edit_text("Нет клиентов")
        return

    client_lines = []
    for c in clients:
        name = c.get("name") or "(Без имени)"
        try:
            stage = get_client_stage(c["id"]) or "—"
        except Exception:
            stage = "—"
        client_lines.append(f"• {name} — {stage}")

    text = "\n".join(client_lines)
    keyboard = build_clients_keyboard(clients, page=page)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("client_details:"))
async def client_details(callback: CallbackQuery):
    # Формат callback_data: client_details:{client_id}:{page}
    _, client_id, page = callback.data.split(":")
    page = int(page)
    # Показываем загрузку
    await callback.message.edit_text("⏳ Загружаю подробную информацию...")

    try:
        name = get_client_name(client_id) or "(Без имени)"
    except Exception:
        name = "(Без имени)"
    try:
        stage = get_client_stage(client_id) or "—"
    except Exception:
        stage = "—"

    try:
        packagings = get_packagings_for_client(client_id)
    except Exception:
        packagings = []

    lines = [f"<b>{name}</b>\nОбщий этап: <b>{stage}</b>\n"]

    if not packagings:
        lines.append("Нет подробной информации по услугам и упаковкам.")
    else:
        for pack in packagings:
            res_type = (pack.get('resource_type', '—') or '—').upper()
            status = (
                pack.get('Статус') or
                pack.get('статус') or
                pack.get('status') or
                pack.get('stage', '—')
            )
            descr = pack.get('description', '')
            block = f"<b>{res_type}</b> — <b>{status}</b>"
            if descr and descr != "—":
                block += f"\nОписание: {descr}"
            lines.append(block)

    text = "\n".join(lines)

    # Кнопка "К списку"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К списку", callback_data=f"clients_page:{page}")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()