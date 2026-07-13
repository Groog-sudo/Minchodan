import asyncio
import os
import sys

# 프로젝트 루트를 sys.path에 추가하여 server 패키지 임포트 허용
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from server.db.connection import engine, async_sessionmaker_factory
from server.db.models import Base, AdminAccount, AdminRole, AdminAccountStatus
from server.db.security import get_password_hash
from sqlalchemy import select

async def main():
    # 1. SQLite의 경우 data/ 디렉토리 사전 생성 확인
    data_dir = os.path.join(project_root, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print("Created data directory.")

    # 2. 테이블 생성 (IF NOT EXISTS)
    print("Creating database tables if they do not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 3. 기본 관리자 계정 생성
    async with async_sessionmaker_factory() as session:
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.employee_no == "admin")
        )
        admin = result.scalars().first()
        
        if admin:
            print("Default admin account 'admin' already exists.")
        else:
            # Bcrypt 해싱 적용
            hashed_pw = get_password_hash("admin1234")
            new_admin = AdminAccount(
                employee_no="admin",
                name="System Administrator",
                password_hash=hashed_pw,
                role=AdminRole.SUPER_ADMIN,
                status=AdminAccountStatus.ACTIVE
            )
            session.add(new_admin)
            await session.commit()
            print("Default admin account ('admin' / 'admin1234') created successfully.")

if __name__ == "__main__":
    asyncio.run(main())
