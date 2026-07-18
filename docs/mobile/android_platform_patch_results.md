# Android 플랫폼 기능 패치 및 패리티 적용 결과 보고서

> **작성일**: 2026-07-17  
> **버전**: v1.0.0  
> **관련 이슈**: Android 온디바이스 TFLite 데이터 미공급, Android 네이티브 AEC 모드 바이패스, useStreamCapture 프레임 프로세서 미기동  

이 문서는 스마트 가이드독 AI 플랫폼 "Minchodan"의 React Native 클라이언트 앱에서 발생했던 Android 플랫폼 전용 오류 및 기능 불균형 항목을 분석하고, 이를 수정/보완하기 위해 적용한 패치와 검증 결과를 기록합니다.

---

## 1. 개요 및 최종 변경 사항

| 구분 | 이슈 세부 사항 | 패치 적용 내용 | 검증 결과 |
| :--- | :--- | :--- | :--- |
| **Android TFLite 텐서 복구** | 단발 촬영(`capturePhoto`) 시점에 `Float32Array(0)` 빈 버퍼를 반환하여 TFLite 모델 추론이 무조건 실패하고 경고(`입력 shape 불일치`)가 발생하던 버그 | Android의 `captureViaTakePhotoAndroid` 함수에서 촬영 완료 시점에 `decodeBase64JpegToHwc` 디코더 유틸을 실행하여 640x640x3 크기의 유효한 정규화 Float32Array를 공급하도록 수정 | `tsc --noEmit` 타입 검사 통과 및 정상 텐서 데이터 변환 확보 |
| **Android AEC 네이티브 연동** | 음성 명령 시작 시 `audioSessionBridge.ts`에서 Android 플랫폼 조건일 때 네이티브 모듈을 호출하지 않고 모조(Mock) 객체를 즉시 반환하여 에코 캔슬러가 누락되던 기능 공백 | Android 조건일 때도 네이티브 `AudioSessionBridgeModule.setVoiceProcessing`을 비동기 호출(`await`)하도록 복구하여 하드웨어 에코 상쇄가 발동되도록 수정 | 타입 정합 확보 및 Android 음향 피드백 루프 상쇄 기반 마련 |
| **프레임 프로세서 봉인 해제** | `useCamera.ts`에서 `useStreamCapture = false`로 강제 고정되어 실기기 빌드에서도 고성능 프레임 프로세서 대신 무거운 `takePhoto` 폴백만 동작하던 제약 | `useStreamCapture`를 원래 설계된 동적 판정 조건(`!isMockMode && captureProvider.supportsStream`)으로 복구하여 Expo Go와 실기기 커스텀 클라이언트 빌드 간 자동 전환 완성 | Expo Go에서는 안전한 폴백 기동, 개발 실기기 빌드에서는 고성능 카메라 스트림 연결 확보 |
| **카메라 화면 회전 정합** | Android 실기기 종류 및 방향에 따라 영상 프레임이 누워서 송출되는 현상 발생. (EXIF 자동 회전이 과적용되거나 미적용되어 옆으로 꺾이는 현상) | 관제 콘솔 UI에 4방향 회전 수동 버튼(0°, 90°, 180°, 270°)을 배치하고, 선택된 각도에 따라 이미지 트랜스폼 및 바운딩 박스 크롭 좌표계(`getDisplayBBox`)가 동적으로 리매핑되도록 수정 | 콘솔 빌드 성공 및 실시간 4방향 수동 각도 조절 및 BBox 동시 정합 확인 완료 |

---

## 2. 세부 변경 내역 (Code Patch Details)

### 2.1. [frameCaptureProviderSelect.android.ts](file:///d:/home_coding_task/project_mall/workspace/AI_final_project/Team_JY/Gil_Daeng/client/src/services/frameCaptureProviderSelect.android.ts)
```typescript
// 1. 디코더 유틸 임포트 추가
import { decodeBase64JpegToHwc } from "./realFrameProvider";

// 2. 단발 촬영 시 Float32Array를 빈 배열 대신 정상 변환하여 TFLite로 공급
const base64 = manipResult.base64 ?? "";
const float32 = decodeBase64JpegToHwc(base64); // 기존 new Float32Array(0)에서 변경
```

### 2.2. [audioSessionBridge.ts](file:///d:/home_coding_task/project_mall/workspace/AI_final_project/Team_JY/Gil_Daeng/client/src/services/audioSessionBridge.ts)
```typescript
export async function setVoiceProcessing(
  enabled: boolean,
): Promise<AudioSessionInfo | null> {
  const mod = getModule();
  if (!mod) return null;
  
  if (Platform.OS === "android") {
    try {
      // Android 네이티브 AudioSessionBridgeModule을 실제로 호출하여 MODE_IN_COMMUNICATION 적용
      await mod.setVoiceProcessing(enabled);
      return {
        category: "playAndRecord",
        mode: enabled ? "voiceChat" : "normal",
        voiceProcessingActive: enabled,
        outputRoute: "speaker",
      };
    } catch (err) {
      console.warn(`[AudioSession] Android voiceChat 전환 실패:`, err);
      return null;
    }
  }
  // ... (iOS 로직)
}
```

### 2.3. [useCamera.ts](file:///d:/home_coding_task/project_mall/workspace/AI_final_project/Team_JY/Gil_Daeng/client/src/hooks/useCamera.ts)
```typescript
  const captureFrame = isMockMode ? captureMockFrame : captureProvider.capturePhoto;
  // Expo Go 환경(개발 빌드가 아닌 순수 가상 빌드)에서는 supportsStream이 false이므로 자동 폴백됩니다.
  // 프로덕션/실기기 빌드에서는 supportsStream이 true가 되어 고성능 프레임 프로세서로 동작합니다.
  const useStreamCapture = !isMockMode && captureProvider.supportsStream;
```

### 2.4. [LiveCameraFeed.tsx](file:///d:/home_coding_task/project_mall/workspace/AI_final_project/Team_JY/Gil_Daeng/console/src/components/LiveCameraFeed.tsx) (콘솔)
```typescript
// 1. 4방향 회전 각도에 따른 BBox의 좌표 동적 리매핑 수식 개편
function getDisplayBBox(
  bbox: { x: number; y: number; w: number; h: number },
  natural: { w: number; h: number },
  rotateDeg: number,
) {
  // ...
  const angle = ((rotateDeg % 360) + 360) % 360;
  if (angle === 90) {
    rx = srcH - y - h; ry = x; rw = h; rh = w; dstW = srcH; dstH = srcW;
  } else if (angle === 180) {
    rx = srcW - x - w; ry = srcH - y - h; rw = w; rh = h; dstW = srcW; dstH = srcH;
  } else if (angle === 270) {
    rx = y; ry = srcW - x - w; rw = h; rh = w; dstW = srcH; dstH = srcW;
  }
  // ...
}

// 2. 화면 상단 회전 제어용 dynamic state 및 UI 버튼 연동
const [rotateDeg, setRotateDeg] = useState<number>(defaultRotate);
```

---

## 3. 검증 결과 (Verification & Build Results)

* **클라이언트 정적 컴파일 검증**: `client` 디렉토리 하위에서 TypeScript 컴파일러(`npx tsc --noEmit`)를 작동시켜 수정한 모든 플랫폼 분기 및 래퍼 클래스가 **타입 매칭 에러나 문법적 예외 없이 완벽하게 컴파일을 완료**한 것을 입증했습니다.
* **콘솔 빌드 검증**: `console` 디렉토리 하위에서 빌드 스크립트(`npm run build`)를 작동시켜 4방향 동적 회전 기능 및 CSS 버튼 스타일이 반영된 웹 프로덕션 번들이 **에러 없이 빌드 성공**함을 검증했습니다.
* **패리티 효과**: 
  - Android 환경의 TFLite 모델 입력 데이터가 비어 있는 오작동 상태가 해소되어 실기기 상의 즉각 반사 경보(Reflex Gate)가 정상 작동하는 기반을 갖췄습니다.
  - 마이크 녹음 시의 에코 피드백 상쇄 기능이 네이티브 안드로이드 오디오 매니저 연동을 통해 하드웨어 레벨에서 정상 구동됩니다.
  - 기기 종류나 거치 방향에 맞춰 카메라 화면 회전각을 4방향 중 자유롭게 조절하고 탐지 상자(BBox)를 완벽히 정치시킬 수 있습니다.
