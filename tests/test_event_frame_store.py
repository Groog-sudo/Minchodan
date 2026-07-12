"""
이벤트 프레임 저장소(event_frame_store) 단위 테스트.

검증 항목:
- save_event_frame: 정상 저장, 상대 경로 형식, 잘못된 event_id 거부, None 프레임 거부
- resolve_frame_path: 정상 해석, 경로 탈출 차단, 미존재 파일 None
- cleanup_expired_frames: 보존 기간 초과 날짜 폴더만 삭제
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from server.services import event_frame_store as store


@pytest.fixture
def frames_dir(tmp_path, monkeypatch):
    """EVENT_FRAMES_DIR를 임시 디렉토리로 격리한다."""
    target = tmp_path / "event_frames"
    monkeypatch.setattr(store, "EVENT_FRAMES_DIR", target)
    return target


def _dummy_frame() -> np.ndarray:
    return np.zeros((48, 64, 3), dtype=np.uint8)


def test_save_event_frame_writes_jpeg(frames_dir: Path):
    rel_path = store.save_event_frame("event-dev001-reflex-1234567890123", _dummy_frame())
    assert rel_path is not None
    date_dir = datetime.now(UTC).strftime("%Y%m%d")
    assert rel_path == f"{date_dir}/event-dev001-reflex-1234567890123.jpg"
    assert (frames_dir / rel_path).is_file()
    # JPEG 매직 넘버 확인
    assert (frames_dir / rel_path).read_bytes()[:2] == b"\xff\xd8"


def test_save_event_frame_rejects_invalid_event_id(frames_dir: Path):
    assert store.save_event_frame("../escape", _dummy_frame()) is None
    assert store.save_event_frame("a/b", _dummy_frame()) is None
    assert store.save_event_frame("", _dummy_frame()) is None


def test_save_event_frame_rejects_none_frame(frames_dir: Path):
    assert store.save_event_frame("event-ok-1", None) is None


def test_resolve_frame_path_roundtrip(frames_dir: Path):
    rel_path = store.save_event_frame("event-ok-2", _dummy_frame())
    resolved = store.resolve_frame_path(rel_path)
    assert resolved is not None
    assert resolved.is_file()


def test_resolve_frame_path_blocks_traversal(frames_dir: Path, tmp_path: Path):
    outside = tmp_path / "secret.jpg"
    outside.write_bytes(b"x")
    assert store.resolve_frame_path("../secret.jpg") is None
    assert store.resolve_frame_path(None) is None
    assert store.resolve_frame_path("20990101/missing.jpg") is None


def test_cleanup_expired_frames_removes_only_old_date_dirs(frames_dir: Path):
    old_dir = frames_dir / (datetime.now(UTC) - timedelta(days=30)).strftime("%Y%m%d")
    fresh_dir = frames_dir / datetime.now(UTC).strftime("%Y%m%d")
    other_dir = frames_dir / "not_a_date"
    for d in (old_dir, fresh_dir, other_dir):
        d.mkdir(parents=True)
        (d / "sample.jpg").write_bytes(b"\xff\xd8")

    removed = store.cleanup_expired_frames(retention_days=7)
    assert removed == 1
    assert not old_dir.exists()
    assert fresh_dir.exists()
    assert other_dir.exists()


def test_cleanup_disabled_when_retention_zero(frames_dir: Path):
    old_dir = frames_dir / "20200101"
    old_dir.mkdir(parents=True)
    assert store.cleanup_expired_frames(retention_days=0) == 0
    assert old_dir.exists()
