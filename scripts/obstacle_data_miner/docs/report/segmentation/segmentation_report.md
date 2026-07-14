# Segmentation 데이터 수집 및 검증 보고서

## 1. 데이터 수집 출처 (Sources)

Segmentation 데이터는 전적으로 픽셀 단위의 정밀한 폴리곤(Polygon)을 요구하므로, 형태가 불규칙한 노면 상태를 담은 국내 공공 데이터를 집중적으로 활용했습니다.

### 1.1 국내 데이터셋 (AI Hub 연동)
- **dataSetSn=186 (베리어프리존 장애물 없는 생활공간 주행영상):**
  - **포맷:** JSON 형식의 Polygon 데이터 (`segmentation: [[x, y], ...]`)
  - **특징:** 휠체어/보행자 관점에서 촬영된 인프라 및 보도/차도 데이터를 포함.

## 2. 데이터 변환 및 매핑 (Class Mapping)
시각장애인 보행 보조를 위한 4개의 핵심 클래스로만 엄격하게 매핑했습니다.
- `floor_normal`, `sidewalk`, `보도`, `인도` ➡️ **`sidewalk_normal`** (안전한 보도)
- `damage`, `파손`, `턱`, `경사로`, `웅덩이`, `공사`, `curb` ➡️ **`caution`** (주의 구간)
- `road`, `차도`, `도로` ➡️ **`roadway`** (차도/진입 금지)
- `braille`, `점자`, `유도블록` ➡️ **`braille_normal`** (점자블록)

## 3. YOLO Polygon 검증 결과 (Verification Results)
- **추출 결과:** AI Hub 베리어프리존 샘플 파싱 결과, **653장**의 유효 Segmentation 마스크 데이터가 추출됨.
- 폴리곤 좌표 0~1 정규화(Normalization) 처리를 완벽히 수행하여 YOLO 포맷 에러 방지.
- 디렉토리 구조 딥서치: `rglob`를 활용하여 `원천데이터` 등 불규칙한 하위 폴더에 존재하는 원본 `.jpg` 이미지와 JSON 라벨의 매칭 매커니즘 구현.
- **시각화 검증:** `utils/visualize_samples.py`(`--mode seg`)를 통해 Polygon 색상 마스킹(Fill) 오버레이를 진행하여 정답지 라벨 품질 확인 완료.
