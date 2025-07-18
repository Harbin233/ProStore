from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from core.notion.notion_client import set_telegram_id_for_client_by_username

router = Router()

@router.message(Command("start"))
async def handle_start(message: Message):
    tg_id = message.from_user.id
    username = message.from_user.username
    name = message.from_user.full_name

    if not username:
        await message.answer("У вас не установлен username в Telegram. Установите его, чтобы продолжить.")
        return

    # Вписываем Telegram ID по username, если такой клиент уже есть
    updated = set_telegram_id_for_client_by_username("@" + username, tg_id)
    if updated:
        await message.answer("✅ Ваш Telegram ID привязан к карточке клиента. Спасибо!")
    else:
        await message.answer(
            "❗️Вы не зарегистрированы как клиент, обратитесь к менеджеру."
        )