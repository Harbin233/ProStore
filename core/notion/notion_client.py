import os
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

NOTION_TOKEN     = os.getenv("NOTION_TOKEN")
DATABASE_ID      = os.getenv("NOTION_DB_ID")
SERVICES_DB_ID   = os.getenv("NOTION_SERVICES_DB_ID")
PACKAGING_DB_ID  = os.getenv("NOTION_PACKAGING_DB_ID")

# Инициализация клиента Notion
notion = Client(auth=NOTION_TOKEN)


def create_client_page(name: str, comment: str = "") -> str:
    """
    Создаёт страницу клиента в базе Clients и автоматически заполняет поле Client ID своим page_id.
    """
    response = notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Имя":        {"title": [{"text": {"content": name}}]},
            "Комментарий":{"rich_text": [{"text": {"content": comment}}]},
            "Дата":       {"date": {"start": datetime.now().isoformat()}},
            "Этап":       {"select": {"name": "Новый"}}
        }
    )
    page_id = response["id"]
    notion.pages.update(
        page_id=page_id,
        properties={
            "Client ID": {"rich_text": [{"text": {"content": page_id}}]}
        }
    )
    return page_id


def log_action(page_id: str, person: str, stage: str, comment: str = "") -> None:
    """
    Добавляет комментарий к странице клиента в Clients.
    """
    notion.comments.create(
        parent={"page_id": page_id},
        rich_text=[{"text": {"content": f"{person} — {stage}: {comment}"}}]
    )


def get_all_clients() -> list[dict]:
    """
    Возвращает список клиентов {id, name} из базы Clients.
    """
    results = notion.databases.query(database_id=DATABASE_ID).get("results", [])
    return [
        {
            "id": page["id"],
            "name": page["properties"]["Имя"]["title"][0]["plain_text"]
        }
        for page in results
    ]


def add_service_entry(service_name: str, price: int, client_page_id: str) -> None:
    """
    Добавляет запись об услуге для клиента в базе Services через relation на Clients.
    """
    notion.pages.create(
        parent={"database_id": SERVICES_DB_ID},
        properties={
            "Название услуги": {"title": [{"text": {"content": service_name}}]},
            "Цена":            {"number": price},
            "Клиент":          {"relation": [{"id": client_page_id}]}
        }
    )


def get_services_for_client(client_page_id: str) -> list[dict]:
    """
    Возвращает список услуг {name, price} для клиента по relation-полю Клиент.
    """
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


def update_client_stage(client_page_id: str, stage: str) -> None:
    notion.pages.update(
        page_id=client_page_id,
        properties={"Этап": {"select": {"name": stage}}}
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
        "Client ID":            {"rich_text": [{"text": {"content": client_id}}]},
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
        "Креативы":             {"multi_select": [{"name": c} for c in data.get("creatives", [])]} if data.get("creatives") else [],
        "Передано техспецу?":   {"checkbox": {}}
    }

    await notion.pages.create(
        parent={"database_id": PACKAGING_DB_ID},
        properties=props
    )


def get_packaging_data(client_id: str) -> dict:
    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter={
            "property": "Client ID",
            "rich_text": {"contains": client_id}
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