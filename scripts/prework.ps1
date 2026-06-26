# =============================================================================
# Script Name : prework.ps1
# Platform    : Windows (PowerShell 5.1+)
# Purpose     : Minchodan Pre-work 자동화 -- Git 동기화, 환경 확인, GPU 검증,
#               인프라/문서 리마인더.
# Usage       : powershell -ExecutionPolicy Bypass -File scripts\prework.ps1
# =============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

function Print-Ok($msg)     { Write-Host "[OK] $msg" -ForegroundColor Green }
function Print-Warn($msg)   { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Print-Error($msg)  { Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Print-Info($msg)   { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Print-Manual($msg) { Write-Host "[MANUAL] $msg" -ForegroundColor Yellow }
function Print-Skip($msg)   { Write-Host "[SKIP] $msg" -ForegroundColor Yellow }
function Print-Header($msg) { Write-Host "`n=== $msg ===" -ForegroundColor White }

# --- 스킬 경로 매핑 ---
function Get-SkillPath($stage) {
    switch ($stage) {
        1 { return ".agents\skills\websocket-gateway\SKILL.md" }
        2 { return ".agents\skills\camera-frame-capture\SKILL.md" }
        3 { return ".agents\skills\yolo-obstacle-detection\SKILL.md" }
        4 { return ".agents\skills\rag-knowledge-builder\SKILL.md" }
        5 { return ".agents\skills\rag-realtime-search\SKILL.md" }
        6 { return ".agents\skills\llm-guidance-orchestrator\SKILL.md" }
        7 { return ".agents\skills\tts-voice-streamer\SKILL.md" }
    }
}

$STATUS_GIT = "DONE"
$STATUS_ENV = "DONE"
$STATUS_GPU = "SKIP"

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Minchodan Pre-work 자동화 (PowerShell)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# Step A -- 브랜치 이니셜 입력
# =============================================================================
Print-Header "Step A: 브랜치 이니셜 입력"
$INITIAL = Read-Host "본인 브랜치 이니셜을 입력하세요 (dg/jh/jy/kb/th)"
$validInitials = @("dg", "jh", "jy", "kb", "th")
if ($INITIAL -notin $validInitials) {
    Print-Error "잘못된 이니셜 '$INITIAL'. dg, jh, jy, kb, th 중 하나를 입력하세요."
    exit 1
}
Print-Ok "이니셜: $INITIAL"

# =============================================================================
# Step B -- 파이프라인 단계 입력
# =============================================================================
Print-Header "Step B: 파이프라인 단계 입력"
$STAGE = Read-Host "작업할 파이프라인 단계를 입력하세요 (1-7)"
if ($STAGE -notmatch '^[1-7]$') {
    Print-Error "잘못된 단계 '$STAGE'. 1~7 사이의 정수를 입력하세요."
    exit 1
}
$STAGE = [int]$STAGE
$SKILL_PATH = Get-SkillPath $STAGE
Print-Ok "단계: $STAGE  |  스킬: $SKILL_PATH"

# =============================================================================
# Step C -- Git 동기화
# =============================================================================
Print-Header "Step C: Git 동기화"

Print-Info "원격 저장소에서 가져오는 중..."
git fetch origin 2>&1
if ($LASTEXITCODE -eq 0) { Print-Ok "git fetch origin 완료" }
else { Print-Error "git fetch origin 실패."; $STATUS_GIT = "WARN" }

Print-Info "dev 브랜치로 전환 후 최신 코드 가져오는 중..."
git checkout dev 2>&1
git pull origin dev 2>&1
if ($LASTEXITCODE -eq 0) { Print-Ok "dev 브랜치가 최신 상태입니다." }
else { Print-Error "dev 브랜치 동기화에 실패했습니다."; $STATUS_GIT = "WARN" }

Print-Info "개인 브랜치 '$INITIAL'(으)로 전환 중..."
$branchExists = git branch --list $INITIAL 2>&1
if ($branchExists) {
    git checkout $INITIAL 2>&1
    Print-Ok "'$INITIAL' 브랜치로 전환 완료."
} else {
    Print-Warn "'$INITIAL' 브랜치가 로컬에 없습니다. dev에서 새로 생성합니다..."
    git checkout -b $INITIAL dev 2>&1
    if ($LASTEXITCODE -eq 0) { Print-Ok "dev 기반으로 '$INITIAL' 브랜치 생성 및 전환 완료." }
    else { Print-Error "'$INITIAL' 브랜치 생성에 실패했습니다."; $STATUS_GIT = "WARN" }
}

Print-Info "최신 dev를 '$INITIAL'에 병합 중..."
git merge dev --no-edit 2>&1
if ($LASTEXITCODE -eq 0) { Print-Ok "dev를 '$INITIAL'에 병합 완료." }
else { Print-Warn "병합 충돌이 발생했습니다. 수동으로 해결해주세요."; $STATUS_GIT = "WARN" }

# =============================================================================
# Step D -- 환경 파일 확인
# =============================================================================
Print-Header "Step D: 환경 파일 확인"
if (Test-Path ".env") {
    Print-Ok ".env 파일이 존재합니다."
} elseif (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Print-Warn ".env 파일이 없어서 .env.example에서 복사했습니다. 서버 실행 전 실제 값을 입력해주세요."
    $STATUS_ENV = "WARN"
} else {
    Print-Error ".env.example 파일도 없습니다. .env를 생성할 수 없습니다."
    $STATUS_ENV = "ERROR"
}

# =============================================================================
# Step E -- 가상환경 활성화 확인
# =============================================================================
Print-Header "Step E: 가상환경 활성화 확인"
if ($env:VIRTUAL_ENV) {
    Print-Ok "가상환경이 활성화되어 있습니다: $env:VIRTUAL_ENV"
} else {
    Print-Warn "가상환경이 활성화되어 있지 않습니다."
    Write-Host "  다음 명령어를 실행하세요:  .\.venv\Scripts\Activate.ps1"
}

# =============================================================================
# Step F -- Python 의존성 확인
# =============================================================================
Print-Header "Step F: Python 의존성 확인"
pip install -r requirements.txt --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { Print-Ok "의존성 설치가 완료되었습니다." }
else { Print-Warn "pip install 중 문제가 발생했습니다. requirements.txt를 확인하세요." }

# =============================================================================
# Step G -- GPU 환경 확인 (3단계 이상)
# =============================================================================
Print-Header "Step G: GPU 환경 확인"
if ($STAGE -ge 3) {
    if (Test-Path "scripts\verify_gpu.py") {
        Print-Info "GPU 검증 실행 중..."
        python scripts\verify_gpu.py 2>&1
        if ($LASTEXITCODE -ne 0) { Print-Warn "GPU 검증에서 문제가 보고되었습니다." }
        $STATUS_GPU = "DONE"
    } else {
        Print-Warn "scripts\verify_gpu.py 파일이 없습니다. 건너뜁니다."
        $STATUS_GPU = "WARN"
    }
} else {
    Print-Skip "GPU 확인 생략 (3단계 미만)."
}

# =============================================================================
# Step H -- 인프라 서비스 확인 (안내)
# =============================================================================
Print-Header "Step H: 인프라 서비스 확인"
Write-Host ""
Print-Manual "코딩 시작 전 아래 서비스들이 실행 중인지 확인하세요:"
Write-Host "    - Redis (기본: localhost:6379)"
Write-Host "    - Ollama 모델: gemma2:9b, llava, nomic-embed-text (기본: localhost:11434)"
Write-Host "    - Docker 컨테이너 (해당 시): docker\windows_docker_start.bat"
Write-Host ""

# =============================================================================
# Step I -- 필수 문서 읽기 체크리스트 (안내)
# =============================================================================
Print-Header "Step I: 필수 문서 읽기"
Write-Host ""
Write-Host "  [필수 읽기 -- 코드 작성 전 반드시 완료하세요]"
Write-Host "    [ ] 1. README.md"
Write-Host "    [ ] 2. docs\minchodan_design_note.md"
Write-Host "    [ ] 3. docs\AGENTS.md"
Write-Host "    [ ] 4. docs\course_codebase_guide.md"
Write-Host "    [ ] 5. $SKILL_PATH"
Write-Host ""

# =============================================================================
# Step J -- 이중 경로 원칙 리마인더
# =============================================================================
Print-Header "Step J: 이중 경로 원칙 리마인더"
Write-Host ""
Write-Host "  [필수 -- 이중 경로 원칙 (비협상)]" -ForegroundColor Red
Write-Host "    반사 경로: LLM / RAG / 실시간 TTS 호출 절대 금지."
Write-Host "              data\reflex_clips\ 사전합성 클립만 사용."
Write-Host "              지연 목표: 300ms 미만 (탐지 기준)."
Write-Host "    인지 경로: Redis Streams -> LangGraph L1/L2/L3 -> RAG -> 실시간 TTS 사용."
Write-Host ""

# =============================================================================
# Step K -- 최종 요약
# =============================================================================
Print-Header "Pre-work 요약"
Write-Host ""
Write-Host "  브랜치     : $INITIAL"
Write-Host "  단계       : $STAGE"
Write-Host "  스킬 파일  : $SKILL_PATH"
Write-Host "  ---"
if ($STATUS_GIT -eq "DONE") { $gitColor = "Green" } else { $gitColor = "Yellow" }
if ($STATUS_ENV -eq "DONE") { $envColor = "Green" } else { $envColor = "Yellow" }
if ($STATUS_GPU -eq "DONE") { $gpuColor = "Green" } elseif ($STATUS_GPU -eq "SKIP") { $gpuColor = "Yellow" } else { $gpuColor = "Red" }
Write-Host "  [${STATUS_GIT}] Git 동기화" -ForegroundColor $gitColor
Write-Host "  [${STATUS_ENV}] .env 확인" -ForegroundColor $envColor
Write-Host "  [${STATUS_GPU}] GPU 확인" -ForegroundColor $gpuColor
Print-Manual "서비스 확인 (Redis, Ollama, Docker)"
Print-Manual "문서 읽기 체크리스트"
Write-Host ""
Write-Host "==========================================="
Write-Host "  Pre-work 완료. 코딩을 시작하세요." -ForegroundColor Green
Write-Host "==========================================="
