# -*- coding: utf-8 -*-
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator, DATETIME

# ==========================================
# 🤖 VIBE AREA (AI 위임 영역)
# ORM 모델의 최상위 Base 클래스 선언 및 타입 설정부입니다.
# 특별한 비즈니스 로직이 없는 껍데기 세팅 파일이므로 AI 복붙을 권장합니다.
# ==========================================

class UTCDateTime(TypeDecorator):
    """
    SQLite는 datetime을 naive(UTC를 무시)로 저장하므로,
    강제로 UTC timezone을 부착하여 읽고 쓰는 커스텀 타입입니다.
    """
    impl = DATETIME
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: Optional[datetime], dialect) -> Optional[datetime]:
        if value is not None:
            return value.replace(tzinfo=timezone.utc)
        return value

class Base(DeclarativeBase):
    pass
