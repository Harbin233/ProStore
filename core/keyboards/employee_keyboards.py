# core/keyboards/employee_keyboards.py

from core.keyboards.main_keyboard import build_menu

# Каждый сотрудник получает свой набор кнопок + "Статус клиентов" по умолчанию
egor_kb = build_menu(["Добавить клиента"])
ira_kb = build_menu(["📋 Начать карточку клиента", "Клиенты в работе"])
andrey_kb = build_menu(["📥 Получить карточку на проверку", "Пуш сотрудников"])
alexandr_kb = build_menu(["📊 Админ-панель", "Пуш сотрудников"])
irina_kb = build_menu(["✍️ Начать оформление ТапБлога", "🤖 Настроить чат-бота"])
anastasiya_kb = build_menu([])  # Только "Статус клиентов"

# Словарь ID → клавиатура
employee_keyboards = {
    7585439289: egor_kb,          # Егор
    7925207619: ira_kb,           # Ира (методолог)
    7553118544: anastasiya_kb,    # Анастасия
    8151289930: andrey_kb,        # Андрей
    6503850751: alexandr_kb,      # Александр
    7714773957: irina_kb          # Ирина Горшкова
}