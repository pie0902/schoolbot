from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# 정적 파일 경로 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 루트에 index.html 직접 반환
@app.get("/")
def read_index():
    return FileResponse("static/index.html")
