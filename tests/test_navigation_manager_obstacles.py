import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.navigation.manager import NavigationManager

# ============================================================
# 테스트 파일 역할
# ============================================================
# [바이브 코딩 부분]
# - 2026-07-20 실기기 필드 테스트 피드백 2건 재발 방지 테스트.
# - (1) 안전 노면 클래스("sidewalk_normal")가 장애물로 안내되지 않는지.
# - (2) 클래스명이 SSOT class_name_to_ko로 번역되는지(원문 클래스명 누출 방지).
# - (3) 같은 클래스가 연속 재탐지돼도 억제 시간 동안은 한 번만 안내하는지,
#       다른 클래스는 억제와 무관하게 즉시 안내되는지.
#
# NavigationManager는 싱글톤(__new__)이라 인스턴스는 공유되지만 세션은
# device_id별로 분리되므로, 테스트마다 고유한 device_id를 사용해 격리한다.


def _new_manager() -> NavigationManager:
    return NavigationManager()


def test_safe_surface_class_is_never_cached_as_obstacle():
    """sidewalk_normal/braille_normal은 장애물이 아니므로 캐시에 들어가지 않는다."""
    manager = _new_manager()
    device_id = "test-safe-surface"

    manager.add_obstacle_event(device_id, "sidewalk_normal")
    manager.add_obstacle_event(device_id, "braille_normal")

    session = manager._get_or_create_session(device_id)
    assert session.pending_obstacles == []
    assert manager._pop_obstacle_text(session) == ""


def test_obstacle_text_uses_ssot_korean_translation():
    """원문 클래스명이 그대로 새지 않고 class_name_to_ko로 번역되어야 한다."""
    manager = _new_manager()
    device_id = "test-translation"

    manager.add_obstacle_event(device_id, "roadway")
    session = manager._get_or_create_session(device_id)
    session.last_announced_obstacle_time = 0.0  # 5초 쿨다운 우회

    text = manager._pop_obstacle_text(session)
    assert text == "전방에 차도 주의하세요."
    assert "roadway" not in text


def test_same_class_repeat_is_suppressed_within_window():
    """같은 클래스가 연속 재탐지돼도 억제 시간 안에는 재안내하지 않는다."""
    manager = _new_manager()
    device_id = "test-repeat-suppress"
    session = manager._get_or_create_session(device_id)

    manager.add_obstacle_event(device_id, "caution")
    session.last_announced_obstacle_time = 0.0
    first = manager._pop_obstacle_text(session)
    assert first == "전방에 주의 노면 주의하세요."

    # 같은 클래스가 다시 탐지됨(예: 3초 dedup 창을 피하려면 새 이벤트를 직접 주입)
    session.pending_obstacles.append({"class_name": "caution", "ts": time.time()})
    session.last_announced_obstacle_time = 0.0  # 전역 5초 쿨다운만 우회
    second = manager._pop_obstacle_text(session)
    assert second == ""  # 같은 클래스 재안내 억제(OBSTACLE_REPEAT_SUPPRESS_S 이내)


def test_different_class_interrupts_suppression_immediately():
    """억제 중인 클래스와 다른 클래스가 대기 중이면 억제와 무관하게 즉시 안내한다."""
    manager = _new_manager()
    device_id = "test-different-class"
    session = manager._get_or_create_session(device_id)

    manager.add_obstacle_event(device_id, "caution")
    session.last_announced_obstacle_time = 0.0
    first = manager._pop_obstacle_text(session)
    assert first == "전방에 주의 노면 주의하세요."

    manager.add_obstacle_event(device_id, "scooter")
    session.last_announced_obstacle_time = 0.0
    second = manager._pop_obstacle_text(session)
    assert second == "전방에 전동 킥보드 주의하세요."


def test_same_class_can_reannounce_after_suppress_window_expires():
    """억제 시간이 지나면 같은 클래스도 다시 안내할 수 있다."""
    manager = _new_manager()
    device_id = "test-suppress-expiry"
    session = manager._get_or_create_session(device_id)

    session.last_announced_class = "surface_hazard"  # caution/roadway 그룹 키
    session.last_announced_class_ts = time.time() - 31.0  # OBSTACLE_REPEAT_SUPPRESS_S(30s) 초과
    session.last_announced_obstacle_time = 0.0
    session.pending_obstacles.append({"class_name": "roadway", "ts": time.time()})

    text = manager._pop_obstacle_text(session)
    assert text == "전방에 차도 주의하세요."


def test_caution_roadway_share_surface_hazard_suppress_key():
    """caution 안내 후 roadway는 같은 surface_hazard 그룹으로 억제된다."""
    manager = _new_manager()
    device_id = "test-surface-group"
    session = manager._get_or_create_session(device_id)

    manager.add_obstacle_event(device_id, "caution")
    session.last_announced_obstacle_time = 0.0
    first = manager._pop_obstacle_text(session)
    assert first == "전방에 주의 노면 주의하세요."

    manager.add_obstacle_event(device_id, "roadway")
    session.last_announced_obstacle_time = 0.0
    second = manager._pop_obstacle_text(session)
    assert second == ""
