# -*- coding: utf-8 -*-
"""클라우드 MariaDB에 gildang_db 생성·전용 유저·ORM 스키마 적용.

사용법 (저장소 루트):
    # 대상은 CLOUD_DB_* 또는 인자. 비밀번호는 환경변수/프롬프트만 사용(로그에 출력 금지).
    CLOUD_DB_HOST=x.x.x.x CLOUD_DB_PORT=3307 CLOUD_DB_ROOT_PASSWORD=... \\
      .venv/bin/python scripts/setup_gildang_cloud_db.py --yes

기본값:
    DB명 gildang_db, 포트 3307, 앱 유저 gildang
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".env.network.cloud"), override=True)


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="gildang_db 클라우드 MariaDB 초기화")
    # DB_HOST 등 기존 Pi 값으로 폴백하지 않는다(오적용 방지). CLOUD_DB_* 또는 인자만 사용.
    parser.add_argument("--host", default=_env("CLOUD_DB_HOST"))
    parser.add_argument("--port", type=int, default=int(_env("CLOUD_DB_PORT", default="3307")))
    parser.add_argument("--root-user", default=_env("CLOUD_DB_ROOT_USER", default="root"))
    parser.add_argument(
        "--root-password",
        default=_env("CLOUD_DB_ROOT_PASSWORD"),
        help="루트 비밀번호. 미지정 시 환경변수 CLOUD_DB_ROOT_PASSWORD",
    )
    parser.add_argument("--db-name", default=_env("CLOUD_DB_NAME", default="gildang_db"))
    parser.add_argument("--app-user", default=_env("CLOUD_DB_APP_USER", default="gildang"))
    parser.add_argument(
        "--app-password",
        default=_env("CLOUD_DB_APP_PASSWORD"),
        help="앱 유저 비밀번호. 비어 있으면 랜덤 생성 후 한 번만 stdout에 안내",
    )
    parser.add_argument("--yes", action="store_true", help="대화형 확인 생략")
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="CREATE DATABASE/유저만 하고 ORM create_all 생략",
    )
    return parser.parse_args()


def _confirm(host: str, port: int, db_name: str, yes: bool) -> bool:
    print(f"[setup_gildang] target={host}:{port}/{db_name}")
    if yes:
        return True
    answer = input("이 대상에 gildang_db를 생성합니다. 계속하시겠습니까? (yes): ")
    return answer.strip().lower() == "yes"


def _ensure_database_and_user(
    host: str,
    port: int,
    root_user: str,
    root_password: str,
    db_name: str,
    app_user: str,
    app_password: str,
) -> None:
    import pymysql

    conn = pymysql.connect(
        host=host,
        port=port,
        user=root_user,
        password=root_password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            # '%'와 'localhost'를 모두 만든다(로컬 TCP/소켓 인증 호스트 차이 대응).
            for host_pattern in ("%", "localhost", "127.0.0.1"):
                cur.execute(
                    "CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s",
                    (app_user, host_pattern, app_password),
                )
                cur.execute(
                    "ALTER USER %s@%s IDENTIFIED BY %s",
                    (app_user, host_pattern, app_password),
                )
                cur.execute(
                    f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@%s",
                    (app_user, host_pattern),
                )
            cur.execute("FLUSH PRIVILEGES")
        print(f"[setup_gildang] database/user ready: db={db_name} user={app_user}")
    finally:
        conn.close()


async def _create_orm_tables(host: str, port: int, db_name: str, user: str, password: str) -> None:
    # connection 모듈이 .env DATABASE_URL을 이미 읽었을 수 있어 프로세스 env를 덮어쓴다.
    os.environ["DB_HOST"] = host
    os.environ["DB_PORT"] = str(port)
    os.environ["DB_NAME"] = db_name
    os.environ["DB_USER"] = user
    os.environ["DB_PASSWORD"] = password
    os.environ.pop("DATABASE_URL", None)

    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import create_async_engine

    from server.db.models import Base

    url = URL.create(
        "mysql+aiomysql",
        username=user,
        password=password,
        host=host,
        port=port,
        database=db_name,
        query={"charset": "utf8mb4"},
    )
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("[setup_gildang] ORM create_all 완료")


def main() -> int:
    args = parse_args()
    if not args.host:
        print(
            "[setup_gildang] ERROR: DB 호스트가 없습니다. "
            "CLOUD_DB_HOST 또는 --host 를 지정하십시오.",
            file=sys.stderr,
        )
        return 2
    if not args.root_password:
        print(
            "[setup_gildang] ERROR: 루트 비밀번호가 없습니다. "
            "CLOUD_DB_ROOT_PASSWORD 또는 --root-password 를 지정하십시오.",
            file=sys.stderr,
        )
        return 2

    app_password = args.app_password
    generated = False
    if not app_password:
        import secrets

        app_password = secrets.token_urlsafe(16)
        generated = True

    if not _confirm(args.host, args.port, args.db_name, args.yes):
        print("[setup_gildang] 취소")
        return 0

    try:
        _ensure_database_and_user(
            args.host,
            args.port,
            args.root_user,
            args.root_password,
            args.db_name,
            args.app_user,
            app_password,
        )
        if not args.skip_schema:
            asyncio.run(
                _create_orm_tables(args.host, args.port, args.db_name, args.app_user, app_password)
            )
    except Exception as exc:
        print(f"[setup_gildang] ERROR: {exc}", file=sys.stderr)
        return 1

    if generated:
        print(
            "[setup_gildang] 앱 유저 비밀번호를 생성했습니다. "
            "로컬 .env / .env.network.cloud 의 DB_PASSWORD 에만 저장하고 Git에 올리지 마십시오."
        )
        print(f"[setup_gildang] DB_USER={args.app_user}")
        print(f"[setup_gildang] DB_PASSWORD={app_password}")
    print("[setup_gildang] done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
