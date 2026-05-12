"""사용자 설정 파일 (~/.vws-portfwd/config.yaml) 로드/저장."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# 회사 공통 SSO (변경되지 않는 값)
SSO_START_URL = "https://creditncity.awsapps.com/start"
SSO_REGION = "ap-northeast-2"


def config_dir() -> Path:
    return Path(os.path.expanduser("~/.vws-portfwd"))


def config_path() -> Path:
    return config_dir() / "config.yaml"


def aws_config_path() -> Path:
    return Path(os.path.expanduser("~/.aws/config"))


def load() -> dict[str, Any]:
    p = config_path()
    if not p.exists():
        return {"profiles": {}, "aliases": {}}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("profiles", {})
    data.setdefault("aliases", {})
    return data


def save(data: dict[str, Any]) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
