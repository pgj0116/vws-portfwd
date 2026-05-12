"""AWS CLI / SSM wrapping. Shells out to `aws` CLI — no boto3 dependency."""

from __future__ import annotations

import configparser
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import SSO_REGION, SSO_START_URL, aws_config_path


class AwsToolMissing(Exception):
    pass


def _require(tool: str) -> None:
    if shutil.which(tool) is None:
        raise AwsToolMissing(f"{tool} not found on PATH. Run install script first.")


def sso_login(profile: str) -> None:
    _require("aws")
    subprocess.run(["aws", "sso", "login", "--profile", profile], check=True)


def list_accounts(profile: str) -> list[dict[str, Any]]:
    _require("aws")
    token = _get_sso_access_token(profile)
    out = subprocess.run(
        ["aws", "sso", "list-accounts", "--access-token", token, "--region", SSO_REGION,
         "--output", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout).get("accountList", [])


def list_account_roles(profile: str, account_id: str) -> list[dict[str, Any]]:
    _require("aws")
    token = _get_sso_access_token(profile)
    out = subprocess.run(
        ["aws", "sso", "list-account-roles", "--access-token", token,
         "--account-id", account_id, "--region", SSO_REGION, "--output", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out.stdout).get("roleList", [])


def _get_sso_access_token(profile: str) -> str:
    """Read cached SSO access token written by `aws sso login`."""
    cache_dir = Path.home() / ".aws" / "sso" / "cache"
    if not cache_dir.exists():
        raise RuntimeError("SSO cache 없음. `aws sso login --profile {}` 먼저 실행.".format(profile))
    newest = max(cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, default=None)
    if newest is None:
        raise RuntimeError("SSO 토큰 파일 없음. 다시 로그인 필요.")
    data = json.loads(newest.read_text(encoding="utf-8"))
    tok = data.get("accessToken")
    if not tok:
        raise RuntimeError("accessToken 누락된 SSO 캐시.")
    return tok


def write_aws_profile(profile_name: str, account_id: str, role_name: str) -> None:
    """`~/.aws/config` 의 [profile <name>] 섹션 생성/갱신."""
    cfg = configparser.ConfigParser()
    p = aws_config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        cfg.read(p, encoding="utf-8")
    section = f"profile {profile_name}"
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, "sso_start_url", SSO_START_URL)
    cfg.set(section, "sso_region", SSO_REGION)
    cfg.set(section, "sso_account_id", account_id)
    cfg.set(section, "sso_role_name", role_name)
    cfg.set(section, "region", SSO_REGION)
    cfg.set(section, "output", "json")
    with p.open("w", encoding="utf-8") as f:
        cfg.write(f)


def start_port_forward(profile: str, instance_id: str, local_port: int, remote_port: int) -> int:
    """포어그라운드 SSM port forward 실행. 차단됨 (Ctrl+C 로 종료)."""
    _require("aws")
    _require("session-manager-plugin")
    cmd = [
        "aws", "ssm", "start-session",
        "--profile", profile,
        "--target", instance_id,
        "--document-name", "AWS-StartPortForwardingSession",
        "--parameters", json.dumps({
            "portNumber": [str(remote_port)],
            "localPortNumber": [str(local_port)],
        }),
    ]
    return subprocess.call(cmd)
