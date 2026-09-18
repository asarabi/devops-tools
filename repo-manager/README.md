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
  - Jenkins 콘솔 로그 바로가기 및 실행 이력 대시보드 제공
- **현대적인 다크 테마 UI**: 반응형 레이아웃, 직관적인 상태 필터링 및 검색

## 빠른 시작 (Python 직접 실행)

Docker 없이 파이썬만으로 즉시 실행할 수 있습니다:

```bash
cd repo-manager

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

## 설정 파일 (config.yaml)

```yaml
sync_interval_minutes: 30    # 자동 Sync 주기

gerrit_instances:
  - name: gerrit-main        # 표시 이름
    url: https://gerrit.example.com
    auth_type: http           # http 또는 ssh
    username: admin
    password: secret

github_instances:
  - name: github-main
    url: https://api.github.com
    token: ghp_xxxxxxxxxxxx
    orgs:
      - my-org
```

### Gerrit 인증 방식

**HTTP (REST API)**
- `auth_type: http`
- `username` + `password` (Gerrit HTTP Password)
- 레포, 브랜치, 권한 정보 모두 조회 가능

**SSH**
- `auth_type: ssh`
- `username` + `ssh_key` + `ssh_port`
- 레포, 브랜치 조회 가능 (권한 정보는 제한적)

## API 엔드포인트

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
