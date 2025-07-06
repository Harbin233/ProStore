from aiogram import Bot
import os
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)

async def push_message(
    target_id: int,
    text: str,
    reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | None = None
):
    try:
        await bot.send_message(chat_id=target_id, text=text, reply_markup=reply_markup)
    except Exception as e:
        print(f"[Push Error] Не удалось отправить сообщение {target_id}: {e}")