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
  - 실기기 빌드 과정에서 미사용 `react-native-tts`, CocoaPods 1.17 잠금 결과, Xcode 26 프로젝트 자동 재작성, 개인 `DEVELOPMENT_TEAM` 값이 함께 반영되었습니다.
  - 후속 dev 병합 전 정합성 검토에서 `react-native-worklets-core`는 이미 기준선에 존재했고 `react-native-tts`는 런타임 import가 없음을 확인했습니다.
  - Xcode 26이 `shellScript`를 배열로 저장한 프로젝트 파일은 CocoaPods 1.17.0/xcodeproj 1.28.1의 깨끗한 `pod install`과 호환되지 않는 것도 확인했습니다.
  - FastAPI 서버 기본 경로(`/`)에 서비스 상태, 헬스체크 경로, Swagger 문서 경로, WebSocket 경로를 반환하는 루트 응답을 추가했습니다.
  - 실기기 확인과 세션 로그를 바탕으로 안전 판단 공백, 음성 상호작용 지연, 연결 신뢰성, 안내 품질 검증, 제품화 과제를 정리한 Mitos 보완점 문서를 추가했습니다.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `server/main.py`, `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `client/ios/build-device-debug.log` 기준 `xcodebuild -workspace client/ios/Minchodan.xcworkspace -scheme Minchodan -configuration Debug -destination platform=iOS,id=... build` 실기기 Debug 빌드 성공 확인
  - 기존 Pods가 남아 있던 로컬 빌드 로그에서는 `BUILD SUCCEEDED`를 확인했으나, 후속 깨끗한 `pod install` 검증에서 Xcode 프로젝트 저장 형식 호환 실패를 확인
  - 빌드 로그 마지막 결과 `BUILD SUCCEEDED` 확인
  - `python3 -m py_compile server/main.py` 통과
  - `git diff --check` 통과
  - `server/main.py` 루트 응답은 정적 코드 diff 기준으로 확인했으며, 서버 기동 후 HTTP 요청 검증은 이번 작업 범위에서 아직 수행하지 않았습니다.
- **비고**:
  - `client/ios/build-device-debug.log`는 빌드 성공 근거로 확인했지만 현재 미추적 파일 상태이므로, 커밋 포함 여부는 커밋 직전에 별도 판단이 필요합니다.

---

### 2026-07-11 | 문서 | macOS Xcode 빌드 공유 가이드 문서화

- **커밋**: `6d38ae3` (`docs: macOS Xcode 빌드 공유 가이드 추가`)
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

---

### 2026-07-11 | iOS/문서 | dev 병합 전 정합성 차단 사항 정리

- **커밋**: (이번 커밋)
- **변경 내용**:
  - `client/ios/Minchodan.xcodeproj/project.pbxproj`, `Podfile.lock`, `package.json`, `package-lock.json`을 `origin/dev` 기준으로 복구하여 Xcode 26 자동 재작성, 개인 Signing Team, 미사용 `react-native-tts`와 잠금 파일 노이즈를 제거했습니다.
  - 루트 `PROJECT_IMPROVEMENTS_MITOS.md`를 v0.2.0으로 갱신하여 `3e7ab52`에서 해결된 STT 위험 문구와 전사문 저장 문제를 완료 상태로 분리했습니다.
  - 중복된 `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`를 제거하고 `docs/README.md`가 루트 정본을 가리키도록 수정했습니다.
  - 과거 iOS 작업과 macOS 가이드 changelog를 실제 diff와 커밋 해시에 맞게 정정했습니다.
- **관련 파일**: `client/package.json`, `client/package-lock.json`, `client/ios/Podfile.lock`, `client/ios/Minchodan.xcodeproj/project.pbxproj`, `PROJECT_IMPROVEMENTS_MITOS.md`, `docs/README.md`, `docs/supplement/PROJECT_IMPROVEMENTS_MITOS.md`, `docs/changelogs/jy.md`
- **검증 결과**: `npm ci`, `tsc --noEmit`, `server/main.py`·`server/db/models.py` `py_compile`, `git diff --check` 통과. CocoaPods 1.17.0은 복구된 Xcode 프로젝트를 정상 파싱하고 autolinking까지 완료했으며, `pod install --deployment`는 저장소 기준 1.16.2와 로컬 1.17.0의 4개 Pod 체크섬·도구 버전 차이만 보고했습니다.
- **비고**: `client/ios/build-device-debug.log`는 기존 미추적 상태로 유지하며 커밋에 포함하지 않습니다.

---

### 2026-07-11 | Git | 최신 dev 병합 및 정합성 충돌 해소

- **커밋**: (이번 병합 커밋)
- **변경 내용**:
  - `origin/dev`(`3e7ab52`)를 `jy`에 일반 병합하여 STT·반사 경보 안전 패치와 CoreML FP16+ANE 변경을 통합했습니다.
  - 유일한 명시적 충돌인 `.gitignore`는 `dev`의 LF 버전과 `.zcode/`, `.claude/`, 에이전트 스크립트 제외 규칙을 유지하고 `jy`의 `**/Copy_*` 규칙을 추가하는 방식으로 해소했습니다.
  - CocoaPods 1.17.0으로 네이티브 의존성을 재생성하여 미사용 `TextToSpeech` Pod 제거와 96개 Pod 설치를 확인한 뒤, 추적 `Podfile.lock`은 저장소 기준 1.16.2 체크섬으로 유지했습니다.
- **관련 파일**: `.gitignore`, `docs/changelogs/jy.md` 및 `origin/dev`의 신규 커밋 전체
- **검증 결과**: 서버 테스트 130건 통과·2건 건너뜀(`test_ws_echo.py`, 기존 비결정적 RAG E2E 제외), `tsc --noEmit`, SQLite 5개 테이블 생성, 변경 Python 파일 `py_compile`, CocoaPods 설치, iOS 기기용 Debug 무서명 빌드, `git diff --check` 통과.
- **비고**: `dev` 브랜치와 `origin/dev`에는 아직 `jy`를 병합하지 않았습니다. 본 커밋과 `origin/jy` push 이후 별도 승인 단계로 진행합니다.

---

### 2026-07-13 | iOS/서버/문서 | ngrok 외부 터널에서 Tailscale 외부망 접속 및 RTT 계측 경로 전환

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 기존 외부망 테스트는 `ngrok` 공개 터널 도메인을 통해 FastAPI WebSocket 서버에 접속하는 방식이었으나, 데모·실기기 테스트에서는 터널 중계 구간의 지연과 도메인 변경 가능성이 병목이 될 수 있었습니다.
  - iPhone이 Wi-Fi가 아닌 셀룰러 데이터 환경에 있어도 서버와 같은 tailnet에만 들어오면 접속할 수 있도록, 클라이언트 외부망 모드를 `ngrok` 단일 경로에서 `tailscale` 선택 경로로 확장했습니다.
  - 속도 개선 여부를 감으로 판단하지 않도록, 카메라 인코딩·프레임 디코딩·YOLO 추론·TTS 지연을 제외한 순수 WebSocket RTT만 별도 측정하는 `network_probe` 계약을 추가했습니다.
- **클라이언트 변경 내용**:
  - `client/src/config/index.ts`에 `NetworkMode = "lan" | "ngrok" | "tailscale"` 타입과 `EXPO_PUBLIC_NETWORK_MODE`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_SERVER_PORT` 기반 URL 생성 규칙을 추가했습니다.
  - `EXPO_PUBLIC_NETWORK_MODE=tailscale`일 때 앱이 `ws://{EXPO_PUBLIC_TAILSCALE_HOST}:{EXPO_PUBLIC_SERVER_PORT}/ws/detect`로 접속하도록 하여, Wi-Fi/LAN 주소와 ngrok 도메인을 거치지 않는 Tailscale 직접 경로를 만들었습니다.
  - `client/src/services/serverTransport.ts`에서 외부망 모드일 때 버튼 라벨을 `연결: Tailscale` 또는 `연결: ngrok`으로 표시하고, Tailscale/ngrok 모드에서는 Wi-Fi/USB 토글이 실제 접속 주소를 바꾸지 않도록 정리했습니다.
  - `client/src/hooks/useWebSocket.ts`에 `EXPO_PUBLIC_NETWORK_BENCHMARK=true`일 때 주기적으로 `network_probe`를 전송하는 로직을 추가하고, `network_probe_ack` 수신 시 최신 RTT와 최근 30개 평균 RTT를 계산하도록 했습니다.
  - `client/src/components/CameraView.tsx` 디버그 오버레이에 `망RTT: ...ms (평균 ...ms)` 줄을 추가하여, iOS 실기기에서 셀룰러 데이터 + Tailscale 연결 품질을 앱 화면에서 바로 확인할 수 있게 했습니다.
  - `client/src/types/detection.ts`에 `network_probe_ack` 메시지 타입과 `probe_id`, `payload_bytes`, `server_received_ts`, `server_sent_ts` 필드를 추가해 서버 응답 계약을 타입에 반영했습니다.
  - `client/.env.example`을 추가하여 Tailscale 실기기 테스트에 필요한 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_NETWORK_BENCHMARK=true` 예시를 별도 템플릿으로 제공했습니다.
- **서버 변경 내용**:
  - `server/api/ws_router.py`의 `/ws/detect` 메인 수신 루프에 `network_probe` 분기를 추가했습니다.
  - 서버는 `network_probe`를 받으면 탐지 파이프라인, Redis Streams, RAG, LLM, TTS를 거치지 않고 즉시 `network_probe_ack`를 반환합니다.
  - 응답에는 `probe_id`, `client_sent_ts`, `client_label`, `payload_bytes`, `server_received_ts`, `server_sent_ts`를 담아, 앱과 CLI 스크립트가 동일한 계약으로 RTT를 계산할 수 있게 했습니다.
  - `server/api/ws_router.py` 상단에 UTF-8 선언을 추가하여 프로젝트 Python 파일 헤더 규칙과 맞췄습니다.
- **벤치마크 도구 변경 내용**:
  - `scripts/benchmark_ws_network.py`를 추가하여 `ngrok`, `tailscale`, `lan` 등 여러 WebSocket target을 같은 방식으로 측정할 수 있게 했습니다.
  - 스크립트는 `welcome` 수신 후 `hello` 인증과 `auth_ok`까지의 handshake 시간을 따로 측정하고, `network_probe` 왕복 RTT에 대해 평균, p50, p95, max, 실패 수를 출력합니다.
  - `--json-out`, `--csv-out` 옵션을 제공하여 반복 측정 결과를 파일로 보존할 수 있게 했습니다.
  - `websockets` 패키지는 실제 측정 시점에 lazy import하도록 구성하여, 의존성이 없는 환경에서도 `--help` 출력은 정상 동작하도록 했습니다.
- **문서 동기화 내용**:
  - `docs/ops/environment_variables.md`에 `EXPO_PUBLIC_NETWORK_MODE`, `EXPO_PUBLIC_TAILSCALE_HOST`, `EXPO_PUBLIC_SERVER_PORT`, `EXPO_PUBLIC_NETWORK_BENCHMARK`, `EXPO_PUBLIC_NETWORK_BENCHMARK_INTERVAL_MS`, `EXPO_PUBLIC_NETWORK_BENCHMARK_PAYLOAD_BYTES`를 추가했습니다.
  - `docs/ops/android_wifi_usb_transport.md`를 Wi-Fi/USB뿐 아니라 Tailscale 외부망까지 포함하는 모바일 접속 운영 가이드로 확장했습니다.
  - `docs/mobile/ios_android_bifurcation_contract.md`에 iOS 앱의 Tailscale 외부망 URL 생성 규칙과 앱 내 `network_probe` RTT 표시 계약을 반영했습니다.
  - `docs/design/api_specification.md`에 `network_probe`/`network_probe_ack` 메시지 계약을 추가하여 `/ws/detect` API 명세와 실제 서버 구현을 맞췄습니다.
  - `docs/ops/network_latency_benchmark.md`를 새로 추가하여 iOS 셀룰러 + Tailscale 전제, Metro 재번들 절차, CLI 비교 측정 명령, 결과 해석 기준을 정리했습니다.
- **운영 및 테스트 기준 정리**:
  - iOS 앱 실측은 `client/.env`에 `EXPO_PUBLIC_NETWORK_MODE=tailscale`, `EXPO_PUBLIC_TAILSCALE_HOST=<SERVER_TAILSCALE_IP_OR_MAGICDNS>`, `EXPO_PUBLIC_NETWORK_BENCHMARK=true`를 설정한 뒤 `cd client && npx expo start -c`로 Metro 캐시를 초기화해 진행하는 기준으로 정리했습니다.
  - CLI 비교 측정은 앱과 같은 `device_id`를 동시에 쓰면 서버 세션이 교체될 수 있으므로, 순수 네트워크 비교 시에는 앱을 종료하고 실행하거나 별도 벤치마크용 `device_id`/토큰을 쓰는 기준으로 정리했습니다.
  - `improve` 열은 첫 번째 `--target`의 평균 RTT를 기준으로 뒤 target의 개선율을 계산하므로, ngrok 대비 Tailscale 개선률을 보고 싶을 때는 `--target ngrok=...`을 첫 번째, `--target tailscale=...`을 두 번째로 두는 방식으로 안내했습니다.
  - Tailscale 단일 target 실측에서 `samples=50`, `fail=0`, `avg=5.30ms`, `p50=3.75ms`, `p95=11.94ms`, `max=13.94ms`가 확인되어, 현재 환경 기준 순수 WebSocket RTT는 안정적으로 낮은 편임을 확인했습니다. 실제 Tailscale IP와 토큰은 문서에 기록하지 않았습니다.
  - Docker Compose는 `server/`, `scripts/`를 볼륨 마운트하므로 로컬 컨테이너 테스트에서는 FastAPI 컨테이너 재시작만으로 코드 변경이 반영될 수 있고, 이미지 자체를 배포 레지스트리에 push하려면 Dockerfile의 코드 내장 전략을 별도 검토해야 함을 정리했습니다.
- **관련 파일**: `client/src/config/index.ts`, `client/src/hooks/useWebSocket.ts`, `client/src/components/CameraView.tsx`, `client/src/services/serverTransport.ts`, `client/src/types/detection.ts`, `client/.env.example`, `server/api/ws_router.py`, `scripts/benchmark_ws_network.py`, `docs/design/api_specification.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/ops/android_wifi_usb_transport.md`, `docs/ops/environment_variables.md`, `docs/ops/network_latency_benchmark.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `python3 -m py_compile scripts/benchmark_ws_network.py server/api/ws_router.py server/api/session_manager.py` 통과
  - `git diff --check` 통과
  - `cd client && npx tsc --noEmit` 통과
  - `python3 scripts/benchmark_ws_network.py --help` 정상 출력 확인
  - Tailscale 단일 target 기준 `network_probe` 50개 샘플 수집, 실패 0건, 평균 RTT 5.30ms 확인
- **비고**:
  - `client/.env`와 루트 `.env`의 실제 Tailscale Host, device token, ngrok domain 값은 로컬 비밀/환경값으로 취급하며 changelog에 남기지 않습니다.
  - ngrok 컨테이너나 ngrok 도메인 지원을 제거한 것이 아니라, `lan`/`ngrok`/`tailscale`을 선택 가능한 네트워크 모드로 확장한 작업입니다.

---

### 2026-07-13 | iOS/클라이언트/문서 | LiDAR 거리 필드 우선 표시 및 반사 게이트 fallback 구조 적용

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 단말 "거리측정" 토글은 `DepthProbeBridge` 자체 캡처 세션 기반 계측용 프로토타입이라, 기존 객체 탐지 bbox와 동기화된 실거리로 직접 쓰기 어려웠습니다.
  - 객체별 실거리 융합으로 가기 위한 선행 단계로, 클라이언트 탐지 결과 타입과 화면/반사 게이트가 `distanceMeters`를 우선 소비하고, 값이 없으면 기존 bbox 휴리스틱으로 fallback하는 구조를 먼저 적용했습니다.
- **변경 내용**:
  - `DetectionResult`와 `ServerDetectionResult`에 `distanceMeters`, `distanceSource`, `depthSampleCount`, `depthAccuracy` optional 필드를 추가했습니다.
  - `CameraView.tsx`에 거리 해석 helper를 추가하여 BBox 라벨과 탐지 요약을 `LiDAR` 또는 `추정`으로 구분 표시하도록 바꿨습니다.
  - 단말 반사 게이트는 LiDAR 값이 있는 경우 0.5m/1.0m/1.5m/3.0m 기준으로 우선 판단하고, LiDAR 값이 없을 때만 기존 면적 ratio 기반 주차센서식 판정을 유지합니다.
  - `DepthProbeBridge.swift`와 `depthProbe.ts`에 bbox 중앙 50% 영역 7x7 grid 샘플링, 최소 8개 유효 샘플, 25퍼센타일 거리 계산 helper(`probeBoxes`)를 추가했습니다.
  - `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`를 LiDAR 우선/fallback 구현 상태와 실기기 video+depth 동기화 검증 잔여 상태로 갱신했습니다.
- **관련 파일**: `client/src/inference/types.ts`, `client/src/types/detection.ts`, `client/src/components/CameraView.tsx`, `client/src/services/depthProbe.ts`, `client/ios/DepthProbeBridge.swift`, `client/ios/DepthProbeBridge.mm`, `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `cd client && npx tsc --noEmit` 통과
  - `xcodebuild -workspace Minchodan.xcworkspace ...`는 현재 실행 환경에서 `.xcworkspace` 인식 오류와 CoreSimulator 로그 권한 오류로 완료하지 못했습니다.
  - 대체로 `xcodebuild -project Minchodan.xcodeproj ...`를 실행했으나, 서명 설정에서는 provisioning profile 부재로 실패했고, `CODE_SIGNING_ALLOWED=NO`에서는 `sandbox-exec: sandbox_apply: Operation not permitted`로 CoreML 모델 컴파일 단계가 차단되어 최종 iOS 빌드 완료까지는 확인하지 못했습니다.
- **비고**:
  - 이번 작업은 `distanceMeters` 소비 경로와 bbox depth 샘플링 helper까지의 부분 해소입니다. 정식 객체별 실거리 경보로 승격하려면 VisionCamera video frame과 LiDAR depth map이 같은 세션·같은 타임스탬프·같은 640x640 crop 좌표계임을 실기기에서 검증해야 합니다.

---

### 2026-07-13 | iOS/클라이언트/문서 | `거리측정` 계측용 LiDAR 프로브 동기화 프리뷰 적용

- **커밋**: (이번 커밋)
- **변경 배경**:
  - 기존 `거리측정` 버튼은 `DepthProbeBridge`의 별도 depth 세션에서 고정 3점 값만 읽고, 같은 세션의 실제 카메라 프리뷰를 화면에 보여주지 않았습니다.
  - 그 결과 사용자가 보고 있다고 생각한 벽/물체 위치와 LiDAR depth 샘플 좌표가 정합된다고 보장할 수 없어, 줄자 실측과 앱 표시값이 크게 어긋날 수 있었습니다.
  - 이번 작업의 우선순위는 일반 객체 bbox별 `distanceMeters` 융합이 아니라, 앱 하단 `거리측정` 버튼으로 켜지는 운영자/계측용 프로토타입 자체를 줄자 검증 가능한 상태로 만드는 것입니다.
- **변경 내용**:
  - `DepthProbeBridge.swift`에 `AVCaptureVideoDataOutput`을 추가하고, `AVCaptureDepthDataOutput`과 `AVCaptureDataOutputSynchronizer`로 묶어 video+depth를 같은 네이티브 세션에서 동기화했습니다.
  - `probe()` 결과에 같은 세션에서 생성한 1:1 정사각형 프리뷰 JPEG(`previewUri`)와 `synchronizedAt`, 샘플별 `sampleCount`를 함께 반환하도록 확장했습니다.
  - depth 샘플 좌표를 전체 depth map 기준이 아니라 화면에 보이는 1:1 center square crop 기준으로 변환하도록 수정했습니다.
  - 점 샘플은 기존 3x3 이웃에서 5x5 이웃 미디언으로 넓혀 단일 픽셀 노이즈 영향을 줄였습니다.
  - `CameraView.tsx`의 `거리측정` 모드에서 VisionCamera가 꺼진 동안에도 네이티브 LiDAR 세션 프리뷰를 표시하고, 중앙/전방 하단/발밑 샘플 마커와 거리값을 프리뷰 위에 같이 표시하도록 변경했습니다.
  - `거리측정` 모드가 켜져 있을 때는 단말 캡처 루프와 서버 `detection_control`을 OFF로 보내 stale bbox와 반사 경보가 계측 화면에 섞이지 않도록 했습니다.
  - `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`에 계측용 버튼 개선 상태와 객체별 정식 fusion 잔여 조건을 분리해 기록했습니다.
- **구현 상세**:
  - 네이티브 세션 구성은 `builtInLiDARDepthCamera` 입력 1개에 `AVCaptureVideoDataOutput`과 `AVCaptureDepthDataOutput`을 동시에 붙이는 방식입니다.
  - video/depth 연결은 모두 portrait 기준으로 맞추고, video mirroring은 끈 상태로 유지합니다.
  - JS 화면의 카메라 프레임은 1:1 정사각형이므로, depth map도 전체 map 좌표가 아니라 center square crop 좌표로 변환해 `중앙`, `전방 하단`, `발밑` 샘플을 읽습니다.
  - `previewUri`는 같은 동기화 세션의 video buffer를 640x640 JPEG data URI로 변환한 값이며, `CameraView.tsx`는 이 이미지를 계측 화면의 실제 프리뷰로 사용합니다.
  - 각 샘플 행의 괄호 숫자는 해당 지점 주변 5x5 이웃에서 유효한 depth 픽셀 수입니다. 값이 낮으면 표면 반사, 저조도, 유리/검정 표면 등으로 샘플 신뢰도가 낮을 수 있습니다.
- **관련 파일**: `client/ios/DepthProbeBridge.swift`, `client/src/services/depthProbe.ts`, `client/src/components/CameraView.tsx`, `docs/research/mitos_improvement_roadmap.md`, `docs/design/risk_ssot_contract.md`, `docs/mobile/ios_android_bifurcation_contract.md`, `docs/changelogs/jy.md`
- **검증 결과**:
  - `cd client && npx tsc --noEmit` 통과
  - `git diff --check` 통과
  - `xcodebuild -project client/ios/Minchodan.xcodeproj -scheme Minchodan -configuration Debug -destination generic/platform=iOS -derivedDataPath client/ios/build-lidar-probe-check CODE_SIGNING_ALLOWED=NO build` 실행 시 Swift 산출물은 생성됐으나, 기존과 같은 CoreML 모델 컴파일 sandbox 오류(`sandbox-exec: sandbox_apply: Operation not permitted`) 및 `__preview.dylib` 링크 오류로 최종 iOS 빌드는 완료하지 못했습니다.
- **실기기 확인 절차**:
  - Swift 네이티브 코드 변경이므로 Metro reload만으로는 반영되지 않습니다. `npx expo start -c --dev-client --host lan` 실행 후 Xcode에서 실제 iPhone 대상으로 재빌드해야 합니다.
  - 앱 본화면 진입 후 `탐지 시작`을 누르지 않아도 `거리측정` 버튼만으로 계측 모드를 시작할 수 있습니다.
  - 정상 화면은 `LiDAR 프리뷰 준비 중...`이 잠깐 보인 뒤, 네이티브 LiDAR 세션 프리뷰 위에 `중앙`, `전방 하단`, `발밑` 마커와 거리값이 표시되는 상태입니다.
  - 줄자 검증은 카메라 렌즈면 기준으로 0.5m, 1.0m, 2.0m 지점을 맞추고, 폰을 벽과 최대한 수직으로 둔 상태에서 우선 `중앙` 값을 비교합니다.
  - 벽면, 박스, 의자처럼 난반사가 적고 평평한 표면부터 확인하고, 유리, 거울, 검정 유광 물체, 강한 역광 표면은 별도 실패 표면으로 분리 기록합니다.
- **비고**:
  - 이번 수정은 `거리측정` 버튼 자체를 줄자 검증 가능한 계측 화면으로 개선하는 작업입니다.
  - 일반 객체 탐지 bbox에 `LiDAR` 거리 라벨을 붙이는 정식 경로는 여전히 별도 과제이며, VisionCamera 탐지 프레임과 depth map을 같은 세션·같은 타임스탬프·같은 640x640 crop 좌표계로 묶는 후속 구현이 필요합니다.
  - 실기기에서 여전히 큰 오차가 나면 다음 우선 확인 대상은 프리뷰 방향 180도 보정 필요 여부, depth orientation, 렌즈 기준 줄자 위치, 기기와 벽의 수직 정렬입니다.
