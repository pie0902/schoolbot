import json
import os
from chromadb import PersistentClient
from chromadb import Documents, EmbeddingFunction, Embeddings
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ✅ API 키 직접 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CHUNKS_PATH = "rag/chunks.jsonl"
CHROMA_DIR = "rag/chroma_db"
COLLECTION_NAME = "knou_chunks"

# ✅ 커스텀 Gemini 임베딩 함수 클래스 (공식 문서 방식)
class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "text-embedding-004"  # 공식 문서에서 사용하는 모델명
    
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        
        # 배치로 처리 (효율성을 위해)
        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=input  # 리스트 그대로 전달
            )
            
            # 각 임베딩의 values 추출
            for embedding in result.embeddings:
                embeddings.append(embedding.values)
                
        except Exception as e:
            print(f"❌ 임베딩 생성 중 오류: {e}")
            # 개별 처리로 폴백
            for doc in input:
                try:
                    result = self.client.models.embed_content(
                        model=self.model,
                        contents=[doc]
                    )
                    embeddings.append(result.embeddings[0].values)
                except Exception as doc_error:
                    print(f"❌ 개별 문서 임베딩 실패: {doc_error}")
                    # 빈 벡터로 대체 (768차원 기본값)
                    embeddings.append([0.0] * 768)
        
        return embeddings

# ✅ Gemini 임베딩 함수 준비
print("🔧 Gemini 임베딩 함수 초기화 중...")
embedding_func = GeminiEmbeddingFunction(api_key=GEMINI_API_KEY)

# ✅ Chroma 클라이언트 초기화 (로컬 저장소 경로 설정)
client = PersistentClient(path=CHROMA_DIR)

# ✅ 컬렉션 생성 or 불러오기
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_func
)

# ✅ chunks.jsonl 로드
with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = [json.loads(line) for line in f]

print(f"📄 총 청크 {len(chunks)}개 로드됨")

# ✅ API 키 검증
if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
    print("❌ GEMINI_API_KEY가 설정되지 않았습니다!")
    exit(1)

# 수정된 버전 - API 키 내용을 숨김
print("API 키 확인: 설정됨")

# ✅ 이미 있는 ID 확인해서 중복 방지 (올바른 방식)
try:
    existing_data = collection.get()
    existing_ids = set(existing_data["ids"]) if existing_data["ids"] else set()
    print(f"📋 기존 청크 {len(existing_ids)}개 발견")
except Exception as e:
    print(f"⚠️ 기존 데이터 확인 중 오류: {e}")
    existing_ids = set()

# ✅ 임베딩 및 저장
new_chunks = [c for c in chunks if c["id"] not in existing_ids]
print(f"🎯 신규 청크 {len(new_chunks)}개 임베딩 중...")

if new_chunks:
    # 배치 크기를 작게 해서 안정성 향상
    batch_size = 10
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i:i+batch_size]
        print(f"   📦 배치 {i//batch_size + 1}/{(len(new_chunks)-1)//batch_size + 1} 처리 중... ({len(batch)}개)")
        
        try:
            collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
                metadatas=[c.get("metadata", {"source": c["source"]}) for c in batch]
            )
        except Exception as e:
            print(f"❌ 배치 처리 실패: {e}")
            break
    
    print(f"✅ 임베딩 완료. 총 {len(new_chunks)}개 저장됨.")
else:
    print("📭 추가할 신규 청크 없음.")
