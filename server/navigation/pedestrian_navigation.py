import json
import math
import os
import sys
import time
from contextlib import suppress

import requests
from dotenv import load_dotenv

# Reconfigure stdout and stdin for UTF-8 support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding != "utf-8":
    with suppress(AttributeError):
        sys.stdin.reconfigure(encoding="utf-8")

# 현재 디렉터리를 파이썬 경로에 추가하여 로컬 tts_engine 모듈을 안전하게 가져올 수 있도록 함
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from tts_engine import TTSEngine  # noqa: E402


# 환경 변수 로드 (.env 탐색 순서: 현재 폴더 -> 상위 폴더 -> 그 상위 폴더 -> 그 상위 폴더)
def load_env_file():
    curr = current_dir
    for _ in range(4):
        env_path = os.path.join(curr, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"[INFO] Environment variables loaded from: {env_path}")
            return
        curr = os.path.dirname(curr)
    load_dotenv()


load_env_file()


def search_poi(app_key, keyword, role_name="목적지"):
    """
    TMAP POI 검색 API를 호출하여 입력받은 명칭에 해당하는 위치들의 이름과 좌표를 가져옵니다.
    """
    print(f"DEBUG: keyword = '{keyword}'")
    url = "https://apis.openapi.sk.com/tmap/pois"
    params = {
        "version": 1,
        "searchKeyword": keyword,
        "count": 5,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "format": "json",
        "appKey": app_key,
    }
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pois = data.get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
            if not pois:
                print(f"[알림] '{keyword}'에 대한 검색 결과가 없습니다.")
                return None

            print(f"\n🔍 [{role_name}] '{keyword}' 검색 결과 (최대 5개):")
            for idx, poi in enumerate(pois):
                name = poi.get("name")
                upper_addr = poi.get("upperAddrName", "")
                middle_addr = poi.get("middleAddrName", "")
                lower_addr = poi.get("lowerAddrName", "")
                detail_addr = f"{upper_addr} {middle_addr} {lower_addr}".strip()
                print(f"  [{idx + 1}] {name} ({detail_addr})")

            # 사용자에게 선택 요청
            while True:
                try:
                    choice = input(
                        f"👉 원하는 {role_name} 번호를 선택하세요 (1~{len(pois)}): "
                    ).strip()
                    selected_idx = int(choice) - 1
                    if 0 <= selected_idx < len(pois):
                        selected_poi = pois[selected_idx]
                        return {
                            "name": selected_poi.get("name"),
                            "x": selected_poi.get("noorLon"),  # 경도
                            "y": selected_poi.get("noorLat"),  # 위도
                        }
                    else:
                        print(
                            f"범위를 벗어났습니다. 1부터 {len(pois)} 사이의 숫자를 입력해 주세요."
                        )
                except ValueError:
                    print("유효한 숫자를 입력해 주세요.")
        else:
            print(f"[오류] POI 검색 실패 (상태 코드: {response.status_code})")
            return None
    except Exception as e:
        print(f"[예외 발생] POI 검색 중 문제가 발생했습니다: {e}")
        return None


def fetch_pedestrian_route(app_key, start_poi, end_poi):
    """
    출발지 POI와 목적지 POI를 기반으로 TMAP 보행자 경로 안내 API를 호출합니다.
    """
    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json"
    headers = {"appKey": app_key, "Content-Type": "application/json"}
    payload = {
        "startX": start_poi["x"],
        "startY": start_poi["y"],
        "endX": end_poi["x"],
        "endY": end_poi["y"],
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "startName": start_poi["name"],
        "endName": end_poi["name"],
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[오류] 경로 안내 API 호출 실패 (상태 코드: {response.status_code})")
            print(f"상세 내용: {response.text}")
            return None
    except Exception as e:
        print(f"[예외 발생] 경로 API 통신 중 문제가 발생했습니다: {e}")
        return None


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    두 좌표 사이의 직선거리(m)를 Haversine 공식을 사용해 구합니다.
    """
    R = 6371000  # 지구 반지름 (m)
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi_1) * math.cos(phi_2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def simulate_realtime_walking(route_data):
    """
    실시간 보행 시뮬레이션:
    경로 선(LineString)을 따라 가상으로 전진하며,
    인접한 안내점(Point)과의 거리가 좁혀질 때 TTS 음성 메시지를 송출합니다.
    """
    if not route_data:
        print("[경고] 경로 데이터가 유효하지 않아 시뮬레이션을 시작할 수 없습니다.")
        return

    tts = TTSEngine()
    features = route_data.get("features", [])

    # 1. 경로 선 좌표(LineString) 수집하여 연속적인 보행 트랙 생성
    path_coordinates = []
    for feature in features:
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "LineString":
            # coordinates 형식: [[lon, lat], [lon, lat], ...]
            coords = geometry.get("coordinates", [])
            for coord in coords:
                # 중복 좌표 방지하며 트랙에 누적
                lon, lat = float(coord[0]), float(coord[1])
                if not path_coordinates or path_coordinates[-1] != (lat, lon):
                    path_coordinates.append((lat, lon))

    # 2. 안내점(Point) 목록을 수집하여 waypoint로 정비
    waypoints = []
    for feature in features:
        geometry = feature.get("geometry", {})
        if geometry.get("type") == "Point":
            coords = geometry.get("coordinates", [])
            lon, lat = float(coords[0]), float(coords[1])
            properties = feature.get("properties", {})
            waypoints.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "description": properties.get("description", "").strip(),
                    "facility_type": properties.get("facilityType"),  # 2:횡단보도, 3:육교 등
                    "announced_stages": set(),  # 중복 안내를 막기 위한 가드
                }
            )

    if not path_coordinates:
        print("[오류] 경로의 선(LineString) 데이터를 찾을 수 없어 보행을 재현할 수 없습니다.")
        return

    print("\n" + "=" * 60)
    print("▶ 보행자 실시간 길안내 시뮬레이션 시작 (초속 1.2m 가상 속도)")
    print("=" * 60 + "\n")

    total_points = len(path_coordinates)

    # 3. 가상 보행 루프 실행 (트랙의 좌표를 하나씩 밟고 이동)
    for i, current_pos in enumerate(path_coordinates):
        curr_lat, curr_lon = current_pos

        # 목적지까지의 총 잔여 거리 계산 (경로선을 따라 계산)
        remaining_route_distance = 0.0
        for idx in range(i, total_points - 1):
            p1 = path_coordinates[idx]
            p2 = path_coordinates[idx + 1]
            remaining_route_distance += haversine_distance(p1[0], p1[1], p2[0], p2[1])

        print(
            f"🚶 [보행 중] 현재 좌표: ({curr_lat:.5f}, {curr_lon:.5f}) | 목적지까지 남은 거리: {remaining_route_distance:.1f}m"
        )

        # 4. 각 웨이포인트(안내점)와의 거리 판단 및 발화 트리거
        for wp in waypoints:
            dist = haversine_distance(curr_lat, curr_lon, wp["lat"], wp["lon"])
            description = wp["description"]
            facility_type = wp["facility_type"]

            facility_str = ""
            if facility_type == 2:
                facility_str = "[횡단보도 구역] "
            elif facility_type == 3:
                facility_str = "[육교 구역] "
            elif facility_type == 4:
                facility_str = "[지하도 구역] "

            # 안내 거리에 가까워졌을 때 안내 (100m, 50m, 15m)
            # 100m 단계 안내
            if 80.0 < dist <= 100.0 and "100m" not in wp["announced_stages"]:
                wp["announced_stages"].add("100m")
                announcement = f"100미터 앞, {description}"
                print(f"📣 [TTS 안내 - 100m 전] {announcement}")
                tts.speak(announcement)

            # 50m 단계 안내
            elif 40.0 < dist <= 55.0 and "50m" not in wp["announced_stages"]:
                wp["announced_stages"].add("50m")
                announcement = f"50미터 앞, {facility_str}{description}"
                print(f"📣 [TTS 안내 - 50m 전] {announcement}")
                tts.speak(announcement, is_danger=(facility_type in [2, 3, 4]))

            # 15m 이하 도달 안내 (실제 행동 지시 단계)
            elif dist <= 15.0 and "arrived" not in wp["announced_stages"]:
                wp["announced_stages"].add("arrived")
                announcement = f"곧, {facility_str}{description}"
                print(f"📣 [TTS 안내 - 즉시 행동] {announcement}")
                # 횡단보도, 육교 등 특수 시설물에 즉시 접근했을 때는 강한 위험/알림음(Beep) 트리거
                tts.speak(announcement, is_danger=(facility_type in [2, 3, 4]))

        # 시뮬레이션 보행 속도 조절 (0.8초 간격으로 스텝 진행)
        time.sleep(0.8)

    print("\n" + "=" * 60)
    print("🏁 목적지에 무사히 도달했습니다. 실시간 보행 안내를 종료합니다.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    APP_KEY = os.getenv("TMAP_APP_KEY")

    if not APP_KEY or APP_KEY == "YOUR_TMAP_APP_KEY_HERE":
        print("\n[안내] 프로젝트 루트 디렉터리의 '.env' 파일 내")
        print("       'TMAP_APP_KEY=YOUR_TMAP_APP_KEY_HERE' 부분에 실제 API 키를 입력해 주세요.\n")
    else:
        print("==========================================================")
        print("   시각장애인 실시간 도보 내비게이션 시뮬레이터 (TMAP 연동)")
        print("==========================================================")

        # 1. 출발지 입력 및 좌표 검색
        start_input = input("📍 출발지를 입력하세요 (예: 서울역): ").strip()
        start_poi = search_poi(APP_KEY, start_input, role_name="출발지")

        if not start_poi:
            print("[오류] 출발지 좌표를 확보하지 못해 종료합니다.")
            sys.exit(1)

        # 2. 목적지 입력 및 좌표 검색
        end_input = input("\n🏁 목적지를 입력하세요 (예: 숭례문): ").strip()
        end_poi = search_poi(APP_KEY, end_input, role_name="목적지")

        if not end_poi:
            print("[오류] 목적지 좌표를 확보하지 못해 종료합니다.")
            sys.exit(1)

        print("\n[경로 탐색 시작]")
        print(f"  출발지: {start_poi['name']} ({start_poi['y']}, {start_poi['x']})")
        print(f"  목적지: {end_poi['name']} ({end_poi['y']}, {end_poi['x']})")

        # 3. 보행자 경로 조회
        route = fetch_pedestrian_route(APP_KEY, start_poi, end_poi)

        # 4. 실시간 가상 이동 및 음성 시뮬레이션
        if route:
            simulate_realtime_walking(route)
