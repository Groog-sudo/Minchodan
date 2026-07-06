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
