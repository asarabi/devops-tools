# DevOps Tools

DevOps 자동화 및 형상 관리 운영을 위한 통합 도구 모음입니다.

---

## 구성 요소 (Components)

| 컴포넌트 | 설명 | 기술 스택 | 링크 |
|---|---|---|---|
| **[repo-manager](./repo-manager)** | 레포지토리 및 브랜치 마이그레이션/동기화(Branch Sync) 웹 대시보드 | Python (FastAPI), HTML/CSS/JS, SQLite | [상세 가이드](./repo-manager/README.md) |
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

## 2. Jenkins (Docker Setup)

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
