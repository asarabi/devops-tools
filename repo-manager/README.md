# Repo Manager

레포지토리 및 브랜치 마이그레이션/동기화(Branch Migration & Sync) 파이프라인 웹 대시보드입니다.  
`from-repo from-branch to-repo to-branch` 형태의 대량 작업 목록을 입력받아, **사전 존재 여부 검증(Dry-Run)** 후 **Jenkins를 통해 실제 작업을 수행하고 이력을 관리**합니다.

## 주요 기능

- **배치 입력 지원**: `from-repo from-branch to-repo to-branch` 형식 다중 라인 입력 및 파일(.txt, .csv, .tsv) 드래그 앤 드롭
- **실시간 Dry-Run 사전 검증**:
  - 소스 레포 및 브랜치 존재 여부 확인
  - 타겟 브랜치 충돌/덮어쓰기 감지 (Ready / Warning / Error 상태 구분)
  - `repo-scope` 백엔드 연동 및 개발용 시뮬레이터(Mock) 내장
- **Jenkins 작업 실행 연동**:
  - 검증 완료된 대상을 Jenkins 파이프라인으로 전송 (`buildWithParameters`)
  - 오류 항목 자동 제외 및 덮어쓰기 허용 옵션
  - Jenkins 콘솔 로그 바로가기 연동
- **영구 실행 이력(Execution History) 및 재수행(Rerun)**:
  - 매 실행 시 `data/history/exec-{timestamp}.json` 파일로 영구 보관 (원본 입력 텍스트 포함)
  - 실행 이력 모달에서 과거 내역 조회 및 **[재수행]** 버튼으로 에디터에 입력 데이터 즉시 복원
  - 개별 이력 삭제 지원
- **현대적인 SaaS 스타일 UI**: 사이드바 내비게이션, 3단계 Stepper 워크플로우, 상태 배지, 실시간 필터링 및 검색

## 빠른 시작 (Python 직접 실행)

Docker 없이 파이썬만으로 즉시 실행할 수 있습니다:

```bash
cd repo-manager

# 의존성 설치
pip install -r requirements.txt

# 실행 (기본 포트: 8081, 핫 리로드 지원)
python3 run.py
# 또는
./run.sh
```

- 웹 대시보드: **http://localhost:8081**

---

## Docker 실행 (선택 사항)

```bash
cd repo-manager
docker compose up -d
```

## 설정 (config.yaml 및 환경 변수)

Jenkins 및 repo-scope 백엔드 연동 설정:

```yaml
# config.yaml (선택 사항, 없으면 환경변수 및 기본값 사용)
jenkins:
  url: "http://localhost:9090"
  job_name: "repo-sync-pipeline"
  username: "admin"
  api_token: "your-api-token"

repo_scope:
  url: "http://localhost:8000"  # repo-scope 검증 BE (미설정 시 내장 시뮬레이터 동작)
```

환경 변수로도 동일하게 오버라이드할 수 있습니다:
- `JENKINS_URL`, `JENKINS_JOB`, `JENKINS_USER`, `JENKINS_TOKEN`
- `REPO_SCOPE_URL`

## API 엔드포인트

### Branch Migration & Sync API
| Method | Path | 설명 |
|---|---|---|
| POST | `/api/dry-run` | 배치 목록 사전 검증 (Ready / Warning / Error 판별) |
| POST | `/api/execute` | Jenkins 파이프라인 실행 트리거 및 이력 JSON 파일 저장 |
| GET | `/api/history` | 최근 실행 이력 목록 조회 |
| GET | `/api/history/{id}` | 개별 실행 이력 상세 조회 및 원본 입력 데이터 로드 (재수행용) |
| DELETE | `/api/history/{id}` | 실행 이력 파일 삭제 |
| GET | `/api/jenkins/config` | Jenkins 및 repo-scope 연동 설정/상태 확인 |

### 레포지토리 관리 API (기존)
| Method | Path | 설명 |
|---|---|---|
| GET | `/api/stats` | 전체 통계 |
| GET | `/api/sources` | 등록된 소스 목록 |
| GET | `/api/repositories` | 레포 목록 (필터: source_id, search, state) |
| GET | `/api/repositories/{id}` | 레포 상세 (브랜치, 권한 포함) |
| GET | `/api/inheritance` | Gerrit 권한 상속 트리 |
| POST | `/api/sync` | 수동 Sync 트리거 |

## 개발 모드

코드 수정 시 Docker rebuild 없이 자동 반영됩니다.

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

운영 모드와의 차이:
- `./app:/app/app` — 로컬 소스 코드를 컨테이너에 직접 마운트
- `--reload` — 파일 변경 감지 시 uvicorn 자동 재시작

`.py`, `.html` 파일 수정 후 브라우저 새로고침만 하면 됩니다.
`requirements.txt`를 변경한 경우에만 `--build`로 다시 빌드가 필요합니다.

## 운영 명령어

```bash
# 로그 확인
docker compose logs -f

# DB 초기화 (데이터 삭제 후 재시작)
docker compose down -v
docker compose up -d
```

