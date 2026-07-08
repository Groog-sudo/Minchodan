# -*- coding: utf-8 -*-
import sys
import contextlib
import time
from typing import Dict, List, Optional, Any

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from navigation_filter import NavigationFilter

class NavigationSession:
    """
    개별 디바이스 세션별 네비게이션 상태 및 캐시를 저장합니다.
    """
    def __init__(self):
        self.waypoints: List[Dict[str, Any]] = []
        self.nav_filter: NavigationFilter = NavigationFilter()
        self.lat: Optional[float] = None
        self.lon: Optional[float] = None
        self.heading: Optional[float] = None
        
        # Redis Stream 등으로부터 수신된 미해결 장애물 이벤트 캐시
        # 형식: {"class_name": "kickboard", "ts": 1719216000000}
        self.pending_obstacles: List[Dict[str, Any]] = []
        self.last_announced_obstacle_time: float = 0.0

class NavigationManager:
    """
    디바이스별 세션을 통합 관리하고, 
    객체 탐지 결과와 길안내 멘트를 조화롭게 융합(Integration)해 주는 싱글톤 매니저 클래스입니다.
    """
    _instance: Optional['NavigationManager'] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(NavigationManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 이미 초기화된 경우 스킵
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.sessions: Dict[str, NavigationSession] = {}
        self._initialized: bool = True

    def _get_or_create_session(self, device_id: str) -> NavigationSession:
        if device_id not in self.sessions:
            self.sessions[device_id] = NavigationSession()
        return self.sessions[device_id]

    def update_route(self, device_id: str, waypoints: List[Dict[str, Any]]) -> None:
        """
        특정 디바이스에 새로운 경로 지점(Waypoints) 리스트를 등록합니다.
        """
        session = self._get_or_create_session(device_id)
        session.waypoints = waypoints
        session.nav_filter = NavigationFilter()  # 필터 캐시 초기화
        print(f"[NavigationManager] Route updated for device '{device_id}', waypoints={len(waypoints)}")

    def update_gps(self, device_id: str, lat: float, lon: float, heading: Optional[float]) -> None:
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
        # 중복 유입 방지 가드: 최근 3초 내에 동일 장애물이 이미 들어가 있다면 스킵
        now = time.time()
        for obs in session.pending_obstacles:
            if obs["class_name"] == class_name and (now - obs["ts"]) < 3.0:
                return
        
        session.pending_obstacles.append({
            "class_name": class_name,
            "ts": now
        })
        print(f"[NavigationManager] Obstacle event cached: device='{device_id}', class='{class_name}'")

    def get_combined_guidance(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        네비게이션 필터 멘트와 수신된 장애물 탐지 이벤트를 조합하여,
        하나의 가이드 멘트로 융합(Fusion)한 결과를 반환합니다.
        """
        if device_id not in self.sessions:
            return None

        session = self.sessions[device_id]
        if session.lat is None or session.lon is None:
            return None

        # 1. TMAP 경로 필터 처리로 길안내 멘트 획득
        guidance_event = session.nav_filter.filter_and_format(
            session.lat, session.lon, session.waypoints, current_heading=session.heading
        )

        now = time.time()
        # 유효 기간이 지난(5초 초과) 장애물 정보 필터링
        session.pending_obstacles = [
            obs for obs in session.pending_obstacles if (now - obs["ts"]) < 5.0
        ]

        # 2. 장애물 안내 멘트 조립
        obstacle_text = ""
        is_obstacle_danger = False
        
        if session.pending_obstacles:
            # 가장 신선하고 중요한 첫 번째 장애물 처리
            target_obs = session.pending_obstacles.pop(0)
            class_name = target_obs["class_name"]
            
            # 한국어 장애물 명칭 매핑
            korean_mapping = {
                "scooter": "전동 킥보드",
                "kickboard": "전동 킥보드",
                "bollard": "볼라드",
                "car": "차량",
                "motorcycle": "오토바이",
                "bicycle": "자전거",
                "person": "보행자",
                "pothole": "포트홀",
                "dog": "안내견"
            }
            class_ko = korean_mapping.get(class_name, class_name)
            
            # 장애물 발화 쿨타임 (5초 내에 장애물 연속 발화 억제)
            if (now - session.last_announced_obstacle_time) >= 5.0:
                obstacle_text = f"전방에 {class_ko} 주의하세요."
                is_obstacle_danger = True
                session.last_announced_obstacle_time = now

        # 3. 길안내 정보와 장애물 정보의 조화로운 융합(Integration)
        if guidance_event:
            # 길안내 이벤트와 장애물 이벤트가 동시에 활성화된 경우 문장 결합
            combined_text = guidance_event["text"]
            if obstacle_text:
                combined_text = f"{combined_text} 그리고 {obstacle_text}"
            
            return {
                "type": guidance_event.get("type", "guidance_audio"),
                "text": combined_text,
                "is_danger": guidance_event["is_danger"] or is_obstacle_danger,
                "active_waypoint_idx": session.nav_filter.active_waypoint_idx
            }
        elif obstacle_text:
            # 장애물 단독 경고인 경우
            return {
                "type": "guidance_audio",
                "text": obstacle_text,
                "is_danger": is_obstacle_danger,
                "active_waypoint_idx": session.nav_filter.active_waypoint_idx
            }

        return None

# 전역 싱글톤 인스턴스 노출
nav_manager = NavigationManager()
