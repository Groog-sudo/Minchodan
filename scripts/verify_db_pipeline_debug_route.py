#!/usr/bin/env python3
"""DB에 저장된 pipeline_debug route/zone 필드 샘플 검증 (Tailscale/로컬 DB)."""

import asyncio
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


async def main() -> int:
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from server.db.models import DetectionGuidanceLog

    db_host = os.getenv("DB_HOST", "mariadb")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "minchodan")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "minchodan")

    url = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_async_engine(url, pool_pre_ping=True)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    checks = {"db_connect": False, "recent_rows": 0, "route_field_rows": 0}

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
            checks["db_connect"] = True

            result = await session.execute(
                select(DetectionGuidanceLog)
                .where(DetectionGuidanceLog.pipeline_debug_json.is_not(None))
                .order_by(DetectionGuidanceLog.detected_at.desc())
                .limit(20)
            )
            rows = list(result.scalars().all())
            checks["recent_rows"] = len(rows)

            for row in rows:
                if not row.pipeline_debug_json:
                    continue
                try:
                    payload = json.loads(row.pipeline_debug_json)
                except json.JSONDecodeError:
                    continue
                if payload.get("route") and payload.get("effective_distance_zone"):
                    checks["route_field_rows"] += 1
                    print(
                        f"OK log_id={row.log_id} path={payload.get('path')} "
                        f"route={payload.get('route')} zone={payload.get('effective_distance_zone')}"
                    )
    finally:
        await engine.dispose()

    print("=" * 50)
    print(f"DB connect: {checks['db_connect']}")
    print(f"Recent pipeline_debug rows: {checks['recent_rows']}")
    print(f"Rows with route+zone: {checks['route_field_rows']}")

    if not checks["db_connect"]:
        return 1
    if checks["route_field_rows"] == 0:
        print(
            "WARN: route/zone 필드가 있는 최근 로그가 없음 (신규 코드 배포 후 라이브 탐지가 필요)"
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
