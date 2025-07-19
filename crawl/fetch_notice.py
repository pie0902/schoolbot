from playwright.sync_api import sync_playwright
import csv
import time
import os

BASE_URL = "https://www.knou.ac.kr"
PAGE_URL_TEMPLATE = "https://www.knou.ac.kr/bbs/knou/51/artclList.do?page={}"

def crawl_notices(start_page=1, end_page=22):
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
                title_elem = row.locator("td.td-subject a")
                title = title_elem.inner_text().strip()
                link = title_elem.get_attribute("href")
                full_url = BASE_URL + link
                date = row.locator("td.td-date").inner_text().strip()
                article_id = link.split("/")[4] if link else "unknown"

                # 상세 페이지 진입
                page.goto(full_url)
                content_elem = page.locator("div.view-con").first  # <= 핵심 수정!
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

                # 과부하 방지
                time.sleep(0.5)

        browser.close()
        return notices

# CSV 저장
if __name__ == "__main__":
    data = crawl_notices()
       # ✅ 저장 경로를 data 디렉토리로 지정
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", "notices_2025.csv")

    with open("notices_2025.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "date", "content", "url"])
        writer.writeheader()
        writer.writerows(data)
    print("✅ 크롤링 완료: notices_2025.csv 저장됨")
