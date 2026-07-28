import asyncio
import contextlib
import json
import logging
import math
import os
import sys
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# 현재 디렉터리를 path에 추가하여 로컬 모듈(navigation_filter, manager)을 안전하게 임포트
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


# 환경 변수 로드 (.env 탐색 순서: 현재 폴더 -> 상위 폴더 -> 그 상위 폴더 -> 그 상위 폴더)
def load_env_file():
    curr = current_dir
    for _ in range(4):
        env_path = os.path.join(curr, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info(f"Environment variables loaded from: {env_path}")
            return
        curr = os.path.dirname(curr)
    load_dotenv()


load_env_file()
APP_KEY = (os.getenv("TMAP_APP_KEY") or os.getenv("TMAP_API_KEY") or "").strip()

# 키 자리표시자 목록. 실제 키가 아닌데도 길이만 충분해 통과하던 값을 명시적으로 차단한다.
PLACEHOLDER_APP_KEYS = frozenset({"YOUR_TMAP_APP_KEY_HERE", "DUMMY_TMAP_KEY"})

# 2026-07-28: 시연용 가상 경로는 명시적 opt-in에서만 허용한다(회귀 분석 보고서 §564).
# 기본값은 fail-closed이며, 이 플래그가 켜져도 "키 미설정" 상황에서만 가상 경로를 만든다.
# 유효한 키로 호출했다가 실패한 경우는 어떤 설정에서도 가상 경로를 반환하지 않는다.
NAV_MOCK_ROUTE_ENABLED = os.getenv("NAV_MOCK_ROUTE", "0").strip().lower() in {"1", "true", "yes"}


def _has_valid_app_key() -> bool:
    """TMAP 호출에 사용할 수 있는 실제 키가 설정되어 있는지 판정한다."""
    key = (APP_KEY or "").strip()
    return bool(key) and key not in PLACEHOLDER_APP_KEYS


try:
    from server.navigation.manager import nav_manager
except ImportError:
    # 이 파일을 독립 스크립트로 직접 실행하는 경우
    # (모듈 상단에서 자신의 디렉토리를 sys.path에 추가함)
    from manager import nav_manager  # type: ignore[no-redef]


async def redis_stream_listener():
    """
    기존 Minchodan 서버(8000포트)가 발행하는 Redis Stream(risk.events)을 구독하여
    실시간 장애물 탐지 이벤트를 비침습적으로 가로채고 NavigationManager에 공급합니다.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    logger.info("[NAV REDIS] Connecting to configured Redis stream subscription...")

    r = None
    while True:
        try:
            if r is None:
                r = aioredis.from_url(redis_url, decode_responses=True)

            stream_name = "risk.events"
            streams = {stream_name: "$"}
            logger.info(f"[NAV REDIS] Listening to stream '{stream_name}'...")

            while True:
                events = await r.xread(streams, count=10, block=1000)
                if events:
                    for _, messages in events:
                        for msg_id, payload in messages:
                            class_name = payload.get("class_name")
                            if class_name:
                                # 모든 활성화된 네비게이션 사용자 세션에 장애물 이벤트를 전파
                                for dev_id in list(nav_manager.sessions.keys()):
                                    nav_manager.add_obstacle_event(dev_id, class_name)
                            streams[stream_name] = msg_id
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[NAV REDIS] Error reading from stream: {e}. Retrying in 3 seconds...")
            r = None
            await asyncio.sleep(3.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Redis Stream 리스너 기동
    listener_task = asyncio.create_task(redis_stream_listener())
    yield
    # Shutdown: 리스너 태스크 안전 종료
    listener_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await listener_task


app = FastAPI(title="VIP Assistant AI Navigation-only Simulator", lifespan=lifespan)


def helper_search_poi(keyword):
    """TMAP POI API를 사용하여 검색어에 대한 위경도(가장 첫 번째 매칭 결과)를 조회합니다."""
    # 만약 입력값이 "위도, 경도" 형태라면 검색 없이 즉시 반환
    try:
        parts = [p.strip() for p in keyword.split(",")]
        if len(parts) == 2:
            lat = float(parts[0])
            lon = float(parts[1])
            return {"name": "내 실시간 위치", "x": str(lon), "y": str(lat)}
    except ValueError:
        pass

    if not _has_valid_app_key():
        # 2026-07-20 (회귀 분석 보고서 P0 - fail-closed): 고정 가상 좌표(126.8722/
        # 37.4590) 성공 처리를 제거했다. docs/ops/environment_variables.md와
        # .env.example이 이미 "키 미설정 시 기능 비활성화"를 명시하고 있었는데,
        # 이전 코드는 문서와 반대로 항상 성공 처리해 어떤 목적지를 말해도 같은
        # 위치 부근으로 경로가 생성될 수 있었다.
        logger.warning("[TMAP] API Key가 유효하지 않아 목적지 검색을 비활성화합니다.")
        return None

    url = "https://apis.openapi.sk.com/tmap/pois"
    params = {
        "version": 1,
        "searchKeyword": keyword,
        "count": 1,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "format": "json",
        "appKey": APP_KEY,
    }
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            pois = response.json().get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
            if pois:
                return {
                    "name": pois[0].get("name"),
                    "x": pois[0].get("noorLon"),
                    "y": pois[0].get("noorLat"),
                }
        return None
    except Exception as e:
        logger.error(f"[TMAP] POI helper exception: {e}")
        return None


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 대권거리(직선거리, 미터)를 계산한다."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def helper_search_nearest_poi(keyword: str, center_lat: float, center_lon: float, count: int = 5):
    """TMAP POI 검색 결과 후보 중 center_lat/center_lon에서 가장 가까운 POI를 계산해 반환한다.

    helper_search_poi(count=1)는 T맵 relevance 기준 최상위 1건만 반환해 "가장 가까운"을
    보장하지 못한다. 여러 후보(count)를 받아 직접 거리 계산 후 최소값을 골라야
    "가까운 지하철역이 어디야" 같은 근접 질의에 정확히 답할 수 있다.
    """
    if not _has_valid_app_key():
        # 2026-07-20 (회귀 분석 보고서 P0 - fail-closed): 가상 인접 목적지 성공
        # 처리를 제거했다(위 helper_search_poi와 동일 이유).
        logger.warning("[TMAP] API Key가 유효하지 않아 인접 목적지 검색을 비활성화합니다.")
        return None

    url = "https://apis.openapi.sk.com/tmap/pois"
    params = {
        "version": 1,
        "searchKeyword": keyword,
        "count": count,
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "format": "json",
        "appKey": APP_KEY,
        "centerLon": center_lon,
        "centerLat": center_lat,
    }
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        pois = response.json().get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
        if not pois:
            return None

        nearest = None
        nearest_dist = None
        for poi in pois:
            try:
                poi_lat = float(poi.get("noorLat"))
                poi_lon = float(poi.get("noorLon"))
            except (TypeError, ValueError):
                continue
            dist = _haversine_distance_m(center_lat, center_lon, poi_lat, poi_lon)
            if nearest_dist is None or dist < nearest_dist:
                nearest = poi
                nearest_dist = dist

        if nearest is None:
            return None
        return {
            "name": nearest.get("name"),
            "x": nearest.get("noorLon"),
            "y": nearest.get("noorLat"),
            "distance_m": nearest_dist,
        }
    except Exception as e:
        logger.error(f"[TMAP] Nearest POI helper exception: {e}")
        return None


# 2026-07-20 (회귀 분석 보고서 P0 확정 결함 3): 동명 POI 모호성 판단 임계값(미터).
# 최상위 후보와 동일 이름의 차상위 후보 간 거리 차가 이 값보다 작으면 거리만으로
# 자신 있게 고를 수 없다고 보고 사용자 확인을 요구한다.
POI_AMBIGUITY_DISTANCE_GAP_M = 2000.0


def helper_resolve_destination_poi(
    keyword: str, center_lat: float, center_lon: float, count: int = 5
) -> dict | None:
    """목적지 설정 전용 POI 해석기.

    `helper_search_poi(count=1, pois[0] 고정)`는 현재 위치·주소 확인 없이 TMAP
    relevance 1위를 무조건 확정해, 동명 지점이 여러 지역에 있을 때 엉뚱한 곳으로
    안내될 수 있었다(회귀 분석 보고서 §6.4). 여러 후보를 받아 (1) 정확 이름 일치,
    (2) 현재 위치에서의 거리 순으로 점수화하고, 동명 후보 간 거리 우위가 불분명하면
    `ambiguous=True`로 표시해 호출측이 사용자 확인을 거치도록 신호한다.

    Returns:
        {
            "best": {"name", "x", "y", "distance_m"},       # 최상위 후보
            "candidates": [{"name", "x", "y", "distance_m"}, ...],  # 점수순, 최대 count개
            "ambiguous": bool,
        }
        검색 결과가 없거나 API 실패 시 None.
    """
    if not _has_valid_app_key():
        if NAV_MOCK_ROUTE_ENABLED:
            logger.warning(
                "[TMAP] API Key 미설정 + NAV_MOCK_ROUTE=1: 가상 POI로 폴백합니다(시연 전용)."
            )
            mock_best = {"name": keyword, "x": "127.0380", "y": "37.5010", "distance_m": 250.0}
            return {"best": mock_best, "candidates": [mock_best], "ambiguous": False}
        logger.warning("[TMAP] API Key가 유효하지 않아 목적지를 해석할 수 없습니다.")
        return None

    url = "https://apis.openapi.sk.com/tmap/pois"
    params = {
        "version": 1,
        "searchKeyword": keyword,
        "count": max(count, 5),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
        "format": "json",
        "appKey": APP_KEY,
        "centerLon": center_lon,
        "centerLat": center_lat,
    }
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            # 유효한 키로 호출했는데 실패한 경우다. 가상 좌표로 성공 처리하면 사용자가
            # 실재하지 않는 목적지로 안내받게 되므로 fail-closed를 유지한다.
            logger.warning(f"[TMAP] POI HTTP {response.status_code}: 목적지 해석을 중단합니다.")
            return None
        pois = response.json().get("searchPoiInfo", {}).get("pois", {}).get("poi", [])
        if not pois:
            return None

        scored = []
        for poi in pois:
            name = poi.get("name")
            try:
                poi_lat = float(poi.get("noorLat"))
                poi_lon = float(poi.get("noorLon"))
            except (TypeError, ValueError):
                continue
            dist = _haversine_distance_m(center_lat, center_lon, poi_lat, poi_lon)
            scored.append(
                {
                    "name": name,
                    "x": poi.get("noorLon"),
                    "y": poi.get("noorLat"),
                    "distance_m": dist,
                    "_exact": (name or "").strip() == keyword.strip(),
                }
            )
        if not scored:
            return None

        # 정확 이름 일치를 최우선으로, 그 다음은 현재 위치에서 가까운 순으로 정렬.
        scored.sort(key=lambda c: (0 if c["_exact"] else 1, c["distance_m"]))
        best = scored[0]

        ambiguous = False
        same_name_others = [c for c in scored[1:] if c["name"] == best["name"]]
        if same_name_others:
            nearest_gap = min(c["distance_m"] for c in same_name_others) - best["distance_m"]
            if nearest_gap < POI_AMBIGUITY_DISTANCE_GAP_M:
                ambiguous = True

        for c in scored:
            c.pop("_exact", None)

        return {"best": best, "candidates": scored[:count], "ambiguous": ambiguous}
    except Exception as e:
        logger.error(f"[TMAP] Destination POI resolver exception: {e}")
        return None


def helper_fetch_route(start_poi, end_poi):
    """TMAP 보행자 경로 API를 호출해 경로 GeoJSON을 가져옵니다."""

    def get_mock_route():
        sx, sy = float(start_poi.get("x", 127.0359)), float(start_poi.get("y", 37.4995))
        ex, ey = float(end_poi.get("x", 127.0380)), float(end_poi.get("y", 37.5010))
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [sx, sy]},
                    "properties": {
                        "name": start_poi.get("name", "출발지"),
                        "description": "출발지입니다. 직진하세요.",
                        "turnType": 200,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [(sx + ex) / 2, (sy + ey) / 2]},
                    "properties": {
                        "name": "중간 경유지",
                        "description": "전방 50m 우회전입니다.",
                        "turnType": 12,
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [ex, ey]},
                    "properties": {
                        "name": end_poi.get("name", "목적지"),
                        "description": "목적지 부근에 도착했습니다.",
                        "turnType": 201,
                    },
                },
            ],
        }

    if not _has_valid_app_key():
        if NAV_MOCK_ROUTE_ENABLED:
            logger.warning("[TMAP] API Key 미설정 + NAV_MOCK_ROUTE=1: 가상 경로 사용(시연 전용).")
            return get_mock_route()
        # 2026-07-20 (회귀 분석 보고서 P0 - fail-closed): 가상 경로를 성공으로 처리하면
        # 사용자가 실재하지 않는 회전 안내를 듣게 된다. 기본값은 기능 비활성화다.
        logger.warning("[TMAP] API Key가 유효하지 않아 경로 조회를 비활성화합니다.")
        return None

    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json"
    headers = {"appKey": APP_KEY, "Content-Type": "application/json"}
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
        # 유효한 키의 API 실패는 가상 경로로 덮지 않는다(위 fail-closed와 동일 이유).
        logger.warning(f"[TMAP] Route HTTP {response.status_code}: 경로 조회를 중단합니다.")
        return None
    except Exception as e:
        logger.error(f"[TMAP] Route fetch helper exception: {e}")
        return None


# index.html 로드 경로 지정
INDEX_PATH = os.path.join(current_dir, "index.html")


@app.get("/")
async def get_index():
    if not os.path.exists(INDEX_PATH):
        return HTMLResponse("index.html not found.", status_code=404)
    with open(INDEX_PATH, encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[SERVER] Navigation WebSocket connection accepted.")

    # 길찾기 세션 상태 변수
    session_route_data = None
    session_waypoints = []
    device_id = "default_device"  # 시뮬레이터 단일 사용자 디바이스 식별자

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # 1. 목적지 검색 및 경로 수립 요청
            if message.get("type") == "search_route":
                start_keyword = message.get("start", "").strip()
                end_keyword = message.get("end", "").strip()
                logger.info(f"[NAVIGATOR] Route requested: '{start_keyword}' -> '{end_keyword}'")

                start_poi = helper_search_poi(start_keyword)
                end_poi = helper_search_poi(end_keyword)

                if not start_poi or not end_poi:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "route_error",
                                "message": f"위치를 찾을 수 없습니다. (출발지: {start_keyword}, 목적지: {end_keyword})",
                            }
                        )
                    )
                    continue

                session_route_data = helper_fetch_route(start_poi, end_poi)
                if not session_route_data:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "route_error",
                                "message": "보행자 경로를 탐색하지 못했습니다. TMAP API 키의 활성화 상태를 확인해 주세요.",
                            }
                        )
                    )
                    continue

                # 경로 데이터 파싱
                session_waypoints = []
                route_coordinates = []
                features = session_route_data.get("features", [])
                point_idx = 1
                for feature in features:
                    geom = feature.get("geometry", {})
                    # Point 타입 (안내지점 및 포인터)
                    if geom.get("type") == "Point":
                        coords = geom.get("coordinates", [])
                        props = feature.get("properties", {})
                        session_waypoints.append(
                            {
                                "index": point_idx,
                                "lat": float(coords[1]),
                                "lon": float(coords[0]),
                                "description": props.get("description", "").strip(),
                                "facility_type": props.get("facilityType"),
                            }
                        )
                        point_idx += 1
                    # LineString 타입 (경로 선)
                    elif geom.get("type") == "LineString":
                        coords = geom.get("coordinates", [])
                        for coord in coords:
                            lat, lon = float(coord[1]), float(coord[0])
                            if not route_coordinates or route_coordinates[-1] != [lat, lon]:
                                route_coordinates.append([lat, lon])

                # 필터 인스턴스 초기화 및 manager 세션 등록
                nav_manager.update_route(device_id, session_waypoints)
                nav_manager.update_gps(
                    device_id, float(start_poi["y"]), float(start_poi["x"]), None
                )
                logger.info(
                    f"[NAVIGATOR] Route established! Waypoints: {len(session_waypoints)}, Coordinates: {len(route_coordinates)}"
                )

                # 프론트엔드로 성공 메시지 송출
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "route_success",
                            "start_name": start_poi["name"],
                            "end_name": end_poi["name"],
                            "coordinates": route_coordinates,
                            "waypoints": session_waypoints,
                        }
                    )
                )

            # 2. 실시간 GPS 및 Heading 수신 처리
            elif message.get("type") == "realtime_gps":
                try:
                    curr_lat = float(message.get("lat"))
                    curr_lon = float(message.get("lon"))
                    curr_heading = message.get("heading")
                    if curr_heading is not None:
                        curr_heading = float(curr_heading)

                    if session_waypoints:
                        # 1) NavigationManager에 위치 정보 갱신
                        nav_manager.update_gps(device_id, curr_lat, curr_lon, curr_heading)

                        # 2) 융합 가이드(길안내 멘트 + Redis 장애물 멘트) 추출
                        guidance_event = nav_manager.get_combined_guidance(device_id)

                        if guidance_event:
                            logger.info(f"[NAVIGATOR VOICE OUTPUT] => {guidance_event['text']}")

                            # 알림 종류에 따른 프론트엔드 송출
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": guidance_event.get("type", "guidance_audio"),
                                        "text": guidance_event["text"],
                                        "is_danger": guidance_event["is_danger"],
                                        "active_waypoint_idx": guidance_event.get(
                                            "active_waypoint_idx", 0
                                        ),
                                    }
                                )
                            )
                except Exception as ex:
                    logger.error(f"[NAVIGATOR] GPS processing exception: {ex}")

    except WebSocketDisconnect:
        logger.info("[SERVER] Navigation client disconnected.")
    except Exception as e:
        logger.error(f"[SERVER] Error in websocket loop: {e}")


if __name__ == "__main__":
    import uvicorn

    # 외부 접속 허용을 위해 0.0.0.0 바인딩, 포트는 8001
    logger.info("==========================================================")
    logger.info("   [VIP ASSISTANT AI] 길안내 전용 서버를 구동합니다 (포트: 8001)")
    logger.info("==========================================================")
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)  # nosec B104
