# DevOps Tools

DevOps 자동화 및 형상 관리 운영을 위한 통합 도구 모음입니다.

---

## 구성 요소 (Components)

| 컴포넌트 | 설명 | 기술 스택 | 링크 |
|---|---|---|---|
| **[repo-manager](./repo-manager)** | 레포지토리 및 브랜치 마이그레이션/동기화(Branch Sync) 웹 대시보드 | Python (FastAPI), HTML/CSS/JS, SQLite | [상세 가이드](./repo-manager/README.md) |
| **[service-viewer](./service-viewer)** | 내가 등록한 systemd 커스텀 서비스 전용 경량 관리 대시보드 | Python (FastAPI), HTML/CSS/JS, systemd | [상세 가이드](./service-viewer/README.md) |
| **[jenkins](./jenkins)** | 버전 고정 및 보안 검증 플러그인 기반 재현 가능한 Jenkins CI/CD 환경 | Docker, Jenkins LTS, Docker Compose | [상세 가이드](./jenkins/README.md) |

---

## 1. Repo Manager (Branch Migration & Sync Pipeline)

대량의 `from-repo from-branch to-repo to-branch` 마이그레이션 대상 목록을 입력받아, 사전 검증(Dry-Run) 후 Jenkins 작업을 실행하고 파일 기반 영구 실행 이력을 관리합니다.

- **실행 방법**:
  ```bash
  cd repo-manager
  pip install -r requirements.txt
  python3 run.py
  ```
  - 대시보드: `http://localhost:8081`
- **주요 기능**:
  - 배치 다중 라인 입력 및 파일(.txt, .csv, .tsv) 드래그 앤 드롭
  - 실시간 Dry-Run 사전 검증 (충돌/덮어쓰기 감지)
  - Jenkins 파이프라인 연동 (`buildWithParameters`)
  - `data/history/exec-{timestamp}.json` 파일 기반 영구 실행 이력 및 **원클릭 재수행(Rerun)** 지원
  - SaaS 스타일 모던 대시보드 UI

---

## 2. Service Viewer (systemd Custom Services Dashboard)

Cockpit의 복잡한 400여 개 OS 기본 서비스를 배제하고, **오직 내가 등록한 커스텀 systemd 서비스만** 깔끔한 카드 UI로 모니터링 및 제어(추가/수정/삭제/재시작/로그)합니다.

- **실행 방법**:
  ```bash
  cd service-viewer
  pip install -r requirements.txt
  python3 run.py         # 일반 유저 (조회/로그)
  sudo python3 run.py    # 관리자 (원클릭 생성/수정/재시작)
  ```
  - 대시보드: `http://localhost:8082`
- **주요 기능**:
  - 사용자 등록 서비스 및 커스텀 `.service` 파일 자동 감지
  - 실시간 상태 배지 (Running, Stopped, Failed, Enabled), PID, 메모리 점유율 표시
  - 원클릭 시작 / 중지 / 재시작 및 부팅 시 자동실행 토글
  - 신규 서비스 등록 마법사 (템플릿 실시간 미리보기)
  - Unit 파일 웹 직접 편집기 (`daemon-reload` 자동 반영)
  - `journalctl` 실시간 로그 뷰어

---

## 3. Jenkins (Docker Setup)

LTS 버전 및 의존성이 해결된 플러그인 버전을 고정하여 안전하고 재현 가능한 Jenkins 환경을 제공합니다.

- **실행 방법**:
  ```bash
  cd jenkins
  docker compose up -d
  ```
  - Jenkins 웹 UI: `http://localhost:9090`
- **주요 특징**:
  - 보안 취약 플러그인(`ssh`, `ghprb`, `extended-choice-parameter` 등)을 안전한 최신 대안(`ssh-steps`, `github-branch-source`, `uno-choice`)으로 교체
  - 데이터 영구 보존 (`~/jenkins_backup`)

---

## 커밋 컨벤션 (Commit Convention)

본 저장소는 Conventional Commits 규칙을 준수합니다:
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 변경 (README 등)
- `refactor`: 코드 구조 개선
- `chore`: 빌드, 의존성 및 설정 파일 관리

상세 규칙은 [CLAUDE.md](./CLAUDE.md)를 참고하세요.
