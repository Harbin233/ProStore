from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.utils.push import push_message
from core.notion.notion_client import is_packaging_done, update_client_stage, save_packaging_data

router = Router()

ANDREY_ID = 8151289930
IRA_ID = 7925207619

class MethodologistFSM(StatesGroup):
    choosing_type = State()
    avatar = State()
    description = State()
    greeting = State()
    greeting_photo = State()
    post_text = State()
    button_text = State()
    button_link = State()
    post_image = State()
    ads_recommendation = State()
    ads_target = State()
    ads_creatives_number = State()
    ads_creative_input = State()
    ads_banner_task = State()
    confirm_card = State()

@router.callback_query(F.data.startswith("ira_start:"))
async def start_packaging(callback: CallbackQuery, state: FSMContext):
    _, client_id, client_name = callback.data.split(":")
    if is_packaging_done(client_id):
        await callback.message.answer("❗️ Клиент уже упакован. Проверь карточку в Notion.")
        return

    await state.update_data(client_id=client_id)
    update_client_stage(client_id, "Упаковка")

    await callback.message.answer(
        f"Упаковка клиента: {client_name}\nВыбери тип ресурса:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Канал", callback_data="ira_channel")],
            [InlineKeyboardButton(text="Бот", callback_data="ira_bot")]
        ])
    )
    await state.set_state(MethodologistFSM.choosing_type)

@router.callback_query(MethodologistFSM.choosing_type)
async def resource_type_selected(callback: CallbackQuery, state: FSMContext):
    choice = "Канал" if callback.data == "ira_channel" else "Бот"
    await state.update_data(resource_type=choice)
    await callback.message.answer("Загрузи аватар ресурса.")
    await state.set_state(MethodologistFSM.avatar)

@router.message(MethodologistFSM.avatar)
async def get_avatar(message: Message, state: FSMContext):
    await state.update_data(avatar=message.photo[-1].file_id if message.photo else "Нет фото")
    data = await state.get_data()
    if data.get("resource_type") == "Канал":
        await message.answer("Введи описание ресурса (до 255 символов).")
    else:
        await message.answer("Введи описание бота (до 120 символов).")
    await state.set_state(MethodologistFSM.description)

@router.message(MethodologistFSM.description)
async def get_description(message: Message, state: FSMContext):
    data = await state.get_data()
    resource = data.get("resource_type")
    limit = 255 if resource == "Канал" else 120
    if len(message.text) > limit:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из {limit} символов")
        return
    await state.update_data(description=message.text)
    if resource == "Канал":
        await message.answer("Введи текст поста-закрепа (до 1024 символов).")
        await state.set_state(MethodologistFSM.post_text)
    else:
        await message.answer("Введи приветственное сообщение (до 512 символов).")
        await state.set_state(MethodologistFSM.greeting)

@router.message(MethodologistFSM.greeting)
async def get_greeting(message: Message, state: FSMContext):
    if len(message.text) > 512:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 512 символов")
        return
    await state.update_data(greeting=message.text)
    await message.answer("Прикрепи фото для приветствия или напиши 'Пропустить'.")
    await state.set_state(MethodologistFSM.greeting_photo)

@router.message(MethodologistFSM.greeting_photo)
async def get_greeting_photo(message: Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else "Без фото"
    await state.update_data(greeting_photo=image_id)
    data = await state.get_data()
    if data.get("resource_type") == "Канал":
        await message.answer("Введи текст после кнопки старт (до 1024 символов).")
        await state.set_state(MethodologistFSM.post_text)
    else:
        await message.answer("Есть ли услуга ADS у клиента:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Есть", callback_data="ads_yes")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="ads_no")]
            ])
        )
        await state.set_state(MethodologistFSM.ads_recommendation)

@router.message(MethodologistFSM.post_text)
async def get_post(message: Message, state: FSMContext):
    if len(message.text) > 1024:
        await message.answer(f"❗️ Превышено ограничение: {len(message.text)} из 1024 символов")
        return
    await state.update_data(post=message.text)
    await message.answer("Введи название кнопки или напиши 'Пропустить'.")
    await state.set_state(MethodologistFSM.button_text)

@router.message(MethodologistFSM.button_text)
async def get_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer("Введи ссылку для кнопки или напиши 'Пропустить'.")
    await state.set_state(MethodologistFSM.button_link)

@router.message(MethodologistFSM.button_link)
async def get_button_link(message: Message, state: FSMContext):
    await state.update_data(button_link=message.text)
    await message.answer("Прикрепи фото для поста или напиши 'Пропустить'.")
    await state.set_state(MethodologistFSM.post_image)

@router.message(MethodologistFSM.post_image)
async def get_image(message: Message, state: FSMContext):
    image_id = message.photo[-1].file_id if message.photo else "Без фото"
    await state.update_data(post_image=image_id)
    await message.answer("Есть ли услуга ADS у клиента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Есть", callback_data="ads_yes")],
            [InlineKeyboardButton(text="❌ Нет", callback_data="ads_no")]
        ])
    )
    await state.set_state(MethodologistFSM.ads_recommendation)

@router.callback_query(MethodologistFSM.ads_recommendation)
async def ask_ads(callback: CallbackQuery, state: FSMContext):
    if callback.data == "ads_yes":
        await callback.message.answer("Опиши, что нужно сделать с ресурсом для успешной модерации.")
        await state.set_state(MethodologistFSM.ads_recommendation)
    else:
        await callback.message.answer("Нажми, чтобы передать карточку техспециалисту:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Передать карточку", callback_data="send_card")]
            ])
        )
        await state.set_state(MethodologistFSM.confirm_card)

@router.message(MethodologistFSM.ads_recommendation)
async def get_ads_recommendation(message: Message, state: FSMContext):
    await state.update_data(ads_recommendation=message.text)
    await message.answer("Опиши целевую аудиторию клиента.")
    await state.set_state(MethodologistFSM.ads_target)

@router.message(MethodologistFSM.ads_target)
async def get_ads_target(message: Message, state: FSMContext):
    await state.update_data(ads_target=message.text)
    await message.answer("Сколько креативов будет? Введи число (0 — если этап пропускается).")
    await state.set_state(MethodologistFSM.ads_creatives_number)

@router.message(MethodologistFSM.ads_creatives_number)
async def get_creative_number(message: Message, state: FSMContext):
    try:
        number = int(message.text)
        if number < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректное число (0 или больше).")
        return
    await state.update_data(creative_total=number, creative_index=1, creatives=[])
    if number == 0:
        await message.answer("Этап креативов пропущен. Теперь напиши ТЗ и текст для баннера, если нужен, или напиши 'Пропустить'.")
        await state.set_state(MethodologistFSM.ads_banner_task)
    else:
        await message.answer(f"Введи текст креатива 1 из {number} (до 160 символов):")
        await state.set_state(MethodologistFSM.ads_creative_input)

@router.message(MethodologistFSM.ads_creative_input)
async def get_creative_text(message: Message, state: FSMContext):
    data = await state.get_data()
    creatives = data.get("creatives", [])
    index = data.get("creative_index", 1)
    total = data.get("creative_total", 0)

    if len(message.text) > 160:
        await message.answer(f"❗ Превышено ограничение: {len(message.text)} из 160 символов")
        return

    creatives.append(message.text)
    await state.update_data(creatives=creatives)

    if index >= total:
        await message.answer("Теперь напиши ТЗ и текст для баннера, если нужен, или напиши 'Пропустить'.")
        await state.set_state(MethodologistFSM.ads_banner_task)
    else:
        await state.update_data(creative_index=index + 1)
        await message.answer(f"Введи текст креатива {index + 1} из {total} (до 160 символов):")

@router.message(MethodologistFSM.ads_banner_task)
async def get_ads_banner(message: Message, state: FSMContext):
    await state.update_data(banner_task=message.text)
    await message.answer("Нажми, чтобы передать карточку техспециалисту:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Передать карточку", callback_data="send_card")]
        ])
    )
    await state.set_state(MethodologistFSM.confirm_card)

@router.callback_query(MethodologistFSM.confirm_card)
async def confirm_card(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.answer("✅ Карточка отправлена техспециалисту.")

    client_id = data.get("client_id")
    if client_id:
        update_client_stage(client_id, "Упаковка завершена")
        await save_packaging_data(client_id, data)

        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔧 Приступить к тех.этапу", callback_data=f"andrey_start:{client_id}")]]
        )
        await push_message(ANDREY_ID, "📦 Готовая упаковка. Начни техэтап.", markup)

    bot: Bot = callback.bot
    await bot.send_message(ANDREY_ID, "📤 Карточка готова. Проверь и подтверди, если всё верно.")
    await state.clear()

# ✅ Эта функция была недостающей — теперь добавлена корректно:
async def notify_ira_start_pack(client_id: str, client_name: str):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать упаковку", callback_data=f"ira_start:{client_id}:{client_name}")]
    ])
    await push_message(IRA_ID, f"✅ Клиент готов к упаковке: {client_name}", markup)