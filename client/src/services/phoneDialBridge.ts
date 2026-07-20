/**
 * STT dial_action 전화 연결 브릿지.
 * Android: ACTION_CALL 즉시 발신.
 * iOS: Siri App Intent + Shortcuts(MinchodanDial) 경로. tel: 전화 앱 열기는 사용하지 않는다.
 */

import {
  AccessibilityInfo,
  NativeModules,
  PermissionsAndroid,
  Platform,
} from "react-native";

import { audioEngine } from "./audioEngine";
import { hapticEngine } from "./hapticEngine";

interface PhoneDialBridgeModule {
  placeCall(
    phoneNumber: string,
    contactName: string | null,
  ): Promise<{ mode: string; phoneNumber: string }>;
}

const IOS_SHORTCUT_SETUP_GUIDANCE =
  "시리 바로 가기 MinchodanDial이 필요합니다. 단축어 앱에서 전화 받기 동작으로 추가해 주세요.";

function getModule(): PhoneDialBridgeModule | null {
  if (Platform.OS === "ios") {
    return (NativeModules.PhoneDialBridge as PhoneDialBridgeModule) ?? null;
  }
  if (Platform.OS === "android") {
    return (NativeModules.PhoneDialBridgeModule as PhoneDialBridgeModule) ?? null;
  }
  return null;
}

async function ensureAndroidCallPermission(): Promise<boolean> {
  if (Platform.OS !== "android") {
    return true;
  }
  const granted = await PermissionsAndroid.check(
    PermissionsAndroid.PERMISSIONS.CALL_PHONE,
  );
  if (granted) {
    return true;
  }
  const result = await PermissionsAndroid.request(
    PermissionsAndroid.PERMISSIONS.CALL_PHONE,
    {
      title: "전화 자동 연결 권한",
      message:
        "음성 명령으로 전화를 자동 연결하려면 통화 권한이 필요합니다.",
      buttonPositive: "허용",
      buttonNegative: "거부",
    },
  );
  return result === PermissionsAndroid.RESULTS.GRANTED;
}

/** dial_action 수신 후 전화를 연결한다. */
export async function placePhoneCall(
  phoneNumber: string,
  contactName?: string,
): Promise<void> {
  const cleaned = phoneNumber.replace(/\D/g, "");
  if (!cleaned) {
    return;
  }

  const announceText = contactName
    ? `${contactName}로 전화를 연결합니다.`
    : "전화를 연결합니다.";
  AccessibilityInfo.announceForAccessibility(announceText);
  await hapticEngine.trigger("double");

  const mod = getModule();
  if (!mod) {
    if (Platform.OS === "ios") {
      audioEngine.speakFallback(IOS_SHORTCUT_SETUP_GUIDANCE);
    }
    return;
  }

  try {
    if (Platform.OS === "android") {
      const permitted = await ensureAndroidCallPermission();
      if (!permitted) {
        console.warn("[PhoneDial] CALL_PHONE 권한 거부");
        audioEngine.speakFallback("전화 권한이 필요합니다.");
        return;
      }
      await mod.placeCall(cleaned, contactName ?? null);
      console.log(`[PhoneDial] Android 자동 연결: ${cleaned}`);
      return;
    }

    const result = await mod.placeCall(cleaned, contactName ?? null);
    console.log(
      `[PhoneDial] iOS Siri 경로 요청: mode=${result.mode}, phone=${cleaned}`,
    );
  } catch (error) {
    console.warn(`[PhoneDial] 연결 실패: ${String(error)}`);
    if (Platform.OS === "ios") {
      audioEngine.speakFallback(IOS_SHORTCUT_SETUP_GUIDANCE);
    }
  }
}
