# 개인 설정 파일 Git 제외 가이드

> **작성일**: 2026-07-10
> **버전**: v0.1.0
> **적용 대상**: 개인 절대경로, 장비 ID, 로컬 토큰, 로컬 실행 기본값이 들어가는 설정 파일

---

## 1. 목적

이 문서는 팀원이 로컬 개발 중 만든 **개인 설정 파일**이 Git 커밋과 GitHub push에 포함되지 않도록 관리하는 기준을 정의합니다.

Minchodan 저장소의 `.gitignore`에는 다음 규칙이 포함되어 있습니다.

```gitignore
**/Copy_*
```

따라서 프로젝트 어느 폴더에서든 파일명이 `Copy_`로 시작하는 파일은 기본적으로 Git 추적 대상에서 제외됩니다.

---

## 2. 핵심 원칙

| 구분 | 규칙 | 이유 |
| --- | --- | --- |
| **공유 파일** | Git에 올라가는 원본 파일은 템플릿 또는 예시값만 담습니다. | 모든 팀원이 같은 기준선을 받을 수 있어야 합니다. |
| **개인 파일** | 개인값이 들어간 복사본은 파일명 앞에 `Copy_`를 붙입니다. | `.gitignore`의 `**/Copy_*` 규칙으로 커밋 대상에서 빠집니다. |
| **민감 정보** | 토큰, 비밀번호, 실제 Host, 개인 UDID, 개인 절대경로는 공유 파일에 쓰지 않습니다. | GitHub에 노출되면 보안 사고 또는 환경 충돌이 발생합니다. |
| **추적 중 파일** | 이미 Git이 추적 중인 파일은 `.gitignore`만으로 수정 제외가 되지 않습니다. | `.gitignore`는 주로 아직 추적되지 않은 파일에 적용됩니다. |

---

## 3. 사용 예시

`.xcodebuildmcp/`의 Xcode Build MCP 설정은 다음처럼 관리합니다.

| 용도 | 파일 | Git 처리 | 작성 내용 |
| --- | --- | --- | --- |
| **공유 템플릿** | `.xcodebuildmcp/config.yaml` | 커밋 가능 | 플레이스홀더와 안내 주석만 유지 |
| **개인 설정 복사본** | `.xcodebuildmcp/Copy_config.yaml` | 커밋 제외 | 개인 `workspacePath`, `deviceId` 등 로컬값 입력 |

예시 명령은 다음과 같습니다.

```bash
cp .xcodebuildmcp/config.yaml .xcodebuildmcp/Copy_config.yaml
```

이후 `Copy_config.yaml`에만 개인 Mac 경로, 시뮬레이터 UDID, 실기기 UDID 등을 입력합니다.

---

## 4. 이미 Git에 등록된 파일 주의사항

`config.yaml`처럼 이미 Git이 추적 중인 파일은 로컬에서 개인값으로 수정하면 `git status`에 변경 파일로 표시됩니다. 이 상태에서 커밋하면 개인 설정이 올라갈 수 있습니다.

| 상황 | 올바른 처리 |
| --- | --- |
| 공유 파일에 개인값을 잘못 입력함 | 커밋 전 `git restore <파일>`로 공유 템플릿 상태로 되돌립니다. |
| 개인값을 보관해야 함 | 같은 폴더에 `Copy_<원본파일명>` 형식으로 복사해 사용합니다. |
| `Copy_` 파일이 실수로 stage됨 | `git restore --staged <파일>`로 stage에서 제거합니다. |
| `Copy_` 파일이 이미 추적 중임 | 팀과 합의 후 `git rm --cached <파일>`로 Git 추적에서 제거합니다. |

예시는 다음과 같습니다.

```bash
git restore .xcodebuildmcp/config.yaml
git restore --staged .xcodebuildmcp/Copy_config.yaml
git rm --cached .xcodebuildmcp/Copy_config.yaml
```

`git rm --cached`는 Git 추적만 제거하고 로컬 파일은 남깁니다. 단, 팀 공유 이력에 영향을 주므로 이미 원격에 올라간 파일에는 반드시 팀 합의 후 사용합니다.

---

## 5. 커밋 전 점검 명령

커밋 전에는 아래 명령으로 개인 파일이 제외되는지 확인합니다.

```bash
git check-ignore -v .xcodebuildmcp/Copy_config.yaml
git status --short
git status --ignored --short .xcodebuildmcp
```

정상 상태 예시는 다음과 같습니다.

```txt
!! .xcodebuildmcp/Copy_config.yaml
```

`git status --short`에 `Copy_` 파일이 `A`, `M`, `??` 상태로 보이면 커밋 전에 반드시 제외 상태를 다시 확인합니다.

---

## 6. 팀원 작업 절차

| 순서 | 작업 | 확인 기준 |
| --- | --- | --- |
| 1 | 공유 설정 파일을 확인합니다. | 원본 파일에 개인값이 없는지 봅니다. |
| 2 | 개인 설정 복사본을 만듭니다. | 파일명이 `Copy_`로 시작해야 합니다. |
| 3 | 개인 설정 복사본에 로컬값을 입력합니다. | 절대경로, 장비 ID, 토큰은 `Copy_` 파일에만 둡니다. |
| 4 | 커밋 전 `git status`를 확인합니다. | `Copy_` 파일이 커밋 대상에 없어야 합니다. |
| 5 | 공유 파일 변경이 필요하면 템플릿 주석만 수정합니다. | 개인값 대신 플레이스홀더를 사용합니다. |

---

## 7. 새 개인 설정 파일 추가 기준

새로운 로컬 설정 파일이 필요할 때는 다음 기준을 적용합니다.

| 질문 | 판단 |
| --- | --- |
| 팀 전체가 같은 값을 써야 합니까? | 예이면 일반 파일 또는 템플릿으로 커밋합니다. |
| 개발자마다 값이 다릅니까? | 예이면 `Copy_` 파일 또는 `.example` 템플릿 구조를 사용합니다. |
| 비밀번호, 토큰, 실제 Host가 들어갑니까? | 예이면 절대 커밋하지 않습니다. |
| 도구가 반드시 고정 파일명을 요구합니까? | 공유 파일은 템플릿으로 유지하고, 개인값 적용 절차를 별도 문서화합니다. |

---

## 8. 현재 적용 파일

| 경로 | 상태 | 비고 |
| --- | --- | --- |
| `.gitignore` | `**/Copy_*` 규칙 포함 | 프로젝트 전체 `Copy_` 개인 파일 제외 |
| `.xcodebuildmcp/config.yaml` | 공유 템플릿 | 개인 절대경로와 UDID 금지 |
| `.xcodebuildmcp/Copy_config.yaml` | 개인 설정 복사본 | Git 커밋 제외 대상 |
