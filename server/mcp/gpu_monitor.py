"""
System/GPU Monitor MCP 연동 모듈.
GPU 자원 사용량과 CUDA 메모리 한계를 모니터링하고 임계치 돌파 시 OpenAI 핫스왑 제어를 지원합니다.
아웃오브밴드 비동기 처리를 지향하여 메인 루프에 영향을 주지 않도록 구현합니다.
"""

import asyncio
import contextlib
import logging
import os
import shutil
import subprocess  # nosec B404
import sys

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)


class GPUMonitorMCP:
    """
    GPU 및 System 자원을 모니터링하는 MCP 연동 클래스.
    """

    def __init__(self, memory_threshold_mb: float = 8000.0, usage_threshold_pct: float = 85.0):
        self.memory_threshold_mb = memory_threshold_mb
        self.usage_threshold_pct = usage_threshold_pct
        self._has_cuda = False

        # PyTorch 및 CUDA 가용 여부 확인 (방어적 임포트)
        try:
            import torch

            self._has_cuda = torch.cuda.is_available()
            if self._has_cuda:
                logger.info("CUDA GPU 감지됨. PyTorch를 통한 실시간 GPU 모니터링을 활성화합니다.")
            else:
                logger.info("CUDA GPU 미감지. 가상 Mock GPU 모니터링으로 폴백합니다.")
        except ImportError:
            logger.info("PyTorch 모듈 미설치. 가상 Mock GPU 모니터링으로 폴백합니다.")

    @staticmethod
    def _read_nvidia_smi() -> tuple[float, float, float] | None:
        """nvidia-smi로 (사용률%, 사용메모리MB, 총메모리MB)를 읽는다. 실패 시 None.

        torch.cuda.memory_allocated는 "현재 파이썬 프로세스"의 얼로케이터 통계라, YOLO 추론이
        별도 스레드풀/컨텍스트에서 돌면 0으로 나온다(콘솔 MCP 검증 패널에 메모리 0 MB로
        표시되던 근본 원인). nvidia-smi는 디바이스 전체 실사용을 보고하므로 콘솔 표시값이
        실제와 일치한다.
        """
        exe = shutil.which("nvidia-smi")
        if not exe:
            return None
        try:
            proc = subprocess.run(  # nosec B603
                [
                    exe,
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
        except Exception as e:
            logger.debug(f"nvidia-smi 조회 실패: {e!s}")
            return None
        line = proc.stdout.strip().splitlines()
        if not line:
            return None
        parts = [p.strip() for p in line[0].split(",")]
        if len(parts) < 3:
            return None
        try:
            return float(parts[0]), float(parts[1]), float(parts[2])
        except (TypeError, ValueError):
            return None

    async def get_gpu_status(self) -> dict:
        """
        현재 GPU 자원 상태를 딕셔너리 형태로 반환합니다. (방어적 코딩 및 Mock 폴백 적용)

        - MOCK_GPU_USAGE_PCT가 명시적으로 설정되면 CUDA 유무와 무관하게 모의값을 사용한다
          (테스트/데모에서 부하 상황 강제용). 미설정 + CUDA면 nvidia-smi 실측을 우선한다.
        - CUDA 실측 메모리는 nvidia-smi(디바이스 전체) 기준으로 보고한다. nvidia-smi가 없으면
          torch.cuda.mem_get_info(디바이스 free/total)로 폴백한다.
        """
        force_mock = "MOCK_GPU_USAGE_PCT" in os.environ
        if not self._has_cuda or force_mock:
            # Mock 데이터 반환 (시스템 부하 시뮬레이션용 환경변수 대응 가능)
            mock_usage = float(os.getenv("MOCK_GPU_USAGE_PCT", "30.0"))
            mock_mem_used = float(os.getenv("MOCK_GPU_MEM_USED_MB", "2048.0"))
            mock_mem_total = 16384.0
            return {
                "has_cuda": self._has_cuda,
                "gpu_usage_pct": mock_usage,
                "memory_used_mb": mock_mem_used,
                "memory_total_mb": mock_mem_total,
                "should_fallback": mock_usage >= self.usage_threshold_pct
                or mock_mem_used >= self.memory_threshold_mb,
            }

        # 실측 1순위: nvidia-smi (디바이스 전체 사용률/메모리).
        # subprocess 블로킹이 이벤트 루프(실시간 반사 경로 포함)를 막지 않도록 executor로 위임.
        loop = asyncio.get_running_loop()
        real = await loop.run_in_executor(None, self._read_nvidia_smi)
        if real is not None:
            usage_pct, mem_used_mb, mem_total_mb = real
            return {
                "has_cuda": True,
                "gpu_usage_pct": usage_pct,
                "memory_used_mb": mem_used_mb,
                "memory_total_mb": mem_total_mb,
                "should_fallback": usage_pct >= self.usage_threshold_pct
                or mem_used_mb >= self.memory_threshold_mb,
            }

        # 실측 2순위: torch device 메모리(프로세스가 아닌 디바이스 free/total 기반 실사용)
        try:
            import torch

            free_b, total_b = torch.cuda.mem_get_info(0)
            mem_used_mb = (total_b - free_b) / (1024**2)
            mem_total_mb = total_b / (1024**2)
            return {
                "has_cuda": True,
                "gpu_usage_pct": 0.0,  # nvidia-smi 없이 사용률은 미상
                "memory_used_mb": mem_used_mb,
                "memory_total_mb": mem_total_mb,
                "should_fallback": mem_used_mb >= self.memory_threshold_mb,
            }
        except Exception as e:
            logger.error(f"GPU 상태 조회 중 예외 발생: {e!s}")
            return {
                "has_cuda": False,
                "gpu_usage_pct": 0.0,
                "memory_used_mb": 0.0,
                "should_fallback": False,
            }

    async def check_hotswap_trigger(self) -> bool:
        """
        자원 임계치 초과 여부를 반환하여 핫스왑 필요성을 진단합니다.
        """
        status = await self.get_gpu_status()
        return status.get("should_fallback", False)
