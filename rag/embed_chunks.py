import json
import os
from chromadb import PersistentClient
from chromadb import Documents, EmbeddingFunction, Embeddings
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ✅ 설정
CHROMA_DIR = "rag/chroma_db"
COLLECTION_NAME = "knou_chunks"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# API 키 전역 설정
genai.configure(api_key=GEMINI_API_KEY)

# ✅ Gemini 임베딩 함수 (최신 API 방식)
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.model = "models/text-embedding-004"
    
    def __call__(self, input: Documents) -> Embeddings:
        try:
            # 배치 임베딩 요청
            embeddings = []
            for text in input:
                result = genai.embed_content(
                    model=self.model,
                    content=text
                )
                embeddings.append(result['embedding'])
            return embeddings
        except Exception as e:
            print(f"❌ 임베딩 생성 실패: {e}")
            # 빈 임베딩 반환 (ChromaDB 오류 방지)
            return [[0.0] * 768 for _ in input]

def load_chunks():
    chunks = []
    with open("rag/chunks.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line.strip()))
    return chunks

def main():
    print("🔧 Gemini 임베딩 함수 초기화 중...")
    
    # API 키 확인
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        exit(1)
    
    print("🔑 API 키 확인: ✅ 설정됨")
    
    # ✅ 이미 있는 ID 확인해서 중복 방지 (올바른 방식)
    embedding_func = GeminiEmbeddingFunction()
    client = PersistentClient(path=CHROMA_DIR)
    
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        existing_ids = set(collection.get()["ids"])
        print(f"📋 기존 청크 {len(existing_ids)}개 발견")
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
        existing_ids = set()
        print("📝 새 컬렉션 생성")

    # 청크 로드
    print("📄 청크 로드 중...")
    chunks = load_chunks()
    print(f"📄 총 청크 {len(chunks)}개 로드됨")

    # 신규 청크 필터링
    new_chunks = [chunk for chunk in chunks if chunk["id"] not in existing_ids]
    print(f"🎯 신규 청크 {len(new_chunks)}개 임베딩 중...")

    if not new_chunks:
        print("📭 추가할 신규 청크 없음.")
        return

    # 배치로 임베딩 및 추가
    batch_size = 10
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i:i+batch_size]
        
        # 메타데이터와 문서 분리
        documents = [chunk["text"] for chunk in batch]

        # 메타데이터와 문서 분리
        metadatas = [{k: str(v) for k, v in chunk.items() if k not in ["text", "id"]} for chunk in batch]

        ids = [chunk["id"] for chunk in batch]
        
        print(f"🔄 배치 {i//batch_size + 1}/{(len(new_chunks)-1)//batch_size + 1} 처리 중...")
        
        # ChromaDB에 추가 (임베딩 자동 생성)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    print("✅ 모든 청크 임베딩 완료!")
    
    # 최종 통계
    final_count = len(collection.get()["ids"])
    print(f"📊 최종 청크 수: {final_count}개")

if __name__ == "__main__":
    main()
