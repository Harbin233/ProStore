from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.notion.notion_client import get_packagings_for_client, update_client_stage

router = Router()

IRA_ID = 7925207619

class AndreyFSM(StatesGroup):
    checking = State()
    comment = State()
    final = State()

# --- Кнопка Баланс OpenAI API ---
@router.message(F.text == "💰 Баланс OpenAI API")
async def show_openai_balance_link(message: Message):
    await message.answer(
        "💰 Перейти к балансу OpenAI:\n"
        "https://platform.openai.com/account/usage\n\n"
        "⚡️ Здесь видно остаток, дату оплаты и историю расходов.",
        disable_web_page_preview=True
    )

@router.callback_query(F.data.startswith("andrey_start:"))
async def andrey_start(callback: CallbackQuery, state: FSMContext):
    _, client_id = callback.data.split(":")
    all_packs = get_packagings_for_client(client_id)

    if not all_packs:
        await callback.message.answer("⛔️ Нет доступных упаковок для проверки.")
        return

    await state.clear()
    await state.update_data(
        client_id=client_id,
        packs=all_packs,
        pack_index=0
    )

    await callback.message.answer(
        f"Вам поступили упаковки: {', '.join([p['resource_type'] for p in all_packs])}.\n\n"
        f"Начинаем проверку!",
    )
    await next_pack_step(callback.message, state)

async def next_pack_step(message: Message, state: FSMContext):
    data = await state.get_data()
    packs = data.get("packs", [])
    index = data.get("pack_index", 0)

    if index >= len(packs):
        await message.answer(
            "✅ Все упаковки проверены!\n\n"
            "Готов отправить клиента на следующий этап?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📈 Клиент выведен в ТОП", callback_data="andrey_final_top")]
                ]
            )
        )
        await state.set_state(AndreyFSM.final)
        return

    cur_pack = packs[index]
    resource = cur_pack.get("resource_type", "—")

    await message.answer(f"🔹 Проверка упаковки: {resource.upper()}")

    if resource == "Канал":
        await show_channel_pack(message, cur_pack)
    elif resource == "Бот":
        await show_bot_pack(message, cur_pack)
    elif resource == "ADS":
        await show_ads_pack(message, cur_pack)
    else:
        await message.answer("Неизвестный тип упаковки.")

    await message.answer(
        "Всё верно?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Всё верно", callback_data="andrey_confirm_pack")],
                [InlineKeyboardButton(text="🔄 На доработку", callback_data="andrey_redo_pack")]
            ]
        )
    )
    await state.set_state(AndreyFSM.checking)

# --- Показать упаковку КАНАЛА
async def show_channel_pack(message: Message, data: dict):
    if data.get("avatar") and data["avatar"] not in ["Нет фото", "—"]:
        await message.answer_photo(data["avatar"], caption="Аватар")
    text = (
        f"📝 Описание: {data.get('description', '—')}\n"
        f"📌 Пост-закреп: {data.get('post', '—')}\n"
        f"🔘 Кнопка: {data.get('button_text', '—')}\n"
        f"🔗 Ссылка для кнопки: {data.get('button_link', '—')}\n"
    )
    await message.answer(text)
    if data.get("post_image") and data["post_image"] not in ["Без фото", "—"]:
        await message.answer_photo(data["post_image"], caption="Фото в посте")

# --- Показать упаковку БОТА
async def show_bot_pack(message: Message, data: dict):
    if data.get("avatar") and data["avatar"] not in ["Нет фото", "—"]:
        await message.answer_photo(data["avatar"], caption="Аватар")
    text = (
        f"📝 Описание: {data.get('description', '—')}\n"
        f"👋 Приветствие: {data.get('greeting', '—')}\n"
    )
    await message.answer(text)
    if data.get("greeting_photo") and data["greeting_photo"] not in ["Без фото", "—"]:
        await message.answer_photo(data["greeting_photo"], caption="Фото приветствия")

# --- Показать упаковку ADS
async def show_ads_pack(message: Message, data: dict):
    text = (
        f"🧠 ТЗ: {data.get('ads_recommendation', '—')}\n"
        f"🎯 ЦА: {data.get('ads_target', '—')}\n"
        f"📋 Баннер: {data.get('banner_task', '—')}\n"
    )
    creatives = data.get("creatives", [])
    if creatives:
        text += "🎨 Креативы:\n" + "\n".join([f"• {c}" for c in creatives])
    await message.answer(text)

# --- Кнопка "Всё верно"
@router.callback_query(AndreyFSM.checking, F.data == "andrey_confirm_pack")
async def confirm_pack(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get("pack_index", 0)
    packs = data.get("packs", [])
    resource = packs[index]["resource_type"]
    await callback.message.answer(f"✅ {resource} — подтверждён.")
    await state.update_data(pack_index=index + 1)
    await next_pack_step(callback.message, state)

# --- Кнопка "На доработку"
@router.callback_query(AndreyFSM.checking, F.data == "andrey_redo_pack")
async def redo_pack(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введи комментарий для возврата Ирине:")
    await state.set_state(AndreyFSM.comment)

# --- Обработка комментария и возврат
@router.message(AndreyFSM.comment)
async def comment_redo(message: Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("pack_index", 0)
    packs = data.get("packs", [])
    client_id = data.get("client_id")
    resource = packs[index]["resource_type"]
    comment = message.text

    # --- теперь пуш вынесен в notifications.py
    from core.utils.notifications import notify_ira_pack_reject
    await notify_ira_pack_reject(client_id, resource, comment)

    update_client_stage(client_id, f"Доработка: {resource}")
    await message.answer(f"Карточка отправлена на доработку ({resource}).")
    await state.clear()

# --- Финальное подтверждение ТОПа
@router.callback_query(AndreyFSM.final, F.data == "andrey_final_top")
async def andrey_final_top(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    update_client_stage(client_id, "Выведен в ТОП")
    await callback.message.answer("🔝 Статус клиента обновлён: ВЫВЕДЕН В ТОП.")
    await state.clear()