# Minchodan DB Migrations

> **작성일**: 2026-07-10
> **버전**: v0.1.0

---

## 목적

이 폴더는 운영 또는 공유 MariaDB에 반영한 DB 구조 변경 이력을 SQL 파일 단위로 보관합니다.
프로젝트 전체 초기 세팅은 루트의 `Minchodan DB.session.sql`을 기준으로 하고, 이후 증분 변경은 이 폴더에 누적합니다.

---

## 파일명 규칙

파일명은 아래 형식을 사용합니다.

```text
YYYYMMDD_NNN_change_summary.sql
```

예시:

```text
20260710_001_add_detection_guidance_logs.sql
```

---

## 운영 반영 원칙

- 운영 DB에 적용하기 전 대상 DB(`DB_HOST`, `DB_NAME`)와 백업 여부를 확인합니다.
- 변경 SQL은 PR 또는 팀 리뷰 후 실행합니다.
- 실행 후 `SHOW CREATE TABLE` 또는 `information_schema`로 구조를 확인합니다.
- `CREATE TABLE IF NOT EXISTS`는 없는 테이블 생성에는 안전하지만, 기존 테이블 구조 변경을 자동 마이그레이션하지 않습니다.
