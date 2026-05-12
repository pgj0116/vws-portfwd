"""vws-portfwd CLI entrypoint.

Commands:
  init                          최초 설정 (SSO 로그인 + 계정/role 선택 + profile 등록)
  add <alias>                   alias 새로 등록 (instance/local/remote port 입력)
  list                          등록된 alias 목록
  up <alias>                    포어그라운드 포트포워딩 시작
  config edit                   설정 파일 OS 기본 에디터로 열기
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from . import aws as aws_mod
from . import config as cfg_mod


@click.group()
@click.version_option(__version__, prog_name="vws-portfwd")
def main() -> None:
    pass


@main.command()
def init() -> None:
    """Initial setup — SSO login → pick account/role → register first profile."""
    click.echo("vws-portfwd 초기 설정")
    click.echo(f"SSO start URL : {cfg_mod.SSO_START_URL}")
    click.echo(f"SSO region    : {cfg_mod.SSO_REGION}\n")

    profile_name = click.prompt("기본 AWS profile 이름", default="sso-personal")
    # SSO 로그인을 위한 임시 profile 을 ~/.aws/config 에 우선 만들고 token 발급
    # 그 후 list_accounts / list_account_roles 로 발견
    aws_mod.write_aws_profile(profile_name, account_id="000000000000", role_name="__placeholder__")
    click.echo(f"\nAWS profile '{profile_name}' 임시 등록. 브라우저에서 SSO 로그인 진행...\n")
    try:
        aws_mod.sso_login(profile_name)
    except subprocess.CalledProcessError:
        click.echo("SSO 로그인 실패. AWS CLI 설치/네트워크 확인.", err=True)
        sys.exit(1)

    accounts = aws_mod.list_accounts(profile_name)
    if not accounts:
        click.echo("권한 있는 계정 없음.", err=True)
        sys.exit(1)
    click.echo("\n사용 가능한 AWS 계정:")
    for i, a in enumerate(accounts, 1):
        click.echo(f"  [{i}] {a['accountId']}  {a.get('accountName', '')}")
    pick = click.prompt("계정 번호 선택", type=int, default=1)
    account = accounts[pick - 1]

    roles = aws_mod.list_account_roles(profile_name, account["accountId"])
    if not roles:
        click.echo("권한 role 없음.", err=True)
        sys.exit(1)
    click.echo("\n사용 가능한 role:")
    for i, r in enumerate(roles, 1):
        click.echo(f"  [{i}] {r['roleName']}")
    pick = click.prompt("role 번호 선택", type=int, default=1)
    role = roles[pick - 1]

    # 정식 값으로 다시 기록
    aws_mod.write_aws_profile(profile_name, account["accountId"], role["roleName"])
    data = cfg_mod.load()
    data["profiles"][profile_name] = {
        "accountId": account["accountId"],
        "role": role["roleName"],
    }
    cfg_mod.save(data)
    click.echo(f"\n✓ Profile '{profile_name}' 등록 완료")
    click.echo("\n다음: vws-portfwd add <alias> 로 alias 추가")


@main.command()
@click.argument("alias", required=False)
def add(alias: str | None) -> None:
    """Register a new alias for SSM port forwarding.

    alias 인자 생략 시 wizard 안에서 직접 입력하도록 묻습니다.
    예) vws-portfwd add mongo-prod
        vws-portfwd add               # 대화형으로 alias 입력
    """
    data = cfg_mod.load()
    profiles = list(data["profiles"].keys())
    if not profiles:
        click.echo("등록된 profile 없음. 먼저 `vws-portfwd init` 실행.", err=True)
        sys.exit(1)

    if not alias:
        alias = click.prompt("alias 이름 (예: mongo-prod)").strip()
    if not alias:
        click.echo("alias 이름이 비어있습니다.", err=True)
        sys.exit(1)
    if alias in data["aliases"]:
        ow = click.confirm(f"alias '{alias}' 이미 존재합니다. 덮어쓸까요?", default=False)
        if not ow:
            click.echo("취소됨.")
            sys.exit(0)

    default_profile = profiles[0]
    profile = click.prompt("AWS profile", default=default_profile)
    if profile not in profiles:
        click.echo(f"알 수 없는 profile: {profile}. 등록된 것: {profiles}", err=True)
        sys.exit(1)
    instance = click.prompt("EC2 instance ID")
    local_port = click.prompt("Local port", type=int)
    remote_port = click.prompt("Remote port", type=int)

    data["aliases"][alias] = {
        "profile": profile,
        "instance": instance,
        "localPort": local_port,
        "remotePort": remote_port,
    }
    cfg_mod.save(data)
    click.echo(f"✓ alias '{alias}' 등록")
    click.echo(f"   사용: vws-portfwd up {alias}")


@main.command()
def list() -> None:  # noqa: A001 - intentional shadowing
    """List registered aliases."""
    data = cfg_mod.load()
    aliases = data["aliases"]
    if not aliases:
        click.echo("등록된 alias 없음. `vws-portfwd add <alias>` 로 추가.")
        return
    click.echo(f"{'ALIAS':<20} {'PROFILE':<14} {'INSTANCE':<25} {'LOCAL':<7} REMOTE")
    for name, a in aliases.items():
        click.echo(f"{name:<20} {a['profile']:<14} {a['instance']:<25} {a['localPort']:<7} {a['remotePort']}")


@main.command()
@click.argument("alias")
def up(alias: str) -> None:
    """Start foreground SSM port forwarding for an alias."""
    data = cfg_mod.load()
    a = data["aliases"].get(alias)
    if not a:
        click.echo(f"alias '{alias}' 없음. `vws-portfwd list` 확인.", err=True)
        sys.exit(1)
    profile = a["profile"]
    click.echo(f"[1/2] SSO 토큰 확인 ({profile}) ...")
    try:
        aws_mod._get_sso_access_token(profile)
    except RuntimeError:
        click.echo("  SSO 토큰 만료/없음 → 재로그인")
        aws_mod.sso_login(profile)
    click.echo(f"[2/2] Port forward 시작: localhost:{a['localPort']} -> {a['instance']}:{a['remotePort']}")
    click.echo("  (Ctrl+C 로 종료)\n")
    rc = aws_mod.start_port_forward(profile, a["instance"], int(a["localPort"]), int(a["remotePort"]))
    sys.exit(rc)


@main.group()
def config() -> None:
    """Config inspection/edit."""
    pass


@config.command("edit")
def config_edit() -> None:
    p = cfg_mod.config_path()
    if not p.exists():
        click.echo("config 없음. 먼저 `vws-portfwd init` 실행.", err=True)
        sys.exit(1)
    if platform.system() == "Windows":
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif platform.system() == "Darwin":
        subprocess.call(["open", str(p)])
    else:
        editor = os.environ.get("EDITOR", "nano")
        subprocess.call([editor, str(p)])


@config.command("path")
def config_path() -> None:
    click.echo(str(cfg_mod.config_path()))


if __name__ == "__main__":
    main()
