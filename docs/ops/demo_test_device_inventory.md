# 시연/테스트 장비 제원 인벤토리

> **작성일**: 2026-07-21
> **버전**: v1.1.2 (2026-07-21 시연 스킬에 서버 기동(Docker·Ollama·Metro·console·Pi) 체크리스트 편입 반영. 이전 v1.1.1: Mac mini Ollama keepalive. 이전 v1.1.0: 토폴로지 확정 — LLM Mac mini 분리, 서버-LLM-DB LAN + 아이폰-서버 Tailscale)
> **목적**: 시연·통합 테스트에 실제 사용하는 4개 장비(GPU 추론 서버, LLM 호스트 겸 macOS 개발 머신, iOS 클라이언트 단말, DB·미디어 저장 Raspberry Pi)의 제원과 네트워크 연결 방식을 한 곳에 모아, 신규 시연 장비 도입 시 성능·호환성을 비교하는 기준선으로 사용한다.
> **관련 문서**: [`ai_model_hardware_setup.md`](ai_model_hardware_setup.md), [`db_tailscale_guide/README.md`](../db_tailscale_guide/README.md), [`ondevice_coreml_benchmark.md`](ondevice_coreml_benchmark.md)
> **관련 스킬**: [`rpi-network-profile-switcher`](../../.agents/skills/rpi-network-profile-switcher/SKILL.md)(시연 서버 기동 + 네트워크 프로필 전환), [`integration-test-orchestrator`](../../.agents/skills/integration-test-orchestrator/SKILL.md)(iOS 빌드·설치·세션 로그 등 통합 테스트 세부)

---

## 1. 장비 개요

| 역할 | 장비 | 담당 |
| :--- | :--- | :--- |
| GPU 추론 서버 (FastAPI/Docker) | Windows (i9-13950HX + RTX 4090 Laptop) | 서버 담당 |
| LLM(Ollama) 호스트 + macOS 개발 머신 | Mac mini (Apple M4 Pro) | kb |
| iOS 클라이언트 단말 | iPhone 16 Pro Max | th |
| DB·미디어 저장 서버 | Raspberry Pi 5 Model B | Pi 운영 담당자 |

---

## 2. 네트워크 토폴로지 (2026-07-21 확정)

시연 테스트 환경에서는 4개 장비가 아래와 같이 연결된다. **서버 기동(역할별)과** 네트워크 전환·검증 절차는 [`rpi-network-profile-switcher`](../../.agents/skills/rpi-network-profile-switcher/SKILL.md) 스킬을 참조한다.

| 연결 | 방식 | 비고 |
| :--- | :--- | :--- |
| iPhone 16 Pro Max ↔ 서버(Windows) | Tailscale | 통합 테스트 때와 동일하게 유지. 단말이 시연 장소 LAN에 없어도 접속 가능 |
| 서버(Windows) ↔ LLM(Mac mini) | LAN | `COMPOSE_OLLAMA_BASE_URL=http://<Mac mini LAN IP>:11434`. Mac mini의 Ollama가 `OLLAMA_HOST=0.0.0.0`로 바인딩돼 있어야 함 |
| 서버(Windows) ↔ DB·미디어(Raspberry Pi) | LAN | `.env.network.demo`의 `DB_HOST`/`IMAGE_SERVER_BASE_URL`을 Pi의 LAN 주소로 설정 |
| 서버 ↔ DB·미디어(클라우드, 선택) | 공인/전용망 | `.env.network.cloud`: MariaDB `gildang_db`:3307 + Cloudflare R2. 절차 [`gildang_cloud_r2_guide.md`](gildang_cloud_r2_guide.md) |

**변경 이력**: 기존에는 GPU 추론(YOLO)과 LLM(Ollama)이 같은 장비(Windows)에서 함께 돌았으나, 이번 시연 구성부터 LLM을 Mac mini로 분리해 GPU 서버의 VRAM/연산 경합을 줄인다. `switch_rpi_network.sh demo` 실행 시 서버(Windows)는 **WSL2 안에서** 스크립트를 실행해야 한다(`docker-compose.yml`이 Linux/GPU 변형을 전제하므로).

---

## 3. GPU 추론 서버 (Windows)

```
===== CPU =====

Name                      : 13th Gen Intel(R) Core(TM) i9-13950HX
NumberOfCores             : 24
NumberOfLogicalProcessors : 32
MaxClockSpeed             : 2200


===== RAM =====

Capacity             : 17179869184 (16 GB) x2 = 32 GB
Speed                : 5600
ConfiguredClockSpeed : 5600
PartNumber            : HMCG78AGBSA092N
DeviceLocator (1)     : Controller0-ChannelA-DIMM0
DeviceLocator (2)     : Controller1-ChannelA-DIMM0


===== GPU =====

Name           : NVIDIA GeForce RTX 4090 Laptop GPU
DriverVersion  : 32.0.15.9579
VideoProcessor : NVIDIA GeForce RTX 4090 Laptop GPU
AdapterRAM     : 4293918720 (VRAM 보고값, 실제 VRAM 16GB - Windows WMI AdapterRAM은 4GB 상한 버그로 실용량과 다름)

Name           : Intel(R) UHD Graphics
DriverVersion  : 31.0.101.4146
VideoProcessor : Intel(R) RaptorLake-S Mobile Graphics Controller
AdapterRAM     : 1073741824
```

- `AnyViewerIddDriver Device`(원격 제어용 가상 디스플레이 어댑터)는 실제 GPU가 아니므로 표에서 제외했다.
- `docs/ops/ai_model_hardware_setup.md` §1.1 기준으로 이 장비는 CUDA GPU 서버 분류(`torch==2.13.0+cu130`)에 해당하며, RTX 5090(sm_120) 대비 낮은 세대이므로 팀 최대 사양이 아닌 개발/시연용 GPU로 취급한다.

---

## 4. LLM(Ollama) 호스트 + macOS 개발 머신 (Mac mini)

```
===== 기기 =====

Model Name       : Mac mini
Model Identifier : Mac16,11
Chip             : Apple M4 Pro
OS               : macOS (Darwin 25.5.0)


===== CPU =====

Name                       : Apple M4 Pro
NumberOfCores              : 14 (Performance 10 + Efficiency 4)
NumberOfLogicalProcessors  : 14
MaxClockSpeed              : N/A (Apple Silicon, sysctl 미노출)


===== RAM =====

Capacity              : 25769803776 (24 GB)
Speed                 : N/A (통합 메모리, LPDDR5, SoC 패키지 내장이라 WMI 방식 조회 불가)
ConfiguredClockSpeed  : N/A
Architecture          : Unified Memory (CPU/GPU/NPU 공유)


===== GPU =====

Name           : Apple M4 Pro (통합 GPU)
DriverVersion  : N/A (macOS는 별도 GPU 드라이버 버전 미노출)
VideoProcessor : Apple M4 Pro GPU, 20-core
AdapterRAM     : N/A (Unified Memory 24GB 공유, 별도 VRAM 없음)
Metal Support  : Metal 4
```

- `docs/ops/ai_model_hardware_setup.md` §1.1 기준으로 macOS는 Apple MPS 우선, 미지원 시 CPU 폴백 경로이며 CUDA 서버로 분류하지 않는다.
- 시리얼 넘버·Hardware UUID·Provisioning UDID는 기기 식별 정보라 이 문서에는 기록하지 않는다(`integration-test-orchestrator` 스킬 안전 가드레일과 동일 원칙).
- **LLM 호스트 역할(2026-07-21 신규)**: 이 장비에서 Ollama(`gemma4:e4b`, `nomic-embed-text`)를 구동하고, 서버(Windows)의 FastAPI 컨테이너가 LAN으로 접속한다. 데모 시연 시 `OLLAMA_HOST=0.0.0.0`로 바인딩하고 방화벽에서 `11434/tcp`를 서버 LAN 대역에 허용해야 한다(§2 참조).
- **시연 전 모델 상주**: 기본 `keep_alive`로 인한 콜드 로드(수 초)를 막으려면 Mac mini에서 `bash scripts/ollama_demo_keepalive.sh`를 실행한다(`rpi-network-profile-switcher` 스킬 전제조건). 스크립트는 GUI 루프백 바인딩을 감지하면 CLI/LaunchAgent로 `0.0.0.0:11434`를 강제한다.

---

## 5. iOS 클라이언트 단말 (iPhone 16 Pro Max)

| 항목 | 내용 | 출처 |
| :--- | :--- | :--- |
| 기종 | iPhone 16 Pro Max | `docs/changelogs/th.md` 2026-07-20 항목("iPhone 16 Pro Max 실기기에 `com.minchodan.app.th` 설치 및 실행 확인") |
| 칩/RAM/저장용량 | **문서에 기록 없음** | - |
| iOS 버전 | **문서에 기록 없음** | - |

- 프로젝트 문서에는 이 기기의 하드웨어 제원(칩/RAM/저장용량/iOS 버전)이 별도로 기록돼 있지 않다. 정확한 값이 필요하면 담당자(th)에게 실기기에서 직접 확인받아 이 표를 채워야 한다.
- **혼동 주의**: `docs/ops/ondevice_coreml_benchmark.md`에는 CoreML/ANE 벤치마크용으로 사용된 **다른 기기**(iPhone 14 Pro Max, 고태현 개인 소유, iOS 26.5)의 상세 제원이 있다. 이 문서의 iPhone 16 Pro Max와는 별개 기기이므로 시연 장비 스펙 비교 시 섞어 쓰지 않는다.

---

## 6. DB·미디어 저장 서버 (Raspberry Pi)

| 항목 | 내용 | 출처 |
| :--- | :--- | :--- |
| 모델 | Raspberry Pi 5 Model B | `docs/db_tailscale_guide/README.md`, `docs/changelogs/jy.md` |
| RAM | 16GB | `docs/changelogs/jy.md`("Raspberry Pi 5B 16GB 단일 장비") |
| 저장 장치 | SSD (외장, 인터페이스·용량 비공개) | `docs/db_tailscale_guide/README.md` |
| 저장 용량 | **의도적 비공개** | `docs/db_tailscale_guide/README.md` 39행 |
| OS/서비스 버전 | **의도적 비공개** | `docs/db_tailscale_guide/README.md` 39행 |
| 구동 서비스 | MariaDB 11.4(팀 공동 DB), 미디어 저장 API(FastAPI, 이벤트 프레임 JPEG·STT 원본 음성) | `docs/db_tailscale_guide/README.md` |
| 네트워크(test 프로필) | Tailscale 사설망 경유 | `.agents/skills/rpi-network-profile-switcher/SKILL.md` |
| 네트워크(demo 프로필) | 시연 장소 내부망(LAN), 서버(Windows)와 직접 라우팅 | `.agents/skills/rpi-network-profile-switcher/SKILL.md`, §2 |

- `docs/db_tailscale_guide/README.md` 39행은 "공개 문서에는 실제 호스트명, Tailscale IP, 서비스 버전, 현재 가동 상태, 디스크 용량을 기록하지 않는다"고 명시한다. 이는 문서 누락이 아니라 팀의 의도적 보안 정책이므로, 정확한 디스크 용량·OS 버전이 필요하면 Pi 운영 담당자에게 내부 채널로만 확인한다.
- 시연/테스트망 전환 절차는 `rpi-network-profile-switcher` 스킬을 참조한다.

---

## 7. 미확인 항목 요약

| 장비 | 미확인 항목 | 확인 방법 |
| :--- | :--- | :--- |
| iPhone 16 Pro Max | 칩, RAM, 저장 용량, iOS 버전 | 담당자(th) 실기기 확인 |
| Raspberry Pi 5B | SSD 정확한 용량, OS/서비스 버전, 호스트명 | Pi 운영 담당자에게 내부 채널로 확인 (공개 문서 기록 금지 정책 유지) |
| Mac mini | 시연 장소 LAN IP(`COMPOSE_OLLAMA_BASE_URL`에 필요), `OLLAMA_HOST=0.0.0.0` 바인딩 여부 | 시연 장소 도착 후 실측, `.env.network.demo`에 기록(Git-ignore 대상이라 문서에는 값을 남기지 않음) |
