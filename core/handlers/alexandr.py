from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.notion.notion_client import get_all_clients  # Новый импорт

router = Router()

ALEXANDR_ID = 6503850751  # Telegram ID Александра

@router.message(CommandStart())
async def show_admin_button(message: Message):
    if message.from_user.id == ALEXANDR_ID:
        await message.answer(
            "Добро пожаловать! Выберите действие:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨‍💼 Админ-панель", callback_data="open_admin")]
            ])
        )
    else:
        await message.answer("Здравствуйте! Вы не администратор.")

@router.callback_query(F.data == "open_admin")
async def open_admin_panel(callback: CallbackQuery):
    if callback.from_user.id != ALEXANDR_ID:
        await callback.message.answer("⛔️ У вас нет доступа.")
        return

    await callback.message.answer(
        "📊 Админ-панель:\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Все клиенты", callback_data="view_clients")],
            [InlineKeyboardButton(text="📈 Прогресс проектов", callback_data="view_progress")],
            [InlineKeyboardButton(text="🧾 Логи действий", callback_data="view_logs")]
        ])
    )

@router.callback_query(F.data == "view_clients")
async def show_clients(callback: CallbackQuery):
    clients = get_all_clients()
    client_names = [client['name'] for client in clients]
    await callback.message.answer("📋 Список клиентов:\n" + "\n".join(client_names))

@router.callback_query(F.data == "view_progress")
async def show_progress(callback: CallbackQuery):
    await callback.message.answer("📈 Прогресс по клиентам (в разработке)...")

@router.callback_query(F.data == "view_logs")
async def show_logs(callback: CallbackQuery):
    await callback.message.answer("🧾 Логи (в разработке или временно недоступны)...")