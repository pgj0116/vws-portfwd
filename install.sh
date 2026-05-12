#!/usr/bin/env bash
# vws-portfwd Mac/Linux bootstrap installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/pgj0116/vws-portfwd/main/install.sh | bash

set -euo pipefail
REPO="pgj0116/vws-portfwd"

step() { printf "\n\033[36m[vws-portfwd] %s\033[0m\n" "$*"; }
has() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
case "$OS" in
  Darwin)
    step "사전 도구 확인 (macOS)"
    if ! has brew; then
      echo "Homebrew 가 필요합니다. https://brew.sh 에서 설치 후 다시 실행해주세요." >&2
      exit 1
    fi
    if ! has python3; then step "Python 설치"; brew install python; else echo "  ✓ python3"; fi
    if ! has aws; then step "AWS CLI 설치"; brew install awscli; else echo "  ✓ aws"; fi
    if ! has session-manager-plugin; then
      step "Session Manager Plugin 설치"
      brew install --cask session-manager-plugin
    else
      echo "  ✓ session-manager-plugin"
    fi
    if ! has pipx; then step "pipx 설치"; brew install pipx; fi
    pipx ensurepath >/dev/null || true
    ;;
  Linux)
    step "사전 도구 확인 (Linux)"
    has python3 || { echo "python3 먼저 설치" >&2; exit 1; }
    has aws || { echo "AWS CLI v2 먼저 설치 (https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)" >&2; exit 1; }
    has session-manager-plugin || { echo "Session Manager Plugin 먼저 설치 (https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)" >&2; exit 1; }
    if ! has pipx; then python3 -m pip install --user pipx; fi
    python3 -m pipx ensurepath >/dev/null || true
    ;;
  *)
    echo "지원 안 함: $OS" >&2
    exit 1
    ;;
esac

step "vws-portfwd 설치 (Github)"
pipx install --force "git+https://github.com/${REPO}.git"

step "쉘 alias 등록 (옵션)"
read -rp "각 alias 를 짧은 명령으로 쓰고 싶으면 쉘 profile 에 함수 자동 등록할까요? [Y/n] " ans
if [[ "$ans" != "n" && "$ans" != "N" ]]; then
  RC="$HOME/.zshrc"
  [[ -f "$HOME/.bashrc" ]] && RC="$HOME/.bashrc"
  [[ "$SHELL" == *zsh* ]] && RC="$HOME/.zshrc"
  MARKER_START="# >>> vws-portfwd aliases >>>"
  MARKER_END="# <<< vws-portfwd aliases <<<"
  if ! grep -q "$MARKER_START" "$RC" 2>/dev/null; then
    cat >> "$RC" <<EOF

$MARKER_START
vpf() { vws-portfwd up "\$1"; }
# 등록한 alias 마다 함수 직접 만들고 싶으면 예시:
# mongo-prod() { vws-portfwd up mongo-prod; }
$MARKER_END
EOF
    echo "  ✓ $RC 에 추가됨. 새 터미널 열거나 'source $RC' 로 reload."
  else
    echo "  ✓ 이미 등록됨"
  fi
fi

step "완료"
cat <<'EOM'

다음 단계:
  1) vws-portfwd init           # SSO 로그인 + 기본 profile 등록
  2) vws-portfwd add <alias>    # mongo-prod 등 alias 등록
  3) vws-portfwd up <alias>     # 포트포워딩 시작

EOM
