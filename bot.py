import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# 1. Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# 2. Главное меню с Reply-кнопками (пример для Егора — остальные меню через свои keyboard-файлы)
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить клиента")],
        [KeyboardButton(text="Статус клиентов")],
    ],
    resize_keyboard=True
)

# 3. Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# 4. Импорт и подключение всех обработчиков
from core.handlers.start_handler import router as start_router
from core.handlers.andrey import router as andrey_router
from core.handlers.ira import router as ira_router
from core.handlers.anastasiya import router as anastasiya_router
from core.handlers.egor import router as egor_router
from core.handlers.alexandr import router as alexandr_router
from core.handlers.irina_gorshkova import router as irina_router
from core.handlers.status import router as status_router
from core.handlers.push_admin import router as push_admin_router  # <--- Новый роутер для пушей

dp.include_router(start_router)        # ⏫ Стартовое меню
dp.include_router(andrey_router)
dp.include_router(ira_router)
dp.include_router(anastasiya_router)
dp.include_router(egor_router)
dp.include_router(alexandr_router)
dp.include_router(irina_router)
dp.include_router(status_router)
dp.include_router(push_admin_router)   # <--- Включаем роутер PUSH-админки

# 5. APScheduler PUSH-уведомления — импорт и запуск
from core.push_scheduler import setup_push_jobs

# 6. Основной цикл запуска бота
async def main():
    logging.basicConfig(level=logging.INFO)
    setup_push_jobs(bot)   # <-- Запускаем PUSH-напоминания
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())