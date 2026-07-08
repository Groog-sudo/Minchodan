import sys
# ============================
import os
from dotenv import load_dotenv

# .env 파일의 환경 변수를 시스템 환경 변수로 로드
# 프로젝트 루트 디렉토리에서 .env 파일을 찾도록 설정
# load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv()

db_type = os.getenv("DB_TYPE")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# ===========================

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ==========================================
# 🧠 TH HARDCODE AREA (면접/발표 핵심 방어 영역)
# DB 커넥션 풀 관리 및 비동기 엔진 세팅입니다.
# 아래 주석의 안내에 따라 코드를 직접 타이핑해 보세요!
# ==========================================

from collections.abc import AsyncGenerator

# 1. 비동기 연결에 필요한 SQLAlchemy 모듈들을 임포트하세요.
# (힌트: sqlalchemy.ext.asyncio 에서 AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine 를 가져옵니다)
# 여기에 작성:
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 2. MariaDB 접속 주소를 정의하세요.
# (힌트: "mysql+aiomysql://minchodan_team:minCho_0717@100.105.221.31:3306/minchodan_db" 형식입니다)
#   - 보안을 위해 mariaDB의 접속 정보를 .env 파일에서 로드해서 사용합니다.
DATABASE_URL = f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# 3. 비동기 엔진을 생성하세요. (면접 단골 질문!)
# (힌트: create_async_engine 사용.
#       pool_pre_ping=True 로 좀비 커넥션 방어,
#       pool_recycle=3600 으로 커넥션 재생성 옵션을 꼭 넣으세요)
# 여기에 작성:
engine: AsyncEngine = create_async_engine(
    DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600
)

# 4. 비동기 세션 공장(Factory)을 생성하세요.
# (힌트: async_sessionmaker 사용. engine 연결, expire_on_commit=False, class_=AsyncSession 옵션 부여)
# 여기에 작성:
# expire_on_commit=False, => DB 커밋을 하고 나면 Object data 날아가서 다시 DB 조회 비효율
# 이 과정에서 Error 높음 그래서 커밋후 메모리 데이터 유지 재사용 >> expire_on_commit=False
async_sessionmaker_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# 5. FastAPI 의존성 주입(Depends)용 제너레이터 함수를 만드세요.
# (힌트: async def get_db() -> AsyncGenerator[AsyncSession, None]:
#       try-except-finally 구조로 rollback과 close 처리가 필수입니다)
# 여기에 작성:
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_sessionmaker_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
