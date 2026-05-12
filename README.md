# vws-portfwd

AWS SSO 로그인 + SSM Port Forwarding 을 OS 무관하게 다루는 작은 CLI.

VWS 내부 mongo-prod / mongo-dev 등 alias 기반 터널을 동료들이 자기 컴퓨터(Windows/Mac) 에서도 그대로 쓸 수 있도록 함.

---

## 설치

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/pgj0116/vws-portfwd/main/install.ps1 | iex
```

**Mac (zsh/bash)**
```bash
curl -fsSL https://raw.githubusercontent.com/pgj0116/vws-portfwd/main/install.sh | bash
```

스크립트가 자동 처리:
- Python, AWS CLI v2, Session Manager Plugin, pipx 설치 (없는 것만)
- `pipx install vws-portfwd` (이 repo 에서 직접)
- (옵션) 쉘 profile 에 alias 함수 등록

---

## 사용

### 최초 설정 (1회)
```bash
vws-portfwd init
```
- AWS SSO 로그인 (브라우저)
- 권한 있는 계정/role 자동 발견 → 골라서 첫 profile 등록

### Alias 등록
```bash
vws-portfwd add mongo-prod
# AWS profile? sso-dba2
# EC2 instance ID? i-0a690f24812482ab1
# Local port?  37777
# Remote port? 27017
```

### 실행
```bash
vws-portfwd up mongo-prod
# [1/2] SSO 토큰 확인 (sso-dba2) ...
# [2/2] Port forward 시작: localhost:37777 -> i-...:27017
#   (Ctrl+C 로 종료)
```

다른 터미널에서:
```bash
mongosh "mongodb://user:pass@localhost:37777/db?authSource=admin"
```

### 목록 / 설정 편집
```bash
vws-portfwd list
vws-portfwd config edit   # ~/.vws-portfwd/config.yaml 을 OS 기본 에디터로 열기
vws-portfwd config path
```

---

## 설정 파일 위치

| OS | 경로 |
|---|---|
| Windows | `%USERPROFILE%\.vws-portfwd\config.yaml` |
| Mac/Linux | `~/.vws-portfwd/config.yaml` |

예시:
```yaml
profiles:
  sso-pkj:
    accountId: "123456789012"
    role: DeveloperAccess
  sso-dba2:
    accountId: "987654321098"
    role: DBAReadOnly
aliases:
  mongo-prod:
    profile: sso-dba2
    instance: i-0a690f24812482ab1
    localPort: 37777
    remotePort: 27017
  mongo-dev:
    profile: sso-pkj
    instance: i-05dbb9aedc1320f0a
    localPort: 37017
    remotePort: 27017
```

AWS 측 profile 은 `~/.aws/config` 에 자동 기록됩니다 (SSO 토큰 인증용).

---

## 외부 의존성

이 도구는 다음을 호출만 합니다 (직접 포함 X):
- `aws` CLI v2 (Amazon)
- `session-manager-plugin` (Amazon)

라이선스 상 우리 패키지 안에 binary 로 포함 못 함 — install 스크립트가 winget/brew 로 가져옵니다.

---

## 트러블슈팅

**`session-manager-plugin not found`**
- Windows: `winget install Amazon.SessionManagerPlugin` 또는 [installer](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
- Mac: `brew install --cask session-manager-plugin`

**`SSO 토큰 없음`**
- 만료됐을 가능성. `vws-portfwd up <alias>` 다시 실행하면 재로그인 자동 트리거.

**Windows SmartScreen 차단**
- install.ps1 처음 실행 시 'Microsoft Defender SmartScreen 차단' 뜨면 "추가 정보" → "실행" 클릭. 코드 서명 안 했음 (사내용).

---

## 회사 공통 (코드에 하드코드됨)

- SSO start URL: `https://creditncity.awsapps.com/start`
- SSO region: `ap-northeast-2`

다른 회사면 `src/vws_portfwd/config.py` 의 `SSO_START_URL`/`SSO_REGION` 수정 후 fork.
