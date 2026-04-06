# CLAUDE.md

## Commit Convention

커밋 메시지는 Conventional Commits 형식을 따른다.

### 형식

```
<type>(<scope>): <subject>

<body (optional, 한국어)>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

### Type

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 변경 (README 등)
- `refactor`: 기능 변경 없는 코드 개선
- `chore`: 빌드, 설정, 의존성 등 기타 변경
- `test`: 테스트 추가/수정
- `ci`: CI/CD 관련 변경

### 규칙

- type과 subject는 영어로 작성
- subject는 소문자로 시작, 마침표 없음, 50자 이내
- body는 한국어로 작성하며 변경 사유를 설명
- scope는 변경 대상 디렉토리 또는 컴포넌트 (예: jenkins, docker)
- Co-Authored-By 라인은 항상 포함

### 예시

```
feat(jenkins): add Docker setup with pinned LTS version and plugins

Jenkins 2.541.3-lts 기반 Docker 환경 구성. 보안 취약 플러그인을
안전한 대안으로 교체하고, 전체 플러그인 버전을 고정.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```
