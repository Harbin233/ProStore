# inspect_schema.py
import os
import json
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

notion       = Client(auth=os.getenv("NOTION_TOKEN"))
PACKAGING    = os.getenv("NOTION_PACKAGING_DB_ID")
SERVICES     = os.getenv("NOTION_SERVICES_DB_ID")

def print_schema(db_id, name):
    db = notion.databases.retrieve(database_id=db_id)
    print(f"\n=== Schema of {name} (ID={db_id}) ===\n")
    for prop, info in db["properties"].items():
        # Тип свойства
        t = info["type"]
        print(f"{prop!r}: type={t}")
    print("\n")

if __name__ == "__main__":
    print_schema(PACKAGING, "Packaging")
    print_schema(SERVICES,  "Services")