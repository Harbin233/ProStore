import os
import time
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime
from notion_client.errors import APIResponseError

load_dotenv()

NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("NOTION_DB_ID")
SERVICES_DB_ID    = os.getenv("NOTION_SERVICES_DB_ID")
PACKAGING_DB_ID   = os.getenv("NOTION_PACKAGING_DB_ID")
PUSH_DB_ID        = os.getenv("NOTION_PUSH_DB_ID")
STAGE_LOG_DB_ID   = os.getenv("NOTION_STAGE_LOG_DB_ID")  # Для истории этапов

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
    now = datetime.now().isoformat()
    response = retry_notion_update(
        notion.pages.create,
        parent={"database_id": DATABASE_ID},
        properties={
            "Имя":        {"title": [{"text": {"content": name}}]},
            "Комментарий":{"rich_text": [{"text": {"content": comment}}]},
            "Дата":       {"date": {"start": now}},
            "Этап":       {"select": {"name": "Новый"}},
            "Время старта этапа": {"date": {"start": now}},
            "Время окончания этапа": {"date": None}
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
    safe_clients = []
    for page in results:
        props = page.get("properties", {})
        name_prop = props.get("Имя", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop and "plain_text" in name_prop[0] else "(Без имени)"
        safe_clients.append({
            "id": page.get("id", ""),
            "name": name
        })
    return safe_clients

# =================== Услуги клиента ==========================

def add_service_entry(service_name: str, price: int, client_page_id: str) -> None:
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
        props = res.get("properties", {})
        title = props.get("Название услуги", {}).get("title", [])
        name = title[0]["plain_text"] if title and "plain_text" in title[0] else ""
        price = props.get("Цена", {}).get("number", 0)
        services.append({"name": name, "price": price})
    return services

def get_client_services(client_id: str) -> list[str]:
    return [service["name"] for service in get_services_for_client(client_id)]

# ================== Этапы и упаковка =========================

def update_client_stage(client_page_id: str, new_stage: str, user_id: int = None):
    """Обновляет этап, проставляет время начала и конца, пишет историю."""
    page = notion.pages.retrieve(client_page_id)
    props = page.get("properties", {})
    current_stage = props.get("Этап", {}).get("select", {}).get("name", "")
    now = datetime.now().isoformat()

    # Проверяем когда был старт этапа
    stage_start = props.get("Время старта этапа", {}).get("date", {}).get("start")

    updates = {
        "Этап": {"select": {"name": new_stage}}
    }

    # Если меняем этап — закрываем старый и стартуем новый
    if current_stage != new_stage:
        if stage_start:
            updates["Время окончания этапа"] = {"date": {"start": now}}
        updates["Время старта этапа"] = {"date": {"start": now}}
        updates["Время окончания этапа"] = {"date": None}
    else:
        # Если на тот же этап, просто обновляем старт (редко)
        updates["Время старта этапа"] = {"date": {"start": now}}

    retry_notion_update(
        notion.pages.update,
        page_id=client_page_id,
        properties=updates
    )

    # История перехода (лог)
    if STAGE_LOG_DB_ID:
        log_stage_change(client_page_id, current_stage, new_stage, user_id, now)

def log_stage_change(client_page_id, from_stage, to_stage, user_id, date):
    """Лог смены этапа (в историю этапов)"""
    try:
        notion.pages.create(
            parent={"database_id": STAGE_LOG_DB_ID},
            properties={
                "Клиент": {"relation": [{"id": client_page_id}]},
                "От этапа": {"rich_text": [{"text": {"content": from_stage}}]},
                "К этапу": {"rich_text": [{"text": {"content": to_stage}}]},
                "Изменил": {"number": user_id or 0},
                "Дата": {"date": {"start": date}}
            }
        )
    except Exception as e:
        print(f"[NOTION] Ошибка лога смены этапа: {e}")

def get_client_stage(client_page_id: str) -> str:
    page = notion.pages.retrieve(client_page_id)
    props = page.get("properties", {})
    stage_prop = props.get("Этап")
    if not stage_prop:
        return ""
    select_val = stage_prop.get("select")
    if not select_val:
        return ""
    return select_val.get("name", "")

def is_packaging_done(client_page_id: str) -> bool:
    return get_client_stage(client_page_id) == "Упаковка завершена"

def get_client_name(client_page_id: str) -> str:
    page = notion.pages.retrieve(client_page_id)
    title = page.get("properties", {}).get("Имя", {}).get("title", [])
    return title[0]["plain_text"] if title and "plain_text" in title[0] else ""

# ================== Упаковка ==========================

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
    retry_notion_update(
        notion.pages.create,
        parent={"database_id": PACKAGING_DB_ID},
        properties=props
    )

def get_packaging_data(client_id: str) -> dict:
    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter={
            "property": "Клиент",
            "relation": {"contains": client_id}
        }
    ).get("results", [])
    if not results:
        return {}
    props = results[0].get("properties", {})
    def extract_text(key: str) -> str:
        rich = props.get(key, {}).get("rich_text", [])
        return rich[0]["plain_text"] if rich and "plain_text" in rich[0] else ""
    def extract_select(key: str) -> str:
        select = props.get(key, {}).get("select")
        if not select:
            return ""
        return select.get("name", "")
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
    results = notion.databases.query(
        database_id=PACKAGING_DB_ID,
        filter={
            "property": "Клиент",
            "relation": {"contains": client_id}
        }
    ).get("results", [])
    packs = []
    for res in results:
        props = res.get("properties", {})
        def extract_text(key: str) -> str:
            rich = props.get(key, {}).get("rich_text", [])
            return rich[0]["plain_text"] if rich and "plain_text" in rich[0] else ""
        def extract_select(key: str) -> str:
            select = props.get(key, {}).get("select")
            if not select:
                return ""
            return select.get("name", "")
        def extract_multi(key: str) -> list[str]:
            return [item["name"] for item in props.get(key, {}).get("multi_select", [])]
        packs.append({
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

def get_packagings_by_stage(client_id: str, stage: str = None) -> list[dict]:
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
        props = res.get("properties", {})
        def extract_text(key: str) -> str:
            rich = props.get(key, {}).get("rich_text", [])
            return rich[0]["plain_text"] if rich and "plain_text" in rich[0] else ""
        def extract_select(key: str) -> str:
            select = props.get(key, {}).get("select")
            if not select:
                return ""
            return select.get("name", "")
        def extract_multi(key: str) -> list[str]:
            return [item["name"] for item in props.get(key, {}).get("multi_select", [])]
        packs.append({
            "id":                 res.get("id", ""),
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

# ================= PUSH-уведомления ==========================
def get_push_row_by_user_id(user_id: int):
    results = notion.databases.query(
        database_id=PUSH_DB_ID,
        filter={"property": "User ID", "number": {"equals": int(user_id)}}
    ).get("results", [])
    return results[0] if results else None

def get_push_interval_from_notion(user_id: int) -> int:
    row = get_push_row_by_user_id(user_id)
    if row:
        return row["properties"].get("Интервал", {}).get("number", 1)
    return 1

def update_push_interval_notion(user_id: int, interval: int) -> bool:
    row = get_push_row_by_user_id(user_id)
    if not row:
        print(f"[NOTION PUSH] Не найден user_id {user_id} для обновления!")
        return False
    page_id = row["id"]
    try:
        retry_notion_update(
            notion.pages.update,
            page_id=page_id,
            properties={"Интервал": {"number": interval}}
        )
        print(f"[NOTION PUSH] Интервал обновлён: user_id={user_id} -> {interval}")
        return True
    except Exception as e:
        print(f"[NOTION PUSH] Ошибка при обновлении интервала: {e}")
        return False

# =================== Время этапов и статусов =========================
# Оставляем, если будешь делать для упаковок или других сущностей

def update_client_stage_with_time(client_page_id: str, stage: str, is_new_stage: bool = True) -> None:
    now_iso = datetime.now().isoformat()
    props = {"Этап": {"select": {"name": stage}}}
    if is_new_stage:
        props["Время старта этапа"] = {"date": {"start": now_iso}}
        props["Время окончания этапа"] = {"date": None}
    else:
        props["Время окончания этапа"] = {"date": {"start": now_iso}}
    retry_notion_update(
        notion.pages.update,
        page_id=client_page_id,
        properties=props
    )

def update_packaging_status_with_time(pack_page_id: str, status: str, is_new_status: bool = True) -> None:
    now_iso = datetime.now().isoformat()
    props = {"Этап": {"select": {"name": status}}}
    if is_new_status:
        props["Время старта статуса"] = {"date": {"start": now_iso}}
        props["Время окончания статуса"] = {"date": None}
    else:
        props["Время окончания статуса"] = {"date": {"start": now_iso}}
    retry_notion_update(
        notion.pages.update,
        page_id=pack_page_id,
        properties=props
    )