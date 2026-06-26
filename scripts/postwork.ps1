# =============================================================================
# Script Name : postwork.ps1
# Platform    : Windows (PowerShell 5.1+)
# Purpose     : Minchodan Post-work 자동화 -- 코딩 규칙 확인, 테스트 실행,
#               changelog 기록, git 커밋/푸시, PR 생성.
# Usage       : powershell -ExecutionPolicy Bypass -File scripts\postwork.ps1
# =============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

function Print-Ok($msg)     { Write-Host "[OK] $msg" -ForegroundColor Green }
function Print-Warn($msg)   { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Print-Error($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Print-Info($msg)   { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Print-Manual($msg) { Write-Host "[MANUAL] $msg" -ForegroundColor Yellow }
function Print-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor White }

# --- 테스트 명령어 매핑 ---
function Get-TestCmd($stage) {
    switch ($stage) {
        1 { return "python tests\test_ws_echo.py" }
        2 { return "python tests\test_frame_decode.py" }
        3 { return "python scripts\verify_gpu.py; python tests\test_detection.py" }
        4 { return "python scripts\eval_hitrate.py" }
        5 { return "python tests\test_rag_retrieval.py" }
        6 { return "python tests\test_langgraph.py" }
        7 { return "python tests\test_tts_reflex.py" }
    }
}

$COMMIT_MSG = ""
$PR_STATUS = "생략"

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Minchodan Post-work 자동화 (PowerShell)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# Step A -- 기본 정보 입력
# =============================================================================
Print-Header "Step A: 기본 정보 입력"

$INITIAL = Read-Host "본인 브랜치 이니셜을 입력하세요 (dg/jh/jy/kb/th)"
$validInitials = @("dg", "jh", "jy", "kb", "th")
if ($INITIAL -notin $validInitials) {
    Print-Error "잘못된 이니셜 '$INITIAL'. dg, jh, jy, kb, th 중 하나를 입력하세요."
    exit 1
}
Print-Ok "이니셜: $INITIAL"

$STAGE = Read-Host "작업한 파이프라인 단계를 입력하세요 (1-7)"
if ($STAGE -notmatch '^[1-7]$') {
    Print-Error "잘못된 단계 '$STAGE'. 1~7 사이의 정수를 입력하세요."
    exit 1
}
$STAGE = [int]$STAGE
Print-Ok "단계: $STAGE"

$DATE = Read-Host "오늘 날짜를 입력하세요 (YYYY-MM-DD)"
if ($DATE -notmatch '^\d{4}-\d{2}-\d{2}$') {
    Print-Error "잘못된 날짜 형식 '$DATE'. YYYY-MM-DD 형식으로 입력하세요."
    exit 1
}
Print-Ok "날짜: $DATE"

$SUMMARY = Read-Host "작업 요약을 입력하세요 (영문 소문자, 숫자, 밑줄만 허용, 예: websocket_handshake)"
if ($SUMMARY -notmatch '^[a-z0-9_]+$') {
    Print-Error "잘못된 요약 '$SUMMARY'. 영문 소문자, 숫자, 밑줄만 사용할 수 있습니다."
    exit 1
}
Print-Ok "요약: $SUMMARY"

$CHANGELOG_FILE = "docs\changelogs\$INITIAL.md"

# =============================================================================
# Step B -- 코딩 규칙 자체 점검 (안내)
# =============================================================================
Print-Header "Step B: 코딩 규칙 자체 점검"
Write-Host ""
Write-Host "  [코딩 규칙 자체 점검 -- 커밋 전 아래 항목을 확인하세요]"
Write-Host "    [ ] 모든 새 Python 파일 첫 줄: # -*- coding: utf-8 -*- 및 sys.stdout.reconfigure(encoding='utf-8')"
Write-Host "    [ ] 임포트 순서: 표준 라이브러리 -> 외부 라이브러리 -> 로컬 모듈"
Write-Host "    [ ] 절대 경로 하드코딩 없음 (os.path.dirname(os.path.abspath(__file__)) 사용)"
Write-Host "    [ ] 환경 변수: load_dotenv() + os.getenv(key, default) 패턴 적용"
Write-Host "    [ ] 방어적 코딩: None 가드, dict.get(), 예외 후 루프 유지"
Write-Host "    [ ] FastAPI 3계층 구조: Router -> Service -> Repository"
Write-Host "    [ ] 코드 주석, 커밋 메시지, 문서 내 이모지 없음"
Write-Host "    [ ] 모든 파일 UTF-8로 저장"
Write-Host ""

$CODING_CHECK = Read-Host "위 항목을 모두 확인했습니까? (y/N)"
if ($CODING_CHECK -ne "y" -and $CODING_CHECK -ne "Y") {
    Print-Warn "코딩 규칙 점검이 확인되지 않았습니다. 위 체크리스트를 검토 후 다시 실행하세요."
    exit 1
}
Print-Ok "코딩 규칙 자체 점검 확인 완료."

# =============================================================================
# Step C -- 이중 경로 원칙 위반 확인 (안내)
# =============================================================================
Print-Header "Step C: 이중 경로 원칙 위반 확인"
Write-Host ""
Write-Host "  [이중 경로 위반 확인]"
Write-Host "    [ ] 반사 경로 코드에 LLM 호출 없음"
Write-Host "    [ ] 반사 경로 코드에 RAG 검색 호출 없음"
Write-Host "    [ ] 반사 경로 코드에 실시간 TTS 합성 호출 없음"
Write-Host "    [ ] 반사 음성이 data\reflex_clips\ 사전합성 클립만 참조"
Write-Host ""

$DUAL_CHECK = Read-Host "이중 경로 원칙 위반이 없는 것을 확인했습니까? (y/N)"
if ($DUAL_CHECK -ne "y" -and $DUAL_CHECK -ne "Y") {
    Print-Warn "이중 경로 위반 확인이 되지 않았습니다. 반사 경로 코드를 검토하세요."
    exit 1
}
Print-Ok "이중 경로 원칙 확인 완료."

# =============================================================================
# Step D -- 단계별 테스트 실행
# =============================================================================
Print-Header "Step D: 테스트 실행 (${STAGE}단계)"
$TEST_CMD = Get-TestCmd $STAGE
Print-Info "실행 중: $TEST_CMD"
Write-Host ""

Invoke-Expression $TEST_CMD 2>&1
Write-Host ""

$TEST_PASS = Read-Host "모든 테스트를 통과하고 KPI 목표를 달성했습니까? (y/N)"
if ($TEST_PASS -ne "y" -and $TEST_PASS -ne "Y") {
    Print-Warn "테스트가 완전히 통과되지 않았습니다. 계속 진행하지만 PR 병합 전 수정하세요."
}

# =============================================================================
# Step E -- Changelog 엔트리 추가
# =============================================================================
Print-Header "Step E: Changelog 엔트리 추가"

if (-not (Test-Path $CHANGELOG_FILE)) {
    $header = @"
# Changelog - $INITIAL

> 이 파일은 **$INITIAL**의 작업 내역을 시간순으로 누적 기록합니다.
> 새 항목은 파일 하단에 추가됩니다.
"@
    $header | Out-File -FilePath $CHANGELOG_FILE -Encoding UTF8
    Print-Ok "Changelog 파일 생성: $CHANGELOG_FILE"
}

$entry = @"

---

### $DATE | ${STAGE}단계 | $SUMMARY

- **커밋**: ``(postwork 스크립트에서 입력 예정)``
- **변경 내용**:
  - (작업 완료 후 상세 내용을 직접 기입하세요.)
- **관련 파일**: (변경된 파일 목록을 기입하세요.)
- **검증 결과**: (테스트 결과 및 KPI 달성 여부를 기입하세요.)
"@
$entry | Out-File -FilePath $CHANGELOG_FILE -Append -Encoding UTF8
Print-Ok "Changelog 엔트리 추가 완료: $CHANGELOG_FILE"
Print-Manual "[필수] $CHANGELOG_FILE 파일을 열어 상세 내용을 기입하세요."
Write-Host ""

# =============================================================================
# Step F -- Git 스테이징 안전 검사
# =============================================================================
Print-Header "Step F: Git 스테이징 안전 검사"

$gitStatus = git status --short 2>&1
$FORBIDDEN_FOUND = $false

foreach ($line in $gitStatus) {
    if (-not $line) { continue }
    $filePath = $line.Substring(3).Trim()
    if ($filePath -eq ".env") {
        Print-Error "금지된 파일이 감지되었습니다: .env -- 이 파일을 커밋하지 마세요."
        $FORBIDDEN_FOUND = $true
    }
    if ($filePath -like "server/models/*" -or $filePath -like "server\models\*") {
        Print-Error "금지된 파일이 감지되었습니다: $filePath -- 모델 가중치를 커밋하지 마세요."
        $FORBIDDEN_FOUND = $true
    }
}

if ($FORBIDDEN_FOUND) {
    Print-Error "금지된 파일이 감지되었습니다. .gitignore에 추가하고 스테이징에서 제거하세요."
    exit 1
}
Print-Ok "금지된 파일이 감지되지 않았습니다."

# =============================================================================
# Step G -- Git 커밋
# =============================================================================
Print-Header "Step G: Git 커밋"

$PREFIX = Read-Host "커밋 접두어를 입력하세요 (예: 1단계, docs, infra, test)"
$DESC = Read-Host "커밋 설명을 입력하세요"

$COMMIT_MSG = "${PREFIX}: ${DESC}"
Write-Host ""
Print-Info "커밋 메시지: $COMMIT_MSG"

$COMMIT_CONFIRM = Read-Host "이 커밋 메시지로 진행하시겠습니까? (y/N)"
if ($COMMIT_CONFIRM -ne "y" -and $COMMIT_CONFIRM -ne "Y") {
    Print-Warn "사용자에 의해 커밋이 취소되었습니다."
    exit 1
}

git add . 2>&1
git commit -m "$COMMIT_MSG" 2>&1
if ($LASTEXITCODE -eq 0) { Print-Ok "커밋 완료: $COMMIT_MSG" }
else { Print-Error "커밋 실패."; exit 1 }

# =============================================================================
# Step H -- Git 푸시
# =============================================================================
Print-Header "Step H: Git 푸시"
Print-Info "origin/$INITIAL(으)로 푸시 중..."

git push origin $INITIAL 2>&1
if ($LASTEXITCODE -eq 0) { Print-Ok "origin/$INITIAL(으)로 푸시 완료." }
else { Print-Error "푸시 실패. 원격 연결 상태를 확인하세요."; exit 1 }

# =============================================================================
# Step I -- PR 생성 (선택)
# =============================================================================
Print-Header "Step I: Pull Request (선택)"

$CREATE_PR = Read-Host "dev 브랜치로 Pull Request를 지금 생성하시겠습니까? (y/N)"
if ($CREATE_PR -eq "y" -or $CREATE_PR -eq "Y") {
    $PR_TITLE = Read-Host "PR 제목을 입력하세요"
    gh pr create --base dev --head $INITIAL --title "$PR_TITLE" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Print-Ok "Pull Request가 생성되었습니다."
        $PR_STATUS = "생성 완료"
    } else {
        Print-Warn "PR 생성에 실패했습니다. 수동으로 생성하세요."
        $PR_STATUS = "실패"
    }
    Write-Host ""
    Print-Manual "[리마인더] PR 설명에 다음을 포함하세요: 변경 파일 목록, 테스트 결과(KPI), 이중 경로 원칙 확인."
} else {
    $PR_STATUS = "생략"
    Write-Host ""
    Print-Info "수동으로 PR을 생성하려면 다음 명령어를 사용하세요:"
    Write-Host "  gh pr create --base dev --head $INITIAL --title `"[${STAGE}단계] $SUMMARY`""
}

# =============================================================================
# Step J -- 문서 정합성 확인 (안내)
# =============================================================================
Print-Header "Step J: 문서 정합성 확인"
Write-Host ""
Write-Host "  [문서 정합성 확인 -- 수동으로 검토하세요]"
Write-Host "    [ ] 새 파일 추가? -> Directory_Structure.md 업데이트"
Write-Host "    [ ] 새 환경변수 추가? -> .env.example 및 README.md 환경변수 표 업데이트"
Write-Host "    [ ] 새 Python 의존성 추가? -> requirements.txt 업데이트 (팀 사전 협의 필수)"
Write-Host "    [ ] API 계약 변경? -> docs\api_specification.md 업데이트"
Write-Host "    [ ] 아키텍처 변경? -> docs\architecture.md 업데이트"
Write-Host ""

# =============================================================================
# Step K -- 최종 요약
# =============================================================================
Print-Header "Post-work 요약"
Write-Host ""
Write-Host "  브랜치     : $INITIAL"
Write-Host "  단계       : $STAGE"
Write-Host "  날짜       : $DATE"
Write-Host "  Changelog  : $CHANGELOG_FILE (엔트리 추가됨)"
Write-Host "  커밋       : $COMMIT_MSG"
Write-Host "  푸시       : origin/$INITIAL"
Write-Host "  PR         : $PR_STATUS"
Write-Host "  ---"
Print-Manual "$CHANGELOG_FILE 상세 내용 기입"
Print-Manual "문서 정합성 확인"
Write-Host ""
Write-Host "==========================================="
Write-Host "  Post-work 완료. 수고하셨습니다!" -ForegroundColor Green
Write-Host "==========================================="
