import time
import math

class NavigationFilter:
    """
    시각장애인의 청각 피로(Cognitive Overload)를 방지하기 위해
    네비게이션 음성 안내의 빈도와 복잡성을 정밀하게 조율하는 필터 클래스입니다.
    순차적 active 웨이포인트 추적 및 Heading(방향) 기반 경로 이탈 감지 기능이 내장되어 있습니다.
    """
    def __init__(self, silence_interval_sec=10.0):
        self.silence_interval_sec = silence_interval_sec
        self.last_announced_time = 0.0
        self.last_announced_text = ""
        # 이미 안내를 완료한 (지점_인덱스, 안내_단계)를 기록
        self.announced_cache = set()
        
        # 순차적 웨이포인트 추적을 위한 상태 변수
        self.active_waypoint_idx = None
        self.deviation_start_time = 0.0

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """두 좌표 간의 직선 거리(m) 계산"""
        R = 6371000  # 지구 반지름 (m)
        phi_1 = math.radians(lat1)
        phi_2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2.0)**2 + \
            math.cos(phi_1) * math.cos(phi_2) * \
            math.sin(delta_lambda / 2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        """좌표 1에서 좌표 2로의 방위각(0~360도) 계산"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(delta_lon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon_rad)
            
        bearing = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing) + 360) % 360
        return bearing_deg

    def is_actionable_waypoint(self, description, facility_type):
        """
        웨이포인트가 시각장애인에게 유의미한 행동/안내 지점인지 판단합니다.
        단순 직진 정보는 무시하고, 회전/방향전환/특수시설물이 있는 경우에만 발화합니다.
        """
        if facility_type in [2, 3, 4, 11, 12, 14, 15, 16]:  # 주요 보행 보조 시설물
            return True
            
        turn_keywords = ["회전", "꺾으세요", "오른쪽", "왼쪽", "방향", "진입", "도착", "출발", "횡단"]
        for kw in turn_keywords:
            if kw in description:
                return True
                
        return False

    def get_facility_name(self, facility_type):
        """시설물 타입 번호를 명확한 한국어 명칭으로 변환"""
        mapping = {
            2: "횡단보도",
            3: "육교",
            4: "지하도",
            11: "엘리베이터",
            12: "계단",
            14: "경사로",
            15: "에스컬레이터",
            16: "대형 출입구"
        }
        return mapping.get(facility_type, "")

    def filter_and_format(self, current_lat, current_lon, waypoints, current_heading=None):
        """
        사용자의 실시간 좌표와 방향(heading)을 받아 활성화된 웨이포인트와 비교하고,
        청각 마비를 방지하는 최적의 음성 멘트를 선별하여 반환합니다.
        """
        if not waypoints:
            return None
            
        current_time = time.time()
        
        # 1. 초기 활성 웨이포인트 탐색
        if self.active_waypoint_idx is None:
            # 시작 시점에서 가장 가까운 웨이포인트를 찾음
            closest_idx = 0
            min_dist = float('inf')
            for i, wp in enumerate(waypoints):
                dist = self.haversine_distance(current_lat, current_lon, wp["lat"], wp["lon"])
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            self.active_waypoint_idx = closest_idx

        # 2. 이미 지나쳤거나 의미 없는 웨이포인트 스킵 필터링
        while self.active_waypoint_idx < len(waypoints):
            wp = waypoints[self.active_waypoint_idx]
            dist = self.haversine_distance(current_lat, current_lon, wp["lat"], wp["lon"])
            
            # 15m 이내이고 비행동성 웨이포인트인 경우 자동 스킵
            if dist <= 15.0:
                description = wp.get("description", "")
                facility_type = wp.get("facility_type")
                is_actionable = self.is_actionable_waypoint(description, facility_type)
                
                # 안내할 가치가 없거나, 출발지 문구는 15m 내 도달 시 즉시 스킵
                if not is_actionable or (self.active_waypoint_idx == 0 and "출발" in description):
                    self.active_waypoint_idx += 1
                    continue
            break

        # 만약 목적지 끝에 도달했다면 종료
        if self.active_waypoint_idx >= len(waypoints):
            return None

        # 3. 현재 타겟팅 중인 활성 웨이포인트 추출
        target_wp = waypoints[self.active_waypoint_idx]
        wp_idx = target_wp.get("index", self.active_waypoint_idx)
        wp_lat = target_wp.get("lat")
        wp_lon = target_wp.get("lon")
        description = target_wp.get("description", "").strip()
        facility_type = target_wp.get("facility_type")
        
        dist = self.haversine_distance(current_lat, current_lon, wp_lat, wp_lon)
        target_bearing = self.calculate_bearing(current_lat, current_lon, wp_lat, wp_lon)

        # 4. 경로 이탈(Heading Deviation) 검사
        # 사용자가 타겟 웨이포인트를 향해 올바르게 걷고 있는지 확인 (방향차 45도 초과 감지)
        if current_heading is not None and dist > 20.0:  # 20m 이내에선 각도 변화가 급격하므로 제외
            heading_diff = abs(current_heading - target_bearing) % 360
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
                
            if heading_diff > 50.0:  # 50도 이상 어긋난 경우
                if self.deviation_start_time == 0.0:
                    self.deviation_start_time = current_time
                elif (current_time - self.deviation_start_time) >= 5.0:
                    # 5초 이상 지속적으로 잘못된 방향인 경우 경고 알림
                    self.deviation_start_time = current_time  # 쿨타임 재설정
                    deviation_text = "경로를 벗어났거나 반대 방향으로 걷고 있습니다. 원래 방향으로 돌아가세요."
                    return {
                        "text": deviation_text,
                        "is_danger": True,
                        "distance": dist,
                        "waypoint_index": wp_idx,
                        "type": "deviation_alert"
                    }
            else:
                self.deviation_start_time = 0.0

        # 5. 거리 기반 안내 단계 트리거 판단 (50m, 15m)
        target_stage = None
        announcement = ""
        
        facility_name = self.get_facility_name(facility_type)
        facility_str = f"앞에 {facility_name}가 있습니다. " if facility_name else ""
        
        # 50m 전 단계 안내
        if 40.0 < dist <= 55.0:
            target_stage = "50m"
            if facility_name:
                announcement = f"50미터 앞, {facility_name}가 있습니다."
            else:
                # 회전 등의 정보
                announcement = f"50미터 앞, {description}"
                
        # 15m 이하 도달 안내 (즉시 행동)
        elif dist <= 15.0:
            target_stage = "arrived"
            if facility_name:
                announcement = f"곧, {facility_name}가 있습니다. 주의하세요."
            else:
                announcement = f"곧, {description}"

        if not target_stage or not announcement:
            return None

        cache_key = (wp_idx, target_stage)

        # 6. 중복 알림 차단 필터
        if cache_key in self.announced_cache:
            return None

        # 7. 최소 무음 간격(silence_interval_sec) 제어 (15m 이하 긴급 도착 멘트는 즉시 출력)
        if target_stage != "arrived" and (current_time - self.last_announced_time) < self.silence_interval_sec:
            return None

        # 8. 동일 텍스트 연속 발화 차단
        if announcement == self.last_announced_text:
            return None

        # 모든 필터를 통과한 경우 상태 기록 및 이벤트 리턴
        self.announced_cache.add(cache_key)
        self.last_announced_time = current_time
        self.last_announced_text = announcement
        
        # 도착 멘트 송출 후 다음 웨이포인트로 포커스 스위칭 준비
        if target_stage == "arrived":
            self.active_waypoint_idx += 1

        is_danger = facility_type in [2, 3, 4, 12]  # 횡단보도, 육교, 지하도, 계단 등 위험할 수 있는 시설물
        
        return {
            "text": announcement,
            "is_danger": is_danger,
            "distance": dist,
            "waypoint_index": wp_idx,
            "target_bearing": target_bearing,
            "type": "guidance_audio"
        }
