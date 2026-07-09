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
