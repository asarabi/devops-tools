# Gerrit Manager

다중 Gerrit 인스턴스 및 GitHub 레포지토리를 통합 관리하는 웹 대시보드입니다.

## 기능

- 다중 Gerrit/GitHub 인스턴스 지원
- 전체 레포지토리 목록 및 상태 조회
- 브랜치 정보 조회
- Gerrit 권한 상속 트리 시각화
- 검색 및 필터링 (Source, State)
- DB 기반 캐싱 (주기적 Sync)
- 수동 Sync 트리거

## 빠른 시작

### 설정

```bash
cd gerrit-manager
cp config.yaml.example config.yaml
# config.yaml 편집: Gerrit/GitHub 접속 정보 입력
```

### 빌드

```bash
docker compose build
```

### 시작

```bash
docker compose up -d
```

- 대시보드: http://localhost:8081

### 중단

```bash
docker compose down
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

## 운영 명령어

```bash
# 로그 확인
docker compose logs -f

# DB 초기화 (데이터 삭제 후 재시작)
docker compose down -v
docker compose up -d
```
