# update_required_flag.py
import os
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN        = os.getenv("NOTION_TOKEN")
PACKAGING_DB_ID     = os.getenv("NOTION_PACKAGING_DB_ID")
CLIENTS_DB_ID       = os.getenv("NOTION_DB_ID")  # база «Клиенты»

notion = Client(auth=NOTION_TOKEN)

def unset_client_required():
    resp = notion.databases.update(
        database_id=PACKAGING_DB_ID,
        properties={
            "Клиент": {
                "relation": {
                    "database_id": CLIENTS_DB_ID,
                    "required": False
                }
            }
        }
    )
    # Проверяем
    flag = resp["properties"]["Клиент"]["relation"].get("required")
    print(f"Required flag for 'Клиент' is now set to: {flag}")  # должно вывести False

if __name__ == "__main__":
    unset_client_required()