from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu(custom_buttons: list[str]) -> ReplyKeyboardMarkup:
    """
    Строит Reply-клавиатуру для любой роли.
    custom_buttons — уникальные кнопки роли (список строк).
    Кнопка "Статус клиентов" добавляется всегда в конце.
    """
    keyboard = [[KeyboardButton(text=btn)] for btn in custom_buttons]
    keyboard.append([KeyboardButton(text="Статус клиентов")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)