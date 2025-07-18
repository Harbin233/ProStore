import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.notion.notion_client import (
    is_packaging_done,
    update_client_stage,
    save_packaging_data,
    get_client_name,
    get_client_services,
)

router = Router()

class IraGlobalFSM(StatesGroup):
    idle = State()
    final_confirm = State()

class IraChannelFSM(StatesGroup):
    avatar = State()
    description = State()
    post_text = State()
    button_text = State()
    button_link = State()
    post_image = State()

class IraBotFSM(StatesGroup):
    avatar = State()
    description = State()
    greeting = State()
    greeting_photo = State()

class IraAdsFSM(StatesGroup):
    ads_recommendation = State()
    ads_target = State()
    ads_creatives_number = State()
    ads_creative_input = State()
    ads_banner_task = State()

# === ВХОД В УПАКОВКУ (без пушей) ===
@router.callback_query(F.data.startswith("ira_start:"))
async def start_packaging(callback: CallbackQuery, state: FSMContext):
    _, client_id = callback.data.split(":")
    if is_packaging_done(client_id):
        await callback.message.answer("❗️ Клиент уже упакован.")
        return

    await callback.message.answer("⏳ Загружаю данные клиента…")
    await asyncio.sleep(0.7)
    await state.clear()
    await state.update_data(client_id=client_id)
    update_client_stage(client_id, "Упаковка")

    # Три попытки загрузить услуги клиента
    client_services = None
    for _ in range(3):
        try:
            client_services = get_client_services(client_id)
            if client_services:
                break
        except Exception:
            await asyncio.sleep(1)
    if not client_services:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Повторить попытку", callback_data=f"ira_start:{client_id}")]
        ])
        await callback.message.answer("❌ Не удалось получить данные клиента из Notion. Проверь соединение и попробуй ещё раз.", reply_markup=markup)
        return

    queue = []
    if "Вывод в ТОП" in client_services:
        queue += ["Канал", "Бот"]
    if "ADS" in client_services:
        queue.append("ADS")
    queue = list(dict.fromkeys(queue))
    if not queue:
        await callback.message.answer("Нет задач для упаковки!")
        return

    await state.update_data(pack_queue=queue, pack_index=0)
    await start_next_packaging(callback.message, state)

# === СТАРТ КАЖДОГО ЭТАПА ===
async def start_next_packaging(message: Message, state: FSMContext):
    data = await state.get_data()
    queue = data.get("pack_queue", [])
    index = data.get("pack_index", 0)

    if index >= len(queue):
        await message.answer(
            "✅ Все этапы упаковки завершены!\n\n"
            "Проверь все введённые данные. Когда всё готово — нажми кнопку ниже, чтобы отправить все карточки техспециалисту.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📤 Передать все карточки", callback_data="send_all_cards")]
                ]
            )
        )
        await state.set_state(IraGlobalFSM.final_confirm)
        return

    current = queue[index]
    if current == "Канал":
        await message.answer("Упаковка КАНАЛА:\n\n1️⃣ Сначала загрузи аватар канала (фото). Если нет — напиши 'Пропустить'.")
        await state.set_state(IraChannelFSM.avatar)
    elif current == "Бот":
        await message.answer("Упаковка БОТА:\n\n1️⃣ Сначала загрузи аватар бота (фото). Если нет — напиши 'Пропустить'.")
        await state.set_state(IraBotFSM.avatar)
    elif current == "ADS":
        await message.answer("Упаковка ADS:\n\n1️⃣ Опиши ТЗ для модерации (например: требования к ресурсу, рекомендации).")
        await state.set_state(IraAdsFSM.ads_recommendation)

# === КАНАЛ ===
@router.message(IraChannelFSM.avatar)
async def channel_avatar(message: Message, state: FSMContext):
    await state.update_data(channel_avatar=message.photo[-1].file_id if message.photo else "Нет фото")
    await message.answer("2️⃣ Введи описание канала (до 255 символов).")
    await state.set_state(IraChannelFSM.description)

@router.message(IraChannelFSM.description)
async def channel_description(message: Message, state: FSMContext):
    if len(message.text) > 255:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 255 символов")
        return
    await state.update_data(channel_description=message.text)
    await message.answer("3️⃣ Введи текст поста-закрепа (до 1024 символов).")
    await state.set_state(IraChannelFSM.post_text)

@router.message(IraChannelFSM.post_text)
async def channel_post_text(message: Message, state: FSMContext):
    if len(message.text) > 1024:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 1024 символов")
        return
    await state.update_data(channel_post_text=message.text)
    await message.answer("4️⃣ Введи название кнопки или напиши 'Пропустить'.")
    await state.set_state(IraChannelFSM.button_text)

@router.message(IraChannelFSM.button_text)
async def channel_button_text(message: Message, state: FSMContext):
    await state.update_data(channel_button_text=message.text)
    await message.answer("5️⃣ Введи ссылку для кнопки или напиши 'Пропустить'.")
    await state.set_state(IraChannelFSM.button_link)

@router.message(IraChannelFSM.button_link)
async def channel_button_link(message: Message, state: FSMContext):
    await state.update_data(channel_button_link=message.text)
    await message.answer("6️⃣ Прикрепи фото для поста или напиши 'Пропустить'.")
    await state.set_state(IraChannelFSM.post_image)

@router.message(IraChannelFSM.post_image)
async def channel_post_image(message: Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else "Без фото"
    await state.update_data(channel_post_image=image_id)
    data = await state.get_data()
    await state.update_data(pack_index=data.get("pack_index", 0) + 1)
    await start_next_packaging(message, state)

# === БОТ ===
@router.message(IraBotFSM.avatar)
async def bot_avatar(message: Message, state: FSMContext):
    await state.update_data(bot_avatar=message.photo[-1].file_id if message.photo else "Нет фото")
    await message.answer("2️⃣ Введи описание бота (до 120 символов).")
    await state.set_state(IraBotFSM.description)

@router.message(IraBotFSM.description)
async def bot_description(message: Message, state: FSMContext):
    if len(message.text) > 120:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 120 символов")
        return
    await state.update_data(bot_description=message.text)
    await message.answer("3️⃣ Введи приветственное сообщение (до 512 символов).")
    await state.set_state(IraBotFSM.greeting)

@router.message(IraBotFSM.greeting)
async def bot_greeting(message: Message, state: FSMContext):
    if len(message.text) > 512:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 512 символов")
        return
    await state.update_data(bot_greeting=message.text)
    await message.answer("4️⃣ Прикрепи фото для приветствия или напиши 'Пропустить'.")
    await state.set_state(IraBotFSM.greeting_photo)

@router.message(IraBotFSM.greeting_photo)
async def bot_greeting_photo(message: Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else "Без фото"
    await state.update_data(bot_greeting_photo=image_id)
    data = await state.get_data()
    await state.update_data(pack_index=data.get("pack_index", 0) + 1)
    await start_next_packaging(message, state)

# === ADS ===
@router.message(IraAdsFSM.ads_recommendation)
async def ads_recommendation(message: Message, state: FSMContext):
    await state.update_data(ads_recommendation=message.text)
    await message.answer("2️⃣ Опиши целевую аудиторию клиента.")
    await state.set_state(IraAdsFSM.ads_target)

@router.message(IraAdsFSM.ads_target)
async def ads_target(message: Message, state: FSMContext):
    await state.update_data(ads_target=message.text)
    await message.answer("3️⃣ Сколько креативов будет? Введи число (0 — если этап пропускается).")
    await state.set_state(IraAdsFSM.ads_creatives_number)

@router.message(IraAdsFSM.ads_creatives_number)
async def ads_creatives_number(message: Message, state: FSMContext):
    try:
        number = int(message.text)
        if number < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректное число (0 или больше).")
        return
    await state.update_data(ads_creative_total=number, ads_creative_index=1, ads_creatives=[])
    if number == 0:
        await message.answer("4️⃣ Этап креативов пропущен. Теперь напиши ТЗ и текст для баннера, если нужен, или напиши 'Пропустить'.")
        await state.set_state(IraAdsFSM.ads_banner_task)
    else:
        await message.answer(f"4️⃣ Введи текст креатива 1 из {number} (до 160 символов):")
        await state.set_state(IraAdsFSM.ads_creative_input)

@router.message(IraAdsFSM.ads_creative_input)
async def ads_creative_input(message: Message, state: FSMContext):
    data = await state.get_data()
    creatives = data.get("ads_creatives", [])
    index = data.get("ads_creative_index", 1)
    total = data.get("ads_creative_total", 0)
    if len(message.text) > 160:
        await message.answer(f"❗ Превышено ограничение: {len(message.text)} из 160 символов")
        return
    creatives.append(message.text)
    await state.update_data(ads_creatives=creatives)
    if index >= total:
        await message.answer("5️⃣ Теперь напиши ТЗ и текст для баннера, если нужен, или напиши 'Пропустить'.")
        await state.set_state(IraAdsFSM.ads_banner_task)
    else:
        await state.update_data(ads_creative_index=index + 1)
        await message.answer(f"Введи текст креатива {index + 1} из {total} (до 160 символов):")

@router.message(IraAdsFSM.ads_banner_task)
async def ads_banner_task(message: Message, state: FSMContext):
    await state.update_data(ads_banner_task=message.text)
    data = await state.get_data()
    await state.update_data(pack_index=data.get("pack_index", 0) + 1)
    await start_next_packaging(message, state)

# === ФИНАЛ: Передать все карточки ===
@router.callback_query(IraGlobalFSM.final_confirm)
async def send_all_cards(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    client_id = data.get("client_id")
    queue = data.get("pack_queue", [])

    if "Канал" in queue:
        channel_data = {
            "avatar": data.get("channel_avatar"),
            "description": data.get("channel_description"),
            "post": data.get("channel_post_text"),
            "button_text": data.get("channel_button_text"),
            "button_link": data.get("channel_button_link"),
            "post_image": data.get("channel_post_image"),
            "resource_type": "Канал"
        }
        await save_packaging_data(client_id, channel_data)
        update_client_stage(client_id, "Упаковка канала завершена")

    if "Бот" in queue:
        bot_data = {
            "avatar": data.get("bot_avatar"),
            "description": data.get("bot_description"),
            "greeting": data.get("bot_greeting"),
            "greeting_photo": data.get("bot_greeting_photo"),
            "resource_type": "Бот"
        }
        await save_packaging_data(client_id, bot_data)
        update_client_stage(client_id, "Упаковка бота завершена")

    if "ADS" in queue:
        ads_data = {
            "ads_recommendation": data.get("ads_recommendation"),
            "ads_target": data.get("ads_target"),
            "creatives": data.get("ads_creatives"),
            "banner_task": data.get("ads_banner_task"),
            "resource_type": "ADS"
        }
        await save_packaging_data(client_id, ads_data)
        update_client_stage(client_id, "Упаковка ADS завершена")

    await callback.message.answer("✅ Все карточки успешно отправлены техспециалисту!")
    # Здесь нет push_message и уведомления!
    await state.clear()