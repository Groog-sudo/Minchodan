"""
tests/conftest.py
pytest 수집 전 DB 등 필수 환경 변수 기본값을 주입한다.
fresh clone에서 server/db/connection.py import 시 RuntimeError가 나지 않도록 한다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# connection.py는 모듈 import 시 build_database_url()을 호출한다.
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "minchodan_test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret-key-with-at-least-32-characters")
os.environ.setdefault("JWT_ISSUER", "minchodan-test")
os.environ.setdefault("JWT_AUDIENCE", "minchodan-test-clients")
