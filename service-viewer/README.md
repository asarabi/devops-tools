# Service Viewer

내가 등록한 systemd 커스텀 서비스 전용 **경량 웹 관리 대시보드**입니다.  
Cockpit의 복잡한 400여 개 OS 시스템 서비스 대신, **오직 내가 등록한 서비스들만 직관적인 카드 뷰로 모니터링하고 추가 / 편집 / 삭제 / 재시작 / 실시간 로그를 관리**할 수 있습니다.

---

## 주요 기능

- **내 등록 서비스 목록**:
  - 사용자 등록 서비스 및 `/etc/systemd/system/`의 커스텀 단위 파일만 자동 감지하여 표시
  - 실시간 상태 배지 (Running 🟢, Stopped ⚪, Failed 🔴, Enabled ⚡)
  - PID, 메모리 점유율, 시작 시각 표시
- **원클릭 제어**:
  - 시작(Start), 중지(Stop), 재시작(Restart)
  - 부팅 시 자동실행 토글 (Enable / Disable)
- **신규 서비스 등록 마법사**:
  - 복잡한 `.service` 문법 없이 폼(이름, 설명, ExecStart, WorkingDirectory, User, Restart 등) 입력으로 자동 생성
  - 실시간 Unit 파일 미리보기 및 즉시 활성화(`enable --now`)
- **Unit 파일 직접 편집기**:
  - 기존 서비스의 `.service` 파일을 웹 에디터로 조회 및 수정
  - 저장 시 `systemctl daemon-reload` 및 자동 서비스 재시작 지원
- **실시간 로그 뷰어**:
  - `journalctl -u <service> -n 100` 스트리밍 및 3초 간격 자동 새로고침 모니터링
  - 클립보드 원클릭 복사

---

## 빠른 시작

### 1. 일반 사용자 모드 실행 (상태 및 실시간 로그 조회)

```bash
cd service-viewer

# 의존성 설치
pip install -r requirements.txt

# 실행 (기본 포트: 8082)
python3 run.py
```

- 웹 대시보드: **http://localhost:8082**

### 2. 관리자(ROOT) 모드 직접 실행

```bash
cd service-viewer
./run.sh
# 또는
sudo python3 run.py
```

### 3. systemd 영구 데몬으로 등록 (권장 🌟)

서버 부팅 시 자동으로 백그라운드에서 상시 실행되도록 systemd 서비스로 등록합니다:

```bash
cd service-viewer
./install-service.sh
```

- **서비스 관리 명령어**:
  ```bash
  sudo systemctl status service-viewer    # 상태 확인
  sudo systemctl restart service-viewer   # 재시작
  sudo systemctl stop service-viewer      # 중지
  journalctl -u service-viewer -f         # 실시간 로그 확인
  ```

---

## API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/services` | 등록된 커스텀 서비스 목록 및 실시간 상태/통계 조회 |
| POST | `/api/services/preview` | 폼 입력 기반 systemd unit 템플릿 실시간 미리보기 |
| POST | `/api/services` | 신규 systemd 서비스 생성 및 데몬 리로드 |
| GET | `/api/services/{name}` | 특정 서비스 상세 및 Unit 파일 내용 조회 |
| PUT | `/api/services/{name}` | Unit 파일 수정 및 반영 (daemon-reload) |
| DELETE | `/api/services/{name}` | 서비스 중지, disable 및 Unit 파일 삭제 |
| POST | `/api/services/{name}/{action}` | 서비스 제어 (`start`, `stop`, `restart`, `enable`, `disable`) |
| GET | `/api/services/{name}/logs` | 실시간 `journalctl` 로그 조회 |
