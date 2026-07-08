> 작성일: 2026-07-04
> 버전: v1.0

# 백엔드 DB 코어 아키텍처 (Backend DB Core Architecture)

이 문서는 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼(Minchodan)의 백엔드 DB 구조 및 비즈니스 로직(Service 계층)에 대한 설계 원칙을 정리합니다.

## 1. 개요 (Overview)

본 시스템은 **MariaDB** 기반의 관계형 데이터베이스를 사용하며, 프레임워크로는 **FastAPI**와 **SQLAlchemy 2.0 (비동기, AsyncIO)**를 결합하여 설계되었습니다. 실시간 객체 탐지 및 알림이 주된 도메인이므로, 데이터베이스 입출력 과정에서 발생하는 대기 시간(Blocking)을 최소화하기 위해 전면 비동기 아키텍처를 도입했습니다.

## 2. 3계층 아키텍처 (3-Tier Architecture)

데이터베이스 로직의 유지보수성과 확장성을 위해 코어 로직은 크게 세 가지 계층으로 철저히 분리됩니다.

### 2.1. Router (HTTP API 계층)
- **위치**: `server/api/admin_router.py`, `server/api/user_router.py`
- **역할**: 클라이언트의 HTTP 요청을 받아, 의존성 주입(`Depends(get_db)`)을 통해 세션을 생성한 후 Service 계층에 위임합니다.
- **특징**: 직접적인 비즈니스 로직이나 DB 쿼리를 수행하지 않으며, 클라이언트 데이터 검증(Pydantic Schema) 및 응답 구조 변환만을 담당합니다.

### 2.2. Service (비즈니스 로직 계층)
- **위치**: `server/services/admin_service.py`, `server/services/user_service.py`
- **역할**: 실제 도메인 비즈니스 로직을 처리합니다. 암호화/복호화 처리, 예외 발생(HTTPException), 다중 Repository 간의 트랜잭션 묶기 등을 담당합니다.
- **특징**: 단일 세션(`session`)을 공유받아 여러 개의 Repository 인스턴스를 내부적으로 생성합니다. 이를 통해 다중 DB 조작이 하나의 트랜잭션 단위에서 원자성(Atomicity)을 보장받도록 설계되었습니다.

### 2.3. Repository (데이터 접근 계층)
- **위치**: `server/db/repositories.py`
- **역할**: 데이터베이스와의 직접적인 통신(CRUD 쿼리 실행)만을 전담합니다.
- **특징**: `await self.session.execute(select(...))` 형태의 비동기 SQLAlchemy 2.0 최신 문법을 사용하여 쿼리 결과를 반환합니다.

## 3. 핵심 비동기 방어 원칙 (Core Defensive Strategies)

면접 및 실제 프로덕션 서버에서 발생할 수 있는 주요 에러를 방어하기 위한 설정들입니다.

### 3.1. 비동기 엔진 방어 (Connection Pool)
- **`pool_pre_ping=True`**: 데이터베이스 서버가 커넥션을 일방적으로 끊었을 때 발생하는 좀비 커넥션 에러를 방지하기 위해 쿼리 전 사전 점검을 수행합니다.
- **`pool_recycle=3600`**: 1시간 단위로 커넥션을 재생성하여 커넥션 타임아웃 및 메모리 누수를 방지합니다.

### 3.2. 의존성 주입 트랜잭션 수거 (get_db)
```python
async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_sessionmaker_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```
- API 요청 처리 중 어떠한 형태의 예외가 발생하더라도 즉시 `rollback()` 처리하여 데이터 오염을 방지하고, 성공 여부에 관계없이 커넥션을 `close()`하여 안전하게 풀(Pool)로 반환합니다.

### 3.3. 객체 상태 유지 (expire_on_commit=False)
- 트랜잭션 `commit()` 이후 객체의 상태 정보가 초기화되는 것을 막기 위해 `async_sessionmaker` 옵션에 `expire_on_commit=False`를 부여하여, 커밋 직후에도 로컬 메모리에서 객체의 데이터를 활용할 수 있도록 했습니다.

## 4. 데이터베이스 매핑 전략

- **`AdminAccount` & `AdminLoginAudit`**: 관리자 계정 정보와 로그인 성공/실패 시도 이력을 별도의 감사(Audit) 테이블에 저장하여 보안 사고를 추적합니다.
- **`AppUser` & `UserDevice` (1:N 분리)**: 한 명의 시각장애인 유저가 폰을 변경하거나 중고폰 등을 등록할 때 발생하는 기기 식별자(`UUID`) 관리 문제를 해소하기 위해 사용자 테이블과 기기 테이블을 분리하여 저장 및 관리합니다.
