# 🚨 COCO 모델 오탐(Hallucination) 시각화 증거

현재 서버 폴더(`server/models/yolo26n/object_detection.pt`)에 들어있는 모델로 100장 테스트를 돌린 결과 중, 가장 치명적인 **COCO 클래스 오탐 증거 사진** 두 장을 가져왔습니다.

이 사진들은 현재 모델이 **우리가 학습시킨 29종(AI Hub) 모델이 아님을 명백하게 증명**합니다.

---

### 🎒 증거 1: 가방(Backpack)을 찾아내는 모델

![가방(Backpack)을 인식한 증거 사진](C:\Users\USER\.gemini\antigravity\brain\1a2375cf-856e-44c4-a03b-f4e36d8c0869\coco_backpack.jpg)

> [!WARNING]
> 오른쪽 아래를 보시면 사람이 매고 있는 백팩을 정확히 **`backpack`**이라고 박스를 치고 있습니다. 우리 AI Hub 29종 클래스에는 가방이라는 정답지 자체가 존재하지 않습니다!

---

### ⏰ 증거 2: 시계(Clock)를 찾아내는 모델

![시계(Clock)를 인식한 증거 사진](C:\Users\USER\.gemini\antigravity\brain\1a2375cf-856e-44c4-a03b-f4e36d8c0869\coco_clock.jpg)

> [!IMPORTANT]
> 자동차 위의 희미한 원형 표지판 같은 구조물을 보고 **`clock`**이라고 박스를 쳤습니다. 시계 역시 29종 클래스에는 없는 COCO 기본 모델 전용 클래스입니다.

---

### 💡 결론 및 다음 단계
이 두 장의 사진이 모든 것을 증명합니다. **누군가 우리가 100 Epoch나 돌려서 만든 진짜 가중치 파일 대신, 빈 깡통 같은 기본 모델을 서버 폴더에 복사해 둔 것입니다.** 

이제 제가 진짜 학습된 `best.pt` 파일을 찾아서 이 가짜 모델을 교체하고, 앱에서 쓸 수 있도록 `.tflite`와 `.mlpackage`로 다시 추출(Export)하는 작업을 진행하겠습니다!
