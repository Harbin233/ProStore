from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.utils.push import push_message
from core.notion.notion_client import get_packaging_data, update_client_stage

router = Router()

IRA_ID = 7925207619
ANDREY_ID = 8151289930

class TopFSM(StatesGroup):
    checking_card = State()
    confirming_top = State()

@router.callback_query(F.data.startswith("andrey_start:"))
async def andrey_start(callback: CallbackQuery, state: FSMContext):
    _, client_id = callback.data.split(":")
    await state.update_data(client_id=client_id)

    data = get_packaging_data(client_id)
    if not data:
        await callback.message.answer("⛔️ Не удалось загрузить упаковку из Notion.")
        return

    await state.update_data(resource=data.get("resource_type", "—"))
    resource = data.get("resource_type", "—")

    # 1. Аватар
    avatar = data.get("avatar")
    if avatar and avatar not in ["—", "Нет фото", "Без фото"]:
        await callback.message.answer_photo(avatar, caption="🖼 Аватар ресурса",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_avatar")]]
            )
        )
    else:
        await callback.message.answer("🖼 Аватар ресурса: отсутствует",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_avatar")]]
            )
        )

    # 2. Основная текстовая информация
    text = f"📄 Информация по ресурсу ({resource}):\n"
    text += f"🔹 Тип: {resource}\n"
    text += f"🔹 Описание: {data.get('description', '—')}\n"
    text += f"🔹 Приветствие: {data.get('greeting', '—')}\n"
    text += f"🔹 Кнопка: {data.get('button_text', '—')}\n"
    text += f"🔹 Ссылка: {data.get('button_link', '—')}"
    await callback.message.answer(text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_info")]]
        )
    )

    # 3. Фото поста или приветствия
    label = "Фото поста" if resource == "Канал" else "Фото приветствия"
    media = data.get("post_image") if resource == "Канал" else data.get("greeting_photo")
    if media and media not in ["—", "Нет фото", "Без фото"]:
        await callback.message.answer_photo(media, caption=f"📷 {label}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_photo")]]
            )
        )
    else:
        await callback.message.answer(f"📷 {label}: отсутствует",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_photo")]]
            )
        )

    # 4. ADS
    ads = "🧠 ADS: \n"
    ads += f"- ТЗ: {data.get('ads_recommendation', '—')}\n"
    ads += f"- ЦА: {data.get('ads_target', '—')}\n"
    ads += f"- Баннер: {data.get('banner_task', '—')}\n"
    creatives = data.get("creatives", [])
    if creatives:
        ads += f"- Креативы:\n  • " + "\n  • ".join(creatives)
    else:
        ads += "- Креативы: —"

    await callback.message.answer(ads,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить этот блок", callback_data="confirm_block_ads")]]
        )
    )

    # Итоговые действия
    await callback.message.answer("Проверь карточку. Готов передать?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📤 Передать на этап 'ТОП'", callback_data="confirm_card")],
                              [InlineKeyboardButton(text="🔁 На доработку", callback_data="revise_card")]]
        )
    )
    await state.set_state(TopFSM.checking_card)

@router.callback_query(TopFSM.checking_card)
async def handle_card(callback: CallbackQuery, state: FSMContext):
    client_id = (await state.get_data()).get("client_id")

    if callback.data == "confirm_card":
        await callback.message.answer("✅ Подтверждено. Нажми, когда клиент выйдет в ТОП.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📈 Вышел в ТОП", callback_data="confirm_top")]]
            )
        )
        await state.set_state(TopFSM.confirming_top)
    elif callback.data == "revise_card":
        await push_message(IRA_ID, "🔁 Карточка возвращена на доработку от Андрея.")
        await callback.message.answer("⛔️ Отправлено на доработку.")
        update_client_stage(client_id, "Упаковка")
        await state.clear()

@router.callback_query(TopFSM.confirming_top)
async def confirm_top(callback: CallbackQuery, state: FSMContext):
    client_id = (await state.get_data()).get("client_id")
    update_client_stage(client_id, "Выведен в ТОП")
    await callback.message.answer("🔝 Статус клиента обновлён: ВЫВЕДЕН В ТОП.")
    await state.clear()