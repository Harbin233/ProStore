import os
from notion_client import Client
from dotenv import load_dotenv, find_dotenv
from datetime import datetime

load_dotenv(find_dotenv())

NOTION_TOKEN         = os.getenv("NOTION_TOKEN")
TOP_CLIENTS_DB_ID    = os.getenv("NOTION_TOP_CLIENTS_DB_ID")
TOP_HISTORY_DB_ID    = os.getenv("NOTION_TOP_HISTORY_DB_ID")
TOP_PAYMENTS_DB_ID   = os.getenv("NOTION_TOP_PAYMENTS_DB_ID")
TOP_EXTENSIONS_DB_ID = os.getenv("NOTION_TOP_EXTENSIONS_DB_ID")
TOP_STAFF_DB_ID      = os.getenv("NOTION_TOP_STAFF_DB_ID")
TOP_SERVICES_DB_ID   = os.getenv("NOTION_TOP_SERVICES_DB_ID")
TOP_EXPENSES_DB_ID   = os.getenv("NOTION_TOP_EXPENSES_DB_ID")

notion = Client(auth=NOTION_TOKEN)

def get_all_top_clients():
    results = notion.databases.query(database_id=TOP_CLIENTS_DB_ID).get("results", [])
    clients = []
    for page in results:
        props = page.get("properties", {})
        name_prop = props.get("Имя клиента", {}).get("title", [])
        name = name_prop[0]["plain_text"] if name_prop and "plain_text" in name_prop[0] else "(Без имени)"
        
        status_val = props.get("Статус")
        status = ""
        if status_val and isinstance(status_val, dict):
            select_val = status_val.get("select")
            if select_val and isinstance(select_val, dict):
                status = select_val.get("name", "")
        
        date_val = props.get("Дата добавления")
        date = ""
        if date_val and isinstance(date_val, dict):
            date_dict = date_val.get("date")
            if date_dict and isinstance(date_dict, dict):
                date = date_dict.get("start", "")

        telegram_id = props.get("Telegram ID", {}).get("number", None)
        username_val = ""
        username = props.get("UserName", {}).get("rich_text", [])
        if username and isinstance(username, list) and "plain_text" in username[0]:
            username_val = username[0]["plain_text"]
        elif username and isinstance(username, list) and len(username) > 0:
            username_val = username[0].get("plain_text", "")

        clients.append({
            "id": page.get("id", ""),
            "name": name,
            "status": status,
            "date": date,
            "telegram_id": telegram_id,
            "username": username_val
        })
    return clients

def get_top_client_card(client_id: str) -> dict:
    page = notion.pages.retrieve(client_id)
    props = page.get("properties", {})
    def extract_title(key):
        t = props.get(key, {}).get("title", [])
        return t[0]["plain_text"] if t and "plain_text" in t[0] else ""
    def extract_text(key):
        t = props.get(key, {}).get("rich_text", [])
        return t[0]["plain_text"] if t and "plain_text" in t[0] else ""
    def extract_select(key):
        val = props.get(key, {}).get("select")
        return val["name"] if val else ""
    def extract_relation(key):
        return [item["id"] for item in props.get(key, {}).get("relation", [])]
    def extract_date(key):
        return props.get(key, {}).get("date", {}).get("start", "")
    def extract_number(key):
        return props.get(key, {}).get("number", "")

    return {
        "id": client_id,
        "name": extract_title("Имя клиента"),
        "telegram_id": extract_number("Telegram ID"),
        "username": extract_text("UserName"),
        "status": extract_select("Статус"),
        "services": extract_relation("Услуги"),
        "date_added": extract_date("Дата добавления"),
        "manager": extract_relation("Ответственный"),
        "comment": extract_text("Комментарий"),
        "budget": extract_number("Бюджет") or "",
        "note": extract_text("Заметки") or "",
    }

def get_top_services():
    results = notion.databases.query(database_id=TOP_SERVICES_DB_ID).get("results", [])
    services = []
    for page in results:
        name = page.get("properties", {}).get("Название услуги", {}).get("title", [])
        name_val = name[0]["plain_text"] if name and "plain_text" in name[0] else ""
        price = page.get("properties", {}).get("Цена", {}).get("number", 0)
        services.append({"id": page["id"], "name": name_val, "price": price})
    return services

def get_service_ids_by_names(names: list):
    all_services = get_top_services()
    name_to_id = {s["name"]: s["id"] for s in all_services}
    return [name_to_id[n] for n in names if n in name_to_id]

def add_top_client(
    main_client_id: str,
    name: str,
    status: str = "Ожидает счёт",
    date: str = None,
    comment: str = "",
    telegram_id: int = None,
    username: str = None,
    services: list = None,
    budget: int = None
):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    props = {
        "Имя клиента": {"title": [{"text": {"content": name}}]},
        "Статус": {"select": {"name": status}},
        "Дата добавления": {"date": {"start": date}},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]},
        "Связанный клиент": {"relation": [{"id": main_client_id}]}
    }
    if username:
        props["UserName"] = {"rich_text": [{"text": {"content": username}}]}
    if telegram_id is not None and str(telegram_id).isdigit():
        props["Telegram ID"] = {"number": int(telegram_id)}
    if services:
        props["Услуги"] = {"relation": [{"id": s} for s in services]}
    if budget is not None:
        props["Бюджет"] = {"number": budget}

    print("\n=== [add_top_client] ДАННЫЕ для записи ===")
    for k, v in props.items():
        print(f"{k}: {v}")

    notion.pages.create(
        parent={"database_id": TOP_CLIENTS_DB_ID},
        properties=props
    )

def set_telegram_id_for_top_client_by_username(username: str, telegram_id: int):
    """Обновляет Telegram ID в таблице ТОП по username."""
    clients = get_all_top_clients()
    for cl in clients:
        if cl["username"] == username:
            notion.pages.update(
                page_id=cl["id"],
                properties={"Telegram ID": {"number": telegram_id}}
            )
            print(f"[NOTION_TOP] Telegram ID обновлён в ТОП: {telegram_id} для {username} (id={cl['id']})")
            return True
    print(f"[NOTION_TOP] Клиент с username {username} не найден в ТОП!")
    return False

def add_top_payment(client_id: str, amount: int, date=None, article="Основная оплата", comment="", method="Карта"):
    if not date:
        date = datetime.now().isoformat()
    props = {
        "Клиент": {"relation": [{"id": client_id}]},
        "Сумма": {"number": amount},
        "Дата оплаты": {"date": {"start": date}},
        "Статья": {"select": {"name": article}},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]},
        "Способ оплаты": {"select": {"name": method}},
    }
    notion.pages.create(
        parent={"database_id": TOP_PAYMENTS_DB_ID},
        properties=props
    )

def add_top_extension(client_id: str, new_end_date: str, amount=0, comment="", staff_id=None):
    props = {
        "Клиент": {"relation": [{"id": client_id}]},
        "Дата продления": {"date": {"start": datetime.now().isoformat()}},
        "Новая дата окончания": {"date": {"start": new_end_date}},
        "Сумма": {"number": amount},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]},
    }
    if staff_id:
        props["Сотрудник"] = {"relation": [{"id": staff_id}]}
    notion.pages.create(
        parent={"database_id": TOP_EXTENSIONS_DB_ID},
        properties=props
    )

def update_top_stage(client_id: str, new_status: str):
    notion.pages.update(
        page_id=client_id,
        properties={
            "Статус": {"select": {"name": new_status}},
        }
    )

def log_top_stage(
    client_id: str,
    stage: str,
    staff_id: str = None,
    start_date: str = None,
    end_date: str = None,
    comment: str = ""
):
    now = datetime.now().isoformat()
    props = {
        "Клиент": {"relation": [{"id": client_id}]},
        "Этап": {"select": {"name": stage}},
        "Дата старта этапа": {"date": {"start": start_date or now}},
        "Комментарий/описание этапа": {"rich_text": [{"text": {"content": comment}}]},
    }
    if end_date:
        props["Дата окончания этапа"] = {"date": {"start": end_date}}
        try:
            from dateutil.parser import isoparse
            start_dt = isoparse(start_date or now)
            end_dt = isoparse(end_date)
            duration = int((end_dt - start_dt).total_seconds() // 60)
            props["Длительность"] = {"number": duration}
        except Exception as e:
            print("[NOTION_TOP] Ошибка расчёта длительности:", e)
    if staff_id:
        props["Сотрудник"] = {"relation": [{"id": staff_id}]}
    notion.pages.create(
        parent={"database_id": TOP_HISTORY_DB_ID},
        properties=props
    )

def add_top_expense(client_id: str, amount: int, date=None, article="Другое", comment="", service_id=None):
    if not date:
        date = datetime.now().isoformat()
    props = {
        "Клиент": {"relation": [{"id": client_id}]},
        "Сумма": {"number": amount},
        "Дата расхода": {"date": {"start": date}},
        "Статья расхода": {"select": {"name": article}},
        "Комментарий": {"rich_text": [{"text": {"content": comment}}]}
    }
    if service_id:
        props["Связанная услуга"] = {"relation": [{"id": service_id}]}
    notion.pages.create(
        parent={"database_id": TOP_EXPENSES_DB_ID},
        properties=props
    )

def get_top_staff():
    results = notion.databases.query(database_id=TOP_STAFF_DB_ID).get("results", [])
    staff = []
    for page in results:
        name = page.get("properties", {}).get("Имя", {}).get("title", [])
        name_val = name[0]["plain_text"] if name and "plain_text" in name[0] else ""
        tg_id = page.get("properties", {}).get("Telegram ID", {}).get("number", 0)
        role = page.get("properties", {}).get("Роль", {}).get("select", {}).get("name", "")
        staff.append({"id": page["id"], "name": name_val, "tg_id": tg_id, "role": role})
    return staff