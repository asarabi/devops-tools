import os
import sys
import pwd

# If running under sudo, automatically inherit the original user's site-packages (e.g. fastapi, uvicorn)
sudo_user = os.environ.get("SUDO_USER")
candidate_users = [sudo_user] if sudo_user else ["ck21im"]

for u in candidate_users:
    try:
        u_home = pwd.getpwnam(u).pw_dir
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        user_site = os.path.join(u_home, ".local", "lib", py_ver, "site-packages")
        if os.path.exists(user_site):
            if user_site not in sys.path:
                sys.path.insert(0, user_site)
            # Propagate to uvicorn reloader subprocesses
            cur_pypath = os.environ.get("PYTHONPATH", "")
            if user_site not in cur_pypath:
                os.environ["PYTHONPATH"] = f"{user_site}:{cur_pypath}" if cur_pypath else user_site
    except Exception:
        pass

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
