import os
import csv
import json
import uuid
from datetime import datetime

CHUNK_SIZE = 1000
OVERLAP = 200

INPUT_FILES = [
    {"path": "data/notices_2025.csv", "type": "notice"},
    {"path": "data/cs_notices_2025.csv", "type": "cs_notice"},
    {"path": "data/common_schedule.csv", "type": "schedule"},
]

OUTPUT_FILE = "rag/chunks.jsonl"


def split_text(text, max_length=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunks.append(text[start:end])
        start += max_length - overlap
    return chunks

def generate_unique_id(file_type, row_data, chunk_text, chunk_index):
    """UUID 기반 고유 ID 생성 - 모든 청크가 고유한 ID를 가짐"""
    return f"{file_type}_{uuid.uuid4().hex[:12]}_{chunk_index}"

def process_row(row, file_type):
    if file_type in ["notice", "cs_notice"]:
        title = row["title"]
        date = row["date"]
        content = row["content"]
        source = row["url"]
        full_text = f"[{title}]\n{date}\n{content}"
        
        # 메타데이터 구성
        metadata = {
            "date": date,
            "title": title,
            "type": file_type,
            "source": source
        }
    elif file_type == "schedule":
        date = row["date"]
        content = row["content"]
        title = row.get("title", "일정")
        source = None
        full_text = f"[{title}]\n{date}\n{content}"
        
        # 메타데이터 구성
        metadata = {
            "date": date,
            "title": title,
            "type": file_type,
            "source": source or file_type
        }
    else:
        return []

    chunks = split_text(full_text)
    return [
        {
            "id": generate_unique_id(file_type, row, chunk, i),
            "text": chunk,
            "date": metadata["date"],
            "title": metadata["title"], 
            "type": metadata["type"],
            "source": metadata["source"]
        }
        for i, chunk in enumerate(chunks)
    ]

def prepare_chunks():
    all_chunks = []

    for file_info in INPUT_FILES:
        path = file_info["path"]
        file_type = file_info["type"]

        print(f"📂 처리 중: {path}")
        
        if not os.path.exists(path):
            print(f"⚠️ 파일이 존재하지 않습니다: {path}")
            continue
            
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                chunks = process_row(row, file_type)
                all_chunks.extend(chunks)

    print(f"📊 처리 결과:")
    print(f"   - 총 청크: {len(all_chunks)}개 (UUID 사용으로 모든 청크 고유)")

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # JSONL 파일로 저장
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for chunk in all_chunks:
            out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"✅ {len(all_chunks)}개 청크 저장 완료 → {OUTPUT_FILE}")


if __name__ == "__main__":
    prepare_chunks()
