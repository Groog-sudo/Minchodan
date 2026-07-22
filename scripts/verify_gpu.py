# -*- coding: utf-8 -*-
import platform
import sys

import torch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


MIN_CUDA_MAJOR = 13
MIN_TORCH_VERSION = (2, 13)
BLACKWELL_CAPABILITY_MAJOR = 12


def _run_tensor_step(device: torch.device) -> bool:
    """선택한 가속기에서 행렬 연산을 실행해 실제 커널 동작을 검증합니다."""
    try:
        x = torch.randn(100, 100, device=device)
        y = torch.randn(100, 100, device=device)
        z = torch.matmul(x, y)
        _ = z.cpu()
    except Exception as exc:  # pragma: no cover - 하드웨어별 런타임 오류 출력
        print(f"오류: {device.type.upper()} 연산 검증 실패: {exc}")
        return False

    print(f"{device.type.upper()} 연산 1 step 검증 성공.")
    return True


def _verify_macos() -> bool:
    """macOS는 CUDA 대신 Apple MPS를 우선 사용하고 CPU를 폴백으로 검증합니다."""
    if torch.backends.mps.is_available():
        print("macOS Apple MPS 가속기를 발견했습니다.")
        return _run_tensor_step(torch.device("mps"))

    print("경고: MPS를 사용할 수 없어 macOS CPU 폴백을 검증합니다.")
    return _run_tensor_step(torch.device("cpu"))


def _verify_cuda() -> bool:
    """Ubuntu/Windows GPU 서버의 CUDA 13 및 실제 GPU 연산을 검증합니다."""
    if not torch.cuda.is_available():
        print("오류: CUDA를 사용할 수 없습니다. NVIDIA 드라이버와 cu130 PyTorch 휠을 확인하세요.")
        return False

    compiled_cuda = torch.version.cuda
    if not compiled_cuda:
        print("오류: 현재 PyTorch가 CUDA 지원 없이 빌드됐습니다.")
        return False

    try:
        cuda_major = int(compiled_cuda.split(".", maxsplit=1)[0])
    except ValueError:
        print(f"오류: PyTorch CUDA 버전을 해석할 수 없습니다: {compiled_cuda}")
        return False

    print(f"PyTorch CUDA 빌드: {compiled_cuda}")
    if cuda_major < MIN_CUDA_MAJOR:
        print(
            f"오류: RTX 5090 지원 기준은 CUDA {MIN_CUDA_MAJOR}.x 이상입니다. "
            f"현재 빌드는 CUDA {compiled_cuda}입니다."
        )
        return False

    device_id = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(device_id)
    capability = torch.cuda.get_device_capability(device_id)

    print(f"발견된 GPU 디바이스: {device_name}")
    print(f"CUDA Capability: {capability[0]}.{capability[1]}")

    # RTX 5090은 팀 GPU 서버의 최대 사양입니다. 이전 세대 GPU도 개발용으로 허용합니다.
    if capability[0] < BLACKWELL_CAPABILITY_MAJOR:
        print(
            f"경고: 현재 GPU Capability ({capability[0]}.{capability[1]})는 "
            "RTX 5090의 sm_120보다 낮아 Blackwell 최적화가 적용되지 않을 수 있습니다."
        )
    else:
        print("팀 최대 사양 RTX 5090(sm_120) 호환 검증 성공.")

    return _run_tensor_step(torch.device("cuda", device_id))


def main() -> int:
    """운영체제별 PyTorch 가속기 호환성을 검증합니다."""
    current_os = platform.system()
    print("PyTorch 가속 환경 검증을 시작합니다.")
    print(f"운영체제: {current_os}")
    print(f"PyTorch 버전: {torch.__version__}")

    try:
        torch_version = tuple(
            int(part) for part in str(torch.__version__).split("+", maxsplit=1)[0].split(".")[:2]
        )
    except ValueError:
        print(f"오류: PyTorch 버전을 해석할 수 없습니다: {torch.__version__}")
        return 1

    if torch_version < MIN_TORCH_VERSION:
        required = ".".join(str(part) for part in MIN_TORCH_VERSION)
        print(f"오류: 보안 수정 기준은 PyTorch {required} 이상입니다.")
        return 1

    passed = _verify_macos() if current_os == "Darwin" else _verify_cuda()
    if not passed:
        return 1

    print("환경 검증 완료: 정상 작동 중")
    return 0


if __name__ == "__main__":
    sys.exit(main())
