# Minchodan Dataset & Fine-Tuning Info

> **작성일**: 2026-07-25

본 프로젝트는 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼을 위한 객체 탐지 및 분할(Segmentation)을 수행합니다. 

원천 데이터 및 파인튜닝 학습 데이터의 원본은 매우 방대하여 Git 저장소 관리 효율 및 용량 최적화를 위해 **대표 샘플 데이터 10장만 본 저장소에 포함**되어 있습니다.

## 1. 원천 데이터 출처
- **AI Hub 시각장애인 보행 안전 및 편의 데이터셋** 등 외부 공개 데이터셋 활용
- Yolo 26N - Object Detection 및 Yolo 26N - Segmentation 모델 학습에 필요한 원본 이미지 및 라벨은 별도 보관(또는 AI Hub에서 다운로드 가능)합니다.

## 2. 파인튜닝 (Fine-Tuning) 개요
- **모델**: Ultralytics Yolo 26N (Object Detection / Segmentation)
- **학습 결과 디렉토리**: `training/runs/`
- 전체 중간 학습 체크포인트(`epoch*.pt`, `last.pt`)는 용량 최적화를 위해 삭제되었으며, 가장 성능이 좋은 **최종 가중치(`best.pt`, `segbest.pt`)와 학습 성능 그래프**만 보존되어 있습니다.

## 3. 샘플 데이터 안내
- `data/` 및 `training/datasets/` 내부에는 파이프라인과 코드가 정상 동작하는지 테스트하고 구조를 확인할 수 있도록 **10장 내외의 샘플 이미지와 라벨링 파일만 남겨두었습니다.**
- 전체 데이터를 이용하여 재학습이 필요한 경우, 원본 데이터셋을 다운로드하여 `training/datasets/`의 구조에 맞게 배치한 뒤 스크립트를 실행해 주십시오.
