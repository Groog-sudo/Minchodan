# 안드로이드 실기기 영상 왜곡 해소 및 Center Crop 기반 객체 탐지율 고도화 보고서

## 1. 배경 및 현상 분석 (Current Status)
- **상황:** EAS 개발 빌드 환경에서 스마트폰 실기기와 FastAPI 백엔드 간의 웹소켓 바이너리 통신망 구축이 완료되었음 (`WS: connected`).
- **문제점:** TFLite 로컬 추론 및 서버 추론 엔진이 정상 가동되어 텐서 쉐이프(`[1, 300, 6]`)가 정상 추출됨에도 불구하고, 실시간 카메라 화면에서 객체 바უნ딩 박스(BBox)가 전혀 그려지지 않거나 `[실시간 감지] 없음` 상태가 지속되는 치명적인 성능 저하가 발생함.

## 2. 원인 진단 (Root Cause Analysis)
스마트폰 카메라 센서의 원본 캡처 해상도는 세로가 긴 **직사각형 비율(3:4 또는 9:16)**을 가집니다. 그러나 기존 코드는 이 데이터를 AI 모델 규격에 맞추기 위해 가로세로 비율 유지 없이 **강제로 640x640 정사각형으로 짜부러뜨려(Squish) 리사이즈**를 감행했습니다. 이로 인해 두 가지 치명적인 결함이 발생했습니다.

1. **YOLO AI 모델 인지 기능 상실:** 원본 이미지의 사물들이 세로로 길게 찌그러지기 때문에, 정비율의 실제 야외 도로 장애물(볼라드, 킥보드 등) 이미지로 학습된 커스텀 YOLO 모델(`best_20260705.pt`)이 사물의 특징값을 식별하지 못해 신뢰도 점수(Confidence Score)가 임계값 미만으로 폭락함.
2. **화면 프리뷰 좌표계 단절:** 프론트엔드 UI(`CameraView.tsx`)의 카메라 컨테이너는 `aspectRatio: 1` 정사각형 뷰포트로 선언되어 해상도의 상/하단이 잘린 중앙 영역만 보여주는 반면, AI 엔진은 상/하단이 강제 압축된 전체 스케일을 보게 됨으로써 BBox 투사 좌표가 완전히 어긋나 화면 밖으로 튕겨 나가는 우주 미아 현상이 발생함.

## 3. 해결 기법 비교 및 센터 크롭(Center Crop) 채택
AI 모델에게 정비율 이미지를 급여하기 위해 고려된 두 가지 후보 엔진의 비교 명세는 다음과 같습니다.

| 기법 | 메커니즘 | 우리 프로젝트 적용 판정 및 사유 |
| :--- | :--- | :--- |
| **래터박스 (Letterbox)** | 이미지 비율을 유지하며 축소하고 남는 여백을 검은색 바(Padding)로 채움 | **부적합.** 검은색 패딩 영역이 AI 신경망에 불필요한 노이즈 특성으로 작용할 수 있으며, 클라이언트 컨테이너가 이미 정사각형이므로 UI 매핑 연산이 복잡해짐. |
| **센터 크롭 (Center Crop)** | 원본 직사각형 이미지의 정중앙을 기준으로 1:1 정사각형 영역만 칼로 도려내어 추출 | **최적 (선택).** 유저가 눈으로 바라보는 `CameraView` 프리뷰 범위와 AI가 연산하는 시각적 범위를 100% 일치시켜 기하학적 왜곡을 원천 제거함. |

## 4. 아키텍처 수정 명세 (Code Fix Specification)
- **대상 파일:** `client/src/services/frameCaptureProviderSelect.android.ts`
- **수정 내용:** 원본 사진(`PhotoFile`)의 폭과 높이 중 짧은 축을 기준으로 정사각형 `minSize`를 도출하고, 상/하단 혹은 좌/우측의 남는 마진을 반으로 나누어 정중앙 시작점(`originX`, `originY`)을 역산함. `manipulateAsync` 파이프라인의 1단계에 `crop`을 주입하여 왜곡을 제거한 후, 2단계에서 `640x640`으로 청정 리사이즈를 수행함.

```typescript
// 1:1 정사각형 센터 영역 계산
const minSize = Math.min(photo.width, photo.height);
const originX = Math.floor((photo.width - minSize) / 2);
const originY = Math.floor((photo.height - minSize) / 2);

const manipResult = await manipulateAsync(
  path,
  [
    { crop: { originX, originY, width: minSize, height: minSize } }, // 1단계: 왜곡 제거
    { resize: { width: 640, height: 640 } },                        // 2단계: 모델 규격화
  ],
  { compress: 0.5, format: SaveFormat.JPEG, base64: true },
);
