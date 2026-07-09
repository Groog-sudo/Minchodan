"""
MariaDB 스키마 초기화 스크립트 (독립 실행 전용, 자동 배선 금지).

[배경] server/db/models.py의 SQLAlchemy ORM 모델은 이미 완성돼 있으나, 이를 실제
테이블로 만드는 자동화 경로가 없어 팀은 지금까지 `Minchodan DB.session.sql`을 DBeaver
등에서 수동 실행해왔다(MariaDB ENUM/COMMENT/CHARSET까지 정확히 반영한 버전). 이 스크립트는
models.py의 Base.metadata를 그대로 create_all()에 넘겨 동일한 결과를 코드로 재현하되,
SQLAlchemy가 생성하는 DDL은 COMMENT 절 등 일부 세부사항이 손실될 수 있다.
`Minchodan DB.session.sql`이 여전히 1차 기준이며, 이 스크립트는 반복 가능한 대안/보조
경로로 제공한다(둘 중 하나만 실행하면 된다 - 중복 실행 시 CREATE TABLE IF NOT EXISTS라
안전하다).

[중요] server/db/connection.py의 DATABASE_URL은 .env의 DB_HOST 등을 그대로 사용한다.
즉 이 스크립트를 실행하면 로컬이 아니라 .env에 설정된 실제 대상 DB(팀 공유 원격 MariaDB일
수 있음)에 테이블을 생성한다. 반드시 .env의 DB_HOST/DB_NAME이 의도한 대상인지 확인한 뒤
아래처럼 명시적으로만 실행한다.

    python -m server.db.init_db

자동 실행 배선 금지: server/main.py의 lifespan 등 서버 기동 경로에서 이 스크립트를
임포트하거나 호출하지 않는다 - 서버가 뜰 때마다 공유 원격 DB에 자동으로 스키마 변경을
시도하는 것은 위험하다. 실행은 항상 담당자가 의도를 갖고 수동으로 트리거한다.
"""

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.db.connection import DATABASE_URL, engine
from server.db.models import Base


async def create_all_tables() -> None:
    """Base.metadata에 등록된 전체 테이블을 대상 DB에 생성한다(이미 있으면 건너뜀)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _confirm_target(database_url: str) -> bool:
    """대화형 실행 시 대상 DB를 사람이 눈으로 확인하고 명시적으로 동의하게 한다."""
    masked = database_url.split("@")[-1] if "@" in database_url else database_url
    print(f"[init_db] 대상 DB: {masked}")
    answer = input("이 DB에 테이블을 생성합니다. 계속하시겠습니까? (yes 입력 시 진행): ")
    return answer.strip().lower() == "yes"


if __name__ == "__main__":
    if not _confirm_target(DATABASE_URL):
        print("[init_db] 취소되었습니다.")
        sys.exit(0)

    asyncio.run(create_all_tables())
    print(
        "[init_db] 스키마 생성 완료 (CREATE TABLE IF NOT EXISTS 기반, 기존 테이블은 변경되지 않음)."
    )
