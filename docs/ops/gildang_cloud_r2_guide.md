# gildang_db + Cloudflare R2 전환 가이드

> **작성일**: 2026-07-24
> **버전**: v1.0.0
> **목적**: Tailscale/Raspberry Pi MariaDB·미디어 API 의존을 클라우드 MariaDB(`gildang_db`, 포트 3307)와 Cloudflare R2로 분리하는 운영 절차
> **관련**: [`environment_variables.md`](environment_variables.md), [`rpi-network-profile-switcher`](../../.agents/skills/rpi-network-profile-switcher/SKILL.md), [`demo_test_device_inventory.md`](demo_test_device_inventory.md)

---

## 1. 역할 분리

| 구성 | 기존 (demo/test) | cloud 프로필 |
| :--- | :--- | :--- |
| DB | Pi MariaDB `minchodan_db` (3306) | 클라우드 MariaDB **`gildang_db` (3307)** |
| 미디어 | Pi `IMAGE_SERVER_*` HTTP API | **Cloudflare R2** (`EVENT_FRAME_STORAGE_BACKEND=r2`) |
| 단말↔FastAPI | Tailscale 유지 | Tailscale 유지 |

`demo`/`test` 프로필은 롤백용으로 유지합니다.

---

## 2. 사전 준비 (사람)

1. Cloudflare 대시보드에서 R2 버킷 생성, S3 API 토큰(Read/Write), Account ID 확인
2. 클라우드 MariaDB에서 3307 포트·방화벽(개발 Mac / GPU 서버 egress만 허용)
3. 로컬에서 프로필 파일 생성:

```bash
cp .env.network.cloud.example .env.network.cloud
# DB_HOST, DB_PASSWORD, R2_* 실값 기입 (Git 금지)
```

4. (최초 1회) DB·유저·스키마:

```bash
export CLOUD_DB_HOST='<호스트>'
export CLOUD_DB_PORT=3307
export CLOUD_DB_ROOT_PASSWORD='<루트비밀번호>'
# 앱 유저 비밀번호를 지정하지 않으면 스크립트가 생성해 한 번만 출력합니다.
.venv/bin/python scripts/setup_gildang_cloud_db.py --yes
```

생성된 `DB_USER`/`DB_PASSWORD`를 `.env.network.cloud`에 넣고, 장기적으로는 root 직접 사용을 중단합니다.

---

## 3. 프로필 전환

```bash
# 사전검사만
MINCHODAN_SWITCH_CHECK_ONLY=1 bash scripts/switch_rpi_network.sh cloud

# FastAPI 재기동까지
bash scripts/switch_rpi_network.sh cloud
```

macOS에서 `cloud`일 때는 Tailscale `socat` DB 프록시를 기동하지 않고 `COMPOSE_DB_HOST`로 클라우드에 직접 연결합니다.

롤백:

```bash
bash scripts/switch_rpi_network.sh test   # 또는 demo
```

---

## 4. 코드 계약

| 모듈 | 역할 |
| :--- | :--- |
| `server/services/r2_storage_client.py` | R2 Put/Get/HeadBucket/보존 삭제 |
| `server/services/remote_storage_client.py` | `remote` vs `r2` 파사드 |
| `server/services/event_frame_store.py` | 저장·R2 보존 정리 |
| object_key | `event_frames/YYYYMMDD/{event_id}.jpg` |

콘솔 프레임 조회는 기본으로 `GET /api/v1/admin/event-frames/{event_id}`가 FastAPI에서 JPEG를 프록시합니다(관리자 JWT 유지).
R2 단기 URL이 필요하면 `?delivery=presigned`로 302 리다이렉트합니다.

증분 SQL(`server/db/migrations/`)은 역사적으로 `USE minchodan_db`가 박혀 있으므로,
신규 `gildang_db`는 `setup_gildang_cloud_db.py`의 ORM `create_all`(현재 `models.py` 스키마)을 사용합니다.

---

## 5. 검증 체크리스트

- [ ] `SHOW DATABASES`에 `gildang_db`
- [ ] FastAPI 컨테이너 `DB_HOST`/`DB_PORT=3307`/`DB_NAME=gildang_db`
- [ ] `EVENT_FRAME_STORAGE_BACKEND=r2`, HeadBucket OK
- [ ] 탐지 이벤트 1건 후 R2에 객체 생성, DB `frame_path`에 `event_frames/...` 키
- [ ] 콘솔에서 프레임 JPEG 표시
- [ ] `demo`/`test`로 전환 시 Pi 경로 복구
