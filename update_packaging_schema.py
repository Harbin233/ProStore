#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from notion_client import Client

"""
Скрипт создаёт с нуля все необходимые поля в базе "Упаковка" через Notion API:
- Relation поле "Клиент" на базу Clients
- Rollup "Client ID", "Client Name", "Client Start"
- Поля упаковки (select, rich_text, multi_select, checkbox)

Убедитесь, что в .env указаны:
NOTION_TOKEN
NOTION_DB_ID
NOTION_PACKAGING_DB_ID
"""

def update_packaging_schema():
    load_dotenv()
    token      = os.getenv("NOTION_TOKEN")
    clients_db = os.getenv("NOTION_DB_ID")
    pack_db    = os.getenv("NOTION_PACKAGING_DB_ID")

    notion = Client(auth=token)

    # Обновляем схему базы Packaging
    notion.databases.update(
        database_id=pack_db,
        properties={
            # Relation-поле «Клиент»
            "Клиент": {
                "relation": {"database_id": clients_db}
            },
            # Rollup-поля для подтяжки из Clients
            "Client ID": {
                "rollup": {
                    "relation_property_name": "Клиент",
                    "rollup_property_name":   "Client ID",
                    "function":               "show_original"
                }
            },
            "Client Name": {
                "rollup": {
                    "relation_property_name": "Клиент",
                    "rollup_property_name":   "Имя",
                    "function":               "show_original"
                }
            },
            "Client Start": {
                "rollup": {
                    "relation_property_name": "Клиент",
                    "rollup_property_name":   "Дата",
                    "function":               "show_original"
                }
            },
            # Поля упаковки
            "Тип ресурса": {"select": {"options": [
                {"name": "Канал"}, {"name": "Бот"}, {"name": "Канал+Бот"}
            ]}},
            "Аватар":             {"rich_text": {}},
            "Описание":           {"rich_text": {}},
            "Приветствие":        {"rich_text": {}},
            "Фото приветствия":   {"rich_text": {}},
            "Текст после кнопки": {"rich_text": {}},
            "Кнопка":             {"rich_text": {}},
            "Ссылка":             {"rich_text": {}},
            "Фото поста":         {"rich_text": {}},
            "ADS: ТЗ":            {"rich_text": {}},
            "ADS: ЦА":            {"rich_text": {}},
            "ADS: Баннер":        {"rich_text": {}},
            "Креативы":           {"multi_select": {"options": []}},
            "Передано техспецу?": {"checkbox": {}}
        }
    )
    print("✅ Поля базы 'Упаковка' созданы/обновлены через API")

if __name__ == "__main__":
    update_packaging_schema()