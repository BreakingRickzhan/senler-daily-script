import requests
import datetime
import json
import time

today = datetime.datetime.now()
yesterday = today - datetime.timedelta(days=1)

DATE = yesterday.strftime("%d.%m.%Y")
DATE_FROM = yesterday.strftime("%d.%m.%Y 00:00:00")
DATE_TO = today.strftime("%d.%m.%Y 00:00:00")
MONTH = yesterday.month

print(f"Дата: {DATE}")
print(f"Период: {DATE_FROM} → {DATE_TO}")

POST_LABELS = {
    1: "Ютуб",
    6: "Рассылка",
    7: "Посты",
    8: "Воронка",
    9: "Телега",
    11: "Товары",
    12: "ВК Видео",
    13: "ВК Клип"
}

GROUPS = {
    "Русский": {
        "group_id": 205902460,
        "access_token": "00daa7a3a7e45e97fed9211568c56047de86d810dfdab0a8",
        "subscriptions": {
            1: [2395975, 1234567], # ютуб
            6: [3266278],
            7: [2406181],
            8: [1111111],
            9: [2395963],
            11: [2581551],
            12: [3220962],
            13: [3221344]
        }
    },
    "Общество": {
        "group_id": 197891249,
        "access_token": "f90d22b146b588ed09ffc862b77653871209dd4416fed243",
        "subscriptions": {
            1: [2389343],
            6: [3266261],
            7: [2406180],
            8: [1111111],
            9: [2389344],
            11: [2581550],
            12: [3220821],
            13: [3221304]
        }
    },
    "История": {
        "group_id": 211095341,
        "access_token": "53c5ec2b055e77b5ad267353ae09b9d4f23d581913133b3f",
        "subscriptions": {
            1: [2395989],
            6: [3266303],
            7: [2406185],
            8: [1111111],
            9: [2395988],
            11: [2581552],
            12: [3220964],
            13: [3221168]
        }
    },
    "Биология": {
        "group_id": 229541725,
        "access_token": "1c76173165de588b68c6660f5957cecf95fdda3f3c54b461",
        "subscriptions": {
            1: [3247874],
            6: [3266310],
            7: [3247893],
            8: [1111111],
            9: [3247890],
            11: [1111111],
            12: [3247896],
            13: [3247899]
        }
    }
}

def get_all_subscribers(group_id, token, subscription_ids, max_retries=3, timeout=20):
    url = "https://senler.ru/api/subscribers/get"
    users = []
    offset = None
    retries = 0

    while True:
        params = {
            "access_token": token,
            "vk_group_id": group_id,
            "subscription_id[]": subscription_ids,
            "date_subscription_from": DATE_FROM,
            "date_subscription_to": DATE_TO,
            "v": 2
        }
        if offset:
            params["offset_id"] = offset

        try:
            print(f"Запрос: group_id={group_id}, sub_ids={subscription_ids}, offset={offset}")
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            users.extend(items)
            offset = data.get("offset_id")
            if not offset:
                break
            retries = 0  # сброс повторов после успешного запроса
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса: {e}")
            retries += 1
            if retries > max_retries:
                print(f"Превышено число попыток ({max_retries}), прерываем.")
                break
            wait = retries * 5
            print(f"Повтор через {wait} секунд...")
            time.sleep(wait)

    return users

results = []

for group_name, config in GROUPS.items():
    print(f"\n=== Обработка группы: {group_name} ===")
    group_id = config["group_id"]
    token = config["access_token"]
    all_user_ids = set()

    for label_key, sub_ids in config["subscriptions"].items():
        if any(sub_id == 1111111 for sub_id in sub_ids):
            continue

        label = POST_LABELS.get(label_key, f"ID {','.join(map(str, sub_ids))}")
        total_count = 0

        for sub_id in sub_ids:
            users = get_all_subscribers(group_id, token, [sub_id])

            count = 0
            for user in users:
                if user.get("status") != 1:
                    continue
                for sub in user.get("subscriptions", []):
                    if sub["subscription_id"] == sub_id and sub["status"] == 1:
                        sub_date = sub["date"].split()[0]
                        if sub_date == DATE:
                            count += 1
                            all_user_ids.add(user["vk_user_id"])
                            break

            print(f"{label} (sub_id={sub_id}): {count}")
            total_count += count
            time.sleep(1)  # задержка между запросами к API, чтобы не перегружать

        results.append({
            "date": DATE,
            "month": MONTH,
            "object": group_name,
            "post": label,
            "count": total_count
        })

    results.append({
        "date": DATE,
        "month": MONTH,
        "object": group_name,
        "post": "Уникальные",
        "count": len(all_user_ids)
    })

    print(f"Уникальные пользователи: {len(all_user_ids)}")

def send_to_google(results):
    url = "https://script.google.com/macros/s/AKfycbya3sMFue7mlSMVn2lV6TeQIXw9V7BRtzzjsBeuNgxfPdAGaMW9HkFVF-BTinW2bMY3/exec"
    headers = {"Content-Type": "application/json"}
    print("\n=== Отправка данных в Google Sheets ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))

    if not results:
        print("Пустой список результатов — ничего не отправляем.")
        return

    try:
        response = requests.post(url, json=results, headers=headers, timeout=20)
        print("Status code:", response.status_code)
        print("Response:", response.text)
    except Exception as e:
        print("Ошибка при отправке:", e)

print(results)
send_to_google(results)
print(json.dumps(results, indent=2, ensure_ascii=False))
