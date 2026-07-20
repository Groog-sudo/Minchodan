# Changelog - jh (진형)

> 이 파일은 **jh(진형)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-07-01 | 7단계 | stage7_tts_design.md 문서 작성

- **커밋**: `doc : stage7__tts_design.md 문서 작성 (추후 피드백 및 수정 사항 관련 조정 예정)`
- **변경 내용**:
  - Minchodan 7단계 음성 안내 출력 (이중 채널) 설계서 신규 작성
  - 이중 채널 구조(반사=사전합성 클립, 인지=실시간 TTS), 아키텍처, 구현 파일 목록, 핵심 설계 결정, 클래스 분리, 이중 게이트 규칙, 검증 기준, 코딩 패턴 준수, 데이터 인터페이스, 에러 가드레일, 의존성 및 전제 등 상세 문서화
  - TEMPLATE.md 및 기존 설계서 스타일 준수
- **관련 파일**: `docs/stage7_tts_design.md`
- **검증 결과**: 문서 내용이 docs 기반 아키텍처 및 설계 원칙과 일치하도록 작성 완료
- **비고**: 추후 피드백 및 수정 사항 관련 조정 예정

---

### 2026-07-01 | 7단계 | TTSService 기본 추상화 계층 및 팩토리 구조 추가

- **커밋**: `feat : TTSService 기본 추상화 계층 및 팩토리 구조 추가`
- **변경 내용**:
  - TTSService 추상 클래스 및 get_tts_service() 팩토리 골격 작성
  - TTS_ENGINE 환경변수 기반 엔진 선택 로직 추가
  - 프로젝트 코딩 패턴(경로 계산, env 로드) 준수
  - 가독성을 위한 파트별 주석 대폭 추가
- **관련 파일**: `server/tts/tts_service.py`
- **검증 결과**: 기본 틀 구조 작성 및 코드 가독성 확보(미완성 상태)
- **비고**: 실제 [TTS 모델 구현체(Kokoro/Coqui)폐기된 상태(사실상 폐기된 상태)] 연동 및 클라이언트 react-native-tts 중심 전환 시 수정 예정

---

### 2026-07-02 | 7단계 | Redis 기반 경보 억제기 뼈대 추가

- **커밋**: `feat(tts): 실시간 TTS 서비스 추상화와 Redis 기반 경보 억제기 뼈대 추가(추가 사항 시 수정 예정)`
- **변경 내용**:
  - `server/tts/suppressor.py` 신규 추가로 `AlertSuppressor` 클래스의 기본 골격을 구성함
  - `device_id`와 `alert_id`를 조합한 Redis 억제 키 생성 로직을 추가함
  - Redis `exists` 조회와 `setex` 등록 흐름을 통해 중복 경보 억제의 기본 동작을 정의함
  - TTL 기본값과 예외 처리, 싱글톤 인스턴스 노출까지 포함해 후속 연동이 가능한 초기 구조를 마련함
  - 현재 상태는 실제 파이프라인 완성 전의 기본 로직 뼈대 수준이며, 명명 정리와 Redis 핸들 정합성 보완이 필요한 단계임
- **관련 파일**: `server/tts/suppressor.py`
- **검증 결과**: 코드 골격 추가 완료, 실제 통합 검증은 후속 작업 필요
- **비고**: 커밋 메시지의 범위보다 실제 변경은 억제기 파일 추가에 집중되어 있음

---

### 2026-07-02 | 7단계 | 실시간 TTS 래퍼 기본 골격 추가

- **커밋**: `feat(tts): 실시간 TTS 서비스 추상화와 Redis 기반 경보 억제기 뼈대 추가(추가 사항 시 수정 예정)`
- **변경 내용**:
  - `server/tts/realtime_tts.py`에 `RealtimeTTS` 래퍼 클래스를 추가해 인지 경로의 실시간 음성 합성 흐름을 감싸는 기본 구조를 마련함
  - 텍스트 입력 검증, TTS 서비스 호출, MP3 바이트의 base64 인코딩 반환까지의 처리 골격을 정의함
  - 합성 실패 시 `None` 반환과 예외 로그 처리로 후속 통합 시 안전하게 확장 가능한 형태를 구성함
  - 전역 인스턴스를 노출해 향후 WebSocket 전송 및 안내문 재생 모듈과 연결하기 쉬운 초기 구조를 세움
  - 현재 상태는 실제 서비스 연동과 세부 정리 전의 미완성 뼈대 단계이며, 호출 주입 방식과 불필요한 import 정리는 후속 작업이 필요함
- **관련 파일**: `server/tts/realtime_tts.py`
- **검증 결과**: 구조 추가 완료, 실제 합성 및 전송 통합 검증은 후속 작업 필요
- **비고**: 구현 방향은 잡았지만, 아직 동작 완성본이 아니라 기본 프레임 수준임

---

### 2026-07-02 | 7단계 | TTS 출력 경로 기본 골격 통합 및 작업 이력 정리

- **커밋**: `feat, docs : 7단계 TTS 출력 경로 기본 골격 통합 및 작업 이력 정리`
- **변경 내용**:
  - `server/tts/realtime_tts.py` 신규 추가로 인지 경로 실시간 음성 합성 래퍼(`RealtimeTTS`) 기본 골격을 구성하고, 텍스트 입력 검증 및 base64 인코딩 반환 흐름을 정의함
  - `server/tts/reflex_clip_sender.py` 신규 추가로 반사 경로 사전합성 클립 전송 함수(`send_reflex_clip`) 기본 구조를 작성하고, 중복 억제 체크/고우선 전송/페이로드 조립 위치를 명시함
  - `docs/changelogs/jh.md`에 7단계 관련 작업 이력을 누적 정리해 changelog 기록을 보강함
- **관련 파일**: `server/tts/realtime_tts.py`, `server/tts/reflex_clip_sender.py`, `docs/changelogs/jh.md`
- **검증 결과**: 기본 골격 코드 및 문서 기록 반영 완료(실제 WebSocket 우선 전송 및 suppressor 연동은 후속 통합 검증 필요)
- **비고**: 본 커밋은 기능 완성보다 구조 통합과 작업 이력 정리에 중점을 둔 초기 단계임

---

### 2026-07-06 | 7단계 | LLM 출력 기반 실시간 TTS 합성 경로 추가

- **커밋**: `feat: LLM 출력 기반 실시간 TTS 합성 경로 추가 및 초기화 안정성 보강`
- **변경 내용**:
  - `server/tts/realtime_tts.py`에서 불필요한 import를 정리하고 `extract_llm_text`를 추가 임포트하여 LLM 결과 연계 준비를 완료함
  - `RealtimeTTS.__init__`에서 `get_tts_service()`를 즉시 호출하도록 수정해 TTS 서비스 초기화 안정성을 보강함
  - `synthesize`의 입력 검증 로그 메시지를 구체화하고 오디오 반환 설명 문구를 정리해 디버깅 가독성을 개선함
  - `synthesize_from_llm` 메서드를 신규 추가해 LLM 출력(dict/string)에서 텍스트를 추출한 뒤 기존 `synthesize` 경로로 합성하도록 통합함
- **관련 파일**: `server/tts/realtime_tts.py`
- **검증 결과**: 커밋 기준 단일 파일 변경 반영 완료(LLM 입력 포맷별 통합 동작 검증 및 TTS 엔진 실합성 테스트는 후속 수행 필요)
- **비고**: 기존 실시간 TTS 경로를 유지하면서 LLM 출력 직접 입력 경로를 추가한 확장 커밋임

---

### 2026-07-06 | 7단계 | 반사 경로 클립 전송 로직 구현 및 reflex alert 페이로드 확장

- **커밋**: `feat: 반사 경로 클립 전송 로직 구현 및 reflex alert 페이로드 확장. 위험 탐지 시 경보음 활성화`
- **변경 내용**:
  - `server/tts/reflex_clip_sender.py`에 `REFLEX_CLIP_MAP`/`DEFAULT_REFLEX_CLIP` 및 `_resolve_reflex_clip()`을 추가해 `alert_id` 기반 사전합성 클립 선택 로직을 구현함
  - `_resolve_beep_profile()`을 추가해 거리 기반 기본 비프 주기(`beep_interval_ms`)와 햅틱 패턴(`haptic_pattern`) 보정 규칙을 정의함
  - `send_reflex_clip()` 시그니처를 확장해 `panning`, `distance`, `beep_interval_ms`, `haptic_pattern`, `clip` 인자를 지원하고, 입력 검증 기준을 `direction` 필수로 정비함
  - 페이로드 타입을 `reflex_alert`로 정리하고 `device_id`, 자동 `event_id`, 거리/패닝/비프/햅틱 메타데이터 및 밀리초 타임스탬프를 포함하도록 확장함
  - `server.api.session_manager.manager` 연동을 통해 연결 여부 확인 후 즉시 전송하고, 성공 시 suppressor 마킹·실패 시 예외 로깅으로 전송 흐름을 완성함
- **관련 파일**: `server/tts/reflex_clip_sender.py`
- **검증 결과**: 커밋 기준 단일 파일 변경 반영 완료(실단말 연동 기준 반사 경로 우선 전송·중복 억제 동작 통합 검증은 후속 수행 필요)
- **비고**: 반사 경로에서 실시간 TTS를 사용하지 않고 사전합성 클립 기반 즉시 경보를 강화하는 방향으로 구조를 정리한 커밋임

---

### 2026-07-06 | 7단계 | Redis 경보 억제기 안정화 및 오타 호환 메서드 추가

- **커밋**: `feat: Redis 경보 억제기 안정화 및 오타 호환 메서드 추가`
- **변경 내용**:
  - `server/tts/suppressor.py`에서 기본 TTL 상수를 `DEFAULT_TTL`로 정리하고, 기존 참조 호환을 위해 `DEFALUT_TTL` 별칭 상수를 유지함
  - 중복 판별 메서드 명을 `should_suppress`로 정정하고, 기존 오타 호출 경로를 위한 `should_supperss` 래퍼를 추가해 하위 호환성을 확보함
  - Redis 조회 경로를 `redis_bus._redis` 기준으로 통일하고, 연결이 비어 있을 때 `redis_bus.connect()`를 선행 호출하는 방어 로직을 추가함
  - `mark_as_sent`에도 동일한 Redis 연결 보정 절차를 적용해 `setex` 기록 실패 가능성을 낮춤
  - 불필요 import 정리 및 import 순서 정돈으로 파일 가독성과 유지보수성을 개선함
- **관련 파일**: `server/tts/suppressor.py`
- **검증 결과**: 커밋 기준 단일 파일 변경 반영 완료(실서비스 환경 Redis 연결 단절/재연결 시나리오 통합 검증은 후속 수행 필요)
- **비고**: 기존 코드와의 호환성을 유지하면서 억제기 핵심 경로(조회·기록)의 안정성을 보강한 커밋임

---

### 2026-07-06 | 7단계 | Piper 기반 TTS 서비스 구현 및 LLM 출력 텍스트 추출 유틸 추가

- **커밋**: `feat(tts): Piper 기반 TTS 서비스 구현 및 LLM 출력 텍스트 추출 유틸 추가`
- **변경 내용**:
  - `server/tts/tts_service.py`에 `NullTTSService`와 `PiperTTSService`를 추가해 기존 추상 인터페이스 기반의 안전한 폴백 및 Piper ONNX 합성 구현을 제공함
  - `PIPER_MODEL_PATH`, `PIPER_CONFIG_PATH`, `PIPER_BINARY_PATH`, `PIPER_LENGTH_SCALE_MIN/MAX` 환경변수 기반 설정을 반영하고, `pygoruut` 표기를 `espeak`로 보정하는 runtime compat config 생성 로직을 구현함
  - Piper 실행 경로를 동기 함수(`_run_piper_sync`)로 분리하고 `asyncio.to_thread`를 적용해 이벤트 루프 블로킹을 줄이도록 합성 경로를 개선함
  - `get_tts_service()`를 `piper` 기본 엔진 중심으로 재구성하고, 미지원 엔진 값이나 초기화 실패 시 `NullTTSService`로 폴백하도록 안정성을 강화함
  - `extract_llm_text()` 유틸 함수를 추가해 LLM 출력(dict/string)에서 `guidance_text`/`answer`/`text`/`content` 키 우선으로 TTS 입력 문장을 추출할 수 있도록 확장함
- **관련 파일**: `server/tts/tts_service.py`
- **검증 결과**: 커밋 기준 단일 파일 변경 반영 완료(실제 Piper 바이너리 실행 환경에서 모델·설정 경로 유효성 및 합성 음성 품질 검증은 후속 수행 필요)
- **비고**: TTS 엔진을 piper 중심으로 정비하면서 오케스트레이션 출력과의 결합 지점을 함께 마련한 구조 확장 커밋임

---

### 2026-07-06 | 7단계 | TTS 패키지 진입점 export 정리 및 Piper 경로 공개

- **커밋**: `feat: TTS 패키지 진입점 export 정리 및 Piper 경로 공개`
- **변경 내용**:
  - `server/tts/__init__.py` 신규 추가로 TTS 패키지 진입점을 명시하고 모듈 역할(인지 경로/억제기 중심 노출)을 문서화함
  - `RealtimeTTS`, `realtime_tts`, `AlertSuppressor`, `Alert_suppressor`를 패키지 레벨에서 직접 import 가능하도록 재노출함
  - `NullTTSService`, `PiperTTSService`, `TTSService`, `get_tts_service`, `extract_llm_text`를 패키지 레벨 export에 포함해 Piper 기반 경로 접근성을 높임
  - `__all__`을 정의해 외부 공개 심볼 집합을 고정하고 import 경로 일관성을 강화함
- **관련 파일**: `server/tts/__init__.py`
- **검증 결과**: 커밋 기준 단일 파일 신규 추가 반영 완료(패키지 레벨 import 경로 사용처 통합 검증은 후속 수행 필요)
- **비고**: TTS 서브모듈 접근 지점을 단일 패키지 진입점으로 정리해 유지보수성과 재사용성을 높인 정리 커밋임

---

### 2026-07-06 | 7단계 | 인지 경로 가이드 전송에 오케스트레이션·TTS 연동 추가

- **커밋**: `feat: 인지 경로 가이드 전송에 오케스트레이션·TTS 연동 추가`
- **변경 내용**:
  - `server/detection/consumer.py`에 `run_orchestrator`와 `realtime_tts` 의존성을 추가해 인지 경로에서 오케스트레이션 결과 기반 가이드 전송이 가능하도록 연동함
  - DetectionResult 처리 시 `risk_hint`가 `mid`/`low`인 경우 `_send_cognitive_guide()`를 호출하도록 분기 로직을 확장함
  - 반사 알림 페이로드에 `panning`, `distance`, `beep_interval_ms`, `haptic_pattern` 필드를 추가해 클라이언트 경보 제어 정보를 강화함
  - `_send_cognitive_guide()` 메서드를 신규 구현해 탐지 결과를 오케스트레이션 입력으로 변환하고, `guidance_text` 검증 후 TTS 합성(base64)과 `guide` 타입 WS 전송까지 연결함
  - 가이드 생성 실패/텍스트 누락 케이스에 대한 경고·오류 로그를 추가해 런타임 관측성과 장애 대응성을 보강함
- **관련 파일**: `server/detection/consumer.py`
- **검증 결과**: 커밋 기준 단일 파일 변경 반영 완료(실단말 기준 guide 이벤트 수신·오디오 재생 및 오케스트레이션 지연 시간 통합 검증은 후속 수행 필요)
- **비고**: 반사 경로 즉시 경보를 유지하면서 인지 경로를 오케스트레이션/TTS까지 확장한 단계적 통합 커밋임

---

### 2026-07-06 | 7단계 | Piper 한국어 모델 호환 설정 및 추론 메타데이터 파일 정리

- **커밋**: `chore: Piper 한국어 모델 호환 설정 및 추론 메타데이터 파일 정리`
- **변경 내용**:
  - `server/models/piper/piper-kss-korean.onnx` 모델 바이너리 파일을 추가해 Piper 한국어 음성 합성 런타임 자산을 프로젝트에 포함함
  - `server/models/piper/piper-kss-korean.onnx.json` 설정 파일을 추가해 샘플레이트, 추론 파라미터(`noise_scale`, `length_scale`, `noise_w`), `phoneme_type`, `phoneme_id_map` 등 모델 메타데이터를 구성함
  - `server/models/piper/piper-kss-korean.compat.json` 파일을 추가해 STT/LLM/TTS 단계 메타데이터 및 출력 샘플(요청 ID, 단계별 타임스탬프, provider, audio URL)을 기록함
  - Piper 한국어 모델 자산(모델·설정·호환 메타데이터) 3종을 `server/models/piper/` 경로에 정리해 추론 및 디버깅 준비도를 높임
- **관련 파일**: `server/models/piper/piper-kss-korean.compat.json`, `server/models/piper/piper-kss-korean.onnx`, `server/models/piper/piper-kss-korean.onnx.json`
- **검증 결과**: 커밋 기준 3개 파일 신규 추가 반영 완료(실제 Piper 바이너리 연동 기반 음성 합성 실행 검증 및 모델 로드/출력 품질 검증은 후속 수행 필요)
- **비고**: `piper-kss-korean.compat.json`의 일부 한글 문자열은 인코딩 깨짐 형태로 기록되어 있어 후속 정규화가 필요할 수 있음

### 2026-07-06 | 7단계 | Changelog 정리 사전 작성

- **커밋**: docs(changelog): jh 7단계 작업 이력 정리
- **변경 내용**:
  - 2026-07-06 기준 7단계 관련 커밋 이력을 템플릿 형식으로 일관되게 정리함
  - 오케스트레이션·TTS 연동, Piper 모델 자산, TTS 패키지 export 정리 등 최근 변경 항목을 누락 없이 반영함
  - 각 항목에 커밋, 변경 내용, 관련 파일, 검증 결과, 비고를 동일한 구조로 통일함
  - 모델 메타데이터 항목의 인코딩 유의사항을 비고에 명시해 후속 정비 포인트를 남김
- **관련 파일**: `jh.md`
- **검증 결과**: 템플릿 필수 필드 구조 준수 확인, 최신 작업 이력 기준 누락 항목 없음
- **비고**: 이 항목은 실제 커밋 전 사전 작성본이며, 최종 반영 시점에 문구만 미세 조정하면 됩니다.

---

### 2026-07-06 | STT 테스트 | stt config 정책 검증 테스트 설명 정합화

- **커밋**: `test(stt): stt config 정책 검증 테스트 설명 정합화`
- **변경 내용**:
  - `validate_stt_runtime_config`가 현재 정책 기준에서 성공해야 한다는 테스트 목적 설명으로 정리함
  - `server/stt` 계층에 테스트 모드 헬퍼가 없어야 한다는 구조 검증 의도를 명확히 반영함
  - 향후 추가 가능한 경계값 실패 시나리오(언어 코드, beam_size, device/compute_type) 가이드를 주석에 명시함
- **관련 파일**: `tests/test_stt_config_policy.py`
- **검증 결과**: STT 정책 검증 테스트 설명이 현재 구현 코드와 정합하도록 반영 완료
- **비고**: 커밋 해시 `1c22e2ea23b41f23c3b7dc9db4fe7782737544f5`

---

### 2026-07-06 | STT 테스트 | faster-whisper 테스트 하네스 설명을 구현 기준으로 정리

- **커밋**: `test(stt): faster-whisper 하네스 설명을 구현 기준으로 정리`
- **변경 내용**:
  - tests 전용 하네스 목적(운영 코드와 테스트 모드 분리)을 유지하면서 설명을 최신화함
  - "하드코딩 메서드를 비워 둔다"는 문구를 실제 구현 완료 상태에 맞는 설명으로 교체함
  - 모델 캐시 재사용과 전사 결과 조립 테스트의 의도와 코드 동작 간 설명 불일치를 해소함
- **관련 파일**: `tests/test_stt_faster_whisper_mode_template.py`
- **검증 결과**: 테스트 하네스 주석/설명이 현재 구현된 테스트 로직과 일치하도록 반영 완료
- **비고**: 커밋 해시 `c594d08ab4134b0ca6096358a5efc5a12790bd44`

---

### 2026-07-06 | STT 테스트 | stt service 테스트 설명을 실제 검증 범위로 갱신

- **커밋**: `test(stt): stt service 테스트 설명을 실제 검증 범위로 갱신`
- **변경 내용**:
  - NotImplemented 전제 설명을 제거하고 위임/모델 캐시/결과 조립 검증 중심으로 목적을 재정렬함
  - 운영 예외/실패 경로는 현재 검증 범위 밖의 후속 확장 항목으로 분리해 안내함
  - 파일 상단 설명과 실제 assertion 포인트 간의 차이를 해소해 테스트 문서성을 높임
- **관련 파일**: `tests/test_stt_service_template.py`
- **검증 결과**: STT 서비스 테스트 설명이 현재 구현 테스트 항목과 정합하도록 반영 완료
- **비고**: 커밋 해시 `d0fa645567459307fef89ace9c200a95634c7a58`

---

### 2026-07-06 | STT 테스트 | stt-llm bridge 테스트 설명을 구현 흐름에 맞춤

- **커밋**: `test(stt): stt-llm bridge 테스트 설명을 구현 흐름에 맞춤`
- **변경 내용**:
  - NotImplemented 전제 문구를 제거하고 입력 변환/빈 입력 폴백/정상 매핑 검증 흐름으로 정리함
  - 예외 폴백(`source=stt-bridge-error`) 시나리오를 후속 추가 항목으로 명확히 구분함
  - `invoke_existing_llm` 동작 계약과 테스트 설명 간 정합성을 확보함
- **관련 파일**: `tests/test_stt_to_llm_bridge_template.py`
- **검증 결과**: 브리지 테스트 설명이 현재 코드 동작 기준으로 일관되게 정리됨
- **비고**: 커밋 해시 `0bbc41f6112633f701e5e4c0103dd7a68c7042e8`

---

### 2026-07-06 | STT 서버 | STT 패키지 진입점 export 설명 정리

- **커밋**: `feat(stt): 패키지 진입점 export 설명 정리`
- **변경 내용**:
  - STT 패키지 공개 심볼 목적을 파일 상단 설명으로 명시함
  - 상위 계층 import 안정성을 위한 `__all__` 사용 의도를 설명에 반영함
  - 구현 로직 변경 없이 문서성 주석만 정합화함
- **관련 파일**: `server/stt/__init__.py`
- **검증 결과**: STT 패키지 진입점 설명이 현재 export 구조와 일치하도록 반영 완료
- **비고**: 커밋 해시 `76ef157f19e460dedef00d9549285983d35edafe`

---

### 2026-07-06 | STT 서버 | 설정 상수 설명을 런타임 사용 기준으로 정합화

- **커밋**: `feat(stt): 설정 상수 설명을 런타임 사용 기준으로 정합화`
- **변경 내용**:
  - `stt_config` 상수가 서비스/브리지 경로에서 실제 사용된다는 점을 설명에 반영함
  - 정책 확정 이유에 런타임 `validate` 통과 요구사항을 추가함
  - 실행 코드 변경 없이 설정 주석만 최신화함
- **관련 파일**: `server/stt/stt_config.py`
- **검증 결과**: 설정 상수 설명이 현재 런타임 검증 및 서비스 사용 흐름과 정합함
- **비고**: 커밋 해시 `1cce492639f6d982e07cd61fcb09368bd3a0f5a1`

---

### 2026-07-06 | STT 서버 | 런타임 검증 함수 책임 범위 설명 보강

- **커밋**: `feat(stt): 런타임 검증 함수 책임 범위 설명 보강`
- **변경 내용**:
  - `runtime`/`bridge` 검증 함수의 역할 분리를 파일 상단 설명에 명시함
  - 설정 검증 책임 분리 의도를 코드 동작과 일치하게 정리함
  - 검증 로직 변경 없이 설명만 정합화함
- **관련 파일**: `server/stt/stt_runtime.py`
- **검증 결과**: 런타임 검증 설명이 함수 책임 분리 구조와 일관되게 반영됨
- **비고**: 커밋 해시 `f0322f8e2b2688f5d5b83a5c08d487faa78eafea`

---

### 2026-07-06 | STT 서버 | 스키마 역할 설명을 응답 단위 기준으로 명확화

- **커밋**: `feat(stt): 스키마 역할 설명을 응답 단위 기준으로 명확화`
- **변경 내용**:
  - `SegmentOut`과 `SttTranscribeResult`의 책임을 파일 주석에 명시함
  - 라우터/서비스/테스트 공용 스키마 의도를 현재 구조와 일치시킴
  - 데이터 모델 변경 없이 설명만 개선함
- **관련 파일**: `server/stt/stt_schema.py`
- **검증 결과**: 스키마 설명이 현재 STT 응답 모델 사용 방식과 정합함
- **비고**: 커밋 해시 `1473bf251f8baa43a1e1bc5322c642479ad28758`

---

### 2026-07-06 | STT 서버 | 서비스 docstring을 구현 동작 중심으로 정리

- **커밋**: `feat(stt): 서비스 docstring을 구현 동작 중심으로 정리`
- **변경 내용**:
  - `get_model` docstring을 캐시 재사용/예외 분기 중심 설명으로 갱신함
  - `_transcribe_production` docstring을 전사 결과 조립/예외 래핑 흐름에 맞게 정리함
  - 실행 로직 변경 없이 설명성 주석만 정합화함
- **관련 파일**: `server/stt/stt_service.py`
- **검증 결과**: 서비스 문서화가 실제 구현 동작과 일치하도록 반영 완료
- **비고**: 커밋 해시 `d0441b7f10af6c65b4a46d2d75855e5872e41091`

---

### 2026-07-06 | STT 서버 | 브리지 docstring을 폴백 계약 중심으로 정리

- **커밋**: `feat(stt): 브리지 docstring을 폴백 계약 중심으로 정리`
- **변경 내용**:
  - `invoke_existing_llm` 설명을 빈 입력/예외 폴백 계약 기준으로 갱신함
  - 오케스트레이션 재사용과 메타 정보 처리 의도를 문서화함
  - 브리지 동작 코드 변경 없이 설명 문구만 정합화함
- **관련 파일**: `server/stt/stt_to_llm_bridge.py`
- **검증 결과**: 브리지 설명이 현재 반환 계약(`stt-bridge-empty`, `stt-bridge-error`)과 일치함
- **비고**: 커밋 해시 `9dfcf905f576bc3bdc5b9cff9d5b788b5d0015fa`

---

### 2026-07-07 | 문서화 | jh changelog에 STT 작업 이력 추가 정리

- **커밋**: `docs(changelog): jh STT 테스트/서버 변경 이력 추가 정리`
- **변경 내용**:
  - TEMPLATE 양식에 맞춰 STT 테스트 4건과 STT 서버 6건 커밋 이력을 순서대로 정리함
  - 각 항목의 커밋 메시지, 핵심 변경 내용, 관련 파일, 검증 결과를 동일 구조로 통일함
  - 이후 커밋 전 검토가 쉽도록 항목 간 구분선과 서술 밀도를 일관되게 맞춤
- **관련 파일**: `docs/changelogs/jh.md`
- **검증 결과**: changelog 항목 구조가 TEMPLATE 필수 필드(커밋/변경 내용/관련 파일/검증 결과/비고)와 정합함
- **비고**: 본 항목은 jh.md 문서 갱신 내역을 기록하기 위한 문서화 엔트리임

---

### 2026-07-08 | STT 서버 | Whisper 기본 모델 정책을 medium으로 상향

- **커밋**: `feat(stt): Whisper 기본 모델 정책 small→medium 상향`
- **변경 내용**:
  - `MODEL_NAME_MAP` 기본 매핑을 `faster-whisper-small/small`에서 `faster-whisper-medium/medium`으로 변경함
  - `DEFAULT_REQUEST_MODEL` 값을 `faster-whisper-medium`으로 동기화하여 미매핑 요청 폴백 정책을 상향함
  - 나머지 STT 실행 정책(`language`, `beam_size`, `device`, `compute_type`)은 기존 값을 유지함
- **관련 파일**: `server/stt/stt_config.py`
- **검증 결과**: 설정 변경 기준으로 `MODEL_NAME_MAP`과 `DEFAULT_REQUEST_MODEL` 정합성 유지 확인
- **비고**: 현재 커밋 전 상태의 변경 내역 기록이며, 커밋 해시는 확정 후 추가 가능

---

### 2026-07-08 | STT API | STT 전사·가이드 라우터 연결 및 패키지 의존성 보강

- **커밋**: `feat(stt): STT 전사·가이드 라우터 연결 및 패키지 의존성 보강`
- **변경 내용**:
  - `server/api/stt_router.py`를 신규 추가해 음성 파일 업로드 기반 `POST /api/v1/stt/transcribe` 와 `POST /api/v1/stt/transcribe-and-guide` 엔드포인트를 구현함
  - 업로드 파일을 임시 경로로 저장한 뒤 `SttService.transcribe_file()`로 전사하고, 필요 시 `SttToLlmBridge.invoke_existing_llm()`로 기존 오케스트레이션 연결까지 이어지도록 배선함
  - `server/main.py`에 STT 라우터를 마운트하고 OpenAPI 태그에 STT 섹션을 추가해 API 노출 경로를 정리함
  - `requirements.txt`에 `faster-whisper` 의존성을 명시해 STT 런타임이 패키지 수준에서 설치 가능하도록 보강함
- **관련 파일**: `server/api/stt_router.py`, `server/main.py`, `requirements.txt`
- **검증 결과**: 라우터·메인 마운트·의존성 선언 반영 완료, 실제 음성 업로드 E2E 및 모델 실행 검증은 후속 필요
- **비고**: STT는 서비스/브리지/라우터의 입구가 생긴 상태이며, 클라이언트 녹음·업로드 경로와 실사용 검증은 아직 남아 있음

---

### 2026-07-08 | STT 연동 및 평가 | navigation 검증, 브리지 주석 정리, Top-5 평가 스크립트 정리

- **커밋**: `feat(stt): navigation 연동 검증, 브리지 주석 정리, Top-5 평가 스크립트 정리`
- **변경 내용**:
  - `server/stt/stt_to_llm_bridge.py`에서 STT 입력 정규화, 네비게이션 wake-up/shutdown, 목적지 파싱, POI/route 수립, 오케스트레이션 예외 폴백 흐름에 대해 바이브/하드코딩 주석을 반반 구조로 재정리함
  - `tests/test_stt_to_llm_bridge_template.py`에 목적지 파싱과 navigation 연동 검증 케이스를 추가해 wake-up, shutdown, 목적지 수립 성공/실패 흐름을 고정 시나리오로 확인하도록 확장함
  - `scripts/eval_hitrate.py`를 기준 Top-5 hit-rate 평가 스크립트로 정리해 `safety_guidelines.json` 103건 기준의 RAG 평가 루틴을 구성함
  - `data/safety_guidelines.json`은 33건에서 103건 규모로 확장된 상태를 유지하며, `objects`/`scene_type` 기반 평가 정합성을 확보함
  - `requirements.txt`에는 `faster-whisper`가 반영되어 STT 실행 의존성 조건을 만족함
- **관련 파일**: `server/stt/stt_to_llm_bridge.py`, `tests/test_stt_to_llm_bridge_template.py`, `scripts/eval_hitrate.py`, `data/safety_guidelines.json`, `requirements.txt`, `docs/changelogs/jh.md`
- **검증 결과**: `scripts/eval_hitrate.py` 실행 기준 RAG 평가 루틴 구성 확인, STT 라우터/브리지 연동 코드와 네비게이션 상태 전이 경로 확인 완료. 단, 테스트 실행은 현재 환경에서 `langgraph` 미설치로 수집 단계에서 중단됨
- **비고**: 이번 항목은 ⑤ navigation 검증을 중심으로 ① RAG 확충, ② 평가 스크립트 정리, ③ STT 의존성 반영, ④ 라우터 마운트 완료 상태까지 함께 묶어 정리한 통합 기록임

---

### 2026-07-10 | DB | detction_guidance_logs 기본틀 및 하드코딩 템플릿 추가

- **커밋**: `db: detction_guidance_logs 기본틀 및 하드코딩 템플릿 추가`
- **변경 내용**:
  - `detction_guidance_logs` 테이블 대응 ORM 매핑을 추가하고 `StreamType(reflex/cognitive/unknown)` enum, 인덱스, UNIQUE(event_id), FK(`app_users`/`user_devices`)를 반영함
  - 로그 저장용 DTO(`DetectionGuidanceLogCreate`, `DetectionGuidanceLogResponse`)를 추가해 DB 입력/응답 스키마 경계를 분리함
  - Repository 계층에 `DetectionGuidanceLogRepository`를 추가해 event_id 중복 조회 및 저장 경로를 구성함
  - `DetectionGuidanceLogService`를 신규 추가하고, 바이브/하드코딩 파트를 주석으로 명확히 구분한 템플릿 구조를 적용함
  - 하드코딩 핵심 구현부는 `NotImplementedError`와 단계별 힌트를 남겨 직접 작성 학습이 가능한 상태로 유지함
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/services/detection_guidance_log_service.py`
- **검증 결과**: 변경 파일 정적 오류 검사 기준 문법 오류 없음 확인(`models.py`, `schemas.py`, `repositories.py`, `detection_guidance_log_service.py`)
- **비고**: 본 커밋은 동작 완성본이 아니라 템플릿/골격 커밋이며, HARDCODE PART 구현은 후속 커밋에서 채울 예정임

---

### 2026-07-10 | DB | detection_guidance_logs 4개 파일 정합화 및 저장 서비스 동작 구현

- **커밋**: `feat(db): detection_guidance_logs 4개 파일 정합화 및 저장 서비스 동작 구현`
- **변경 내용**:
  - `server/db/models.py`에서 테이블명/인덱스명을 `detection_guidance_logs` 기준으로 정렬하고 `detected_objects_json`을 MySQL JSON(with sqlite fallback)으로 맞춤
  - `server/db/models.py`, `server/db/schemas.py`에서 타임스탬프 필드명을 `created_at`으로 통일함
  - `server/db/repositories.py`의 `DetectionGuidanceLogRepository.create()`를 add → commit → refresh 순서로 구현해 저장 경로를 완성함
  - `server/services/detection_guidance_log_service.py`의 `create_log()`를 구현해 event_id 중복 조회, 신규 저장, Response 변환 흐름을 동작 상태로 전환함
  - `build_detected_objects_json()`을 `json.dumps(..., ensure_ascii=False)`로 구현해 한글 JSON 직렬화가 유지되도록 반영함
- **관련 파일**: `server/db/models.py`, `server/db/repositories.py`, `server/db/schemas.py`, `server/services/detection_guidance_log_service.py`
- **검증 결과**: 변경 4개 파일 기준 정적 오류 검사에서 오류 없음 확인
- **비고**: 이력/관계 보존 정책(FK ON DELETE SET NULL)과 event_id 중복 방지 정책을 코드에 반영한 정합화 커밋임

---

### 2026-07-10 | 문서 | TTS/STT 문서 정합화 및 STT 통합 가이드 추가

- **커밋**: `docs: TTS/STT 문서 정합화 및 STT 통합 가이드 추가`
- **변경 내용**:
  - `docs/design/architecture.md`의 TTS 엔진/표기 내용을 현재 선택 이력(`pyttsx3` 기본, `piper` 선택, `supertonic` 최종 선정안) 기준으로 정리함
  - `docs/ops/environment_variables.md`에 TTS 엔진 선택 이력 및 현재 런타임 반영 범위를 보강함
  - `docs/stage-guides/stage7_tts_design.md` 버전을 `v0.4.0`으로 올리고 TTS 엔진 현황 및 환경 변수 설명을 최신화함
  - `docs/stage-guides/stage_stt_integration_guide.md`를 신규 추가해 `stt_audio -> STT -> Bridge -> TTS -> guide` 흐름, 메시지 계약, 가드레일, 테스트 체크리스트를 문서화함
- **관련 파일**: `docs/design/architecture.md`, `docs/ops/environment_variables.md`, `docs/stage-guides/stage7_tts_design.md`, `docs/stage-guides/stage_stt_integration_guide.md`, `docs/changelogs/jh.md`
- **검증 결과**: 문서 상호 참조 및 항목 정합성 점검 완료(코드 동작 검증은 별도 테스트 범위)
- **비고**: 문서 포맷은 기존 구조를 유지하고 내용 위주로 업데이트함

---

### 2026-07-10 | DB API | detection_guidance_logs 라우터 신규 추가 및 메인 배선

- **커밋**: `feat(api): detection_guidance_logs 라우터 추가 및 main 등록`
- **변경 내용**:
  - `server/api/detection_guidance_log_router.py`를 신규 생성해 로그 저장/조회용 REST 엔드포인트 기본틀을 추가함
  - HARDCODE/VIBE 파트를 분리해 함수/변수/코드 구조 설명과 직접 작성 힌트를 함께 배치함
  - `POST /api/v1/logs/detection-guidance`, `GET /api/v1/logs/detection-guidance/by-event`, `POST /api/v1/logs/detection-guidance/sample` 경로를 구성함
  - `server/main.py`에 `detection_guidance_log_router` import 및 `app.include_router(...)` 등록을 추가해 서버 기동 시 라우팅되도록 배선함
- **관련 파일**: `server/api/detection_guidance_log_router.py`, `server/main.py`, `docs/changelogs/jh.md`
- **검증 결과**: main 라우터 등록 경로 반영 완료, 라우터 파일 정적 진단 기준 문법 오류 없음
- **비고**: 학습형 구현 흐름을 위해 일부 HARDCODE 힌트 주석을 유지한 템플릿 형태로 반영함

---

### 2026-07-10 | DB API | detection_guidance_logs 라우터 제거 및 메인 배선 해제

- **커밋**: `revert(api): detection_guidance_logs 라우터 제거 및 main 배선 해제`
- **변경 내용**:
  - `server/api/detection_guidance_log_router.py` 파일을 제거해 로그 저장/조회용 REST 라우터 기본틀을 되돌림
  - `server/main.py`에서 `detection_guidance_log_router` import와 `app.include_router(...)` 배선을 제거해 미정의 심볼 오류가 남지 않도록 정리함
  - 결과적으로 detection_guidance_logs는 다시 모델/서비스 계층까지만 남고, HTTP 엔드포인트 노출은 해제된 상태로 정리됨
- **관련 파일**: `server/api/detection_guidance_log_router.py`, `server/main.py`, `docs/changelogs/jh.md`
- **검증 결과**: `server/main.py` 기준 미정의 심볼 오류 제거 확인
- **비고**: 라우터 구조 재설계 또는 WebSocket 경로 배선 방향 재검토 전의 정리 커밋임

---

### 2026-07-13 | RAG | 생활지원 통합 안내 RAG 파이프라인 추가

- **커밋**: `feat(rag,stt): convenience_guidelines 기반 생활지원 RAG 구축 및 STT 질의 분기 연동`
- **변경 내용**:
  - `data/convenience_guidelines.json` 신규 추가: 기관/서비스/인물/긴급연락망/FAQ/통합 문서 기반의 생활지원 더미 코퍼스 구성
  - `server/rag/convenience_rag.py` 신규 추가:
    - JSON 코퍼스를 문서 단위(`organization`, `service`, `person`, `emergency_contact`, `faq`, `rag_document`)로 정규화
    - Chroma 컬렉션(`convenience_guidelines`) 빌드/로딩 함수 추가
    - 질의 키워드 기반 편의성 질문 판별(`looks_like_convenience_query`) 추가
    - 검색 결과를 Gemini로 근거 기반 요약 응답하는 `ConvenienceKnowledgeBase.answer()` 구현
  - `scripts/build_convenience_db.py` 신규 추가:
    - convenience 전용 ChromaDB 빌드 CLI 스크립트 추가
    - JSON 경로/저장경로/컬렉션/임베딩 모델을 인자로 주입 가능하도록 구성
  - `server/stt/stt_to_llm_bridge.py` 수정:
    - 자유 질의응답 경로에서 근접 POI 질의 다음 단계로 convenience RAG 분기 추가
    - `question-convenience-rag` source와 RAG 메타(`rag_query`, `rag_results`, `rag_latency_ms`) 반환
- **관련 파일**: `data/convenience_guidelines.json`, `server/rag/convenience_rag.py`, `scripts/build_convenience_db.py`, `server/stt/stt_to_llm_bridge.py`, `docs/changelogs/jh.md`
- **검증 결과**:
  - `git diff --cached --stat` 기준 4개 파일 `1646 insertions(+), 1 deletion(-)` 확인
  - STT 브리지 캐시 diff에서 convenience RAG 분기 추가 내용 반영 확인

---

### 2026-07-13 | Changelog | 오늘 커밋 작업 요약(추가 정리)

- **요약 대상 커밋**:
  - `84c9281` - `feat(rag,stt): convenience_guidelines 기반 생활지원 RAG 구축`
  - `a39a089` - `feat(client,server,console): 실기기 WS/STT 안정화 및 콘솔 라이브피드 보정`
- **커밋별 핵심 내용**:
  - `84c9281`
    - 생활지원 코퍼스(`data/convenience_guidelines.json`) 추가
    - convenience 전용 RAG 모듈(`server/rag/convenience_rag.py`) 및 DB 빌드 스크립트(`scripts/build_convenience_db.py`) 추가
    - STT 자유질의 경로에 convenience RAG 분기(`question-convenience-rag`) 연동
  - `a39a089`
    - 클라이언트 WS 재연결/종료 레이스 방지, STT 전송 전 연결 상태 가드 추가
    - 서버 STT 짧은 오디오 가드(`MIN_STT_AUDIO_BYTES=4096`) 및 data URI base64 허용 보강
    - STT WhisperModel 초기화 동시성 lock 적용
    - 콘솔 라이브피드 90도 회전 보정 및 bbox 좌표 변환, 동적 API base URL/재연결 안정화
    - `console/public/favicon.ico`, `console/public/favicon.svg`, `scripts/fix_android_usb_ws.ps1`, `package-lock.json` 반영
- **검증 결과**:
  - 두 커밋 모두 `origin/jh` 푸시 완료
  - 현재 항목은 당일 작업 추적 강화를 위한 후속 정리 기록

---

### 2026-07-14 | 콘솔 UI | MCP 검증 모니터 레이아웃 정리 및 gitignore 추적 정리

- **커밋**:
  - `e407fb0` - `refactor(console): MCP 검증 모니터 레이아웃/스타일 정리 및 gitignore 추적 파일 제거`
  - `df0d5b8` - `fix(console): MCP/지연 요약 패널에 monitor-latency-layout 래퍼 연결`
- **변경 내용**:
  - `console/src/components/McpValidationMonitor.tsx`: 카드/그리드 인라인 스타일을 CSS 클래스(`panel-mcp`, `mcp-grid`, `mcp-card`)로 분리하고 루트 요소를 `section.panel.panel-mcp`로 정리
  - `console/src/pages/DashboardPage.tsx`: `McpValidationMonitor`와 `LatencySummaryPanel`을 상단 `dashboard-grid` 밖으로 재배치하고, `section.monitor-latency-layout`으로 감싸 2열 배치를 실제로 적용
  - `console/src/styles.css`: `.panel-title`, `.panel-content`, `.panel-mcp`, `.mcp-grid`, `.mcp-card`, `.monitor-latency-layout` 및 반응형(1024px/720px) 그리드 규칙 추가
  - `console/src/styles.css`: 좌측 MCP 열에서 카드가 2x2로 보이도록 `.monitor-latency-layout .mcp-grid` 오버라이드 추가
  - `.claude/` 하위 스킬·설정 파일의 Git 추적을 제거해 `.gitignore`의 `.claude/` 정책과 정합화 (로컬 스킬은 `.agents/skills/` 기준 유지)
  - `server/models/piper/piper-kss-korean.onnx` Git 추적 제거 (`*.onnx` gitignore 정책 정합, 로컬 폴백 가중치는 필요 시 별도 배치)
  - `scratch/create_default_admin.py` 제거 (`scratch/` gitignore 정책 정합)

---

### 2026-07-16 | RAG 데이터 | 편의 데이터 전화번호·시간·날짜·주소 하이픈 제거

- **커밋**: `data(rag): convenience_guidelines 전화번호·시간·날짜·주소 하이픈 제거`
- **변경 내용**:
  - `data/convenience_guidelines.json`에서 전화번호 문자열에 남아 있던 하이픈을 제거해 STT/TTS 음독 시 끊김이 없도록 정리함
  - 시간, 날짜, 주소 관련 숫자 표기와 함께 남아 있던 하이픈을 제거해 한글 음독 일관성을 높임
  - 긴급 연락망의 내부 연락 순서 항목까지 포함해 대상 필드의 하이픈 제거를 일괄 반영함
- **관련 파일**: `data/convenience_guidelines.json`, `docs/changelogs/jh.md`
- **검증 결과**: 대상 필드 하이픈 점검 스크립트 실행 결과 0건 확인
- **비고**: 숫자 한글화 정규화 이후 후속 정리로, 실제 음독 품질과 검색 데이터 일관성을 함께 맞추는 보정 작업임

---

### 2026-07-16 | 콘솔 UI | 회원 목록 및 Detection Guidance Log 페이지네이션 UX 통일

- **커밋**: `feat(console): 회원 목록 및 detection guidance log 페이지네이션 UX 통일`
- **변경 내용**:
  - `MembersPage`의 등록 회원 목록 페이지네이션을 이전/다음 화살표, 10개 번호창, `...` 점프 검색, 마지막 페이지 버튼 형태로 정리함
  - `...` 점프 버튼 클릭 시 페이지 번호를 직접 입력하는 검색 팝오버를 추가해 버튼이 보이지 않는 구간으로도 바로 이동할 수 있게 함
  - `totalCount <= 11`일 때는 페이지네이션 컨트롤을 비활성화해 소량 데이터에서 불필요한 조작을 막도록 정리함
  - `DetectionGuidanceLogTable`에도 동일한 페이지네이션 UX를 적용하고, `DashboardPage`에서 직접 페이지 점프 콜백을 전달하도록 연결함
  - 콘솔 스타일에 맞춰 점프 버튼 폭과 팝오버 스타일을 정리하고, 전체 건수 표시처럼 불필요한 문구는 제거함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`
- **검증 결과**: `console` 빌드(`npm run build`) 성공 확인
- **비고**: 회원 관리와 감지 이력의 페이지 이동 패턴을 동일하게 맞춰 운영자 콘솔의 조작 일관성을 높인 작업임
  - `docs/ops/reports/` 임시 역활 보고서(TTS 반사경로·Navigation 가이드 기준 연동 적용 완료 보고서) 삭제
- **관련 파일**: `console/src/components/McpValidationMonitor.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `.claude/**`, `server/models/piper/piper-kss-korean.onnx`, `scratch/create_default_admin.py`, `docs/ops/reports/`, `docs/changelogs/jh.md`
- **검증 결과**:
  - 1차 커밋 `e407fb0` GitHub `origin/jh` 반영 확인 완료
  - 후속 수정: CSS에만 있던 `.monitor-latency-layout`을 DashboardPage에 연결해 레이아웃 미적용 상태 해소
  - 콘솔 로고(`console/public/gildang-logo.jpeg`)는 UI 참조 유지로 복원하여 제외
  - 정적 레이아웃 리팩터 위주 변경으로 단위 테스트 미실행
- **비고**: 기능 변경 없이 콘솔 모니터 패널 구조/스타일 정리와 저장소 추적 정리에 초점

## Commit Message

style(console): MCP 모니터와 지연 요약 패널 분리 및 MCP 1행 레이아웃 정리

## Staged Changes (정확 기준)

- 대상 파일: `console/src/pages/DashboardPage.tsx`
  - `McpValidationMonitor`와 `LatencySummaryPanel`을 `monitor-stack-layout` 래퍼로 감싸 별도 섹션으로 분리
  - 두 패널이 같은 블록 안에서 세로로 쌓이되, 서로 간격이 명시적으로 유지되도록 구조 정리

- 대상 파일: `console/src/styles.css`
  - `.monitor-stack-layout` 신규 추가
    - `display: flex`
    - `flex-direction: column`
    - `gap: 20px` (모바일에서는 `16px`)
  - `.mcp-grid`를 결과/출력량을 고려한 데스크톱 `1행 4열` 구조로 유지하면서 카드 간 여백을 `14px`로 조정
  - `.mcp-grid`에 `align-items: stretch`를 추가해 카드 높이 차이로 레이아웃이 흔들리지 않도록 보정
  - 기존 `.monitor-latency-layout` 의존 배치 흔적(중간 해상도 1열 전환 규칙, 좌측 2x2 전용 override)을 제거해 현재 구조와 스타일 규칙을 일치시킴

## Scope

- 관리자 콘솔 대시보드의 MCP 검증 패널 및 파이프라인 지연 요약 패널 배치/간격/UI 구조만 변경
- API, 상태관리, 백엔드 로직, 데이터 계약 변경 없음

---

# 2026-07-14 Commit Note

## Commit Message

style(console): 회원등록 폼 1열 세로 정렬 및 등록 버튼 높이 조정

## Staged Changes (정확 기준)

- 대상 파일: `console/src/styles.css`
- `.member-form` 레이아웃을 다열 자동 배치에서 1열 고정으로 변경
  - `grid-template-columns: 1fr`
  - `row-gap: 16px`, `column-gap: 0`
- `.member-form label` 간격을 `gap` 단일값에서 축별 값으로 조정
  - `row-gap: 14px`, `column-gap: 6px`
- 회원등록 폼 내부 등록 버튼 세로 크기 증가
  - `.member-form .refresh-btn { padding: 10px 10px; }`

## Scope

- 회원관리 페이지의 등록 폼 UI 배치 및 버튼 높이만 변경
- 비즈니스 로직/API/상태관리 변경 없음

---

## Commit Message

fix(console): localhost 하드코딩 제거 및 네트워크 URL 해석 공통화

## Pending Changes (정확 기준)

- 신규 파일 추가: `console/src/config/network.ts`
  - `resolveApiBaseUrl(apiBaseUrlFromEnv?)`:
    - `VITE_API_BASE_URL`이 없거나 파싱 실패 시 `http(s)://{현재브라우저호스트}:8000` 폴백
    - env 주소가 `localhost/127.0.0.1/::1`인데 콘솔 접속 호스트가 원격이면 현재 브라우저 호스트로 자동 치환
    - trailing slash 제거
  - `resolveServiceUrl(envUrl, pathFromApiBase, apiBaseUrlFromEnv?)`:
    - 서비스별 URL env(`VITE_MONITOR_STREAM_URL`, `VITE_NAV_MAP_URL`) 우선
    - 없거나 파싱 실패 시 API Base + 경로로 생성
    - localhost 원격접속 치환 동일 적용

- 변경 파일: `console/src/components/Login.tsx`
  - 로그인 엔드포인트를 `http://localhost:8000/api/v1/admin/login` 하드코딩에서
    `resolveApiBaseUrl(...)` 기반 `LOGIN_ENDPOINT`로 변경

- 변경 파일: `console/src/api/useMembers.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경

- 변경 파일: `console/src/api/useDetectionLogs.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경

- 변경 파일: `console/src/api/useLiveFeed.ts`
  - `API_BASE_URL` 생성 로직을 공통 `resolveApiBaseUrl(...)` 사용으로 변경
  - 이 값을 기반으로 WS URL(`.../ws/console/live-feed`) 유지

- 변경 파일: `console/src/api/useMonitorStream.ts`
  - `DEFAULT_STREAM_URL`을 고정 문자열에서 `resolveServiceUrl(...)` 계산값으로 변경
  - `resolvedUrl` 계산도 공통 URL 해석 함수 사용하도록 변경

- 변경 파일: `console/src/components/LiveCameraFeed.tsx`
  - `NAV_MAP_URL`을 고정 기본값 대신 `resolveServiceUrl(...)` 기반으로 변경

- 변경 파일: `console/src/components/OperatorLiveMap.tsx`
  - `NAV_MAP_URL`을 고정 기본값 대신 `resolveServiceUrl(...)` 기반으로 변경

## Scope

- 콘솔의 API/SSE/WS/지도 URL 결정 로직 공통화
- localhost 하드코딩으로 인한 원격 접속 `Failed to fetch` 재발 방지
- UI/DB 스키마/백엔드 비즈니스 로직 변경 없음

---

### 2026-07-14 | 콘솔 UI | 라이트박스 스크롤 위치를 컨테이너로 전환하고 상세 패널 폭을 확장

- **커밋**: `fix(console): lightbox-content 스크롤 위치를 컨테이너로 전환하고 상세 패널 폭 확장`
- **변경 내용**:
  - `lightbox-content`에 세로 스크롤을 부여해 이미지 내부가 아니라 모달 본체에서 스크롤되도록 조정함
  - `frame-overlay-lightbox`의 내부 스크롤과 높이 제한을 제거해 이미지가 별도 스크롤바를 만들지 않도록 정리함
  - `frame-detail-body`, `frame-detail-header`, `lightbox-content`, `lightbox-summary`를 전체 폭으로 확장해 오른쪽 빈공간이 남지 않도록 보정함
- **관련 파일**: `console/src/styles.css`, `console/src/components/DetectionGuidanceLogTable.tsx`
- **검증 결과**: `npm run build` 성공
- **비고**: 라이트박스 상세 UI의 가로 여백과 세로 스크롤 위치를 사용자가 요청한 형태로 정리한 변경임

---

### 2026-07-15 | 콘솔 UI | 회원 등록 폼 1열 고정 복원 및 배치 규칙 단순화

- **커밋**: `style(console): 회원 등록 폼 1열 고정 배치 복원`
- **변경 내용**:
  - `member-form` 그리드를 2열에서 1열(`grid-template-columns: 1fr`)로 되돌려 사용자 요청대로 고정 배치함
  - 2열 전용 확장 규칙(`label:first-of-type`, `label:last-of-type`, 900px 미디어쿼리)을 제거해 스타일 충돌 가능성을 낮춤
  - 등록 버튼을 1열 폼 흐름에 맞춰 `justify-self: stretch` 기준으로 정렬하고 최소 너비 제한을 해제함
- **관련 파일**: `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 레이아웃 변경은 회원 등록 폼 영역에 한정되며 비즈니스 로직/API 변경 없음

---

### 2026-07-15 | 콘솔 UI | 회원 등록 폼 라벨-입력 정렬 및 간격 미세 조정

- **커밋**: `style(console): 회원 등록 폼 라벨/입력/버튼 정렬 미세 조정`
- **변경 내용**:
  - `MembersPage.tsx`의 회원 등록 각 `label` 텍스트를 `span.member-form-label-text`로 감싸 라벨 텍스트 위치를 입력창 기준으로 제어 가능하게 구조화함
  - `styles.css`에서 `.member-form input`을 폭 `35%`와 중앙 정렬(`margin: 0 auto`)로 설정해 필드 길이를 MVP 데모 기준에 맞게 축소함
  - `.member-form-label-text`를 동일 폭(`35%`)·왼쪽 정렬로 지정해 라벨 텍스트가 가운데 배치된 입력창의 좌상단에 맞춰 보이도록 조정함
  - `.member-form .refresh-btn`도 폭 `35%`·중앙 정렬로 맞추고 상단 여백을 `5px`로 조정해 입력창과 버튼 간격을 일관화함
  - `.member-form-hint`와 폼 사이 하단 간격을 `10px`로 줄여 시각적 밀도를 정리함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 회원 등록 폼의 정보 배치 가독성 개선 목적의 스타일 조정이며 API/비즈니스 로직 변경 없음

---

### 2026-07-15 | 콘솔 UI | refresh 버튼 자동 폭 복원 및 회원 등록 폭 비율 조정

- **커밋**: `style(console): refresh 버튼 폭 자동화 및 회원 등록 폼 폭 40% 조정`
- **변경 내용**:
  - 공통 `.refresh-btn`의 고정 폭을 제거하고 `inline-flex + width: fit-content`로 변경해 `새로고침 중...` 텍스트가 버튼 상자 밖으로 넘치지 않도록 조정함
  - `.member-form input` 폭을 `35%`에서 `40%`로 상향해 회원 등록 입력창 가독성을 개선함
  - `.member-form .refresh-btn` 폭도 `35%`에서 `40%`로 함께 조정해 입력창과 버튼의 폭 기준을 통일함
- **관련 파일**: `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 스타일 레이어만 조정했으며 API/데이터 로직 변경 없음

---

### 2026-07-15 | 콘솔 UI | 대시보드 관제 우선순위 재배치 (Live/Telemetry 상단 고정)

- **커밋**: `refactor(console): 대시보드 관제 패널 우선순위 순서 재배치`
- **변경 내용**:
  - `Live Feed` + `TELEMETRY FEED`를 대시보드 최상단 섹션으로 고정 배치함
  - `파이프라인 지연 요약`을 그 아래 단독 섹션으로 이동해 운영 지연 확인 우선순위를 상향함
  - `발화 추적 타임라인` 바로 아래에 `MCP 검증 모니터`가 오도록 순서를 정렬함
  - `SystemMetrics`, `SessionStatus`, `AiPipelineMonitor`, `DetectionFeed` 4개 패널은 후순위 `dashboard-grid`로 하향 배치함
  - 기존 `monitor-stack-layout` 래퍼 사용을 제거하고 섹션 단위 배치로 정리함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 컴포넌트 내부 로직 변경 없이 렌더링 순서만 조정한 레이아웃 리팩터링

---

### 2026-07-15 | 콘솔 UI | 회원관리 단일 컨테이너화 및 좌측 카테고리 탭 전환 기본틀 구현

- **커밋**: `feat(console): 회원 등록/목록 통합 컨테이너와 좌측 카테고리 탭 전환 추가`
- **변경 내용**:
  - `MembersPage.tsx`에 `activeCategory` 상태(`"register" | "list"`)를 추가해 단일 컨테이너 내 화면 전환 상태를 관리하도록 구현함
  - 기존 분리되어 있던 `회원 등록` 패널과 `등록 회원 목록` 패널을 `panel-member-shell` 하나로 병합하고, 내부를 `member-shell-layout`(좌측 nav + 우측 content) 구조로 재배치함
  - 좌측 네비게이션에 `회원 등록`, `등록 회원 목록` 버튼을 추가하고 클릭 시 `activeCategory` 값 변경으로 각 섹션만 렌더링되도록 조건부 렌더링을 적용함
  - 목록의 `회원 정보 입력` 버튼 클릭 시 폼 프리필 동작과 함께 `setActiveCategory("register")`를 호출해 등록 탭으로 즉시 전환되도록 연결함
  - `styles.css`에 `member-shell-nav`를 `10%` 폭(`flex-basis/max-width 10%`)으로 제한하는 규칙과 활성 버튼(`member-shell-nav-btn-active`) 스타일을 추가해 요구된 배치 기준을 반영함
  - 반응형 대응으로 1024px 이하에서 좌측 nav를 상단 2열 버튼으로 전환하는 폴백 규칙을 추가해 좁은 화면에서의 사용성을 유지함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 서버/API 함수·import 변경 없이 화면 구조와 로컬 상태 기반 탭 전환만 구현한 UI 레이어 작업

---

### 2026-07-18 | 콘솔 UI | 위젯 기능상자 전체삭제 확인 모달 구현

- **커밋**: `feat(console): 기능상자 전체삭제 확인 모달 추가`
- **변경 내용**:
  - 기능상자 메뉴의 `전체 삭제`를 즉시 실행 방식에서 확인 모달 방식으로 변경함
  - `DashboardPage.tsx`에 `isRemoveAllConfirmOpen` 상태와 모달 열기/취소 핸들러를 추가해 삭제 의사 확인 플로우를 구현함
  - 확인 모달 문구를 `현재 기능상자들을 전부 삭제하시겠습니까?`로 표시하고, `예` 선택 시 전체삭제 실행, `아니오` 선택 시 모달만 닫히도록 처리함
  - `removeAllWidgets` 실행 완료 시 모달 상태까지 초기화해 잔여 UI 상태가 남지 않도록 정리함
  - `styles.css`에 모달 오버레이/컨테이너/버튼 스타일(`widget-confirm-*`)을 추가해 대시보드 톤과 맞는 확인 UI를 적용함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 요청사항인 `위젯 기능 기능상자 안에 전체삭제 기능에서 모달상자로 삭제 여부 창 기능 구현` 기준으로 최소 범위 변경만 반영함

---

### 2026-07-18 | 콘솔 UI | MCP 검증 및 저지연 모니터 기능상자 누락 명칭 복구 및 타임라인 상단 배치

- **커밋**: `fix(console): DashboardPage 위젯 누락(mcpMonitor) 복구 및 타임라인 위 배치`
- **변경 내용**:
  - `DashboardPage.tsx`의 기능상자 위젯 타입/목록/기본 순서에서 누락된 `mcpMonitor` 명칭을 복구함
  - `McpValidationMonitor` import는 유지한 상태로, 렌더 분기에 `mcpMonitor` 케이스를 연결해 실제 기능상자에서 다시 표시되도록 복구함
  - 기본 위젯 순서를 조정해 `MCP 검증 및 저지연 모니터`가 `발화 추적 타임라인` 바로 위에 배치되도록 정렬함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 요청사항인 `MCP 검증 및 저지연 모니터 기능상자 import 밑 DashboardPage.tsx 에서 누락된 명칭 살리기`를 기준으로 최소 범위만 반영함

---

### 2026-07-15 | 운영콘솔 UI | Detection Guidance Log 스트림 필터 드롭다운 및 깨진 이미지 fallback 보정

- **커밋**: eat(console): Detection Guidance Log 스트림 선택 UI와 깨진 이미지 fallback 개선
- **변경 내용**:
  - DetectionGuidanceLogTable.tsx에 스트림 필터 상태(ll/reflex/cognitive)와 드롭다운 열기/닫기 상태를 추가하고, 전체/인지/반사 선택 기반 행 필터링을 구현함
  - 필터 UI를 panel-header-actions에서 분리해 제목 아래 배치하고, 외부 클릭 시 닫히는 드롭다운 상호작용을 추가함
  - FrameWithOverlay에 이미지 로드 실패 감지(onError)를 추가해 깨진 이미지에 rame-overlay-broken 클래스를 부여하고 bbox 렌더를 중단하도록 처리함
  - styles.css에서 rame-detail-body, lightbox-content 내 깨진 이미지 fallback 크기를 40x40px로 통일해 레이아웃 붕괴를 방지함
  - LatencySummaryPanel.tsx, DashboardPage.tsx의 최근 콘솔 레이아웃/표시 정비 변경을 함께 커밋 범위에 포함함
- **관련 파일**: console/src/components/DetectionGuidanceLogTable.tsx, console/src/components/LatencySummaryPanel.tsx, console/src/pages/DashboardPage.tsx, console/src/styles.css, docs/changelogs/jh.md
- **검증 결과**:
  pm run build 성공
- **비고**: 워킹트리의 client/src/services/frameCaptureProviderSelect.android.ts 변경은 사용자 지정 범위에 따라 이번 커밋에서 제외함

---

### 2026-07-15 | 운영콘솔 UI | Detection Guidance Log 스트림 필터 드롭다운 및 깨진 이미지 fallback 40x40 적용

- **커밋**: feat(console): Detection Guidance Log 스트림 선택 UI와 깨진 이미지 fallback 40x40 적용
- **변경 내용**:
  - DetectionGuidanceLogTable.tsx에 스트림 필터 상태(all/reflex/cognitive)와 드롭다운 열기/닫기 상태를 추가하고, 전체/인지/반사 선택 기반 행 필터링을 구현함
  - 필터 UI를 panel-header-actions에서 분리해 제목 아래 배치하고, 외부 클릭 시 닫히는 드롭다운 상호작용을 추가함
  - FrameWithOverlay에 이미지 로드 실패 감지(onError)를 추가해 깨진 이미지에 frame-overlay-broken 클래스를 부여하고 bbox 렌더를 중단하도록 처리함
  - styles.css에서 frame-detail-body, lightbox-content 내 깨진 이미지 fallback 크기를 40x40px로 통일해 레이아웃 붕괴를 방지함
  - LatencySummaryPanel.tsx, DashboardPage.tsx의 최근 콘솔 레이아웃/표시 정비 변경을 함께 커밋 범위에 포함함
- **관련 파일**: console/src/components/DetectionGuidanceLogTable.tsx, console/src/components/LatencySummaryPanel.tsx, console/src/pages/DashboardPage.tsx, console/src/styles.css, docs/changelogs/jh.md
- **검증 결과**: npm run build 성공
- **비고**: 워킹트리의 client/src/services/frameCaptureProviderSelect.android.ts 변경은 사용자 지정 범위에 따라 이번 커밋에서 제외함

---

### 2026-07-15 | 콘솔 UI | 회원 등록 좌측 정렬 및 발화 추적 타임라인 간격/폭 미세 조정

- **커밋**: `style(console): 회원 등록 좌측 정렬 및 발화 추적 타임라인 밀도 조정`
- **변경 내용**:
  - `styles.css`에서 `.member-form-label-text`, `.member-form input`, `.member-form .refresh-btn`의 자동 가운데 정렬 마진을 제거해 회원 등록 입력창과 버튼을 좌측 기준으로 정렬함
  - `trace-timeline-table`을 `table-layout: auto`로 전환하고 `시간`, `위험도`, `트리거`, `발화문` 열 폭을 다시 배분해 발화 추적 타임라인의 공백 비율을 축소함
  - `td.trace-time`에 폭 `130px` 및 좌우 패딩 축소를 적용해 시간 셀의 과한 가로 여백을 줄임
  - `시간-트랙`, `트리거-발화문` 경계 패딩을 미세 조정하고 `trace-hit` 정렬을 좌측으로 변경해 텍스트 겹침 없이 더 촘촘하게 보이도록 보정함
- **관련 파일**: `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 회원 관리 등록 폼과 발화 추적 타임라인의 시각 밀도 조정만 포함하며 API/비즈니스 로직 변경은 없음

---

### 2026-07-16 | 콘솔 UI | 회원 등록 폼 2열(3:3) 배치 및 주소/버튼 전체폭 정렬

- **커밋**: `style(console): 회원 등록 폼 2열 배치와 주소/버튼 폭 정렬`
- **변경 내용**:
  - `MembersPage.tsx` 회원 등록 필드 순서를 2열 3행 구조로 재배치함: `기기 식별자|장애 정도`, `이름|생년월일(선택)`, `전화번호|보호자 연락처(선택)`
  - `MembersPage.tsx`의 `주소(선택)` 필드에 `member-form-field-full` 클래스를 추가해 단일 행 전체폭(2칸 span)으로 확장함
  - `styles.css`에서 `.member-form`을 2열 그리드(`repeat(2, minmax(0, 30%))`)로 변경하고 좌측 기준 시작점(`padding-left: 45px`)을 유지함
  - `styles.css`에서 일반 입력창은 칸 폭(`width: 100%`)을 사용하도록 통일하고, 주소 필드(`.member-form-field-full`)와 등록 버튼(`.member-form .refresh-btn`)을 `grid-column: 1 / span 2`로 맞춰 동일 길이로 정렬함
  - `styles.css`에 `@media (max-width: 1100px)` 폴백을 추가해 작은 화면에서는 1열 레이아웃으로 안전하게 전환되도록 처리함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 회원 관리 화면의 폼 배치/스타일 변경만 포함하며 API/비즈니스 로직은 변경하지 않음

---

### 2026-07-16 | RAG 데이터 | STT/TTS 음독 안정화를 위한 숫자 한글화 정규화

- **커밋**: `data(rag): convenience_guidelines 숫자 한글화 및 시간/날짜/전화/주소 표기 정규화`
- **변경 내용**:
  - `data/convenience_guidelines.json`의 STT/TTS 음독 대상 문자열에서 숫자 표기를 한글 음절(`공일이삼사오육칠팔구`) 기준으로 정규화함
  - 전화번호를 하이픈 단위 한글 숫자 표기로 통일함
  - 시간 표기를 `다시` 구분 형식으로 정리함
  - 날짜 표기를 `다시` 구분 형식으로 정리함
  - 주소의 건물번호/우편번호 숫자 표기를 한글 숫자로 변환함
- **관련 파일**: `data/convenience_guidelines.json`, `docs/changelogs/jh.md`
- **검증 결과**: JSON 파싱 검증 완료, 요청된 필드(시간/날짜/전화/주소) 숫자 한글화 반영 완료
- **비고**: ID/타입 키 및 좌표(lat/lon)는 시스템 참조/연동 호환을 위해 유지함

---

### 2026-07-16 | Git·문서 | jh → dev 병합 및 convenience Chroma 재빌드

- **커밋**: dev merge commit + docs sync
- **변경 내용**:
  - `origin/jh` 2커밋을 `dev`에 `--no-ff` 병합(충돌 없음, `DetectionGuidanceLogTable`/`DashboardPage`/`styles.css` 자동 병합).
  - `python scripts/build_convenience_db.py`로 `data/chroma_db/convenience_guidelines` 재빌드(75문서, 한글화 JSON 반영).
  - `api_specification.md` v0.4.23: convenience 재빌드 절차·콘솔 페이지네이션 UX 명시.
- **배포 전 확인**: dev/스테이징에서도 `build_convenience_db.py` 재실행(Ollama `nomic-embed-text` 필요).

---

### 2026-07-17 | 콘솔 UI | 회원 등록 입력 검증 강화, 페이지네이션 색상 조정, 스트림 선택 정렬/페이지네이션 보정

- **커밋**: `fix(console): 회원 등록 검증 강화와 스트림 필터 페이지네이션 정합성 보정`
- **변경 내용**:
  - 회원 등록 폼의 입력값 검증을 필드 단위로 강화하고, 잘못된 형식 입력 시 해당 입력창에 인라인 경고 문구와 오류 스타일이 보이도록 적용함
  - `기기 식별자(device_uuid)`는 일련번호 숫자 3자리를 반드시 포함하도록 규칙을 강화해, 규칙 미충족 시 즉시 fallback 경고 메시지가 노출되도록 구현함
  - `장애 정도`는 `장애등급 N급` 형식 검증을 강제하고, 형식이 맞지 않으면 `잘못된 입력 정보입니다` 경고를 표시하도록 반영함
  - 회원 등록 페이지네이션 비활성 버튼 색상을 가독성 개선 목적에 맞춰 최종적으로 흰색 톤으로 조정함(텍스트/테두리)
  - Detection Guidance Log의 스트림 선택(전체/인지/반사) 시 해당 스트림 데이터만 표시되도록 필터를 강제하고, 선택 변경 시 1페이지로 리셋되도록 보정함
  - 스트림별 실제 데이터 건수에 맞춰 서버/클라이언트 페이지네이션 총 페이지를 재계산하도록 연동했으며, 남은 페이지가 번호창 내에 모두 노출되는 경우 `...`/마지막 페이지 버튼을 숨기도록 정리함
  - 인지/반사 선택 시 최신 데이터가 우선 노출되도록 `detected_at` 기준 내림차순 정렬을 화면 표시 단계에서 재확인하도록 반영함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `console/src/styles.css`, `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/api/useDetectionLogs.ts`, `server/api/detection_log_router.py`, `server/services/detection_guidance_log_service.py`, `server/db/repositories.py`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 사용자 요청 3건(회원 등록 fallback 처리, 회원 목록 페이지네이션 색상, 스트림 선택 시 정렬/페이지 정합성)을 하나의 정합성 개선 커밋으로 묶어 반영함

---

### 2026-07-17 | 콘솔 UI | 파이프라인 지연 요약 카드 1줄 정렬 및 폭 균등화

- **커밋**: `style(console): 파이프라인 지연 요약 카드 1줄 정렬과 폭 균등화`
- **변경 내용**:
  - `LatencySummaryPanel`의 `latency-stat-grid`를 9열 기준으로 재배치해 지연 지표 카드가 아래로 떨어지지 않고 한 줄에 정렬되도록 보정함
  - 카드 간 gap과 내부 padding을 축소하고, 카드 최소 폭 제약을 제거해 우측 여백을 최소화함
  - 각 카드의 라벨/평균/보조 텍스트 글자 크기와 줄높이를 조금 낮춰 한 줄 배치 시 내용이 깨지지 않도록 조정함
  - 결과적으로 `파이프라인 지연 요약` 카드들이 동일한 가로 폭으로 나란히 보이도록 정렬 품질을 개선함
- **관련 파일**: `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공
- **비고**: 기능 변경 없이 대시보드의 지연 요약 패널 시각 배치만 정리한 스타일 보정 작업임

---

### 2026-07-17 | 콘솔 UI | 관제 대시보드 위젯 기능 MVP 복구(추가/옵션/삭제) 및 카드 정렬 보정

- **커밋**: `feat(console): 관제 대시보드 위젯 추가/삭제 MVP 복구와 카드 헤더 정렬 보정`
- **변경 내용**:
  - `DashboardPage.tsx`에 위젯 키(`latency/liveFeed/telemetry/timeline/guidanceLog/riskLog`) 기반 렌더 구조를 재도입하고, 기본 표시 순서를 상태로 관리하도록 복구함
  - main-nav 하단에 `기능상자 추가` 버튼과 위젯 선택 목록을 추가해 선택한 기능상자만 표시되도록 구현함
  - `SSE` 라인은 위젯 대상에서 제외하고 기존처럼 고정 표시를 유지함
  - 각 위젯 카드 우상단에 `⋮` 옵션 트리거를 배치하고, 옵션 팝오버에는 `삭제` 버튼만 제공해 해당 위젯 제거가 가능하도록 구현함
  - 위젯 wrapper 클래스(`widget-<key>`)를 부여해 카드별 레이아웃 제어 지점을 명확히 함
  - `styles.css`에 위젯 툴바/선택 메뉴/옵션 메뉴/삭제 액션 스타일을 추가하고, 헤더 우측 여백(`panel-header` padding-right)을 부여해 옵션 버튼이 제목 텍스트를 가리지 않도록 보정함
  - Live Feed와 Device Telemetry & Control 카드의 세로 높이가 대칭되도록 공통 최소 높이와 패널 stretch 규칙을 추가하고, 모바일 구간에서는 해당 고정 높이를 해제함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 사용자 요청에 따라 기존 TSX 연결에 필요한 import/함수/변수는 임의 삭제하지 않고, 위젯 기능 복구와 레이아웃 보정만 최소 범위로 반영함

---

### 2026-07-17 | 생활지원 RAG | BGE-M3 전환 및 재현 가능한 클린 빌드 적용

- **커밋**: `feat(rag): 생활지원 임베딩을 BGE-M3로 전환`
- **변경 내용**:
  - 생활지원 RAG 전용 기본 임베딩 모델을 `nomic-embed-text`에서 Ollama `bge-m3`로 전환함
  - `build_convenience_db.py`가 기본 실행 시 기존 전용 ChromaDB를 삭제하고 다시 생성하도록 변경해 반복 빌드의 중복 적재를 방지함
  - 기존 DB에 의도적으로 추가 적재해야 하는 경우에만 `--keep-existing` 옵션을 사용하도록 분리함
  - `.env.example`, `README.md`, 환경 변수 명세에 BGE-M3 설치와 생활지원 DB 재빌드 절차를 추가함
- **관련 파일**: `.env.example`, `README.md`, `scripts/build_convenience_db.py`, `server/rag/convenience_rag.py`, `docs/ops/environment_variables.md`, `docs/changelogs/jh.md`
- **검증 결과**: 34문서, 고유 source ID 34건, 중복 0건, BGE-M3 벡터 1024차원 확인. 대표 한국어 질의 3건의 기대 문서 Top-1 검색 확인
- **팀원 적용 절차**: `ollama pull bge-m3` 실행 후 `.env.example`의 생활지원 전용 설정을 `.env`에 반영하고 `python scripts/build_convenience_db.py` 실행
- **비고**: ChromaDB 산출물과 Ollama 모델은 Git 추적 대상이 아니며, 원본 JSON과 추적 가능한 설정·빌드 절차로 각 환경에서 동일하게 재생성함

---

### 2026-07-17 | 콘솔 UI | Detection Guidance Log 의미 분리 및 대시보드 위젯 옮기기/삭제 옵션 확장

- **커밋**: `feat(console): 로그 텍스트 의미 분리와 위젯 이동 옵션 추가`
- **변경 내용**:
  - `DetectionGuidanceLogTable.tsx`에서 `파이프라인 텍스트`를 사용자 입력(STT 전사) 전용으로 축소해 `TTS 안내문`과 의미가 겹치지 않도록 분리함
  - 기존 `파이프라인 텍스트` 영역에서 LLM 응답/최종 안내문을 제거하고, 상세 정보는 별도 `파이프라인 디버그` 섹션으로 분리해 운영자 디버깅 정보는 유지함
  - 대시보드 위젯 카드 옵션에 `옮기기`를 추가하고, 선택 위젯만 드래그 가능하도록 이동 모드를 적용함
  - 드롭 완료 또는 드래그 종료 시 이동 모드를 자동 해제하도록 처리해 조작 실수를 줄임
  - `styles.css`에 이동 모드 시각 피드백(`widget-move-mode`, `widget-move-target`, `widget-drop-target`)과 `옮기기` 옵션 스타일을 추가함
- **관련 파일**: `console/src/components/DetectionGuidanceLogTable.tsx`, `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: Detection Guidance Log의 `파이프라인 텍스트`는 STT 입력 맥락 확인용, `TTS 안내문`은 최종 출력 멘트 확인용으로 역할을 명확히 분리함

---

### 2026-07-17 | 콘솔 UI | 회원 등록 장애등급 범위 검증(1~6급) 및 경고문 강화

- **커밋**: `fix(console): 회원 등록 장애등급 범위 경고 추가`
- **변경 내용**:
  - 회원 등록 폼의 `장애 정도` 입력 검증에서 `장애등급 N급` 형식을 먼저 확인한 뒤, 숫자 등급을 파싱해 **1~6급 범위만 허용**하도록 강화함
  - 형식은 맞지만 범위가 벗어난 입력(예: `장애등급 7급`)에 대해 `올바르지 않은 장애등급입니다. 최대 장애 등급은 6급입니다.` 경고문이 즉시 표시되도록 반영함
  - 범위 내 입력(1~6급)만 정상 제출 가능하도록 폼 검증 흐름을 유지함
- **관련 파일**: `console/src/pages/MembersPage.tsx`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 기존 형식 오류 메시지(`잘못된 입력 정보입니다. 예: 장애등급 1급`)와 범위 오류 메시지를 분리해 운영자가 원인을 즉시 구분할 수 있도록 개선함

---

### 2026-07-17 | 콘솔 UI | 기능상자 메뉴에 추가/전체 삭제 통합

- **커밋**: `feat(console): 기능상자 메뉴에 추가와 전체 삭제 통합`
- **변경 내용**:
  - 대시보드 툴바를 `기능상자` 단일 버튼 중심으로 재구성하고, 클릭 시 `추가`/`전체 삭제` 2개 카테고리를 동일 메뉴에서 제공하도록 변경함
  - `추가` 클릭 시에만 추가 가능한 기능상자 목록을 노출하고, 추가 가능한 항목이 없으면 빈 상태 문구(`추가 가능한 위젯이 없습니다.`)를 표시하도록 적용함
  - `전체 삭제` 클릭 시 현재 표시 중인 기능상자를 모두 제거하도록 처리하고, 메뉴/이동 모드/드롭 상태를 함께 초기화해 잔여 상태가 남지 않도록 보정함
  - `styles.css`에서 기존 툴바의 별도 전체 삭제 버튼 스타일을 제거하고, 메뉴 내 위험 액션(`widget-picker-item-danger`)과 구분선(`widget-picker-divider`) 스타일을 추가함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `console/src/styles.css`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 기존 `기능상자 추가`와 `기능상자 전체 삭제`의 분리 배치를 메뉴형 UX로 통합해 관리 동선을 단순화함

---

### 2026-07-18 | 콘솔 UI | 기능상자 추가 버튼 비활성화 조건 적용

- **커밋**: `feat(console): 기능상자 추가 버튼 비활성화 적용`
- **변경 내용**:
  - 관제 대시보드 `기능상자` 메뉴에서 `추가` 버튼에 비활성화 조건을 적용함
  - 추가 가능한 기능상자가 하나도 없을 때(`availableWidgets.length === 0`) `추가` 버튼이 비활성화되도록 처리함
  - 모든 기능상자가 이미 배치된 상태에서는 `추가` 버튼이 즉시 비활성 상태로 표시되어 불필요한 클릭을 방지함
- **관련 파일**: `console/src/pages/DashboardPage.tsx`, `docs/changelogs/jh.md`
- **검증 결과**: `npm run build` 성공(콘솔 타입체크/번들링 통과)
- **비고**: 요청사항인 `위젯 기능 기능상자 버튼 내 추가되는 기능상자 없을 시 추가 버튼 비활성화` 기준으로 최소 변경만 반영함

---

### 2026-07-19 | 보안·인프라·문서 | 전면 보안 강화 이력 및 팀 반영 가이드 문서화

- **커밋**: `security: 프로젝트 전면 보안 강화 및 팀 적용 가이드 추가`
- **변경 배경**:
  - 미사용 `@expo/ngrok`과 관련 전이 취약점 제거에서 시작해 프로젝트 전체를 다시 감사한 결과, JWT 기본값, 최초 관리자 생성, 역할 기반 권한, 단말 인증, URL 토큰, STT 자원 제한, 디버그 API, 모바일 평문 통신, Docker·Redis·MariaDB, 환경 파일 권한과 공급망 의존성까지 함께 보완해야 했음
  - 코드만 병합하면 기존 JWT·Redis·DB 비밀번호, 콘솔 세션, 단말 토큰, 네이티브 앱 설정이 자동으로 전환되지 않으므로 팀원별 후속 절차를 단일 문서로 제공할 필요가 있었음
  - 팀 GPU 서버 최대 사양인 RTX 5090과 Ubuntu·Windows·macOS 3개 운영체제에서 의존성 설치 기준이 달라, 보안 업데이트가 실행 호환성을 깨지 않도록 OS별 PyTorch·CUDA·MPS 경로와 검증 절차를 함께 기록함
- **보안 구현 요약**:
  - 모든 환경에서 예측 불가능한 32자 이상 JWT 서명 키를 강제하고, `aud`·`exp`·`iat`·`iss`·`jti`·`nbf` 클레임과 bcrypt 12 rounds·관리자 비밀번호 정책을 적용함
  - 최초 최고관리자 1회 부트스트랩과 최고관리자 전용 추가 등록을 분리하고, 활성 DB 계정·현재 역할을 요청마다 검증해 관리자·운영자 권한 경계를 강화함
  - 정적 단말 토큰을 기본 비활성화하고 장치 ID에 결합된 만료 JWT, 인증 후 WebSocket 세션 등록, 콘솔 첫 인증 메시지 방식을 적용함
  - URL 쿼리 토큰을 제거하고 REST·SSE는 Authorization 헤더, 보호 이미지는 인증 fetch, 콘솔 토큰은 탭 종료 시 제거되는 `sessionStorage`를 사용하도록 변경함
  - 관리자 로그인·부트스트랩·단말 JWT 발급·STT 요청에 제한을 추가하고 STT 업로드를 기본 최대 10 MiB·동시 2건·허용 확장자로 제한함
  - 운영 API 문서와 상세 헬스 정보를 축소하고, 디버그·내비게이션 시뮬레이터를 명시적 플래그와 권한으로 잠그며 CORS·보안 응답 헤더를 강화함
  - iOS ATS와 Android cleartext·backup·레거시 권한을 강화하고 개인 IP·토큰·Tailscale 주소 하드코딩 폴백을 제거해 필수 설정 누락 시 연결이 실패하도록 변경함
  - Docker 포트를 loopback에 바인딩하고 Redis·MariaDB 비밀번호를 필수화했으며 비root 실행, 읽기 전용 마운트, `no-new-privileges`, 환경 파일 Docker context 제외를 적용함
  - 비밀값을 출력하지 않고 원자적으로 생성하며 Unix 계열에서 환경 파일 권한을 `0600`으로 제한하는 `scripts/configure_security_secrets.py`를 추가함
  - 외부 XML 파서를 `defusedxml`로 교체하고 취약 의존성을 갱신했으며 npm·pip 감사와 Dependabot을 CI 기준에 포함함
  - Ubuntu·Windows RTX 5090은 PyTorch 2.13·CUDA 13.0 `cu130`, macOS는 PyTorch 2.13 MPS 우선·CPU 폴백으로 분리하고 실제 1-step을 확인하는 `scripts/verify_gpu.py`를 정합화함
- **문서 변경 내용**:
  - `docs/security/README.md`를 신규 작성해 보안 문서 원칙, 독해 순서, 갱신 조건, 비밀정보 금지 기준과 현재 잔여 위험을 인덱스화함
  - `docs/security/security_hardening_and_team_adoption_guide.md`를 신규 작성해 수정 전 이슈와 피해 시나리오, 구현 조치, 제한 수치, 담당·운영체제별 반영 순서, 토큰 회전 영향, 검증 명령, 배포 승인, 사고 대응과 잔여 위험을 상세히 정리함
  - `docs/README.md` 실제 문서 트리에 `security/`를 추가하고 문서 목록·권장 독해 순서를 갱신했으며, 루트 `README.md` 문서 인덱스에도 상세 가이드 링크를 추가함
- **팀원 적용 핵심**:
  - 운영 환경은 비밀값 스크립트 실행 전에 반드시 `APP_ENV=production`을 설정하고 `ALLOW_STATIC_DEVICE_TOKENS=false`를 유지해야 함
  - 새 JWT 서명 키 적용 후 기존 관리자·단말 토큰은 모두 무효가 되므로 콘솔 재로그인과 장치별 JWT 재발급이 필요함
  - Redis·DB 비밀번호 변경은 Compose와 기존 데이터 볼륨 계정을 안전하게 동기화해야 하며, 불일치를 이유로 공동 DB 볼륨을 삭제하면 안 됨
  - iOS `Info.plist`·`AppDelegate.swift`와 Android manifest 변경은 Metro reload만으로 반영되지 않으므로 네이티브 clean build·실기기 재설치를 수행해야 함
  - Tailscale 호스트 도달, FastAPI `/health`, 인증 WebSocket, 실제 음성·탐지 흐름을 서로 다른 검증 단계로 확인해야 함
- **검증 결과**:
  - Python 비통합 테스트 `361 passed, 11 deselected, 4 warnings`, 보안 집중 테스트 `17 passed`
  - Ruff 전체 검사 오류 0, Bandit `server/`·`scripts/` 발견 이슈 0, 보안 변경 핵심 파일 mypy 오류 0
  - 모바일 TypeScript 검사와 콘솔 production build 통과, `client`·`console` npm audit 알려진 취약점 0
  - 일반·macOS Docker Compose config 통과, `pip check` 통과, ChromaDB의 수정 버전 없는 공개 취약점 예외 외 직접 고정 Python 의존성 감사 통과
  - Git 추적 파일에서 비밀 패턴 미검출, 로컬 환경 파일 Git 제외·Unix 권한 `600`, `git diff --check` 통과
  - macOS 로컬 PyTorch 2.13·torchvision 0.28 설치 및 CPU 1-step 통과; 현재 프로세스 MPS와 Ubuntu·Windows RTX 5090, iOS·Android 실기기 WSS는 후속 실장 검증으로 남김
- **관련 파일**: `docs/security/README.md`, `docs/security/security_hardening_and_team_adoption_guide.md`, `docs/README.md`, `README.md`, `docs/changelogs/jh.md`
- **잔여 위험**:
  - `chromadb==1.5.9`의 `CVE-2026-45829`·`PYSEC-2026-311`은 현재 수정 버전이 없어 로컬 `PersistentClient`와 네트워크 경계로 임시 통제하며 수정 버전 발표 후 즉시 갱신해야 함
  - 현재 요청 제한기는 단일 프로세스 메모리 기반이므로 다중 워커·다중 서버 전 Redis 기반 분산 제한기로 교체해야 함
  - 개인정보 DB 필드 암호화, 장치 JWT 개별 `jti` 폐기 목록, Keychain·Keystore 기반 운영 단말 프로비저닝은 후속 과제로 남음
- **비고**: 문서와 명령 예시에는 실제 비밀값·개인 IP·Tailscale 주소·사용자 개인정보를 기록하지 않았으며, 과거 Changelog·비교 연구의 ngrok 언급은 역사 기록일 뿐 현재 설치·운영 기준이 아님
