# fetch_cs_update.py

import os
import csv
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_URL = "https://cs.knou.ac.kr"
PAGE_URL_TEMPLATE = "https://cs.knou.ac.kr/cs1/4812/subview.do?page={}&enc=Zm5jdDF8QEB8JTJGYmJzJTJGY3MxJTJGMjExOSUyRmFydGNsTGlzdC5kbyUzRg%3D%3D"

EXISTING_CSV = os.path.join("data", "cs_notices_2025.csv")
UPDATE_CSV = os.path.join("data", "cs_notices_update.csv")

def load_existing_ids():
    if not os.path.exists(EXISTING_CSV):
        return set()
    with open(EXISTING_CSV, newline='', encoding='utf-8') as f:
        return {row['id'] for row in csv.DictReader(f)}

def crawl_new_cs_notices(existing_ids, max_page=3):
    new_notices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, max_page + 1):
            print(f"🔍 컴공 갱신 확인 중... 페이지 {page_num}")
            page.goto(PAGE_URL_TEMPLATE.format(page_num))
            rows = page.locator("table.board-table tbody tr")

            for i in range(rows.count()):
                row = rows.nth(i)
                dept = row.locator("td.td-write").inner_text().strip()
                if dept != "컴퓨터과학과":
                    continue

                title_elem = row.locator("td.td-subject a")
                title = title_elem.inner_text().strip()
                link = title_elem.get_attribute("href")
                full_url = BASE_URL + link
                date = row.locator("td.td-date").inner_text().strip()
                article_id = link.split("/")[-2] if link else "unknown"

                if article_id in existing_ids:
                    continue

                page.goto(full_url)
                content_elem = page.locator("div.view-con").first
                content = content_elem.inner_text().strip() if content_elem.count() > 0 else "본문 없음"

                new_notices.append({
                    "id": article_id,
                    "title": title,
                    "date": date,
                    "content": content,
                    "url": full_url
                })

                page.goto(PAGE_URL_TEMPLATE.format(page_num))
                time.sleep(0.5)

        browser.close()
    return new_notices

def save_new_notices(notices):
    if not notices:
        print("📭 새로운 공지 없음")
        return

    os.makedirs("data", exist_ok=True)
    notices.sort(key=lambda x: datetime.strptime(x["date"].replace('.', '-'), "%Y-%m-%d"), reverse=True)
    with open(UPDATE_CSV, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "date", "content", "url"])
        writer.writeheader()
        writer.writerows(notices)
    print(f"✅ {len(notices)}건 저장 완료: {UPDATE_CSV}")

if __name__ == "__main__":
    existing_ids = load_existing_ids()
    new_data = crawl_new_cs_notices(existing_ids, max_page=3)
    save_new_notices(new_data)
