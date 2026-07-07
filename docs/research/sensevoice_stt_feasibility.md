# STT 모델 검토 보고서 (Alibaba SenseVoice-Small 도입 정당성: 지연·로딩·한국어 정확도)

> **작성일**: 2026-07-07
> **버전**: v1.0.0
> **대상 경로**: 사용자 음성 명령(STT) 경로 — 현재 7단계 골격 범위 밖의 신규 입력 경로
> **관련 문서**: [`docs/design/minchodan_design_note.md`](../design/minchodan_design_note.md) (§183 "Whisper는 STT 전용, 골격 범위 밖"), [`docs/design/pipeline_stage_design.md`](../design/pipeline_stage_design.md) (§175 "사용자 음성 명령(STT) 경로")

---

## 1. 개요

Minchodan은 카메라 입력을 받아 음성으로 안내하는 **출력 중심**(반사/인지 이중 경로 + TTS) 시스템입니다. 사용자가 시각장애인이므로, 향후 **음성으로 명령/질의를 입력**하는 경로(예: "앞에 뭐 있어?", "가까운 횡단보도 어디야?")를 추가하려면 STT(Speech-to-Text)가 필요합니다.

이 STT 경로는 설계 문서상 **현재 7단계 골격의 범위 밖**으로 명시돼 있으며, Whisper가 플레이스홀더로만 언급돼 있습니다. 본 보고서는 그 자리에 **Alibaba SenseVoice-Small**을 채택하는 것이 타당한지를 **지연 속도·로딩 속도·모델 크기·한국어 정확도·라이선스** 관점에서 검토합니다.

판단 기준이 되는 우리 용도의 특성은 다음 3가지입니다.

- **짧은 발화**: 긴 받아쓰기가 아니라 단문 명령/질의
- **한국어 전용**: 다국어 능력보다 한국어 정확도가 중요
- **오프라인 우선**: 네트워크·비용 의존을 최소화하는 설계 원칙

---

## 2. SenseVoice-Small 실측 스펙 (2026년 7월 조사 기준)

| 항목 | 실측치 | 출처 |
| --- | --- | --- |
| **추론 지연** | 10초 오디오를 **70ms**에 처리, RTF **52~118× 실시간** (Whisper-Large 대비 15×, Whisper-Small 대비 5~7× 빠름) | HF, whispernotes 벤치마크 |
| **로딩 속도** | **0.81초** | whispernotes 벤치마크 |
| **모델 크기 / 메모리** | 다운로드 **827MB**, RAM **약 700MB** | whispernotes 벤치마크 |
| **아키텍처** | 비자기회귀(non-autoregressive) **오프라인** 프레임워크, **스트리밍 미지원**(무음 기준 자동 분절만 제공) | HF, GitHub |
| **한국어 정확도** | CER **8.28%** (Whisper-Large-V3 **5.59%** 대비 약 **2.7%p 열위**) | whispernotes 벤치마크 |
| **구동 환경** | **CPU 구동 가능(GPU 불필요)**, ONNX/libtorch 익스포트, GGUF(llama.cpp) 엣지 빌드 | HF |
| **부가 기능** | 감정 인식(SER), 음향 이벤트 탐지(AED), 언어 식별(LID) 내장 | GitHub, 논문 |
| **라이선스** | FunASR MODEL_LICENSE — **상업적 사용 허용**, 출처·모델명 표기(attribution) 필수 | FunASR MODEL_LICENSE |

> **핵심 관찰**: 속도(지연·로딩·처리량)는 압도적으로 우수하나, **한국어 정확도는 SenseVoice의 강점이 아니다**(강점은 중국어·광둥어). 비자기회귀 구조상 **스트리밍이 아니라 발화 단위 오프라인 전사**다.

---

## 3. Minchodan 아키텍처 적합성 분석

### 3.1 서버(GPU) 배치 — 정합성 높음

| 관점 | 평가 |
| --- | --- |
| 아키텍처 정합 | "모든 추론은 GPU 서버" 원칙과 일치. STT를 FastAPI 서버에 배치하는 것이 자연스럽다 |
| 지연·로딩 | 최상위 강점. 0.81초 로딩·70ms 전사로 서버 워밍업/응답 부담이 낮다 |
| GPU 여유 | Whisper-Large 대비 5~17× 빠르므로, 확보된 GPU 여유를 탐지·LLM에 양보할 수 있다 |
| 스트리밍 미지원 | 짧은 명령 UX에서는 문제가 아니다. VAD로 발화 종료를 잡고 70ms 전사하면 체감 즉시 응답 |

### 3.2 온디바이스 배치 — 재검토 필요

| 관점 | 평가 |
| --- | --- |
| 메모리 경합 | 827MB 모델 + 700MB RAM이 **이미 폰에 올라간 CoreML 탐지 모델(det/seg)과 메모리·발열을 경합**한다 |
| 경량 대안 | 온디바이스 STT가 필요하면 whisper.cpp tiny/base(~75~150MB)가 훨씬 가볍다 |
| 결론 | SenseVoice 온디바이스(GGUF) 자체는 가능하나, 반사 루프가 이미 온디바이스라 자원 압박이 크다 |

---

## 4. 대안 비교

| 후보 | 배치 | 한국어 정확도 | 지연 | 특징 | 우리 용도 적합성 |
| --- | --- | --- | --- | --- | --- |
| **SenseVoice-Small** | 서버 권장 | CER 8.28% (중상) | 매우 낮음(70ms/10s) | 오프라인·비스트리밍·CPU 가능·상업 허용 | 서버 + 짧은 명령이면 최적 후보 |
| **Whisper-Large-V3** | 서버 | CER 5.59% (상) | 높음(RTF ~13×) | 정확도 우선, 무겁고 느림 | 자유 질의·정확도 최우선 시 |
| **faster-whisper** | 서버 | Whisper급(상) | 중(CTranslate2 가속) | 속도-정확도 절충, 청크 처리 | 정확도·속도 균형 필요 시 |
| **whisper.cpp (tiny/base)** | 온디바이스 | 낮음~중 | 중 | 초경량, 오프라인 | 온디바이스 STT 강제 시 |
| 클라우드 STT(Naver Clova 등) | 클라우드 | 최상 | 낮음 | 유료·네트워크 의존 | 오프라인 우선 원칙과 충돌 |

---

## 5. 결론 및 권고

**서버측 STT + 짧은 한국어 음성 명령** 용도라면, **지연·로딩 관점에서 SenseVoice-Small 채택은 정당하며 강력한 후보다.** 다만 다음 3가지 단서를 전제로 한다.

1. **한국어 정확도 열위(약 2.7%p)를 도메인 명령 셋으로 실측 검증한다.** 일반 CER 8.28%는 쓸 만하지만, 실제 명령어(장소명·기능어·고유명사)에서의 오인식률을 측정해야 한다. 명령이 소수 고정 패턴이면 8.28%도 무방하나, 자유 질의 비중이 크면 Whisper-Large-V3가 안전하다.
2. **온디바이스 STT 요구가 생기면 재평가한다.** 그 경우 whisper.cpp 계열이 메모리·발열 측면에서 유리하다(반사 루프가 이미 온디바이스이므로 자원 경합 주의).
3. **라이선스 attribution(FunASR/Alibaba 출처·모델명 표기)을 준수한다.**

### 권장 다음 단계

동일한 한국어 명령 셋(우리 실사용 시나리오 기반 30~50개)으로 **SenseVoice-Small vs faster-whisper vs whisper.cpp**의 CER·지연을 나란히 측정하는 소규모 실측 벤치를 1회 수행하면 최종 결론이 확정된다. STT 경로가 정식 착수될 때 본 보고서를 기준선으로 삼는다.

---

## 6. 참고 자료

- [SenseVoice vs Whisper: Korean/CJK Benchmark (whispernotes.app)](https://whispernotes.app/blog/sensevoice-fastest-cjk-transcription)
- [FunAudioLLM/SenseVoiceSmall (Hugging Face)](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)
- [FunAudioLLM/SenseVoice (GitHub)](https://github.com/FunAudioLLM/SenseVoice)
- [FunASR MODEL_LICENSE](https://github.com/modelscope/FunASR/blob/main/MODEL_LICENSE)
- [FunAudioLLM 논문 (arXiv 2407.04051)](https://arxiv.org/html/2407.04051v1)
