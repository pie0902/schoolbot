#!/usr/bin/env python3
"""
KNOU 챗봇 자동 업데이트 시스템
매일 아침 10시에 실행하여 데이터를 업데이트합니다.
"""
import os
import sys
import subprocess
import logging
from datetime import datetime

# 로그 디렉토리 먼저 생성
os.makedirs("logs", exist_ok=True)

# 현재 사용 중인 파이썬 경로 가져오기
PYTHON_PATH = sys.executable

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_update.log'),
        logging.StreamHandler()
    ]
)

def run_command(command, description):
    """명령어 실행 및 로깅"""
    logging.info(f"🔄 {description} 시작...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode == 0:
            logging.info(f"✅ {description} 완료")
            return True
        else:
            logging.error(f"❌ {description} 실패: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"❌ {description} 오류: {e}")
        return False

def main():
    """자동 업데이트 메인 프로세스"""
    start_time = datetime.now()
    logging.info(f"🚀 KNOU 챗봇 자동 업데이트 시작: {start_time}")
    logging.info(f"🐍 파이썬 경로: {PYTHON_PATH}")
    
    # 1. 크롤링 실행
    logging.info("📡 데이터 크롤링 중...")
    crawl_commands = [
        (f"{PYTHON_PATH} crawl/update_notices.py", "일반 공지사항 업데이트"),
        (f"{PYTHON_PATH} crawl/fetch_cs_update.py", "컴공과 공지사항 업데이트"),
        (f"{PYTHON_PATH} crawl/fetch_common.py", "공통 일정 업데이트")
    ]
    
    crawl_success = True
    for cmd, desc in crawl_commands:
        if not run_command(cmd, desc):
            crawl_success = False
    
    if not crawl_success:
        logging.error("❌ 크롤링 실패로 업데이트 중단")
        return False
    
    # 2. 청크 생성
    if not run_command(f"{PYTHON_PATH} rag/prepare_chunks.py", "청크 파일 생성"):
        return False
    
    # 3. 임베딩 생성
    if not run_command(f"{PYTHON_PATH} rag/embed_chunks.py", "임베딩 생성 및 DB 업데이트"):
        return False
    
    # 4. 업데이트 완료 로그
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"🎉 자동 업데이트 완료! 소요 시간: {duration}")
    logging.info("📊 챗봇이 최신 데이터로 업데이트되었습니다.")
    
    return True

if __name__ == "__main__":    
    # 업데이트 실행
    success = main()
    sys.exit(0 if success else 1) 