import os
from dotenv import load_dotenv, find_dotenv

print('find_dotenv:', find_dotenv())
load_dotenv(find_dotenv())
print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))
print("NOTION_STAGE_LOG_DB_ID:", os.getenv("NOTION_STAGE_LOG_DB_ID"))
print("DEBUG OPENAI (main.py):", os.getenv("OPENAI_API_KEY"))

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить клиента")],
        [KeyboardButton(text="Статус клиентов")],
    ],
    resize_keyboard=True
)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# === Подключаем групповой дебаг-хендлер самым первым ===
from core.handlers.group_join_logger import router as group_logger_router
dp.include_router(group_logger_router)

# --- 100% отлов любого сообщения ---
@dp.message()
async def _debug_all_messages(message):
    print(f"[ALL_MESSAGES_DEBUG] chat={message.chat.id}, from_user={message.from_user.id}, username={message.from_user.username}, text={message.text}")

# --- Подключение ИИ — сразу после дебага! ---
from core.handlers.assistant import router as assistant_router
dp.include_router(assistant_router)

# --- Остальные роутеры ---
from core.handlers.start_handler import router as start_router
from core.handlers.andrey import router as andrey_router
from core.handlers.ira import router as ira_router
from core.handlers.anastasiya import router as anastasiya_router
from core.handlers.egor import router as egor_router
from core.handlers.alexandr import router as alexandr_router
from core.handlers.irina_gorshkova import router as irina_router
from core.handlers.status import router as status_router
from core.handlers.push_admin import router as push_admin_router
from core.handlers.groups import router as groups_router
from core.handlers.catch_all import router as catch_all_router

dp.include_router(start_router)
dp.include_router(andrey_router)
dp.include_router(ira_router)
dp.include_router(anastasiya_router)
dp.include_router(egor_router)
dp.include_router(alexandr_router)
dp.include_router(irina_router)
dp.include_router(status_router)
dp.include_router(push_admin_router)
dp.include_router(groups_router)
dp.include_router(catch_all_router)  # ВСЕГДА последним!

from core.push_scheduler import setup_push_jobs

async def main():
    logging.basicConfig(level=logging.INFO)
    setup_push_jobs(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())