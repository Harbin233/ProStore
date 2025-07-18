import os
import time
from notion_client import Client
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone, timedelta
from notion_client.errors import APIResponseError
from dateutil.parser import isoparse

load_dotenv(find_dotenv())

NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("NOTION_DB_ID")
SERVICES_DB_ID    = os.getenv("NOTION_SERVICES_DB_ID")
PACKAGING_DB_ID   = os.getenv("NOTION_PACKAGING_DB_ID")
PUSH_DB_ID        = os.getenv("NOTION_PUSH_DB_ID")
STAGE_LOG_DB_ID   = os.getenv("NOTION_STAGE_LOG_DB_ID")
STAFF_DB_ID       = os.getenv("NOTION_STAFF_DB_ID")  # <-- Новый

notion = Client(auth=NOTION_TOKEN)
moscow_tz = timezone(timedelta(hours=3))


def now_iso():
    return datetime.now(moscow_tz).isoformat()


def retry_notion_update(func, *args, retries=3, delay=1.0, **kwargs):
    for attempt in range(retries):
        try:
            result = func(*args, **kwargs)
            print(f"[NOTION] {func.__name__} выполнено (попытка {attempt + 1})")
            return result
        except APIResponseError as e:
            print(f"[NOTION] APIResponseError (попытка {attempt + 1}):", e)
            if hasattr(e, "code") and (e.code == 'conflict_error' or '409' in str(e)):
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
            raise
        except Exception as e:
            print(f"[NOTION] Неизвестная ошибка (попытка {attempt + 1}):", e)
            raise

# --- Получение staff_uuid из таблицы сотрудников по user_id (int)
def get_staff_relation_id(user_id: int):
    print(f"[STAFF] Поиск staff_uuid для user_id={user_id}")
    if not STAFF_DB_ID:
        print("[NOTION] STAFF_DB_ID не задан!")
        return None
    res = notion.databases.query(
        database_id=STAFF_DB_ID,
        filter={"property": "Telegram ID", "number": {"equals": int(user_id)}}
    ).get("results", [])
    if res:
        print(f"[STAFF] Найден staff_uuid: {res[0]['id']}")
        return res[0]["id"]
    print(f"[NOTION] Не найден сотрудник с Telegram ID={user_id}")
    return None

# ===== КЛИЕНТЫ =====

def create_client_page(name: str, username: str = None, comment: str = "") -> str:
    now = now_iso()
    print(f"[CREATE_CLIENT_PAGE] name={name}, username={username}, comment={comment}")
    props = {
        "Имя": {"title": [{"text": {"content": name}}]},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]},
        "Дата": {"date": {"start": now}},
        "Этап": {"select": {"name": "Новый"}},
        "Время старта этапа": {"date": {"start": now}},
        "Время окончания этапа": {"date": None},
    }
    if username:
        props["UserName"] = {"rich_text": [{"text": {"content": username}}]}
    print(f"[CREATE_CLIENT_PAGE] props={props}")
    response = retry_notion_update(
        notion.pages.create,
        parent={"database_id": DATABASE_ID},
        properties=props
    )
    page_id = response["id"]
    print(f"[CREATE_CLIENT_PAGE] Страница создана, id={page_id}")
    update_props = {
        "Client ID": {"rich_text": [{"text": {"content": page_id}}]}
    }
    retry_notion_update(
        notion.pages.update,
        page_id=page_id,
        properties=update_props
    )
    print(f"[CREATE_CLIENT_PAGE] Client ID записан")
    return page_id

def log_action(page_id: str, person: str, stage: str, comment: str = "") -> None:
    try:
        print(f"[LOG_ACTION] page_id={page_id}, person={person}, stage={stage}, comment={comment}")
        retry_notion_update(
            notion.comments.create,
            parent={"page_id": page_id},
            rich_text=[{"text": {"content": f"{person} — {stage}: {comment}"}}]
        )
    except Exception as e:
        print("[NOTION] Ошибка log_action:", e)

def get_all_clients() -> list[dict]:
    print("[GET_ALL_CLIENTS] Запрос клиентов из Notion")
    results = notion.databases.query(database_id=DATABASE_ID).get("results", [])
    safe_clients = []
    for page in results:
        props = page.get("properties", {})
        name_prop = props.get("Имя", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop and "plain_text" in name_prop[0] else "(Без имени)"
        username = props.get("UserName", {}).get("rich_text", [])
        username_val = username[0]["plain_text"] if username and "plain_text" in username[0] else ""
        tg_id = props.get("Telegram ID", {}).get("number", None)
        safe_clients.append({
            "id": page.get("id", ""),
            "name": name,
            "username": username_val,
            "telegram_id": tg_id
        })
    print(f"[GET_ALL_CLIENTS] Получено клиентов: {len(safe_clients)}")
    return safe_clients

def set_username_for_client(client_id: str, username: str):
    print(f"[SET_USERNAME] Обновляем username {username} для клиента {client_id}")
    try:
        retry_notion_update(
            notion.pages.update,
            page_id=client_id,
            properties={
                "UserName": {"rich_text": [{"text": {"content": username}}]}
            }
        )
        print(f"[SET_USERNAME] UserName обновлён: {username} для {client_id}")
    except Exception as e:
        print(f"[SET_USERNAME] Ошибка set_username_for_client: {e}")

def set_telegram_id_for_client(client_id: str, telegram_id: int):
    print(f"[SET_TG_ID_CLIENT] Обновляем Telegram ID: {telegram_id} для клиента {client_id}")
    try:
        retry_notion_update(
            notion.pages.update,
            page_id=client_id,
            properties={
                "Telegram ID": {"number": telegram_id}
            }
        )
        print(f"[SET_TG_ID_CLIENT] Telegram ID обновлён: {telegram_id} для {client_id}")
    except Exception as e:
        print(f"[SET_TG_ID_CLIENT] Ошибка set_telegram_id_for_client: {e}")

def add_service_entry(service_name: str, price: int, client_page_id: str) -> None:
    print(f"[ADD_SERVICE_ENTRY] {service_name=} {price=} {client_page_id=}")
    retry_notion_update(
        notion.pages.create,
        parent={"database_id": SERVICES_DB_ID},
        properties={
            "Название услуги": {"title": [{"text": {"content": service_name}}]},
            "Цена": {"number": price},
            "Клиент": {"relation": [{"id": client_page_id}]}
        }
    )

def get_services_for_client(client_page_id: str) -> list[dict]:
    print(f"[GET_SERVICES_FOR_CLIENT] client_page_id={client_page_id}")
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
    print(f"[GET_SERVICES_FOR_CLIENT] Найдено услуг: {len(services)}")
    return services

def get_client_services(client_id: str) -> list[str]:
    print(f"[GET_CLIENT_SERVICES] client_id={client_id}")
    return [service["name"] for service in get_services_for_client(client_id)]

def log_stage_history(
    client_id: str,
    stage: str,
    employee_id: int,
    stage_start: str,
    stage_end: str = None,
    comment: str = ""
):
    print(f"[LOG_STAGE_HISTORY] client_id={client_id}, stage={stage}, employee_id={employee_id}, start={stage_start}, end={stage_end}, comment={comment}")
    if not STAGE_LOG_DB_ID:
        print("[NOTION] Ошибка: STAGE_LOG_DB_ID не задан!")
        return

    staff_uuid = get_staff_relation_id(employee_id) if employee_id else None
    properties = {
        "Клиент": {"relation": [{"id": client_id}]},
        "Этап": {"select": {"name": stage}},
        "Время старта этапа": {"date": {"start": stage_start}},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]}
    }
    if staff_uuid:
        properties["Сотрудник"] = {"relation": [{"id": staff_uuid}]}

    if stage_end:
        properties["Время окончания этапа"] = {"date": {"start": stage_end}}
        try:
            start_dt = isoparse(stage_start)
            end_dt = isoparse(stage_end)
            duration = int((end_dt - start_dt).total_seconds() // 60)
            properties["Длительность"] = {"number": duration}
        except Exception as e:
            print("[NOTION] Ошибка расчёта длительности:", e)

    try:
        retry_notion_update(
            notion.pages.create,
            parent={"database_id": STAGE_LOG_DB_ID},
            properties=properties
        )
    except Exception as e:
        print("[NOTION] Ошибка записи истории этапа:", e)

def update_client_stage(client_page_id: str, new_stage: str, user_id: int = None):
    print(f"[UPDATE_CLIENT_STAGE] client_page_id={client_page_id} -> new_stage={new_stage} user_id={user_id}")
    try:
        page = notion.pages.retrieve(client_page_id)
        props = page.get("properties", {})
        current_stage = props.get("Этап", {}).get("select", {}).get("name", "")
        now = now_iso()
        stage_start = props.get("Время старта этапа", {}).get("date", {}).get("start")

        updates = {
            "Этап": {"select": {"name": new_stage}}
        }
        if current_stage != new_stage:
            if stage_start:
                log_stage_history(
                    client_id=client_page_id,
                    stage=current_stage,
                    employee_id=user_id or 0,
                    stage_start=stage_start,
                    stage_end=now,
                    comment=f"Завершён этап: {current_stage}"
                )
                updates["Время окончания этапа"] = {"date": {"start": now}}
            log_stage_history(
                client_id=client_page_id,
                stage=new_stage,
                employee_id=user_id or 0,
                stage_start=now,
                stage_end=None,
                comment=f"Старт этапа: {new_stage}"
            )
            updates["Время старта этапа"] = {"date": {"start": now}}
            updates["Время окончания этапа"] = {"date": None}
        else:
            updates["Время старта этапа"] = {"date": {"start": now}}
        retry_notion_update(
            notion.pages.update,
            page_id=client_page_id,
            properties=updates
        )
        print("[UPDATE_CLIENT_STAGE] Статус клиента обновлён")
    except Exception as e:
        print("[NOTION] Ошибка update_client_stage:", e)

def get_client_stage(client_page_id: str) -> str:
    print(f"[GET_CLIENT_STAGE] client_page_id={client_page_id}")
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
    print(f"[IS_PACKAGING_DONE] client_page_id={client_page_id}")
    return get_client_stage(client_page_id) == "Упаковка завершена"

def get_client_name(client_page_id: str) -> str:
    print(f"[GET_CLIENT_NAME] client_page_id={client_page_id}")
    page = notion.pages.retrieve(client_page_id)
    title = page.get("properties", {}).get("Имя", {}).get("title", [])
    return title[0]["plain_text"] if title and "plain_text" in title[0] else ""

# ===== УПАКОВКА (SAVE) =====
def save_packaging_data(client_id: str, data: dict) -> None:
    print(f"[SAVE_PACKAGING_DATA] client_id={client_id}, data={data}")
    def as_rich(text: str):
        return [{"text": {"content": text}}] if text and text != "—" else []
    props = {
        "Тип ресурса": {"select": {"name": data.get("resource_type", "—")}},
        "Аватар": {"rich_text": as_rich(data.get("avatar", "—"))},
        "Описание": {"rich_text": as_rich(data.get("description", "—"))},
        "Приветствие": {"rich_text": as_rich(data.get("greeting", "—"))},
        "Фото приветствия": {"rich_text": as_rich(data.get("greeting_photo", "—"))},
        "Текст после кнопки": {"rich_text": as_rich(data.get("post", "—"))},
        "Кнопка": {"rich_text": as_rich(data.get("button_text", "—"))},
        "Ссылка": {"rich_text": as_rich(data.get("button_link", "—"))},
        "Фото поста": {"rich_text": as_rich(data.get("post_image", "—"))},
        "ADS: ТЗ": {"rich_text": as_rich(data.get("ads_recommendation", "—"))},
        "ADS: ЦА": {"rich_text": as_rich(data.get("ads_target", "—"))},
        "ADS: Баннер": {"rich_text": as_rich(data.get("banner_task", "—"))},
        "Креативы": [{"name": c} for c in data.get("creatives", [])] if data.get("creatives") else [],
        "Клиент": {"relation": [{"id": client_id}]}
    }
    retry_notion_update(
        notion.pages.create,
        parent={"database_id": PACKAGING_DB_ID},
        properties=props
    )
    print(f"[SAVE_PACKAGING_DATA] Данные упаковки записаны для клиента: {client_id}")

def get_packagings_for_client(client_id: str) -> list[dict]:
    print(f"[GET_PACKAGINGS_FOR_CLIENT] client_id={client_id}")
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
            "resource_type": extract_select("Тип ресурса"),
            "stage": extract_select("Этап"),
            "avatar": extract_text("Аватар"),
            "description": extract_text("Описание"),
            "greeting": extract_text("Приветствие"),
            "greeting_photo": extract_text("Фото приветствия"),
            "post": extract_text("Текст после кнопки"),
            "button_text": extract_text("Кнопка"),
            "button_link": extract_text("Ссылка"),
            "post_image": extract_text("Фото поста"),
            "ads_recommendation": extract_text("ADS: ТЗ"),
            "ads_target": extract_text("ADS: ЦА"),
            "banner_task": extract_text("ADS: Баннер"),
            "creatives": extract_multi("Креативы")
        })
    return packs

def get_packagings_by_stage(client_id: str, stage: str = None) -> list[dict]:
    print(f"[GET_PACKAGINGS_BY_STAGE] client_id={client_id} stage={stage}")
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
            "id": res.get("id", ""),
            "resource_type": extract_select("Тип ресурса"),
            "stage": extract_select("Этап"),
            "avatar": extract_text("Аватар"),
            "description": extract_text("Описание"),
            "greeting": extract_text("Приветствие"),
            "greeting_photo": extract_text("Фото приветствия"),
            "post": extract_text("Текст после кнопки"),
            "button_text": extract_text("Кнопка"),
            "button_link": extract_text("Ссылка"),
            "post_image": extract_text("Фото поста"),
            "ads_recommendation": extract_text("ADS: ТЗ"),
            "ads_target": extract_text("ADS: ЦА"),
            "banner_task": extract_text("ADS: Баннер"),
            "creatives": extract_multi("Креативы")
        })
    return packs

def get_push_row_by_user_id(user_id: int):
    print(f"[GET_PUSH_ROW_BY_USER_ID] user_id={user_id}")
    results = notion.databases.query(
        database_id=PUSH_DB_ID,
        filter={"property": "User ID", "number": {"equals": int(user_id)}}
    ).get("results", [])
    return results[0] if results else None

def get_push_interval_from_notion(user_id: int) -> int:
    row = get_push_row_by_user_id(user_id)
    if row:
        interval = row["properties"].get("Интервал", {}).get("number", 1)
        print(f"[GET_PUSH_INTERVAL_FROM_NOTION] user_id={user_id} interval={interval}")
        return interval
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

def set_telegram_id_for_client_by_username(username: str, telegram_id: int) -> bool:
    print(f"[SET_TG_ID] Ищем username: {username} для вставки tg_id={telegram_id}")
    clients = get_all_clients()
    for cl in clients:
        print(f"[SET_TG_ID] Проверяем клиента: {cl}")
        if cl["username"] == username:
            set_telegram_id_for_client(cl["id"], telegram_id)
            print(f"[SET_TG_ID] Telegram ID обновлён: {telegram_id} для @{username}")
            return True
    print(f"[SET_TG_ID] Не найден клиент с username @{username}")
    return False

def ensure_client_in_notion(user_id, username, name=None):
    print(f"[ENSURE_CLIENT] Проверяем: user_id={user_id} username={username} name={name}")
    clients = get_all_clients()
    print(f"[ENSURE_CLIENT] Получено клиентов: {len(clients)}")
    for c in clients:
        print(f"[ENSURE_CLIENT] Сравниваем с клиентом: {c}")
        if c["telegram_id"] == user_id:
            print(f"[ENSURE_CLIENT] Уже есть клиент с таким user_id: {user_id}")
            return
    if username:
        updated = set_telegram_id_for_client_by_username(username, user_id)
        print(f"[ENSURE_CLIENT] set_telegram_id_for_client_by_username: {updated}")
        if updated:
            return
    print(f"[ENSURE_CLIENT] Клиент не найден, создаём новый")
    create_client_page(name or username or f"User_{user_id}", username=username or "", comment="Автоматически добавлен")
    print(f"[ENSURE_CLIENT] Новый клиент создан")

if __name__ == "__main__":
    print("Тестовый запуск файла notion_client.py")
    print(f"CLIENTS: {DATABASE_ID}")
    print(f"SERVICES: {SERVICES_DB_ID}")
    print(f"PACKAGING: {PACKAGING_DB_ID}")
    print(f"PUSH: {PUSH_DB_ID}")
    print(f"STAGE_LOG: {STAGE_LOG_DB_ID}")

    try:
        clients = get_all_clients()
        print(f"Найдено клиентов: {len(clients)}")
    except Exception as ex:
        print("Ошибка получения клиентов:", ex)