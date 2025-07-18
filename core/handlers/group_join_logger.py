from aiogram import Router, F, types
from core.notion.notion_client import set_telegram_id_for_client_by_username
import logging

router = Router()

logging.basicConfig(level=logging.INFO)

@router.message()
async def log_and_set_id(message: types.Message):
    # Пропускаем команды и ботов
    if message.from_user.is_bot or (message.text and message.text.startswith("/")):
        return

    tg_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id

    print(f"[GROUP DEBUG] MESSAGE in chat: {chat_id}")
    print(f"[GROUP DEBUG] User: id={tg_id} username={username} full={message.from_user.full_name}")

    # Проверка — не пустой ли username
    if not username:
        print("[GROUP DEBUG] Нет username у пользователя! Пропуск.")
        return

    username_at = "@" + username
    print(f"[GROUP DEBUG] Пробуем искать с @{username} и просто username...")

    # Пытаемся обновить по полю с @username
    updated_at = set_telegram_id_for_client_by_username(username_at, tg_id)
    updated_noat = set_telegram_id_for_client_by_username(username, tg_id)
    print(f"[GROUP DEBUG] set_telegram_id_for_client_by_username('{username_at}') -> {updated_at}")
    print(f"[GROUP DEBUG] set_telegram_id_for_client_by_username('{username}') -> {updated_noat}")

    # Для видимости — можно добавить отправку админу/в лог группу о результате
    # await message.answer(f"DEBUG: попытка записать Telegram ID: {'УСПЕХ' if updated_at or updated_noat else 'НЕ НАЙДЕН В NOTION'}")

# core/notion/notion_client.py (добавь максимально подробный print)
def set_telegram_id_for_client_by_username(username: str, telegram_id: int) -> bool:
    print(f"[SET_TG_ID] username arg = '{username}', telegram_id = {telegram_id}")
    clients = get_all_clients()
    for cl in clients:
        print(f"[SET_TG_ID] Проверяем: Notion username='{cl['username']}' vs input='{username}'")
        # Сравниваем оба варианта (с @ и без)
        if cl["username"].lstrip("@") == username.lstrip("@"):
            print(f"[SET_TG_ID] СОВПАДЕНИЕ! username='{cl['username']}'. Пишем telegram_id={telegram_id}")
            set_telegram_id_for_client(cl["id"], telegram_id)
            return True
    print(f"[SET_TG_ID] Нет совпадения для username '{username}'")
    return False