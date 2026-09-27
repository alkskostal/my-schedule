#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from datetime import datetime
from icalendar import Calendar, Event
import pytz
import sys
import os

# ============ НАСТРОЙКИ ============
# Токен будет браться из секретов GitHub
BEARER_TOKEN = os.environ.get("INSTUDY_TOKEN", "")

# Номер семестра
SEMESTER = 3

# Часовой пояс
TIMEZONE = "Europe/Moscow"

# Куда сохранять результат
OUTPUT_FILE = "schedule.ics"
# ===================================

API_URL = f"https://v2api.instudy.online/api/schedule?semester={SEMESTER}&university_events=0"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Accept-Language": "ru",
    "Origin": "https://v2.instudy.online",
    "Referer": "https://v2.instudy.online/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
}

def fetch_schedule():
    print(f"→ Запрашиваю {API_URL}")
    response = requests.get(API_URL, headers=HEADERS, timeout=30)

    if response.status_code == 401:
        print("❌ Ошибка 401: токен устарел.")
        sys.exit(1)
    if response.status_code != 200:
        print(f"❌ Ошибка {response.status_code}: {response.text[:300]}")
        sys.exit(1)

    data = response.json()
    print(f"✅ Получено {len(data)} дней расписания")
    return data

def parse_datetime(date_str, time_str):
    tz = pytz.timezone(TIMEZONE)
    date = datetime.strptime(date_str, "%d.%m.%Y")

    if " - " in time_str:
        start_str, end_str = time_str.split(" - ")
    elif "-" in time_str:
        start_str, end_str = time_str.split("-")
    else:
        return None, None

    start_h, start_m = map(int, start_str.strip().split(":"))
    end_h, end_m = map(int, end_str.strip().split(":"))

    start_dt = tz.localize(datetime(date.year, date.month, date.day, start_h, start_m))
    end_dt = tz.localize(datetime(date.year, date.month, date.day, end_h, end_m))
    return start_dt, end_dt

def build_ics(data):
    cal = Calendar()
    cal.add("prodid", "-//instudy schedule//RU")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", "Расписание вуза")
    cal.add("X-WR-TIMEZONE", TIMEZONE)

    total_events = 0

    for day in data:
        date_str = day.get("date")
        items = day.get("items", [])
        if not date_str:
            continue

        for item in items:
            if item.get("cancel"):
                continue

            period = item.get("period", "")
            start_dt, end_dt = parse_datetime(date_str, period)
            if not start_dt:
                continue

            event = Event()
            discipline = item.get("discipline", "Занятие")
            event.add("summary", discipline)

            ic = item.get("IC") or {}
            room = ic.get("room", "").strip()
            place = ic.get("place", "").strip()
            workload = ic.get("typeOfWorkload", "")
            teacher = item.get("teacher", "")

            location = room or place
            if location:
                event.add("location", location)

            description_parts = []
            if workload:
                description_parts.append(f"Тип: {workload}")
            if teacher:
                description_parts.append(f"Преподаватель: {teacher}")
            if item.get("online"):
                description_parts.append("Онлайн-занятие")
            if description_parts:
                event.add("description", "\n".join(description_parts))

            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
            event.add("dtstamp", datetime.now(pytz.utc))
            event.add("uid", f"{item.get('id', total_events)}@instudy")

            cal.add_component(event)
            total_events += 1

    with open(OUTPUT_FILE, "wb") as f:
        f.write(cal.to_ical())

    print(f"✅ Создан {OUTPUT_FILE} — {total_events} событий")

if __name__ == "__main__":
    data = fetch_schedule()
    build_ics(data)
