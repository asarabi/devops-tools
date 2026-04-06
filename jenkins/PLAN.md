# Jenkins Docker Setup - Plan

## 목적

Jenkins를 Docker 기반으로 구성하여 재현 가능한 CI/CD 환경을 제공한다.
플러그인 및 베이스 이미지 버전을 고정하여 언제 빌드해도 동일한 결과를 보장한다.

## 현재 상태

- [x] Jenkins LTS 버전 고정 (2.541.3-lts)
- [x] 플러그인 108개 버전 고정 (의존성 포함)
- [x] 보안 취약 플러그인 3개 대안 교체
- [x] Docker Compose 구성 (포트 9090, ~/jenkins_backup 마운트)
- [x] 볼륨 권한 문제 해결 (entrypoint chown)
- [x] README 작성

## 아키텍처

```
Host (Ubuntu 20.04/22.04)
├── ~/jenkins_backup/          # Jenkins 데이터 (영구 저장)
└── docker
    └── jenkins (9090:8080)    # Jenkins LTS 컨테이너
        ├── 50000              # Agent 연결 포트
        └── plugins (108개)    # 버전 고정된 플러그인
```

## 향후 계획

### 단기

- [ ] Jenkins Configuration as Code (JCasC) 도입
  - 시스템 설정, 사용자, 크레덴셜을 YAML로 관리
  - `jenkins.yaml` 파일로 초기 설정 자동화
- [ ] Seed Job 구성
  - Job DSL 플러그인으로 Job 정의를 코드화
  - Git 레포에서 Job 정의를 불러오는 구조

### 중기

- [ ] Agent 구성
  - Docker 기반 빌드 Agent 추가
  - Agent Dockerfile 및 docker-compose 확장
- [ ] Backup/Restore 스크립트 작성
  - ~/jenkins_backup 디렉토리의 주기적 백업
  - 복원 절차 문서화
- [ ] HTTPS 적용
  - Nginx 리버스 프록시 또는 Traefik 연동

### 장기

- [ ] Jenkins 업그레이드 자동화
  - 새 LTS 버전 감지 → 플러그인 호환성 테스트 → 버전 고정 자동화
- [ ] 모니터링 연동
  - Prometheus 메트릭 플러그인 + Grafana 대시보드

## 의사결정 기록

| 날짜 | 결정 | 사유 |
|---|---|---|
| 2026-04-06 | Jenkins LTS 2.541.3 고정 | 최신 LTS, 재현성 확보 |
| 2026-04-06 | ssh → ssh-steps 교체 | SECURITY-2093, 2315 미해결, 미유지보수 |
| 2026-04-06 | extended-choice-parameter → uno-choice 교체 | 공식 EOL, XSS/SSRF 4건 미해결 |
| 2026-04-06 | ghprb → github-branch-source 교체 | SECURITY-2789 미해결, 3년+ 방치 |
| 2026-04-06 | entrypoint에서 chown 처리 | 호스트 디렉토리 root 소유 시 권한 문제 해결 |
