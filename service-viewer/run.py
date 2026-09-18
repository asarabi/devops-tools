import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8082))
    host = os.environ.get("HOST", "0.0.0.0")
    is_root = os.geteuid() == 0

    print(f"\n==================================================")
    print(f"🚀 Service Viewer 시작: http://localhost:{port}")
    if is_root:
        print(f"🔒 실행 권한: ROOT (모든 systemd 생성/제어/재시작 가능)")
    else:
        print(f"👤 실행 권한: USER (ck21im) - 상태/로그 조회 가능")
        print(f"   (서비스 시작/중지/생성 시 sudo 권한 또는 sudoers 설정이 필요할 수 있습니다)")
    print(f"==================================================\n")

    uvicorn.run("app.main:app", host=host, port=port, reload=True)
