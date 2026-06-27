"""
System/GPU Monitor MCP 연동 모듈.
GPU 자원 사용량과 CUDA 메모리 한계를 모니터링하고 임계치 돌파 시 OpenAI 핫스왑 제어를 지원합니다.
아웃오브밴드 비동기 처리를 지향하여 메인 루프에 영향을 주지 않도록 구현합니다.
"""

import contextlib
import logging
import os
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

    async def get_gpu_status(self) -> dict:
        """
        현재 GPU 자원 상태를 딕셔너리 형태로 반환합니다. (방어적 코딩 및 Mock 폴백 적용)
        """
        if not self._has_cuda:
            # Mock 데이터 반환 (시스템 부하 시뮬레이션용 환경변수 대응 가능)
            mock_usage = float(os.getenv("MOCK_GPU_USAGE_PCT", "30.0"))
            mock_mem_used = float(os.getenv("MOCK_GPU_MEM_USED_MB", "2048.0"))
            mock_mem_total = 16384.0
            return {
                "has_cuda": False,
                "gpu_usage_pct": mock_usage,
                "memory_used_mb": mock_mem_used,
                "memory_total_mb": mock_mem_total,
                "should_fallback": mock_usage >= self.usage_threshold_pct
                or mock_mem_used >= self.memory_threshold_mb,
            }

        try:
            import torch

            device_id = 0  # 기본 GPU 0번 기준
            mem_allocated = torch.cuda.memory_allocated(device_id) / (1024**2)  # MB 변환
            mem_reserved = torch.cuda.memory_reserved(device_id) / (1024**2)

            # 대략적인 메모리 지표 계산
            should_fallback = mem_allocated >= self.memory_threshold_mb

            return {
                "has_cuda": True,
                "gpu_usage_pct": 50.0,  # 간단한 API 구조로, PyTorch 자체에서는 usage% 획득이 번거로우므로 대표값 제공
                "memory_used_mb": mem_allocated,
                "memory_reserved_mb": mem_reserved,
                "should_fallback": should_fallback,
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
