# -*- coding: utf-8 -*-
"""Cloudflare R2 / remote 저장 백엔드 분기 단위 테스트 (네트워크 없음)."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def _clear_storage_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # 프로세스에 이미 .env / .env.network.cloud 이 export 된 경우에도
    # 단위 테스트가 격리되도록 비운다(delenv만으로는 재로드 타이밍에 취약).
    for key in (
        "EVENT_FRAME_STORAGE_BACKEND",
        "EVENT_FRAME_BACKEND",
        "IMAGE_SERVER_BASE_URL",
        "IMAGE_SERVER_TOKEN",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_ENDPOINT",
        "R2_PUBLIC_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv(key, "")


def test_storage_backend_local_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from server.services import remote_storage_client as rsc

    monkeypatch.setenv("EVENT_FRAME_STORAGE_BACKEND", "local")
    assert rsc.storage_backend() == "local"
    assert rsc.is_remote_storage_enabled() is False
    assert rsc.is_r2_backend() is False


def test_storage_backend_r2_requires_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from server.services import r2_storage_client as r2
    from server.services import remote_storage_client as rsc

    monkeypatch.setenv("EVENT_FRAME_STORAGE_BACKEND", "r2")
    assert rsc.is_r2_backend() is True
    assert r2.is_r2_configured() is False
    assert rsc.is_remote_storage_enabled() is False

    monkeypatch.setenv("R2_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("R2_BUCKET", "bucket")
    monkeypatch.setenv("R2_ACCOUNT_ID", "acct")
    r2._sync_client.cache_clear()
    assert r2.is_r2_configured() is True
    assert rsc.is_remote_storage_enabled() is True
    assert r2.frame_object_key(
        "evt1", when=__import__("datetime").datetime(2026, 7, 24, tzinfo=__import__("datetime").UTC)
    ) == ("event_frames/20260724/evt1.jpg")


def test_pi_remote_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    from server.services import remote_storage_client as rsc

    monkeypatch.setenv("EVENT_FRAME_STORAGE_BACKEND", "remote")
    monkeypatch.setenv("IMAGE_SERVER_BASE_URL", "http://example.invalid:8081")
    monkeypatch.setenv("IMAGE_SERVER_TOKEN", "token")
    assert rsc.is_pi_remote_backend() is True
    assert rsc.is_r2_backend() is False
    assert rsc.is_remote_storage_enabled() is True


@pytest.mark.asyncio
async def test_r2_upload_disabled_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from server.services import remote_storage_client as rsc

    monkeypatch.setenv("EVENT_FRAME_STORAGE_BACKEND", "r2")
    # R2 키 미설정이면 is_remote_storage_enabled()가 False → 공통 disabled 결과
    result = await rsc.upload_event_frame("evt1", b"jpeg-bytes")
    assert result.status == "not_saved"
    assert result.error_code == "remote_storage_disabled"


@pytest.mark.asyncio
async def test_r2_upload_and_presign_with_mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from server.services import r2_storage_client as r2
    from server.services import remote_storage_client as rsc

    class _FakeClient:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def put_object(self, **kwargs):
            self.objects[kwargs["Key"]] = kwargs["Body"]

        def get_object(self, **kwargs):
            key = kwargs["Key"]
            if key not in self.objects:
                err = Exception("NoSuchKey")
                err.response = {"Error": {"Code": "NoSuchKey"}}  # type: ignore[attr-defined]
                raise err

            class _Body:
                def __init__(self, data: bytes) -> None:
                    self._data = data

                def read(self) -> bytes:
                    return self._data

            return {"Body": _Body(self.objects[key])}

        def generate_presigned_url(self, _op, Params=None, ExpiresIn=300):
            return f"https://r2.example/presigned/{Params['Key']}?e={ExpiresIn}"

        def head_bucket(self, **_kwargs):
            return {}

    fake = _FakeClient()
    monkeypatch.setenv("EVENT_FRAME_STORAGE_BACKEND", "r2")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "sk")
    monkeypatch.setenv("R2_BUCKET", "bucket")
    monkeypatch.setenv("R2_ENDPOINT", "https://example.r2.cloudflarestorage.com")
    r2._sync_client.cache_clear()
    monkeypatch.setattr(r2, "_sync_client", lambda: fake)

    result = await rsc.upload_event_frame("evtSmoke1", b"jpeg-bytes")
    assert result.status == "available"
    assert result.object_key is not None
    assert result.object_key.startswith("event_frames/")
    assert fake.objects[result.object_key] == b"jpeg-bytes"

    fetched = await rsc.fetch_event_frame(result.object_key)
    assert fetched == b"jpeg-bytes"

    url = rsc.resolve_event_frame_url(result.object_key)
    assert url is not None
    assert "presigned" in url
