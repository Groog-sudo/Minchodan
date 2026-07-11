# Changelog - jy (준영)

> 이 파일은 **jy(준영)**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.

---

### 2026-06-26 | 공통 | Changelog 관리 체계 전환 및 한국어 안내 자동화 스크립트 수정

- **커밋**: `refactor: changelog per-member append system and localized scripts`
- **변경 내용**:
  - 기존 작업별 개별 파일 방식의 changelog를 팀원별 단일 파일 누적(append) 방식으로 마이그레이션했습니다.
  - 이에 따라 `docs/changelogs/README.md` 및 `TEMPLATE.md`를 신규 누적형 기준에 맞춰 수정했습니다.
  - 팀원별 changelog 파일 5개(`dg.md`, `jh.md`, `jy.md`, `kb.md`, `th.md`)를 신규 생성하고 기존의 baseline 이력을 이관하였습니다.
  - `scripts/prework.sh`, `scripts/postwork.sh` 내의 안내 메시지 및 사용자 질문을 모두 한국어로 지역화(localization)했습니다.
  - Windows cmd 환경에서 발생하는 CP949 한국어 특수 문자 인코딩 에러를 방지하기 위해 `scripts/prework.bat` 및 `scripts/postwork.bat`를 영어로 복원하고 CP949 호환성을 개선했습니다.
  - Windows 환경의 한국어 안내 지원을 위해 UTF-8 BOM 인코딩 기반의 PowerShell 스크립트 `scripts/prework.ps1` 및 `scripts/postwork.ps1`을 새롭게 추가하고, PowerShell 구문 오류를 수정하여 안정성을 확보했습니다.
  - 변경 사항에 맞추어 `README.md`, `skills.md`, `docs/git_branching_strategy.md`, `SCRIPT_GENERATION_PROMPT.md` 문서 내의 관련 레퍼런스를 일관되게 업데이트했습니다.
- **관련 파일**: `docs/changelogs/README.md`, `docs/changelogs/TEMPLATE.md`, `docs/changelogs/jy.md`, `scripts/prework.sh`, `scripts/postwork.sh`, `scripts/prework.bat`, `scripts/postwork.bat`, `scripts/prework.ps1`, `scripts/postwork.ps1`, `README.md`, `skills.md`, `docs/git_branching_strategy.md`, `SCRIPT_GENERATION_PROMPT.md`
- **검증 결과**:
  - `prework.ps1`, `postwork.ps1` 및 `prework.sh`, `postwork.sh` 스크립트 대화형 안내 및 유효성 검사 흐름 터미널 작동 확인 완료
  - 각 문서 내 구 레퍼런스(`2026-06-24_initial_baseline.md`)에 대한 정합성 일괄 교체 및 삭제 검증 완료

---

### 2026-07-03 | DB | DBeaver 세션 SQL 및 DB명 시트 기준 갱신

- **커밋**: 미커밋
- **변경 내용**:
  - Google Sheets `테이블_명세서`, `스키마_설계` 기준으로 `minchodan_db` 초기화 SQL을 재정리했습니다.
  - `admin_accounts`, `admin_login_audits`, `app_users`, `user_devices` 4개 테이블의 컬럼, 인덱스, FK 정책을 시트 기준과 맞췄습니다.
  - 기존 `minchodan_tmp`, 확장 컬럼, `ON DELETE CASCADE` 중심 설명을 제거하고 `ON DELETE RESTRICT` 및 사번 기반 감사 로그 구조를 문서화했습니다.
  - DBeaver 세션 SQL과 환경 변수 예시의 DB명을 `minchodan_db` 기준으로 정리했습니다.
- **관련 파일**: `Minchodan DB.session.sql`, `.env.example`
- **검증 결과**:
  - Google Sheets 메타데이터와 대상 탭 범위 확인 완료
  - SQL 본문에서 이전 DB명 및 제거 대상 컬럼 잔존 여부 검색 완료
  - 대상 SQL/Markdown 파일의 trailing whitespace 검색 완료

---

### 2026-07-03 | DB | SQLAlchemy ORM 모델 및 Pydantic DTO 추가

- **커밋**: 미커밋
- **변경 내용**:
  - 최종 4개 테이블 명세 기준으로 `server/db/models.py`에 SQLAlchemy 2.0 ORM 모델을 추가했습니다.
  - `app_users`와 `user_devices` 간 1:N 관계 및 `ON DELETE RESTRICT` 외래키 정책을 반영했습니다.
  - `server/db/schemas.py`에 생성용 DTO와 ORM 응답용 Pydantic V2 스키마를 분리해 추가했습니다.
  - SQLite 실행용 `server/db/schema.sql` DDL을 추가하고 ORM 핵심 관계 설명 주석을 보강했습니다.
  - 발표 방어 및 직접 하드코딩 학습을 위해 `models.py` 핵심 ORM 매핑 주석을 보강했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/schema.sql`
- **검증 결과**:
  - `compile()` 기반 순수 문법 검사 완료
  - SQLite 메모리 DB에서 `server/db/schema.sql` 실행 및 4개 테이블 생성 확인
  - `app_users` 삭제 시 연결된 `user_devices`가 있으면 `ON DELETE RESTRICT`로 차단되는지 확인
  - 현재 셸에 `ruff`, `sqlalchemy`, `pydantic` 런타임 의존성이 없어 린트 및 import 검증은 미실행

---

### 2026-07-06 | 문서 | DB 반영 내용 교차 검증 및 정합성 업데이트

- **커밋**: a1b2c3d (본인의 실제 커밋 해시 입력)
- **변경 내용**:
  - `server/db/` 신규 DB 계층을 `README.md`, `AGENTS.md`, `docs/AGENTS.md`의 서버 구조 설명에 반영했습니다.
  - `docs/ops/environment_variables.md`에 `.env.example`의 DB 환경 변수 6종을 추가하고 `DB_NAME=minchodan_db` 기준을 명시했습니다.
  - `Minchodan DB.session.sql` 상단 기준 설명에서 존재하지 않는 `back_sql` 참조를 제거하고 현재 기준 파일을 명시했습니다.
  - `.vscode` 로컬 DB 스키마 문서를 현재 4테이블 구조와 `ON DELETE RESTRICT` 기준으로 재정리했습니다.
- **관련 파일**: `README.md`, `AGENTS.md`, `docs/AGENTS.md`, `docs/ops/environment_variables.md`, `Minchodan DB.session.sql`, `.vscode/mariadb_admin_user_schema.md`, `.vscode/PROJECT_TECH_STACK_DATA_WORKFLOW.md`
- **검증 결과**:
  - `minchodan_app`, `ON DELETE CASCADE`, `disability_grade`, `login_id`, `ws_token_hash` 등 과거 초안 키워드 잔존 여부 검색 완료
  - `minchodan_db`, `DB_*`, `server/db`, `ON DELETE RESTRICT` 기준 반영 여부 검색 완료
  - `git diff --check` 통과

---

### 2026-07-08 | DB | MariaDB 연결 정보 환경 변수 로드 전환

- **커밋**: `db: 환경변수 기반 MariaDB 연결 설정`
- **변경 내용**:
  - `server/db/connection.py`의 MariaDB 비동기 접속 문자열 하드코딩을 제거하고 루트 `.env`의 `DB_*` 값을 조합해 사용하도록 변경했습니다.
  - `mysql+aiomysql` 기반 비동기 SQLAlchemy 엔진 설정은 유지하면서 `pool_pre_ping=True`, `pool_recycle=3600`, `expire_on_commit=False` 세션 팩토리 구성을 보존했습니다.
  - DB 연결에 필요한 런타임 의존성 항목을 `requirements.txt`의 고정 버전 목록에 정리했습니다.
- **관련 파일**: `server/db/connection.py`, `requirements.txt`
- **검증 결과**:
  - `.venv/bin/python -m py_compile server/db/connection.py` 통과
  - `.venv/bin/python -c "import server.db.connection as c; ..."` 기반 import 검증 통과
  - SQLAlchemy 엔진 URL은 비밀번호 마스킹 상태로 `mysql+aiomysql` 형식 확인
  - `git diff --check` 통과

---

### 2026-07-09 | DB | MariaDB Primary-Replica 실습 경로 정리 및 연결 모듈 정리

- **커밋**: `db: connection whitespace cleanup and replica notes`
- **변경 내용**:
  - Raspberry Pi 5B 16GB 단일 장비에서 `3306` Primary와 `3307` Replica를 분리 실행하는 1차 복제 실습 경로를 정리했습니다.
  - 향후 동일 스펙 별도 장비 추가 시 Primary-Replica, 자동 백업/복구 리허설, MaxScale/VIP 자동 페일오버 순서로 고도화하는 운영 방향을 정리했습니다.
  - MariaDB Replica 인스턴스의 AppArmor 프로파일(`mariadbd`)에서 `/var/lib/mysql-replica`, `/var/log/mysql-replica`, `/run/mysqld`, Raspberry Pi block device metadata 접근 허용이 필요한 원인을 확인했습니다.
  - `server/db/connection.py`의 `AsyncSession` 세션 팩토리 옵션 줄에 남아 있던 trailing whitespace를 제거했습니다.
- **관련 파일**: `server/db/connection.py`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `connection.py` import 검증 재실행 완료
  - `.venv/bin/python -m py_compile server/db/connection.py` 통과
  - `.venv/bin/python -c "import server.db.connection as c; ..."` 기반 SQLAlchemy URL 마스킹 출력 확인
  - `git diff --check` 통과

---

### 2026-07-09 | Docker | Compose 경량화, MariaDB 컨테이너 연결, 호스트 로컬 Ollama 전환

- **커밋**: `chore(docker): use host-local ollama with compose`
- **변경 내용**:
  - 프로젝트 루트 `.dockerignore`를 추가하여 실제 Docker build context에서 `.venv/`, `.env`, `.git/`, `client/`, `docs/`, 캐시·빌드 산출물 등이 제외되도록 정리했습니다.
  - `docker/.dockerignore`에는 실제 적용 파일이 루트 `.dockerignore`임을 안내하는 주석을 추가해, `docker/` 하위 ignore 파일만 보고 오해하지 않도록 보완했습니다.
  - `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`에 MariaDB 11.4 서비스를 추가하고, `Minchodan DB.session.sql` 초기화 SQL, `mariadb_data` 볼륨, healthcheck, `COMPOSE_DB_*` 환경 변수를 연결했습니다.
  - FastAPI 컨테이너의 DB 연결값을 compose 내부 기준(`DB_HOST=mariadb`, `DB_PORT=3306`)으로 오버라이드하여 `docker compose up` 시 로컬 MariaDB 컨테이너에 접속하도록 맞췄습니다.
  - 회의 결정에 따라 Ollama는 Docker Compose 서비스에서 제거하고, 호스트 로컬 Ollama(`ollama serve`)를 FastAPI 컨테이너가 `COMPOSE_OLLAMA_BASE_URL`로 호출하는 구조로 전환했습니다.
  - macOS 시작 스크립트는 Colima 실행 시 `host.lima.internal:11434`를 자동 선택하고, Linux/Windows 스크립트는 `host.docker.internal:11434` 기준의 호스트 Ollama 연결 흐름을 안내하도록 수정했습니다.
  - OS별 Docker 시작 스크립트의 시작 메시지, 모델 pull 안내, 로그/중지 명령을 `Redis + MariaDB + FastAPI` 3컨테이너와 호스트 로컬 Ollama 기준으로 정리했습니다.
  - `.env.example`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `SKILLS.md`, `docs/AGENTS.md`, `docs/README.md`, `docs/ops/environment_variables.md`, `docs/ops/deployment_guide.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/ops/test_specification.md`를 새 Docker 실행 구조에 맞게 동기화했습니다.
- **관련 파일**: `.dockerignore`, `.env.example`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `SKILLS.md`, `docker/.dockerignore`, `docker/docker-compose.yml`, `docker/docker-compose.macos.yml`, `docker/linux_docker_start.sh`, `docker/macos_docker_start.sh`, `docker/windows_docker_start.bat`, `docs/AGENTS.md`, `docs/README.md`, `docs/ops/environment_variables.md`, `docs/ops/deployment_guide.md`, `docs/ops/ai_model_hardware_setup.md`, `docs/ops/test_specification.md`
- **검증 결과**:
  - `docker compose --env-file .env -f docker/docker-compose.macos.yml config --quiet` 통과
  - `docker compose --env-file .env -f docker/docker-compose.yml config --quiet` 통과
  - `bash -n docker/macos_docker_start.sh docker/linux_docker_start.sh` 통과
  - `git diff --check` 통과
  - 실제 `docker compose up`은 이미지 빌드·컨테이너 기동 시간이 길 수 있어 이번 정리 작업에서는 실행하지 않았습니다.

---

### 2026-07-09 | iOS | Xcode MCP 로컬 설정 안내 및 스킬 경로 정리

- **커밋**: `docs(ios): document xcodebuildmcp local config`
- **변경 내용**:
  - `.xcodebuildmcp/config.yaml`에 남아 있던 개인 Mac 절대경로와 시뮬레이터/실기기 UDID를 제거하고, 각 개발자가 로컬에서 입력해야 할 값(`workspacePath`, `deviceId`, `scheme`, `platform`, `bundleId`)을 안내하는 템플릿 주석으로 정리했습니다.
  - `.agents/skills/xcode-build-management/SKILL.md`의 iOS 핵심 자산 링크를 특정 사용자 홈 디렉터리의 `file://` 절대경로에서 프로젝트 기준 상대경로로 변경했습니다.
  - `CoreMLInferenceBridge.swift` 링크를 실제 파일 위치인 `client/ios/CoreMLInferenceBridge.swift` 기준으로 정정했습니다.
- **관련 파일**: `.xcodebuildmcp/config.yaml`, `.agents/skills/xcode-build-management/SKILL.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg --files client/ios | rg "CoreMLInferenceBridge|Minchodan\\.xcworkspace|Podfile$"`로 iOS 핵심 파일 실제 위치 확인 완료
  - `git diff --check` 통과

---

### 2026-07-10 | DB | MariaDB Tailscale 외부망 연결 가이드 추가

- **커밋**: `docs(db): add tailscale mariadb guide`
- **변경 내용**:
  - macOS와 Windows 사용자를 분리한 MariaDB Tailscale 연결 절차 문서를 추가했습니다.
  - Tailscale DB Host, DB 이름, DB 사용자명은 플레이스홀더 기준으로 DBeaver 설정값과 `.env` 예시를 정리했습니다.
  - Tailscale 도달성, MariaDB 포트 도달성, DB 인증 실패를 구분하는 점검표와 트러블슈팅 표를 추가했습니다.
  - `docs/README.md` 문서 인덱스에 새 가이드 링크를 반영했습니다.
- **관련 파일**: `docs/db_tailscale_guide/README.md`, `docs/README.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg`로 Tailscale 초대 링크, 실제 Host, 실제 DB 사용자명 잔존 여부 확인 완료
  - `git diff --check` 통과

---

### 2026-07-10 | DB | 탐지 및 TTS 안내 로그 테이블 추가

- **커밋**: `db: add detection guidance log table`
- **변경 내용**:
  - 클라이언트 프레임 이벤트 기준의 탐지/안내 이력을 저장하기 위해 `detection_guidance_logs` 테이블 DDL을 추가했습니다.
  - 탐지 시점은 `detected_at`, YOLO 탐지 결과는 `detected_objects_json`, LLM이 사용자에게 출력한 전체 안내 문장은 `tts_text`에 저장하도록 구성했습니다.
  - 서버/클라이언트 이벤트 추적을 위한 `event_id`, 사용자/기기 연결을 위한 `user_id`, `device_id`, 반사/인지 스트림 구분을 위한 `stream_type`, DB 적재 시각 `created_at`을 함께 추가했습니다.
  - 로그성 데이터 보존을 위해 `app_users`, `user_devices` 참조는 `ON DELETE SET NULL` 정책으로 연결했습니다.
  - 기본 확인 설명을 기존 4개 테이블에서 5개 테이블 기준으로 갱신하고, 선택 검증 쿼리에 `SHOW CREATE TABLE detection_guidance_logs;`를 추가했습니다.
- **관련 파일**: `Minchodan DB.session.sql`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `git diff --check -- 'Minchodan DB.session.sql'` 통과
  - SQL 파일 내 신규 테이블 DDL 및 선택 검증 쿼리 위치 확인 완료
  - 실제 MariaDB 실행 검증은 이번 작업 범위에서 수행하지 않았습니다.

---

### 2026-07-10 | DB | 탐지 안내 로그 ORM 및 migration 파일 추가

- **커밋**: `db: add detection guidance ORM migration`
- **변경 내용**:
  - `detection_guidance_logs` 테이블을 SQLAlchemy ORM 기준 정의에 추가하고, `DetectionStreamType` enum과 사용자/기기 역방향 관계를 연결했습니다.
  - 탐지 안내 로그 생성/응답용 Pydantic DTO와 Repository 저장/조회 메서드를 추가했습니다.
  - SQLite 검증용 `server/db/schema.sql`에도 동일한 로그 테이블과 인덱스/FK 구조를 반영했습니다.
  - 운영 변경 이력 폴더 `server/db/migrations/`와 `20260710_001_add_detection_guidance_logs.sql` 증분 SQL 파일을 추가했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/schemas.py`, `server/db/repositories.py`, `server/db/schema.sql`, `server/db/migrations/README.md`, `server/db/migrations/20260710_001_add_detection_guidance_logs.sql`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `.venv/bin/python -m py_compile server/db/models.py server/db/schemas.py server/db/repositories.py` 통과
  - `.venv/bin/python -c "from server.db.models import DetectionGuidanceLog; ..."` 기반 ORM import 검증 통과
  - `sqlite3 :memory: ".read server/db/schema.sql" ".tables"` 기반 SQLite DDL 실행 및 `detection_guidance_logs` 생성 확인
  - `git diff --check` 통과

---

### 2026-07-10 | Git | 최신 dev 브랜치 jy 병합 및 DB 충돌 해결

- **커밋**: `Merge remote-tracking branch 'origin/dev' into jy` (`c050a00`)
- **변경 내용**:
  - 최신 `origin/dev`(`10f2b12`)를 `jy` 브랜치에 병합하고, 병합 결과를 원격 `origin/jy`에 push했습니다.
  - `jy`의 기존 `detection_guidance_logs` ORM/migration 커밋(`0c98670`)과 `dev`의 탐지 안내 로그 서비스 확장 작업이 같은 DB 계층 파일을 수정해 발생한 충돌을 해결했습니다.
  - `server/db/models.py`는 `dev` 기준의 `StreamType`, `detection_guidance_logs` 관계명, MySQL JSON 호환 문자열 저장 구조를 유지하면서 `jy`의 로그 테이블 ORM 정의가 중복되지 않도록 정리했습니다.
  - `server/db/repositories.py`는 `DetectionGuidanceLogRepository`의 `get_by_event_id()` 중복 조회 메서드와 `create()` 저장 메서드가 모두 남도록 충돌 마커를 제거했습니다.
  - `server/db/schemas.py`는 중복 정의된 `DetectionGuidanceLogCreate`, `DetectionGuidanceLogResponse`를 제거하고, 서비스 코드와 맞는 `StreamType` 및 JSON 문자열 DTO 기준으로 통일했습니다.
- **관련 파일**: `server/db/models.py`, `server/db/repositories.py`, `server/db/schemas.py`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `python3 -m py_compile server/db/models.py server/db/repositories.py server/db/schemas.py server/services/detection_guidance_log_service.py` 통과
  - `git diff --check` 통과
  - `git rev-parse HEAD origin/jy origin/dev`로 `HEAD == origin/jy == c050a00`, `origin/dev == 10f2b12` 확인
  - `git log --oneline HEAD..origin/dev` 결과가 비어 있어 `dev`에만 있고 `jy`에 없는 커밋이 없음을 확인

---

### 2026-07-10 | Git | 개인 설정 파일 제외 규칙 문서화

- **커밋**: `docs(git): document local private config ignores`
- **변경 내용**:
  - `.gitignore` 하단의 `**/Copy_*` 규칙을 팀원이 이해할 수 있도록 개인 설정 파일 제외 가이드를 추가했습니다.
  - 이미 Git이 추적 중인 원본 파일은 `.gitignore`만으로 수정 제외되지 않는다는 주의사항을 명시했습니다.
  - `.xcodebuildmcp/config.yaml`은 공유 템플릿으로 유지하고, `.xcodebuildmcp/Copy_config.yaml`은 개인 설정 복사본으로 사용하는 운영 기준을 정리했습니다.
  - 커밋 전 `git check-ignore`, `git status`, `git status --ignored` 기반 점검 명령을 문서화했습니다.
- **관련 파일**: `.gitignore`, `docs/ops/local_private_config_guide.md`, `docs/README.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `git check-ignore -v .xcodebuildmcp/Copy_config.yaml`로 `**/Copy_*` 규칙 적용 확인
  - `git status --short --ignored .xcodebuildmcp ...`로 `Copy_config.yaml`이 ignored 상태(`!!`)임을 확인
  - `git diff --check` 통과

---

### 2026-07-11 | iOS/서버 | 실기기 빌드 의존성 및 FastAPI 루트 응답 정리

- **커밋**: `15cb978` (`iOS: 실기기 빌드 의존성 및 루트 응답 정리`)
- **변경 내용**:
  - iOS 실기기 Debug 빌드가 React Native 카메라 프레임 처리 경로를 포함할 수 있도록 `react-native-worklets-core`를 클라이언트 의존성에 추가했습니다.
  - `client/package-lock.json`에 `react-native-worklets-core`와 하위 의존성 `string-hash-64` 잠금 정보를 반영하여 팀원별 설치 결과가 달라지지 않도록 고정했습니다.
  - `Podfile.lock`에 `react-native-worklets-core`, `VisionCamera/FrameProcessors`, `TextToSpeech`, `ExpoSpeech` Pod 연결 정보를 반영했습니다.
  - VisionCamera가 FrameProcessors 서브스펙을 포함하도록 CocoaPods 잠금 결과를 갱신하여 카메라 프레임 처리 기반 기능의 iOS 네이티브 링크 누락 가능성을 줄였습니다.
  - Xcode 프로젝트 파일을 최신 Xcode 저장 형식 기준으로 갱신하면서 `objectVersion`, `preferredProjectObjectVersion`, Shell Script Build Phase 표현, 빌드 구성 표시명이 재정렬되었습니다.
  - iOS 실기기 코드사이닝을 위해 `Minchodan` 타깃의 Debug/Release `DEVELOPMENT_TEAM` 값을 현재 로컬 개발팀 기준으로 갱신했습니다.
  - FastAPI 서버 기본 경로(`/`)에 서비스 상태, 헬스체크 경로, Swagger 문서 경로, WebSocket 경로를 반환하는 루트 응답을 추가했습니다.
  - 실기기 확인과 세션 로그를 바탕으로 안전 판단 공백, 음성 상호작용 지연, 연결 신뢰성, 안내 품질 검증, 제품화 과제를 정리한 `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md` 보완점 문서를 추가했습니다.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `server/main.py`, `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `client/ios/build-device-debug.log` 기준 `xcodebuild -workspace client/ios/Minchodan.xcworkspace -scheme Minchodan -configuration Debug -destination platform=iOS,id=... build` 실기기 Debug 빌드 성공 확인
  - 빌드 로그에서 `ExpoSpeech`, `TextToSpeech`, `VisionCamera`, `react-native-worklets-core`, `react-native-fast-tflite` 네이티브 타깃 의존성 연결 확인
  - 빌드 로그 마지막 결과 `BUILD SUCCEEDED` 확인
  - `python3 -m py_compile server/main.py` 통과
  - `git diff --check` 통과
  - `server/main.py` 루트 응답은 정적 코드 diff 기준으로 확인했으며, 서버 기동 후 HTTP 요청 검증은 이번 작업 범위에서 아직 수행하지 않았습니다.
- **비고**:
  - `client/ios/build-device-debug.log`는 빌드 성공 근거로 확인했지만 현재 미추적 파일 상태이므로, 커밋 포함 여부는 커밋 직전에 별도 판단이 필요합니다.

---

### 2026-07-11 | 문서 | macOS Xcode 빌드 공유 가이드 문서화

- **커밋**: 미커밋
- **변경 내용**:
  - `.vscode/xcode_mcp_setup_guide.md`의 Xcode MCP 설정 절차를 팀 공유 문서로 복사하여 `docs/macOS_xcode_build/xcode_mcp_setup_guide.md`를 추가했습니다.
  - `.vscode/ios_device_build_iteration_guide.md`의 iOS 실기기 빌드 및 수정 반복 절차를 공유 문서로 복사하여 `docs/macOS_xcode_build/ios_device_build_iteration_guide.md`를 추가했습니다.
  - 원본 `.vscode` 문서는 로컬 작업 노트로 보존하고, `docs/` 하위 복사본에는 팀원이 그대로 참고할 수 있도록 목적, 사전 준비, MCP 설정, 실기기 빌드, 설치/실행, 커밋 전 점검 절차를 정리했습니다.
  - 개인 Mac 절대경로, `file://` 링크, 실제 단말명, 실제 UDID/CoreDevice ID, 실제 bundle id, Apple 계정/Team 관련 값이 공유 문서에 노출되지 않도록 `<PROJECT_ROOT>`, `<XCODEBUILD_DEVICE_UDID>`, `<COREDEVICE_IDENTIFIER>`, `<IOS_BUNDLE_ID>` 등 안내 문구로 치환했습니다.
  - Xcode MCP 설정 문서에는 `xcodebuildmcp` 개요, `.xcodebuildmcp/config.yaml` 필드 설명, MCP 클라이언트 등록 예시, 오동작 대처 기준, 개인값 점검 명령을 정리했습니다.
  - iOS 단말 빌드 반복 문서에는 환경 확인, 단말 연결 확인, Signing Team 설정, Metro 실행, CLI 빌드, `devicectl` 설치/실행, 앱 확인 체크리스트, 재빌드 판단 기준을 정리했습니다.
- **관련 파일**: `docs/macOS_xcode_build/xcode_mcp_setup_guide.md`, `docs/macOS_xcode_build/ios_device_build_iteration_guide.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `rg`로 `file:///`, `/Users/jjun`, 실제 단말명, 실제 bundle id, Apple 개발자 계정/Team 식별자 잔존 여부 확인 완료
  - `git diff --check -- docs/macOS_xcode_build docs/changelogs/jy.md` 통과
  - 기존 미추적 빌드 로그 `client/ios/build-device-debug.log`는 이번 문서 커밋 대상에서 제외했습니다.
