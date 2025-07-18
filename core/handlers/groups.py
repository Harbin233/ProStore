from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

router = Router()
ANASTASIA_ID = 7553118544

logging.basicConfig(level=logging.INFO)

# Счётчик сообщений пользователя (chat_id, user_id) -> count
user_message_counter = {}

THRESHOLD = 3  # после скольки сообщений показывать кнопку

# "Широкая" инлайн-кнопка (текст можно отредактировать под себя)
group_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Позвать человека 👤", callback_data="call_human_group")]
    ]
)

@router.message()
async def count_user_messages(message: types.Message, bot):
    # Считаем только сообщения, не команды и не от ботов
    if message.from_user.is_bot or (message.text and message.text.startswith("/")):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    key = (chat_id, user_id)
    user_message_counter[key] = user_message_counter.get(key, 0) + 1
    logging.info(f"[SUPPORT] {user_id} отправил {user_message_counter[key]} сообщений в чате {chat_id}")

    if user_message_counter[key] == THRESHOLD:
        await bot.send_message(
            chat_id,
            f"{message.from_user.first_name}, если нужна помощь — жми кнопку 👇",
            reply_markup=group_inline_keyboard,
            reply_to_message_id=message.message_id
        )
        logging.info(f"[SUPPORT] Показана кнопка помощи для пользователя {user_id} ({message.from_user.username})")

@router.callback_query(F.data == "call_human_group")
async def call_human_group_callback(callback: CallbackQuery, bot):
    try:
        logging.info(f"[GROUPS] Получен callback от пользователя: {callback.from_user.id} ({callback.from_user.username})")
        await bot.send_message(
            ANASTASIA_ID,
            f"🔔 В чате <b>{callback.message.chat.title or callback.message.chat.id}</b>\n"
            f"Клиент <b>{callback.from_user.full_name}</b> (@{callback.from_user.username or callback.from_user.id}) нажал кнопку «Позвать человека». Нужно подключиться!",
            parse_mode="HTML"
        )
        logging.info(f"[GROUPS] Пуш отправлен Анастасии ({ANASTASIA_ID})")
        await callback.answer("Человек уже на связи — скоро ответит лично 👩‍💻", show_alert=True)
    except Exception as e:
        logging.error(f"[GROUPS] Ошибка в обработчике call_human_group_callback: {e}")