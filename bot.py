import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ✅ Подключение всех обработчиков (FSM и стартовых)
from core.handlers.start_handler import router as start_router
from core.handlers.andrey import router as andrey_router
from core.handlers.ira import router as ira_router
from core.handlers.anastasiya import router as anastasiya_router
from core.handlers.egor import router as egor_router
from core.handlers.alexandr import router as alexandr_router
from core.handlers.irina_gorshkova import router as irina_router

# ⏫ Подключаем стартовый роутер первым
dp.include_router(start_router)

# FSM-обработчики
dp.include_router(andrey_router)
dp.include_router(ira_router)
dp.include_router(anastasiya_router)
dp.include_router(egor_router)
dp.include_router(alexandr_router)
dp.include_router(irina_router)

# Основной цикл
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())