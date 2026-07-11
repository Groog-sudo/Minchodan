import contextlib
import sys
import time
from typing import Any, Literal, Optional

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

try:
    # server.navigation 패키지 경유(예: detection/consumer.py, stt_to_llm_bridge.py)로
    # 임포트되는 경우
    from server.navigation.navigation_filter import NavigationFilter
except ImportError:
    # server/navigation/server.py를 독립 스크립트로 직접 실행하는 경우
    # (해당 스크립트가 자신의 디렉토리를 sys.path에 추가함)
    from navigation_filter import NavigationFilter


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

        # 네비게이션 동작 상태 기계 (IDLE: 꺼짐, WAITING_FOR_DESTINATION: 목적지 음성 대기, NAVIGATING: 안내 중)
        self.status: Literal["IDLE", "WAITING_FOR_DESTINATION", "NAVIGATING"] = "IDLE"

        # 자유 질의응답 모드 대기 플래그. status(네비게이션 상태)와 독립적으로 관리해
        # NAVIGATING 중에도 "질문할게" 후 자유 질문을 받을 수 있게 한다.
        self.awaiting_free_question: bool = False

        # 2026-07-10 추가: "길댕아" wake-word 이후 "길찾아줘"/"물어볼게" 중 무엇을
        # 고를지 대기하는 플래그. awaiting_free_question과 마찬가지로 status와 독립.
        self.awaiting_intent: bool = False

        # Redis Stream 등으로부터 수신된 미해결 장애물 이벤트 캐시
        self.pending_obstacles: list[dict[str, Any]] = []
        self.last_announced_obstacle_time: float = 0.0


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
        self._initialized: bool = True

    def _get_or_create_session(self, device_id: str) -> NavigationSession:
        if device_id not in self.sessions:
            self.sessions[device_id] = NavigationSession()
        return self.sessions[device_id]

    def set_status(
        self, device_id: str, status: Literal["IDLE", "WAITING_FOR_DESTINATION", "NAVIGATING"]
    ) -> None:
        session = self._get_or_create_session(device_id)
        session.status = status
        print(f"[NavigationManager] Status changed for '{device_id}' to: {status}")

    def get_status(self, device_id: str) -> str:
        session = self._get_or_create_session(device_id)
        return session.status

    def set_awaiting_question(self, device_id: str, waiting: bool) -> None:
        session = self._get_or_create_session(device_id)
        session.awaiting_free_question = waiting

    def is_awaiting_question(self, device_id: str) -> bool:
        session = self._get_or_create_session(device_id)
        return session.awaiting_free_question

    def set_awaiting_intent(self, device_id: str, waiting: bool) -> None:
        session = self._get_or_create_session(device_id)
        session.awaiting_intent = waiting

    def is_awaiting_intent(self, device_id: str) -> bool:
        session = self._get_or_create_session(device_id)
        return session.awaiting_intent

    def update_route(self, device_id: str, waypoints: list[dict[str, Any]]) -> None:
        """
        특정 디바이스에 새로운 경로 지점(Waypoints) 리스트를 등록합니다.
        """
        session = self._get_or_create_session(device_id)
        session.waypoints = waypoints
        session.nav_filter = NavigationFilter()  # 필터 캐시 초기화
        print(
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
        session = self._get_or_create_session(device_id)
        now = time.time()
        for obs in session.pending_obstacles:
            if obs["class_name"] == class_name and (now - obs["ts"]) < 3.0:
                return

        session.pending_obstacles.append({"class_name": class_name, "ts": now})
        print(
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
        """대기 중인 가장 최근 장애물 이벤트를 정제된 한국어 텍스트 경고로 변환하고 뺍니다."""
        now = time.time()
        session.pending_obstacles = [
            obs for obs in session.pending_obstacles if (now - obs["ts"]) < 5.0
        ]

        if not session.pending_obstacles:
            return ""

        target_obs = session.pending_obstacles.pop(0)
        class_name = target_obs["class_name"]

        korean_mapping = {
            "scooter": "전동 킥보드",
            "kickboard": "전동 킥보드",
            "bollard": "볼라드",
            "car": "차량",
            "motorcycle": "오토바이",
            "bicycle": "자전거",
            "person": "보행자",
            "pothole": "포트홀",
            "dog": "안내견",
        }
        class_ko = korean_mapping.get(class_name, class_name)

        if (now - session.last_announced_obstacle_time) >= 5.0:
            session.last_announced_obstacle_time = now
            return f"전방에 {class_ko} 주의하세요."
        return ""


# 전역 싱글톤 인스턴스 노출
nav_manager = NavigationManager()
