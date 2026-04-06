# Jenkins Docker Setup

Jenkins LTS를 Docker로 구성하고, 플러그인 버전을 고정하여 재현 가능한 환경을 만드는 프로젝트입니다.

## 빠른 시작

### 빌드

```bash
cd jenkins
docker compose build
```

### 시작

```bash
docker compose up -d
```

- Jenkins UI: http://localhost:9090
- 데이터 저장 경로: `~/jenkins_backup`

초기 비밀번호 확인:

```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 중단

```bash
docker compose down
```

## 운영 명령어

```bash
# 중지
docker compose down

# 재시작
docker compose restart

# 로그 확인 (실시간)
docker compose logs -f

# 컨테이너 상태 확인
docker compose ps

# Jenkins 쉘 접속
docker exec -it jenkins bash

# 이미지만 새로 빌드 (컨테이너 재생성 없이)
docker compose build --no-cache

# 빌드 후 컨테이너 재생성
docker compose up -d --build

# 데이터 유지하면서 컨테이너만 삭제
docker compose down
# ~/jenkins_backup 디렉토리에 데이터가 보존됩니다

# 완전 삭제 (이미지 포함)
docker compose down --rmi all
```

## 구성 파일

| 파일 | 설명 |
|---|---|
| `Dockerfile` | Jenkins 이미지 빌드 (베이스 이미지 + 플러그인 설치) |
| `plugins.txt` | 설치할 플러그인 목록 (이름:버전) |
| `docker-compose.yml` | 포트, 볼륨, 환경변수 설정 |

## 플러그인 버전 고정 방법 (수동)

Jenkins 플러그인은 의존성이 복잡하여 개별 버전을 직접 지정하면 충돌이 발생할 수 있습니다.
아래 절차를 통해 의존성이 해결된 전체 플러그인 목록을 안전하게 추출할 수 있습니다.

### Step 1: 버전 미지정 plugins.txt 작성

설치할 플러그인 이름만 나열합니다.

```text
github
ansible
workflow-aggregator
dark-theme
...
```

### Step 2: Jenkins 베이스 이미지 버전 확인

Docker Hub에서 현재 LTS 버전을 확인합니다.

```bash
curl -s "https://hub.docker.com/v2/repositories/jenkins/jenkins/tags/?page_size=10&name=lts-jdk17" \
  | python3 -c "
import json,sys
data=json.load(sys.stdin)
for t in data['results']:
    print(t['name'], t['last_updated'])
"
```

출력에서 `2.541.3-lts-jdk17` 같은 형태의 태그를 확인하고, Dockerfile의 `FROM`을 고정합니다.

```dockerfile
FROM jenkins/jenkins:2.541.3-lts
```

### Step 3: 버전 미지정 상태로 빌드

```bash
docker compose build --no-cache
```

`jenkins-plugin-cli`가 의존성을 자동으로 해결하며 최신 호환 버전을 설치합니다.

### Step 4: 설치된 플러그인 버전 추출

빌드된 이미지에서 실제 설치된 전체 플러그인(의존성 포함) 버전을 추출합니다.

```bash
docker run --rm jenkins-jenkins bash -c "
for jpi in /usr/share/jenkins/ref/plugins/*.jpi; do
  name=\$(basename \$jpi .jpi)
  ver=\$(unzip -p \$jpi META-INF/MANIFEST.MF | grep '^Plugin-Version:' | tr -d '\r' | awk '{print \$2}')
  echo \"\${name}:\${ver}\"
done
" | sort
```

출력 예시:

```text
ansible:635.v34b_48e979c86
dark-theme:652.vea_da_dfea_e769
git:5.10.1
workflow-aggregator:608.v67378e9d3db_1
...
```

### Step 5: plugins.txt를 버전 고정된 결과로 교체

Step 4의 출력 전체를 `plugins.txt`에 덮어씁니다.

```bash
docker run --rm jenkins-jenkins bash -c "
for jpi in /usr/share/jenkins/ref/plugins/*.jpi; do
  name=\$(basename \$jpi .jpi)
  ver=\$(unzip -p \$jpi META-INF/MANIFEST.MF | grep '^Plugin-Version:' | tr -d '\r' | awk '{print \$2}')
  echo \"\${name}:\${ver}\"
done
" | sort > plugins.txt
```

### Step 6: 버전 고정된 상태로 재빌드 및 검증

```bash
docker compose build --no-cache
```

보안 경고 없이 빌드되면 완료입니다.

> **`--no-cache` 옵션이 필요한 경우:**
> Docker는 Dockerfile의 각 레이어를 캐시합니다. `plugins.txt` 내용을 변경하더라도
> `COPY plugins.txt` 이전 레이어가 동일하면 캐시된 결과를 재사용하여
> 플러그인이 실제로 다시 설치되지 않을 수 있습니다.
> 다음 상황에서는 반드시 `--no-cache`를 사용하세요:
>
> - `plugins.txt`의 플러그인을 추가/제거/변경한 경우
> - Dockerfile의 베이스 이미지(`FROM`) 버전을 변경한 경우
> - 버전 미지정 플러그인의 최신 버전을 새로 받고 싶은 경우

## 보안 취약 플러그인 교체 이력

아래 플러그인은 보안 취약점이 미해결 상태로 방치되어 대안으로 교체하였습니다.

| 제거된 플러그인 | 사유 | 대안 플러그인 |
|---|---|---|
| `ssh` | CSRF, 권한 검증 누락 (SECURITY-2093, 2315). 미유지보수. | `ssh-steps` |
| `extended-choice-parameter` | XSS, SSRF 등 4건 미해결. 공식 EOL. | `uno-choice` (Active Choices) |
| `ghprb` | CSRF, 권한 검증 누락 (SECURITY-2789). 3년+ 방치. | `github-branch-source` |

### 플러그인 사용법 차이

**ssh -> ssh-steps**

```groovy
// 기존 ssh 플러그인: UI에서 SSH 사이트 설정 후 사용
// ssh-steps: Pipeline 코드에서 직접 사용
def remote = [name: 'server', host: '192.168.1.100', user: 'deploy', allowAnyHosts: true]
withCredentials([sshUserPrivateKey(credentialsId: 'ssh-key', keyFileVariable: 'key')]) {
    remote.identityFile = key
    sshCommand remote: remote, command: 'ls -la'
    sshPut remote: remote, from: 'build.tar.gz', into: '/opt/deploy/'
}
```

**extended-choice-parameter -> uno-choice (Active Choices)**

```groovy
// Jenkinsfile에서 Active Choices 파라미터 사용
properties([
    parameters([
        [$class: 'ChoiceParameter',
         name: 'ENVIRONMENT',
         choiceType: 'PT_SINGLE_SELECT',
         script: [$class: 'GroovyScript',
                  script: [script: "return ['dev', 'staging', 'prod']"]]]
    ])
])
```

**ghprb -> github-branch-source**

Multibranch Pipeline Job을 생성하고, Branch Source에서 GitHub을 선택하면 PR 자동 감지 및 빌드가 동작합니다. Jenkinsfile 기반으로 동작하며 별도 설정이 필요 없습니다.

## Jenkins 업그레이드 시

1. Dockerfile의 `FROM` 버전을 새 LTS 버전으로 변경
2. `plugins.txt`에서 버전을 제거하고 이름만 남김
3. 위의 Step 3~6을 다시 수행하여 새 버전 고정
