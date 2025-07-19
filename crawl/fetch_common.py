import requests
from bs4 import BeautifulSoup
import csv
import os

url = "https://www.knou.ac.kr/schdulmanage/knou/26/monthSchdul.do"
headers = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0"
}

def fetch_month_schedule(year: int, month: int):
    data = {
        "year": str(year),
        "month": str(month).zfill(2)
    }
    res = requests.post(url, headers=headers, data=data)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.select(".sche-comt tbody tr")
    events = []

    for row in rows:
        date_text = row.select_one("th").text.strip()
        content_text = row.select_one("td").text.strip().replace("\n", " ")
        events.append({
            "date": date_text,
            "content": content_text
        })
    return events

# 전체 2025년 일정 수집
all_events = []
for month in range(1, 13):
    monthly = fetch_month_schedule(2025, month)
    all_events.extend(monthly)

# 디렉토리 생성
os.makedirs("data", exist_ok=True)

# CSV 저장
with open("data/common_schedule.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "date", "content"])
    writer.writeheader()
    for i, item in enumerate(all_events, start=1):
        writer.writerow({
            "id": i,
            "date": item["date"],
            "content": item["content"]
        })

print(f"[✅] 2025년 학사일정 {len(all_events)}건 저장 완료 → data/common_schedule.csv")
