# fetch_cs_notice.py

from playwright.sync_api import sync_playwright
import csv
import os
import time
from datetime import datetime


BASE_URL = "https://cs.knou.ac.kr"
PAGE_URL_TEMPLATE = "https://cs.knou.ac.kr/cs1/4812/subview.do?page={}&enc=Zm5jdDF8QEB8JTJGYmJzJTJGY3MxJTJGMjExOSUyRmFydGNsTGlzdC5kbyUzRg%3D%3D"

def crawl_cs_notices(start_page=1, end_page=5):  # 페이지 수는 필요시 조절
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        notices = []

        for page_num in range(start_page, end_page + 1):
            print(f"📄 크롤링 중... 페이지 {page_num}")
            page.goto(PAGE_URL_TEMPLATE.format(page_num))
            rows = page.locator("table.board-table tbody tr")

            for i in range(rows.count()):
                row = rows.nth(i)
                dept = row.locator("td.td-write").inner_text().strip()
                if dept != "컴퓨터과학과":
                    continue  # 다른 학과는 무시

                title_elem = row.locator("td.td-subject a")
                title = title_elem.inner_text().strip()
                link = title_elem.get_attribute("href")
                full_url = BASE_URL + link
                date = row.locator("td.td-date").inner_text().strip()
                article_id = link.split("/")[-2] if link else "unknown"

                # 상세 페이지 진입
                page.goto(full_url)
                content_elem = page.locator("div.view-con").first
                content = content_elem.inner_text().strip() if content_elem.count() > 0 else "본문 없음"
                notices.append({
                    "id": article_id,
                    "title": title,
                    "date": date,
                    "content": content,
                    "url": full_url
                })

                # 다시 목록으로 복귀
                page.goto(PAGE_URL_TEMPLATE.format(page_num))
                time.sleep(0.5)

        browser.close()
        return notices

# CSV 저장
if __name__ == "__main__":
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    data = crawl_cs_notices()
    data.sort(key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d"), reverse=True)  # ✅ 여기 추가

    output_file = os.path.join(data_dir, "cs_notices_2025.csv")
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "date", "content", "url"])
        writer.writeheader()
        writer.writerows(data)

    print(f"✅ 크롤링 완료: {output_file} 저장됨")
