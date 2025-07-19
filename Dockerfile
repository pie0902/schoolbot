FROM python:3.9-slim

WORKDIR /app

# 시스템 패키지 설치 (Linux 환경에 최적화)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 필요한 Python 패키지 먼저 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright 브라우저 설치 (requirements.txt 설치 후)
RUN playwright install chromium
RUN playwright install-deps chromium

# 앱 코드 복사
COPY . .

# 로그 및 데이터 디렉토리 생성
RUN mkdir -p logs data rag/chroma_db

# 환경변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# cron 작업 설정 (Linux 환경용)
RUN echo "0 10 * * * cd /app && python auto_update.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/auto-update
RUN chmod 0644 /etc/cron.d/auto-update
RUN crontab /etc/cron.d/auto-update

# supervisor 설정 (FastAPI + cron 동시 실행)
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 벡터 DB와 데이터 디렉토리를 볼륨으로 설정
VOLUME ["/app/rag/chroma_db", "/app/data", "/app/logs"]

# 8001번 포트 사용
EXPOSE 8001

# supervisor로 여러 프로세스 관리
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
