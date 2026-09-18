import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n🚀 Repo Manager 웹 서버 시작: http://localhost:{port}")
    print(f"👉 브라우저에서 위 주소로 접속하세요.\n")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
