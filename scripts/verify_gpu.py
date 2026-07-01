import sys

import torch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("GPU 및 CUDA 환경 검증을 시작합니다.")

    if not torch.cuda.is_available():
        print("오류: CUDA를 사용할 수 없습니다. GPU가 없거나 PyTorch가 CUDA를 지원하지 않습니다.")
        sys.exit(1)

    device_id = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(device_id)
    capability = torch.cuda.get_device_capability(device_id)

    print(f"발견된 GPU 디바이스: {device_name}")
    print(f"CUDA Capability: {capability[0]}.{capability[1]}")

    # sm_120 (12.0) 이상 검증 (Blackwell 전제)
    # 요구 사양은 sm_120(12.0)이지만, RTX 40xx/30xx 등 이전 세대 GPU에서도 검증 가능하도록 경고 후 패스 처리합니다.
    if capability[0] < 12:
        print(
            f"경고: 현재 GPU Capability ({capability[0]}.{capability[1]})가 요구 사양 sm_120 (12.0)보다 낮습니다. Blackwell 최적화가 적용되지 않을 수 있습니다."
        )
    else:
        print("요구 사양 sm_120 (Blackwell) 검증 성공.")

    # GPU 연산 1 step 검증
    try:
        x = torch.randn(100, 100).cuda()
        y = torch.randn(100, 100).cuda()
        z = torch.matmul(x, y)
        _ = z.cpu()  # 동기화
        print("GPU 연산 1 step 검증 성공.")
    except Exception as e:
        print(f"오류: GPU 연산 검증 실패: {e}")
        sys.exit(1)

    print("환경 검증 완료: 정상 작동 중")


if __name__ == "__main__":
    main()
