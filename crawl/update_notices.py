import os
import csv
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.knou.ac.kr"
PAGE_URL_TEMPLATE = "https://www.knou.ac.kr/bbs/knou/51/artclList.do?page={}"
CSV_PATH = os.path.join("data", "notices_2025.csv")

def load_existing_ids():
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        return {row['id'] for row in csv.DictReader(f)}

def crawl_new_notices(existing_ids, max_page=3):
    new_notices = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, max_page + 1):
            print(f"🔍 갱신 확인 중... 페이지 {page_num}")
            page.goto(PAGE_URL_TEMPLATE.format(page_num))
            rows = page.locator("table.board-table tbody tr")

            for i in range(rows.count()):
                row = rows.nth(i)
                title_elem = row.locator("td.td-subject a")
                title = title_elem.inner_text().strip()
                link = title_elem.get_attribute("href")
                full_url = BASE_URL + link
                date = row.locator("td.td-date").inner_text().strip()
                article_id = link.split("/")[4] if link else "unknown"

                if article_id in existing_ids:
                    continue  # 이미 존재하면 스킵

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

        browser.close()
    return new_notices

def append_new_notices(new_data):
    os.makedirs("data", exist_ok=True)
    with open(CSV_PATH, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "date", "content", "url"])
        if f.tell() == 0:
            writer.writeheader()
        writer.writerows(new_data)

if __name__ == "__main__":
    existing_ids = load_existing_ids()
    new_data = crawl_new_notices(existing_ids, max_page=3)
    if new_data:
        append_new_notices(new_data)
        print(f"✅ {len(new_data)}건 신규 공지사항 저장 완료")
    else:
        print("📭 새로운 공지 없음")
