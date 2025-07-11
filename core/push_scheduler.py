# core/push_scheduler.py

import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_PUSH_DB_ID = os.getenv("NOTION_PUSH_DB_ID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
notion = Client(auth=NOTION_TOKEN)

PUSH_ADMINS = [8151289930, 6503850751]  # Андрей, Александр
SCHEDULER = None

def setup_push_jobs(bot: Bot):
    global SCHEDULER
    SCHEDULER = AsyncIOScheduler()
    push_list = get_all_push_intervals_from_notion()
    logging.info(f"[PUSH] Интервалы, полученные из Notion: {push_list}")
    for user_id, interval in push_list.items():
        SCHEDULER.add_job(
            send_push,
            trigger="interval",
            hours=interval,
            args=[bot, user_id],
            id=f"push_{user_id}",
            replace_existing=True
        )
        logging.info(f"[PUSH] Задача PUSH для {user_id} каждые {interval} ч. запущена.")
    SCHEDULER.start()
    logging.info("[PUSH] SCHEDULER стартовал.")

async def send_push(bot: Bot, user_id: int):
    try:
        await bot.send_message(
            user_id,
            "⏰ Напоминание! Проверь дедлайны по задачам или сообщи о статусе выполнения."
        )
        logging.info(f"[PUSH] PUSH-напоминание отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"[PUSH] Не удалось отправить PUSH {user_id}: {e}")

def update_push_interval(user_id: int, hours: int, bot: Bot):
    logging.info(f"[PUSH] Пытаюсь обновить интервал для user_id={user_id} на {hours} ч.")
    save_push_interval_to_notion(user_id, hours)
    job_id = f"push_{user_id}"
    if SCHEDULER.get_job(job_id):
        SCHEDULER.remove_job(job_id)
        logging.info(f"[PUSH] Старая задача PUSH для {user_id} удалена.")
    SCHEDULER.add_job(
        send_push,
        trigger="interval",
        hours=hours,
        args=[bot, user_id],
        id=job_id,
        replace_existing=True
    )
    logging.info(f"[PUSH] Новый PUSH-interval для {user_id}: {hours} ч.")

def get_push_interval(user_id: int) -> int:
    interval = get_interval_from_notion(user_id) or 4
    logging.info(f"[PUSH] Текущий PUSH-интервал для {user_id}: {interval} ч.")
    return interval

def get_all_push_intervals_from_notion() -> dict:
    res = {}
    try:
        results = notion.databases.query(database_id=NOTION_PUSH_DB_ID).get("results", [])
    except Exception as e:
        logging.error(f"[PUSH:Notion] Ошибка запроса к Notion: {e}")
        return res
    for page in results:
        try:
            user_id = page["properties"].get("User ID", {}).get("number", None)
            interval = page["properties"].get("Интервал", {}).get("number", 4)
            if user_id and interval:
                res[int(user_id)] = int(interval)
        except Exception as e:
            logging.error(f"[PUSH:Notion] Ошибка чтения строки: {e}")
    return res

def save_push_interval_to_notion(user_id: int, hours: int):
    try:
        results = notion.databases.query(
            database_id=NOTION_PUSH_DB_ID,
            filter={
                "property": "User ID",
                "number": {"equals": user_id}
            }
        ).get("results", [])
        if results:
            page_id = results[0]["id"]
            notion.pages.update(
                page_id=page_id,
                properties={
                    "Интервал": {"number": hours}
                }
            )
            logging.info(f"[PUSH:Notion] Интервал для user_id={user_id} обновлен в Notion: {hours}")
        else:
            notion.pages.create(
                parent={"database_id": NOTION_PUSH_DB_ID},
                properties={
                    "Name": {"title": [{"text": {"content": f"User {user_id}"}}]},
                    "User ID": {"number": user_id},
                    "Интервал": {"number": hours}
                }
            )
            logging.info(f"[PUSH:Notion] Создана новая строка для user_id={user_id} с интервалом {hours}")
    except Exception as e:
        logging.error(f"[PUSH:Notion] Ошибка при обновлении/создании строки для {user_id}: {e}")

def get_interval_from_notion(user_id: int) -> int | None:
    try:
        results = notion.databases.query(
            database_id=NOTION_PUSH_DB_ID,
            filter={
                "property": "User ID",
                "number": {"equals": user_id}
            }
        ).get("results", [])
        if results:
            interval = results[0]["properties"].get("Интервал", {}).get("number", 4)
            logging.info(f"[PUSH:Notion] Прочитал интервал из Notion для {user_id}: {interval}")
            return interval
    except Exception as e:
        logging.error(f"[PUSH:Notion] Ошибка чтения интервала для {user_id}: {e}")
    return None

# ============ End of push_scheduler.py ===============