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
