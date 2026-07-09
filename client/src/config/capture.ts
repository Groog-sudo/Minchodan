/**
 * 반사 경로 카메라 캡처 엔진 토글.
 *
 * [2026-07-09 도입] 실기기 시스템 로그(log collect --device) 분석 결과,
 * takePhoto() 반복 호출(AVCapturePhotoOutput)이 촬영마다 AVAudioSessionInterruption을
 * 유발해 동시 재생 중인 TTS 안내 음성이 순간 끊기는 것이 확인됐다. frameProcessor
 * 모드(AVCaptureVideoDataOutput 기반 연속 스트림, AVCapturePhotoOutput 미사용)로
 * 전환해 이 인터럽션 자체를 제거한다.
 *
 * 문제가 재현되면 이 값을 'takePhoto'로 되돌리고 재빌드하면 즉시 원복된다
 * (client/src/hooks/useCamera.ts의 captureRealFramePhoto 경로가 그대로 보존되어 있음).
 */

export const CAPTURE_ENGINE: "takePhoto" | "frameProcessor" = "frameProcessor";
