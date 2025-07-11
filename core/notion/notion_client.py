import os
import time
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime
from notion_client.errors import APIResponseError

load_dotenv()

NOTION_TOKEN     = os.getenv("NOTION_TOKEN")
DATABASE_ID      = os.getenv("NOTION_DB_ID")
SERVICES_DB_ID   = os.getenv("NOTION_SERVICES_DB_ID")
PACKAGING_DB_ID  = os.getenv("NOTION_PACKAGING_DB_ID")

notion = Client(auth=NOTION_TOKEN)

# ============ Вспомогательная функция для ретраев ============
def retry_notion_update(func, *args, retries=3, delay=1.0, **kwargs):
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except APIResponseError as e:
            if hasattr(e, "code") and (e.code == 'conflict_error' or '409' in str(e)):
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
            raise

# ======================= Клиенты =============================

def create_client_page(name: str, comment: str = "") -> str:
    response = retry_notion_update(
        notion.pages.create,
        parent={"database_id": DATABASE_ID},
        properties={
            "Имя":        {"title": [{"text": {"content": name}}]},
            "Комментарий":{"rich_text": [{"text": {"content": comment}}]},
            "Дата":       {"date": {"start": datetime.now().isoformat()}},
            "Этап":       {"select": {"name": "Новый"}}
        }
    )
    page_id = response["id"]
    retry_notion_update(
        notion.pages.update,
        page_id=page_id,
        properties={
            "Client ID": {"rich_text": [{"text": {"content": page_id}}]}
        }
    )
    return page_id

def log_action(page_id: str, person: str, stage: str, comment: str = "") -> None:
    retry_notion_update(
        notion.comments.create,
        parent={"page_id": page_id},
        rich_text=[{"text": {"content": f"{person} — {stage}: {comment}"}}]
    )

def get_all_clients() -> list[dict]:
    results = notion.databases.query(database_id=DATABASE_ID).get("results", [])
    return [
        {
            "id": page["id"],
            "name": page["properties"]["Имя"]["title"][0]["plain_text"]
        }
        for page in results
    ]

# =================== Услуги клиента ==========================

def add_service_entry(service_name: str, price: int, client_page_id: str) -> None:
    print(client_page_id)
    retry_notion_update(
        notion.pages.create,
        parent={"database_id": SERVICES_DB_ID},
        properties={
            "Название услуги": {"title": [{"text": {"content": service_name}}]},
            "Цена":            {"number": price},
            "Клиент":          {"relation": [{"id": client_page_id}]}
        }
    )

def get_services_for_client(client_page_id: str) -> list[dict]:
    results = notion.databases.query(
        database_id=SERVICES_DB_ID,
        filter={
            "property": "Клиент",
            "relation": {"contains": client_page_id}
        }
    ).get("results", [])
    services = []
    for res in results:
        title = res["properties"]["Название услуги"]["title"]
        name = title[0]["plain_text"] if title else ""
        price = res["properties"]["Цена"]["number"]
        services.append({"name": name, "price": price})
    return services

def get_client_services(client_id: str) -> list[str]:
    """ Возвращает список названий услуг (строк) для клиента по его client_id. """
    return [service["name"] for service in get_services_for_client(client_id)]

# ================== Этапы и упаковка =========================

def update_client_stage(client_page_id: str, stage: str, retries: int = 3, delay: float = 1.0) -> None:
    # retry с задержкой для защиты от 409
    retry_notion_update(
        notion.pages.update,
        page_id=client_page_id,
        properties={"Этап": {"select": {"name": stage}}},
        retries=retries,
        delay=delay
    )

def get_client_stage(client_page_id: str) -> str:
    page = notion.pages.retrieve(client_page_id)
    return page["properties"].get("Этап", {}).get("select", {}).get("name", "")

def is_packaging_done(client_page_id: str) -> bool:
    return get_client_stage(client_page_id) == "Упаковка завершена"

def get_client_name(client_page_id: str) -> str:
    page = notion.pages.retrieve(client_page_id)
    title = page["properties"].get("Имя", {}).get("title", [])
    return title[0]["plain_text"] if title else ""

async def save_packaging_data(client_id: str, data: dict) -> None:
    def as_rich(text: str):
        return [{"text": {"content": text}}] if text and text != "—" else []
    props = {
        "Упаковка ID":          {"title": [{"text": {"content": "тест"}}]},
        "Тип ресурса":          {"select": {"name": data.get("resource_type", "—")} },
        "Аватар":               {"rich_text": as_rich(data.get("avatar", "—"))},
        "Описание":             {"rich_text": as_rich(data.get("description", "—"))},
        "Приветствие":          {"rich_text": as_rich(data.get("greeting", "—"))},
        "Фото приветствия":     {"rich_text": as_rich(data.get("greeting_photo", "—"))},
        "Текст после кнопки":   {"rich_text": as_rich(data.get("post", "—"))},
        "Кнопка":               {"rich_text": as_rich(data.get("button_text", "—"))},
        "Ссылка":               {"rich_text": as_rich(data.get("button_link", "—"))},
        "Фото поста":           {"rich_text": as_rich(data.get("post_image", "—"))},
        "ADS: ТЗ":              {"rich_text": as_rich(data.get("ads_recommendation", "—"))},
        "ADS: ЦА":              {"rich_text": as_rich(data.get("ads_target", "—"))},
        "ADS: Баннер":          {"rich_text": as_rich(data.get("banner_task", "—"))},
        "Креативы":             {"multi_select": [{"name": c} for c in data.get("creatives", [])] if data.get("creatives") else []},
        "Передано техспецу?":   {"checkbox": False},
        "Клиент":               {"relation": [{"id": client_id}]}
    }
    # retry Notion (409)
    retry_notion_update(
        notion.pages.create,
        parent={"database_id": PACKAGING_DB_ID},
        properties=props
    )

def get_packaging_data(client_id: str) -> dict:
    """
    Получить первую упаковку для клиента (как было для совместимости с остальным кодом).
    """
    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter={
            "property": "Клиент",
            "relation": {"contains": client_id}
        }
    ).get("results", [])
    if not results:
        return {}

    props = results[0]["properties"]

    def extract_text(key: str) -> str:
        rich = props.get(key, {}).get("rich_text", [])
        return rich[0]["plain_text"] if rich else ""

    def extract_select(key: str) -> str:
        return props.get(key, {}).get("select", {}).get("name", "")

    def extract_multi(key: str) -> list[str]:
        return [item["name"] for item in props.get(key, {}).get("multi_select", [])]

    return {
        "resource_type":      extract_select("Тип ресурса"),
        "avatar":             extract_text("Аватар"),
        "description":        extract_text("Описание"),
        "greeting":           extract_text("Приветствие"),
        "greeting_photo":     extract_text("Фото приветствия"),
        "post":               extract_text("Текст после кнопки"),
        "button_text":        extract_text("Кнопка"),
        "button_link":        extract_text("Ссылка"),
        "post_image":         extract_text("Фото поста"),
        "ads_recommendation": extract_text("ADS: ТЗ"),
        "ads_target":         extract_text("ADS: ЦА"),
        "banner_task":        extract_text("ADS: Баннер"),
        "creatives":          extract_multi("Креативы")
    }

def get_packagings_for_client(client_id: str) -> list[dict]:
    """
    Возвращает список всех упаковок (строк из базы 'Упаковки') по клиенту.
    Каждая упаковка — это словарь с данными по конкретному типу ресурса.
    """
    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter={
            "property": "Клиент",
            "relation": {"contains": client_id}
        }
    ).get("results", [])
    packs = []
    for res in results:
        props = res["properties"]

        def extract_text(key: str) -> str:
            rich = props.get(key, {}).get("rich_text", [])
            return rich[0]["plain_text"] if rich else ""

        def extract_select(key: str) -> str:
            return props.get(key, {}).get("select", {}).get("name", "")

        def extract_multi(key: str) -> list[str]:
            return [item["name"] for item in props.get(key, {}).get("multi_select", [])]

        packs.append({
            "resource_type":      extract_select("Тип ресурса"),
            "stage":              extract_select("Этап"),  # <--- ВАЖНО! теперь будет доступен статус упаковки
            "avatar":             extract_text("Аватар"),
            "description":        extract_text("Описание"),
            "greeting":           extract_text("Приветствие"),
            "greeting_photo":     extract_text("Фото приветствия"),
            "post":               extract_text("Текст после кнопки"),
            "button_text":        extract_text("Кнопка"),
            "button_link":        extract_text("Ссылка"),
            "post_image":         extract_text("Фото поста"),
            "ads_recommendation": extract_text("ADS: ТЗ"),
            "ads_target":         extract_text("ADS: ЦА"),
            "banner_task":        extract_text("ADS: Баннер"),
            "creatives":          extract_multi("Креативы")
        })
    return packs

# ———— НОВОЕ: упаковки по статусу ————
def get_packagings_by_stage(client_id: str, stage: str = None) -> list[dict]:
    """
    Возвращает список упаковок (PACKAGING_DB_ID) для клиента.
    Если указан stage — только для нужного этапа (например, "На доработке").
    """
    filter_ = {
        "and": [
            {"property": "Клиент", "relation": {"contains": client_id}}
        ]
    }
    if stage:
        filter_["and"].append({
            "property": "Этап", "select": {"equals": stage}
        })

    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter=filter_
    ).get("results", [])
    packs = []
    for res in results:
        props = res["properties"]

        def extract_text(key: str) -> str:
            rich = props.get(key, {}).get("rich_text", [])
            return rich[0]["plain_text"] if rich else ""

        def extract_select(key: str) -> str:
            return props.get(key, {}).get("select", {}).get("name", "")

        def extract_multi(key: str) -> list[str]:
            return [item["name"] for item in props.get(key, {}).get("multi_select", [])]

        packs.append({
            "id":                 res["id"],
            "resource_type":      extract_select("Тип ресурса"),
            "stage":              extract_select("Этап"),
            "avatar":             extract_text("Аватар"),
            "description":        extract_text("Описание"),
            "greeting":           extract_text("Приветствие"),
            "greeting_photo":     extract_text("Фото приветствия"),
            "post":               extract_text("Текст после кнопки"),
            "button_text":        extract_text("Кнопка"),
            "button_link":        extract_text("Ссылка"),
            "post_image":         extract_text("Фото поста"),
            "ads_recommendation": extract_text("ADS: ТЗ"),
            "ads_target":         extract_text("ADS: ЦА"),
            "banner_task":        extract_text("ADS: Баннер"),
            "creatives":          extract_multi("Креативы")
        })
    return packs