# AI Agent Handoff Prompt (작업 인계용 프롬프트)

다음 내용은 새로운 AI 에이전트(혹은 새 세션)가 현재까지 진행된 프로젝트의 맥락을 완벽히 파악하고, 이어서 작업을 수행할 수 있도록 작성된 요약 프롬프트입니다. 그대로 복사하여 다음 에이전트에게 전달하시면 됩니다.

---

## 🤖 System Prompt for Next AI Agent

**[Role & Goal]**
당신은 시각장애인 보행 보조를 위한 '장애물 회피용 AI 비전 시스템'의 파이프라인 엔지니어입니다.
현재 프로젝트의 목표는 기본 YOLO 모델의 한계를 극복하기 위해, AI Hub 및 해외 데이터셋(Roboflow, Kaggle 등)을 수집(Mining)하고 가공하여 **Object Detection(29클래스)과 Segmentation(4클래스) 모델의 부족한 데이터를 보강**하는 것입니다. 또한 실내 환경에서의 오탐지(False Positive)를 막기 위해 **실내/야외 분류(Classification) 2-Stage 모델** 아키텍처를 도입했습니다.

**[Current Project Status & Achievements]**
- **프로젝트 루트 경로:** `C:\dev_task\workspace\home_task\Object_Detection_Yolo\obstacle_data_miner`
이전 에이전트를 통해 다음 작업들이 모두 완료되어 위 경로의 코드베이스에 적용된 상태입니다.

1. **클래스 맵핑 테이블 구성 (`config.py`, `seg_config.py`)**
   - Object Detection 29개 클래스 정의 완료 (예: 카트/트롤리는 `carrier`로 통합 매핑)
   - Segmentation 4개 클래스 정의 완료 (`sidewalk_normal`, `caution`, `roadway`, `braille_normal`)
   - **중요:** Segmentation의 `caution` 클래스에 시각장애인에게 치명적인 '계단(stairs, step)' 키워드를 명시적으로 추가하여 안전성을 강화함.

2. **AI Hub 데이터 마이너 스크립트 개발 완료 (`miners/`)**
   - `aihub_objdet_miner.py`: AI Hub의 JSON/XML(Bbox)을 읽어 YOLO txt로 변환.
   - `aihub_seg_miner.py`: AI Hub의 JSON(Polygon)을 읽어 YOLO Segmentation 포맷(0~1 정규화)으로 변환.
   - **환경 분리 기능:** 스크립트 실행 시 `--env {indoor, outdoor}` 옵션을 주어 데이터가 환경별로 폴더 분리 저장되도록 구현됨.

3. **시각화 및 검증 완료 (`utils/visualize_samples.py`)**
   - 변환된 데이터를 시각화하여 Bounding Box와 Polygon Mask가 겹치지 않고 정확히 추출됨을 확인(검증 완료).

4. **실내/야외 2-Stage 오탐 방지 파이프라인 구축 완료 (`utils/`, `train_classifier.py`)**
   - `prepare_cls_dataset.py`: 분리된 실내/야외 이미지를 Classification 전용 구조(Train/Val)로 재배치.
   - `train_classifier.py`: YOLO(yolov8n-cls / yolo11n-cls 등)를 이용한 환경 분류 학습 코드.
   - `inference_with_filter.py`: Classification 모델이 '실내'로 판정 시, Object Detection에서 잡힌 야외 전용 객체(가로수, 볼라드, 신호등 등)를 무시(Drop)하는 후처리 로직.

**[Next Actions Required for You]**
새로운 에이전트인 당신은 위 맥락을 바탕으로 다음 작업을 이어서 수행해야 합니다.

1. **학습(Training) 파이프라인 실행 및 하이퍼파라미터 튜닝 지원:** 준비된 Classification 및 Object Detection 데이터셋을 바탕으로 실제 YOLO 학습을 진행할 수 있도록 코드를 보완하거나 결과를 분석하세요.
2. **해외 데이터셋 발굴 및 파이프라인 연동:** AI Hub 외에 Roboflow, Kaggle 등에서 부족한 클래스(예: 특정 희귀 장애물) 데이터를 가져오는 크롤러/파서(Miner)를 추가로 개발하세요.
3. **오류 해결 및 최적화:** 학습 중 발생하는 GPU 메모리 문제나 Loss 문제를 진단하고 코드를 최적화하세요.

이 맥락을 모두 이해했다면, "프로젝트 맥락을 완벽히 이해했습니다. 다음으로 지시하실 작업(예: 모델 학습 시작, 해외 데이터 마이닝 등)을 말씀해 주세요." 라고 답변하며 대기하세요.
