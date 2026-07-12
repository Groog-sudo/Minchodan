/**
 * [TH HARDCODE] 수신 문자 메시지 읽어주기 편의기능 (Android 전용).
 *
 * 💡 [면접 대비 주석 - 왜 iOS는 지원하지 않는가]
 * Q. iOS 클라이언트에서는 이 기능이 왜 안 됩니까?
 * A. "iOS는 샌드박스 정책상 서드파티 앱에 수신 문자 콘텐츠를 읽을 수 있는 공개
 *    API를 제공하지 않습니다(기본 메시지 앱만 접근 가능). 이건 하드코딩이 아니라
 *    플랫폼 자체 제약이라 Android 전용 편의기능으로 범위를 좁혔습니다."
 *
 * 네이티브 SmsReaderModule(client/android/.../SmsReaderModule.kt)이 SMS_RECEIVED
 * 브로드캐스트를 받아 onSmsReceived 이벤트로 넘기면, 여기서 기존 단말 TTS
 * (audioEngine.speakFallback, expo-speech 기반)로 그대로 읽어준다. 서버 왕복이
 * 필요 없는 순수 로컬 기능이라 Dual Path(반사/인지) 오케스트레이션을 거치지 않는다.
 *
 * [미검증] 실제 문자 수신 테스트는 아직 완료되지 않았다. Android 에뮬레이터의
 * Extended Controls > Phone > SMS(또는 `adb emu sms send <번호> "<본문>"`)로
 * 실기기 SIM 없이도 검증 가능하다 - 테스트가 끝나면 이 주석과 changelog의
 * "미검증" 표기를 갱신할 것.
 */

import { useEffect } from "react";
import { DeviceEventEmitter, NativeModules, PermissionsAndroid, Platform } from "react-native";

import { audioEngine } from "../services/audioEngine";

interface SmsReaderModuleType {
  startListening(): Promise<boolean>;
  stopListening(): Promise<boolean>;
}

interface SmsReceivedPayload {
  sender?: string;
  body?: string;
}

function getModule(): SmsReaderModuleType | null {
  if (Platform.OS !== "android") return null;
  // 구버전 네이티브 빌드(모듈 미포함)에서 JS만 갱신된 경우를 방어한다.
  return (NativeModules.SmsReaderModule as SmsReaderModuleType) ?? null;
}

/** enabled가 true인 동안 수신 문자를 감지해 발신자와 본문을 음성으로 읽어준다. */
export function useSmsReader(enabled: boolean = true): void {
  useEffect(() => {
    if (!enabled) return;
    const mod = getModule();
    if (!mod) return;

    let cancelled = false;
    let subscription: { remove: () => void } | null = null;

    (async () => {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECEIVE_SMS,
          {
            title: "문자 메시지 읽어주기 권한",
            message: "수신한 문자 메시지를 음성으로 읽어드리기 위해 필요합니다.",
            buttonPositive: "허용",
            buttonNegative: "거부",
          },
        );
        if (cancelled || granted !== PermissionsAndroid.RESULTS.GRANTED) return;

        subscription = DeviceEventEmitter.addListener(
          "onSmsReceived",
          (payload: SmsReceivedPayload) => {
            const sender = payload.sender || "알 수 없는 발신자";
            const body = payload.body || "";
            if (!body) return;
            console.log(`[SmsReader] 메시지 수신: sender=${sender}, len=${body.length}`);
            audioEngine.speakFallback(`${sender}님으로부터 문자 메시지가 도착했습니다. ${body}`);
          },
        );
        await mod.startListening();
      } catch (err) {
        console.warn("[SmsReader] 초기화 실패:", err);
      }
    })();

    return () => {
      cancelled = true;
      subscription?.remove();
      mod.stopListening().catch(() => {});
    };
  }, [enabled]);
}
