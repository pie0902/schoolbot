# Campus Assistant Chatbot

> 소프트웨어 경진대회 출품작  
> 학생 생활을 도와주는 AI 챗봇

---

## 📌 소개 (About)

이 프로젝트는 대학생들의 학사, 수강신청, 졸업 요건 등  
학사 관련 질문에 실시간으로 응답하는 AI 챗봇입니다.  
RAG 구조와 대규모 언어 모델(LLM)을 활용하여 정밀하고 정확한 정보를 제공합니다.

---

## 🧠 주요 기능 (Features)

- 자연어 기반 질의응답 시스템
- 주요 학사 정보 검색 및 요약 응답
- FastAPI 백엔드
- RAG (Retrieval-Augmented Generation) 구조 적용
- 터널링 및 무료 도메인 설정으로 외부 접속 지원

---

## 🛠️ 기술 스택 (Tech Stack)

- Python 3.x
- FastAPI
- ChromaDB (벡터DB)
- Playwright / Selenium (웹 크롤링)
- Gemini API (LLM)
- Docker
- Cloudflared + DuckDNS

---

## 🚀 실행 방법 (How to Run)

```bash
git clone https://github.com/yourname/campus-assistant-bot.git
cd campus-assistant-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 환경 설정
cp .env.example .env
# .env 파일 내용을 채워주세요

# 실행
python main.py
```
