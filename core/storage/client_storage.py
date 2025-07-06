import os
from core.notion.notion_client import create_client_page, log_action, get_all_clients

STORAGE_TYPE = os.getenv("STORAGE", "notion")  # fallback для будущих вариантов

def create_client(name: str, comment: str = "") -> str:
    if STORAGE_TYPE == "notion":
        return create_client_page(name, comment)
    else:
        raise NotImplementedError("Поддерживается только Notion.")

def log(client_id: str, person: str, stage: str, comment: str = ""):
    if STORAGE_TYPE == "notion":
        log_action(client_id, person, stage, comment)
    else:
        raise NotImplementedError("Поддерживается только Notion.")

def list_clients():
    if STORAGE_TYPE == "notion":
        return get_all_clients()
    else:
        raise NotImplementedError("Поддерживается только Notion.")