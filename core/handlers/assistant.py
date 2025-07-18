import os
from aiogram import Router, types
import openai

router = Router()

# Дебаг-вывод ключа (оставь пока на всякий случай)
print("DEBUG OPENAI:", os.getenv("OPENAI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY") or "sk-...твой_ключ..."

# Telegram ID сотрудников (кому не отвечать и кого не считать клиентом)
STAFF_IDS = [
    7585439289,    # Егор
    7925207619,    # Ира
    7553118544,    # Анастасия
    8151289930,    # Андрей
    6503850751,    # Александр
]

ANDREY_ID = 8151289930  # ← Андрей получает PUSH при ошибке

@router.message()
async def ai_always_on_for_clients(message: types.Message, bot):
    # Игнорировать команды, сообщения от ботов, сотрудников и короткие сообщения
    if (
        message.from_user.is_bot
        or not message.text
        or message.text.startswith("/")
        or len(message.text) < 4
        or message.from_user.id in STAFF_IDS
    ):
        print(f"[AI] Игнорируем сообщение: {message.text} | От: {message.from_user.id}")
        return

    print(f"[AI] Входящее сообщение от клиента: {message.from_user.id} ({message.from_user.username}) — {message.text!r}")

    try:
        await bot.send_chat_action(message.chat.id, "typing")
        print("[AI] Отправляем запрос в OpenAI...")

        # Правильный вызов для openai>=1.0.0
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": message.text}]
        )
        gpt_answer = response.choices[0].message.content
        print(f"[AI] Ответ GPT: {gpt_answer!r}")
        await message.reply(gpt_answer)

    except Exception as e:
        print(f"[AI ERROR]: {e}")
        await message.reply("⚠️ Временно не могу ответить, попробуйте позже.")

        # --- PUSH Андрею, если это ошибка оплаты/лимита ---
        if "insufficient_quota" in str(e) or "401" in str(e) or "402" in str(e):
            try:
                await bot.send_message(
                    ANDREY_ID,
                    "❗️ OpenAI API: Закончились средства или превышен лимит!\n"
                    "Срочно пополните баланс: https://platform.openai.com/account/usage"
                )
            except Exception as push_err:
                print(f"[PUSH ERROR]: {push_err}")