import os
import httpx
import datetime

async def get_openai_balance():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "❗️API-ключ не найден"

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient() as client:
            sub_resp = await client.get(
                "https://api.openai.com/v1/dashboard/billing/subscription",
                headers=headers
            )
            sub_data = sub_resp.json()
            hard_limit = float(sub_data.get("hard_limit_usd", 0))

            now = datetime.datetime.utcnow()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
            usage_resp = await client.get(
                f"https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}",
                headers=headers
            )
            usage_data = usage_resp.json()
            total_usage = float(usage_data.get("total_usage", 0)) / 100

            balance = hard_limit - total_usage
            return f"💸 Баланс OpenAI API: ${balance:.2f}\nИзрасходовано: ${total_usage:.2f} из ${hard_limit:.2f}"
    except Exception as e:
        return f"Ошибка запроса баланса: {e}"