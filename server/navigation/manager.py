import contextlib
import logging
import sys
import time
from typing import Any, Literal, Optional

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

try:
    # server.navigation 패키지 경유(예: detection/consumer.py, stt_to_llm_bridge.py)로
    # 임포트되는 경우
    from server.navigation.navigation_filter import NavigationFilter
except ImportError:
    # server/navigation/server.py를 독립 스크립트로 직접 실행하는 경우
    # (해당 스크립트가 자신의 디렉토리를 sys.path에 추가함)
    from navigation_filter import NavigationFilter  # type: ignore[no-redef]

try:
    from server.detection.risk_rules import class_name_to_ko
except ImportError:
    # 독립 스크립트 실행 시 detection 패키지 경로가 없을 수 있어, 원문 그대로
    # 반환하는 폴백만 둔다(운영 배포는 항상 패키지 임포트 경로를 탄다).
    def class_name_to_ko(class_name: str) -> str:
        return class_name


# 2026-07-20 (실기기 필드 테스트): 노면 세그멘테이션 클래스 중 "정상"(안전) 클래스는
# 장애물이 아니므로 내비게이션 장애물 안내 대상에서 제외한다. 위험 노면(caution/roadway)만
# server/detection/consumer.py의 SPEECH_SURFACE_HAZARD_CLASSES와 동일하게 유지한다.
NAV_OBSTACLE_EXCLUDED_CLASSES = frozenset({"sidewalk_normal", "braille_normal"})

# 같은 장애물 클래스가 계속 재탐지돼도 한 번 안내한 뒤에는 이 시간(초) 동안 같은
# 클래스 재안내를 억제한다("같은 노면이면 한 번만 안내" 실기기 피드백 대응). 다른
# 클래스가 끼어들면 억제와 무관하게 즉시 안내한다.
# 2026-07-20: caution/roadway는 surface_hazard 그룹으로 묶어 교차 재안내를 막는다.
OBSTACLE_REPEAT_SUPPRESS_S = 30.0
NAV_SURFACE_HAZARD_SUPPRESS_KEY = "surface_hazard"
NAV_SURFACE_HAZARD_CLASSES = frozenset({"caution", "roadway"})


def _nav_obstacle_suppress_key(class_name: str) -> str:
    """내비게이션 장애물 재안내 억제 키. 위험 노면은 단일 그룹."""
    if class_name in NAV_SURFACE_HAZARD_CLASSES:
        return NAV_SURFACE_HAZARD_SUPPRESS_KEY
    return class_name


class NavigationSession:
    """
    개별 디바이스 세션별 네비게이션 상태 및 캐시를 저장합니다.
    """

    def __init__(self):
        self.waypoints: list[dict[str, Any]] = []
        self.nav_filter: NavigationFilter = NavigationFilter()
        self.lat: float | None = None
        self.lon: float | None = None
        self.heading: float | None = None

        # 네비게이션 동작 상태 기계 (IDLE: 꺼짐, WAITING_FOR_DESTINATION: 목적지 음성 대기,
        # WAITING_FOR_POI_CONFIRMATION: 동명 POI 후보 중 선택 대기(2026-07-20 P0 신설),
        # NAVIGATING: 안내 중)
        self.status: Literal[
            "IDLE", "WAITING_FOR_DESTINATION", "WAITING_FOR_POI_CONFIRMATION", "NAVIGATING"
        ] = "IDLE"

        # 자유 질의응답 모드 대기 플래그. status(네비게이션 상태)와 독립적으로 관리해
        # NAVIGATING 중에도 "질문할게" 후 자유 질문을 받을 수 있게 한다.
        self.awaiting_free_question: bool = False

        # 2026-07-10 추가: "길댕아" wake-word 이후 "길찾아줘"/"물어볼게" 중 무엇을
        # 고를지 대기하는 플래그. awaiting_free_question과 마찬가지로 status와 독립.
        self.awaiting_intent: bool = False

        # 클라이언트 "탐지 시작/중지" 토글. 기본 False(앱 기본 OFF와 동일).
        # OFF면 STT 일반 발화를 장애물 오케스트레이터가 아니라 자유 질문으로 처리한다.
        self.detection_enabled: bool = False

        # Redis Stream 등으로부터 수신된 미해결 장애물 이벤트 캐시
        self.pending_obstacles: list[dict[str, Any]] = []
        self.last_announced_obstacle_time: float = 0.0
        # 2026-07-20: 마지막으로 실제 안내한 장애물 클래스와 그 시각. 같은 클래스가
        # 연속 재탐지돼도 OBSTACLE_REPEAT_SUPPRESS_S 동안은 재안내하지 않기 위함.
        self.last_announced_class: str | None = None
        self.last_announced_class_ts: float = 0.0

        # 2026-07-20 (회귀 분석 보고서 P0 - 사용자 확인): 동명 POI 후보가 모호할 때
        # WAITING_FOR_POI_CONFIRMATION 동안 다음 발화(번호 선택)를 해석하기 위해
        # 후보 목록을 임시 보관한다. 확정되거나 취소되면 None으로 비운다.
        self.pending_poi_candidates: list[dict[str, Any]] | None = None


class NavigationManager:
    """
    디바이스별 세션을 통합 관리하고,
    객체 탐지 결과와 길안내 멘트를 조화롭게 융합(Integration)해 주는 싱글톤 매니저 클래스입니다.
    """

    _instance: Optional["NavigationManager"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.sessions: dict[str, NavigationSession] = {}
        # 콘솔 브로드캐스트(_broadcast_nav_change)의 fire-and-forget 태스크 참조를
        # 들고 있지 않으면 GC가 실행 도중 태스크를 수거할 수 있다(server/detection/
        # consumer.py의 _log_tasks와 동일 패턴).
        self._background_tasks: set[Any] = set()
        self._initialized: bool = True

    def _get_or_create_session(self, device_id: str) -> NavigationSession:
        if device_id not in self.sessions:
            self.sessions[device_id] = NavigationSession()
        return self.sessions[device_id]

    def _broadcast_nav_change(self, device_id: str, session: NavigationSession) -> None:
        try:
            import asyncio

            from server.mcp.manager import mcp_manager

            task = asyncio.create_task(
                mcp_manager.broadcast_event(
                    "llm_status",
                    {
                        "device_id": device_id,
                        "navigation_status": session.status,
                        "awaiting_free_question": session.awaiting_free_question,
                        "awaiting_intent": session.awaiting_intent,
                    },
                )
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        except Exception as e:
            logger.error(f"[NavigationManager] Broadcast failed: {e}")

    def set_status(
        self,
        device_id: str,
        status: Literal[
            "IDLE", "WAITING_FOR_DESTINATION", "WAITING_FOR_POI_CONFIRMATION", "NAVIGATING"
        ],
    ) -> None:
        session = self._get_or_create_session(device_id)
        session.status = status
        if status != "WAITING_FOR_POI_CONFIRMATION":
            session.pending_poi_candidates = None
        logger.info(f"[NavigationManager] Status changed for '{device_id}' to: {status}")
        self._broadcast_nav_change(device_id, session)

    def get_status(self, device_id: str) -> str:
        session = self._get_or_create_session(device_id)
        return session.status

    def set_pending_poi_candidates(
        self, device_id: str, candidates: list[dict[str, Any]] | None
    ) -> None:
        """동명 POI 확인 대기 후보 목록을 저장/해제한다."""
        session = self._get_or_create_session(device_id)
        session.pending_poi_candidates = candidates

    def get_pending_poi_candidates(self, device_id: str) -> list[dict[str, Any]] | None:
        session = self._get_or_create_session(device_id)
        return session.pending_poi_candidates

    def set_awaiting_question(self, device_id: str, waiting: bool) -> None:
        session = self._get_or_create_session(device_id)
        session.awaiting_free_question = waiting
        self._broadcast_nav_change(device_id, session)

    def is_awaiting_question(self, device_id: str) -> bool:
        session = self._get_or_create_session(device_id)
        return session.awaiting_free_question

    def set_awaiting_intent(self, device_id: str, waiting: bool) -> None:
        session = self._get_or_create_session(device_id)
        session.awaiting_intent = waiting
        self._broadcast_nav_change(device_id, session)

    def is_awaiting_intent(self, device_id: str) -> bool:
        session = self._get_or_create_session(device_id)
        return session.awaiting_intent

    def set_detection_enabled(self, device_id: str, enabled: bool) -> None:
        """클라이언트 탐지 토글 반영.

        OFF로 전환 시 목적지/인텐트 대기를 풀어, 탐지 끄고 바로 질문해도
        네비 목적지 파싱·장애물 안내로 새지 않게 한다(2026-07-13 실측).
        NAVIGATING(길안내 중)은 GPS 턴바이턴을 위해 유지한다.
        """
        session = self._get_or_create_session(device_id)
        session.detection_enabled = bool(enabled)
        if not enabled:
            if session.status == "WAITING_FOR_DESTINATION":
                session.status = "IDLE"
            session.awaiting_intent = False
            logger.info(
                f"[NavigationManager] detection_enabled=False for '{device_id}' "
                f"(cleared destination/intent wait, status={session.status})"
            )
        else:
            logger.info(f"[NavigationManager] detection_enabled=True for '{device_id}'")
        self._broadcast_nav_change(device_id, session)

    def is_detection_enabled(self, device_id: str) -> bool:
        session = self._get_or_create_session(device_id)
        return session.detection_enabled

    def update_route(self, device_id: str, waypoints: list[dict[str, Any]]) -> None:
        """
        특정 디바이스에 새로운 경로 지점(Waypoints) 리스트를 등록합니다.
        """
        session = self._get_or_create_session(device_id)
        session.waypoints = waypoints
        session.nav_filter = NavigationFilter()  # 필터 캐시 초기화
        logger.info(
            f"[NavigationManager] Route updated for device '{device_id}', waypoints={len(waypoints)}"
        )

    def update_gps(self, device_id: str, lat: float, lon: float, heading: float | None) -> None:
        """
        사용자의 실시간 GPS 좌표 및 방위각 데이터를 업데이트합니다.
        """
        session = self._get_or_create_session(device_id)
        session.lat = lat
        session.lon = lon
        session.heading = heading

    def add_obstacle_event(self, device_id: str, class_name: str) -> None:
        """
        Redis Stream 등을 통해 기존 Minchodan 서버(8000포트)로부터
        전달받은 실시간 장애물 탐지 이벤트를 세션 캐시에 추가합니다.
        """
        # 2026-07-20: "sidewalk_normal" 등 안전 노면 클래스는 애초에 장애물이 아니므로
        # 캐시에 넣지도 않는다(실기기 필드 테스트: "전방에 sidewalk_normal 주의하세요"
        # 처럼 안전한 노면을 경고문으로 안내하던 결함).
        if class_name in NAV_OBSTACLE_EXCLUDED_CLASSES:
            return

        session = self._get_or_create_session(device_id)
        now = time.time()
        for obs in session.pending_obstacles:
            if obs["class_name"] == class_name and (now - obs["ts"]) < 3.0:
                return

        session.pending_obstacles.append({"class_name": class_name, "ts": now})
        logger.info(
            f"[NavigationManager] Obstacle event cached: device='{device_id}', class='{class_name}'"
        )

    def get_combined_guidance(self, device_id: str) -> dict[str, Any] | None:
        """
        네비게이션 필터 멘트와 수신된 장애물 탐지 이벤트를 조합하여,
        하나의 가이드 멘트로 융합(Fusion)한 결과를 반환합니다.
        """
        if device_id not in self.sessions:
            return None

        session = self.sessions[device_id]

        # NAVIGATING 상태가 아닌 경우(길안내 서비스가 꺼진 경우)에는 길안내 피드백을 건너뜁니다.
        if session.status != "NAVIGATING" or session.lat is None or session.lon is None:
            # 길안내는 꺼져 있으나, 수신된 YOLO 장애물 경고 단독 처리는 계속 지원합니다.
            obstacle_text = self._pop_obstacle_text(session)
            if obstacle_text:
                return {
                    "type": "guidance_audio",
                    "text": obstacle_text,
                    "is_danger": True,
                    "active_waypoint_idx": 0,
                }
            return None

        # 1. TMAP 경로 필터 처리로 길안내 멘트 획득
        guidance_event = session.nav_filter.filter_and_format(
            session.lat, session.lon, session.waypoints, current_heading=session.heading
        )

        # 2. 장애물 안내 멘트 획득
        obstacle_text = self._pop_obstacle_text(session)
        is_obstacle_danger = bool(obstacle_text)

        # 3. 길안내 정보와 장애물 정보의 조화로운 융합
        if guidance_event:
            combined_text = guidance_event["text"]
            if obstacle_text:
                combined_text = f"{combined_text} 그리고 {obstacle_text}"

            return {
                "type": guidance_event.get("type", "guidance_audio"),
                "text": combined_text,
                "is_danger": guidance_event["is_danger"] or is_obstacle_danger,
                "active_waypoint_idx": session.nav_filter.active_waypoint_idx,
            }
        elif obstacle_text:
            return {
                "type": "guidance_audio",
                "text": obstacle_text,
                "is_danger": is_obstacle_danger,
                "active_waypoint_idx": session.nav_filter.active_waypoint_idx,
            }

        return None

    def _pop_obstacle_text(self, session: NavigationSession) -> str:
        """대기 중인 장애물 이벤트를 정제된 한국어 텍스트 경고로 변환하고 뺍니다.

        2026-07-20 실기기 필드 테스트 피드백 2건 수정:
        (1) 클래스명을 자체 축약 매핑(9종만 커버) 대신 SSOT `class_name_to_ko`
            (29+4클래스 전체 커버)로 번역해 "sidewalk_normal" 같은 원문 클래스명이
            그대로 음성 안내에 새던 결함을 해소한다.
        (2) 같은 클래스가 계속 재탐지돼도 큐의 맨 앞(가장 오래된 것)을 무조건 꺼내
            5초 전역 쿨다운으로만 반복을 막던 방식이, 연속 재탐지되는 하나의 노면을
            사실상 몇 초마다 계속 재안내하는 결과("같은 노면은 한 번만" 설계 위반)를
            낳았다. 이제 같은 클래스 재안내는 OBSTACLE_REPEAT_SUPPRESS_S 동안
            억제하고, 그사이 다른 클래스가 대기 중이면 그것을 우선 안내한다.
        """
        now = time.time()
        session.pending_obstacles = [
            obs for obs in session.pending_obstacles if (now - obs["ts"]) < 5.0
        ]
        if not session.pending_obstacles:
            return ""
        if (now - session.last_announced_obstacle_time) < 5.0:
            return ""

        for idx, obs in enumerate(session.pending_obstacles):
            class_name = obs["class_name"]
            suppress_key = _nav_obstacle_suppress_key(class_name)
            last_key = session.last_announced_class
            if last_key in NAV_SURFACE_HAZARD_CLASSES:
                last_key = NAV_SURFACE_HAZARD_SUPPRESS_KEY
            is_repeat_suppressed = (
                suppress_key == last_key
                and (now - session.last_announced_class_ts) < OBSTACLE_REPEAT_SUPPRESS_S
            )
            if is_repeat_suppressed:
                continue

            session.pending_obstacles.pop(idx)
            class_ko = class_name_to_ko(class_name)
            session.last_announced_obstacle_time = now
            # 억제 키로 저장해 caution↔roadway 교차 재안내를 막는다.
            session.last_announced_class = suppress_key
            session.last_announced_class_ts = now
            return f"전방에 {class_ko} 주의하세요."

        return ""


# 전역 싱글톤 인스턴스 노출
nav_manager = NavigationManager()
