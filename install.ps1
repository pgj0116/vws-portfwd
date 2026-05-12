# vws-portfwd Windows bootstrap installer.
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/pgj0116/vws-portfwd/main/install.ps1 | iex
#
# 이 스크립트가 하는 일:
#  1. winget 으로 Python / AWS CLI / Session Manager Plugin 자동 설치
#  2. pipx 설치 + PATH 등록
#  3. pipx 로 vws-portfwd 설치 (Github 에서 직접)
#  4. PowerShell profile 에 alias 함수 자동 등록 (옵션)

$ErrorActionPreference = "Stop"
$REPO = "pgj0116/vws-portfwd"

function Step($msg) { Write-Host "`n[vws-portfwd] $msg" -ForegroundColor Cyan }
function HasCommand($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }

Step "사전 도구 확인"

if (-not (HasCommand "winget")) {
    Write-Host "winget 이 없습니다. Microsoft Store 에서 'App Installer' 설치 후 다시 실행하세요." -ForegroundColor Red
    exit 1
}

if (-not (HasCommand "python")) {
    Step "Python 설치 중..."
    winget install --silent --accept-source-agreements --accept-package-agreements Python.Python.3.12
} else {
    Write-Host "  ✓ Python 이미 설치됨"
}

if (-not (HasCommand "aws")) {
    Step "AWS CLI 설치 중..."
    winget install --silent --accept-source-agreements --accept-package-agreements Amazon.AWSCLI
} else {
    Write-Host "  ✓ AWS CLI 이미 설치됨"
}

if (-not (HasCommand "session-manager-plugin")) {
    Step "Session Manager Plugin 설치 중..."
    winget install --silent --accept-source-agreements --accept-package-agreements Amazon.SessionManagerPlugin
} else {
    Write-Host "  ✓ Session Manager Plugin 이미 설치됨"
}

# Refresh PATH in current session
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

Step "pipx 설치 + PATH"
python -m pip install --user --upgrade pipx
python -m pipx ensurepath
# 새로 추가된 PATH 를 즉시 반영
$env:Path = [Environment]::GetEnvironmentVariable("Path","User") + ";" + $env:Path

Step "vws-portfwd 설치 (Github)"
pipx install --force "git+https://github.com/$REPO.git"

Step "PowerShell profile 에 alias 등록 (옵션)"
$wantAliases = Read-Host "각 alias 를 짧은 명령으로 쓰고 싶으면 PowerShell profile 에 함수 자동 등록할게요. 등록할까요? [Y/n]"
if ($wantAliases -ne "n" -and $wantAliases -ne "N") {
    if (-not (Test-Path $PROFILE)) { New-Item -Path $PROFILE -ItemType File -Force | Out-Null }
    $marker = "# >>> vws-portfwd aliases >>>"
    $endMarker = "# <<< vws-portfwd aliases <<<"
    $content = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($content -notmatch [regex]::Escape($marker)) {
        Add-Content -Path $PROFILE -Value "`n$marker`nfunction Invoke-VwsPortfwdUp { param([string]`$Name) vws-portfwd up `$Name }`nSet-Alias vpf Invoke-VwsPortfwdUp`n# 추가로: 등록한 alias 마다 함수 만들고 싶으면 직접 작성. 예:`n# function mongo-prod { vws-portfwd up mongo-prod }`n$endMarker"
        Write-Host "  ✓ PowerShell profile 갱신: $PROFILE"
        Write-Host "    `$PROFILE 을 reload 하려면 새 PowerShell 창을 열거나 ' . `$PROFILE ' 실행"
    } else {
        Write-Host "  ✓ 이미 등록됨"
    }
}

Step "완료"
Write-Host @"

다음 단계:
  1) vws-portfwd init       # SSO 로그인 + 기본 profile 등록
  2) vws-portfwd add <alias>  # mongo-prod 등 alias 등록
  3) vws-portfwd up <alias>   # 포트포워딩 시작

"@
