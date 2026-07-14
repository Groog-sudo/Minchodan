/**
 * GPS 위치 추적 훅.
 * server/navigation/manager.py의 NavigationManager.update_gps()가 소비하는
 * lat/lon/heading을 주기적으로 얻어 상위 컴포넌트가 WS로 전송할 수 있게 제공한다.
 * 판정 로직(경로 이탈, 웨이포인트 도착 등)은 전부 서버(NavigationFilter)가 수행하며,
 * 이 훅은 좌표 획득만 담당한다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as Location from "expo-location";

export interface GpsCoords {
  lat: number;
  lon: number;
  heading: number | null;
}

export interface UseLocationReturn {
  hasPermission: boolean;
  requestLocationPermission: () => Promise<boolean>;
  startWatching: (onUpdate: (coords: GpsCoords) => void) => Promise<void>;
  stopWatching: () => void;
}

const LOCATION_UPDATE_INTERVAL_MS = 2000;
const LOCATION_UPDATE_DISTANCE_M = 1;

export function useLocation(): UseLocationReturn {
  const [hasPermission, setHasPermission] = useState(false);
  const subscriptionRef = useRef<Location.LocationSubscription | null>(null);

  const requestLocationPermission = useCallback(async (): Promise<boolean> => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      const granted = status === "granted";
      setHasPermission(granted);
      return granted;
    } catch (err) {
      console.error("[Location] 권한 요청 오류:", err);
      return false;
    }
  }, []);

  useEffect(() => {
    Location.getForegroundPermissionsAsync()
      .then(({ status }) => setHasPermission(status === "granted"))
      .catch((err) => console.error("[Location] 권한 상태 조회 오류:", err));
  }, []);

  const startWatching = useCallback(
    async (onUpdate: (coords: GpsCoords) => void) => {
      if (subscriptionRef.current) return;
      try {
        const { status } = await Location.getForegroundPermissionsAsync();
        if (status !== "granted") return;

        subscriptionRef.current = await Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.High,
            timeInterval: LOCATION_UPDATE_INTERVAL_MS,
            distanceInterval: LOCATION_UPDATE_DISTANCE_M,
          },
          (location) => {
            onUpdate({
              lat: location.coords.latitude,
              lon: location.coords.longitude,
              heading:
                location.coords.heading != null && location.coords.heading >= 0
                  ? location.coords.heading
                  : null,
            });
          },
        );
      } catch (err) {
        console.error("[Location] 위치 추적 시작 오류:", err);
      }
    },
    [],
  );

  const stopWatching = useCallback(() => {
    subscriptionRef.current?.remove();
    subscriptionRef.current = null;
  }, []);

  useEffect(() => {
    return () => stopWatching();
  }, [stopWatching]);

  return { hasPermission, requestLocationPermission, startWatching, stopWatching };
}
