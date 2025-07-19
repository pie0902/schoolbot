from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import sys
import os
import asyncio

# RAG 시스템 경로 추가
from rag.query_chat import KNOUChatbot

# FastAPI 앱 생성
app = FastAPI(title="KNOU AI Chatbot", description="한국방송통신대학교 AI 챗봇")

# 정적 파일 서빙 (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 챗봇 인스턴스 생성 (서버 시작 시 한 번만)
print("🤖 KNOU 챗봇 서버 초기화 중...")
chatbot = KNOUChatbot()
print("✅ 챗봇 서버 준비 완료!")

# 요청 모델 정의
class ChatRequest(BaseModel):
    query: str

# 루트 경로 - HTML 파일 서빙
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

# 스트리밍 챗봇 API 엔드포인트
@app.post("/api/chat-stream")
async def chat_stream_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")
    
    print(f"💬 사용자 질문 (스트리밍): {request.query}")

    async def stream_generator():
        try:
            # 챗봇의 스트리밍 답변을 비동기적으로 생성
            answer_stream = chatbot.chat(request.query)
            for chunk in answer_stream:
                yield chunk
                await asyncio.sleep(0.01) # 클라이언트 렌더링을 위한 약간의 딜레이
        except Exception as e:
            print(f"❌ 스트리밍 중 오류: {e}")
            yield "죄송합니다, 답변 생성 중 오류가 발생했습니다."

    return StreamingResponse(stream_generator(), media_type="text/plain")


# 헬스 체크 엔드포인트
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "KNOU 챗봇 서버가 정상 작동 중입니다."}

if __name__ == "__main__":
    import uvicorn
    print("🚀 KNOU 챗봇 서버 시작...")
    print("📱 브라우저에서 http://localhost:8001 접속하세요!")
    uvicorn.run(app, host="0.0.0.0", port=8001) 