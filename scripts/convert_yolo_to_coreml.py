"""
YOLO26n .pt 모델을 iOS CoreML (.mlpackage) 포맷으로 변환하는 스크립트.

변환 대상:
    - server/models/yolo26n/object_detection.pt  -> object_detection.mlpackage (NMS 내장)
    - server/models/yolo26n/segmentation.pt      -> segmentation.mlpackage (NMS 미적용, segment task)

산출 위치:
    - client/assets/models/yolo26n/ios/<model_name>.mlpackage

사용법:
    # object_detection 변환 (NMS 내장, Vision 프레임워크 호환) - 기본값
    python scripts/convert_yolo_to_coreml.py

    # segmentation 모델 변환 (NMS 미적용)
    python scripts/convert_yolo_to_coreml.py --model segmentation --no-nms

    # 모델명 직접 지정
    python scripts/convert_yolo_to_coreml.py --model object_detection --imgsz 640

참고:
    - detect 태스크는 nms=True 옵션으로 IOSDetectModel 래핑 + pipeline_coreml 적용
      (VNRecognizedObjectObservation 호환 산출물).
    - segment 태스크는 NMS 미지원(ultralytics TODO) - raw mask tensor 산출.
    - Xcode 빌드 시 .mlpackage는 자동으로 .mlmodelc로 컴파일되어 Bundle.main에 포함됨.
    - coremltools 9.0 / ultralytics 8.4.83 호환.
"""

import argparse
import ast
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from ultralytics import YOLO
except ImportError:
    print(
        "Error: ultralytics 라이브러리가 설치되어 있지 않습니다. requirements.txt를 확인해 주십시오."
    )
    sys.exit(1)


def convert_model(model_name: str, imgsz: int, half: bool, nms: bool) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))

    src_path = os.path.join(project_root, "server", "models", "yolo26n", f"{model_name}.pt")
    dst_dir = os.path.join(project_root, "client", "assets", "models", "yolo26n", "ios")
    dst_path = os.path.join(dst_dir, f"{model_name}.mlpackage")

    if not os.path.exists(src_path):
        print(f"Error: 원본 모델 파일이 존재하지 않습니다: {src_path}")
        sys.exit(1)

    print(f"변환 대상 모델 경로: {src_path}")
    print(f"출력 대상 경로: {dst_path}")
    print(f"매개변수: imgsz={imgsz}, half={half}, nms={nms}")
    print(
        "CoreML 포맷으로 모델 변환(Export)을 시작합니다. 이 작업은 다소 시간이 소요될 수 있습니다..."
    )

    try:
        model = YOLO(src_path, verbose=False)
        task = model.task
        print(f"모델 태스크: {task}")

        # detect 태스크에만 nms 적용 (segment/pose/classify는 ultralytics 미지원)
        effective_nms = nms and task == "detect"
        if nms and not effective_nms:
            print(f"[주의] task={task} 모델에는 NMS 옵션이 지원되지 않음 - nms=False로 변환")

        # CoreML export (imgsz=640, FP16 half, NMS 옵션)
        exported_path = model.export(format="coreml", imgsz=imgsz, half=half, nms=effective_nms)
        print(f"변환 완료! (ultralytics 산출 경로): {exported_path}")

        # client/assets/models/yolo26n/ios/ 디렉토리 보장
        os.makedirs(dst_dir, exist_ok=True)

        # 기존 mlpackage 존재 시 제거 후 이동 (덮어쓰기)
        if os.path.exists(dst_path):
            shutil.rmtree(dst_path)
            print(f"기존 mlpackage 제거: {dst_path}")

        exported_abs = (
            exported_path
            if os.path.isabs(exported_path)
            else os.path.join(project_root, exported_path)
        )
        if not os.path.exists(exported_abs):
            print(f"Error: 변환 산출물을 찾을 수 없습니다: {exported_abs}")
            sys.exit(1)

        shutil.move(exported_abs, dst_path)
        print(f"최종 배치 완료: {dst_path}")

        return dst_path

    except Exception as e:
        print(f"모델 변환 중 오류 발생: {e}")
        sys.exit(1)


def verify_model(mlpackage_path: str, model_name: str, expect_nms: bool) -> bool:
    """변환된 .mlpackage의 메타데이터와 Vision 호환성을 검증."""
    try:
        import coremltools as ct

        model = ct.models.MLModel(mlpackage_path)
        spec = model.get_spec()
        print(f"\n[검증] {model_name}.mlpackage 메타데이터:")
        print(f"  - 입력: {list(spec.description.input)}")
        print(f"  - 출력: {list(spec.description.output)}")
        print(f"  - predictedFeatureName: '{spec.description.predictedFeatureName}'")
        print(f"  - predictedProbabilitiesName: '{spec.description.predictedProbabilitiesName}'")

        # NMS 파이프라인 적용 여부 확인 (출력 이름에 confidence / coordinates)
        output_names = [o.name for o in spec.description.output]
        has_nms_outputs = any(
            name in output_names for name in ("confidence", "coordinates", "boxes")
        )
        if expect_nms:
            if has_nms_outputs:
                print(f"  - [OK] NMS 파이프라인 출력 감지: {output_names}")
            else:
                print(f"  - [경고] NMS 출력 미감지: {output_names} (Vision 호환 문제 가능성)")

        # 클래스 라벨 메타데이터
        user_metadata = spec.description.metadata.userDefined
        if "names" in user_metadata:
            names_dict = ast.literal_eval(user_metadata["names"])
            print(f"  - names 메타데이터: {len(names_dict)}개 클래스")
        if "classes" in user_metadata:
            classes = user_metadata["classes"]
            class_count = len(classes.split(",")) if classes else 0
            print(f"  - classes 선언: {class_count}개")

        return True
    except Exception as e:
        print(f"[검증 경고] 메타데이터 확인 실패 (치명적 아님): {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="YOLO26n .pt -> CoreML .mlpackage 변환")
    parser.add_argument(
        "--model",
        default="object_detection",
        choices=["object_detection", "segmentation"],
        help="변환할 모델명 (기본값: object_detection)",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="입력 이미지 사이즈 (기본값: 640)")
    parser.add_argument(
        "--half",
        action="store_true",
        default=True,
        help="FP16 양자화 적용 (기본값: True, ANE 최적화)",
    )
    parser.add_argument("--no-half", dest="half", action="store_false", help="FP32 유지")
    parser.add_argument(
        "--nms",
        action="store_true",
        default=True,
        help="NMS 후처리 내장 (detect 태스크만, 기본값: True)",
    )
    parser.add_argument(
        "--no-nms", dest="nms", action="store_false", help="NMS 후처리 미적용 (raw tensor 산출)"
    )
    args = parser.parse_args()

    mlpackage_path = convert_model(args.model, args.imgsz, args.half, args.nms)
    verify_model(mlpackage_path, args.model, expect_nms=args.nms)
    print("\n모든 변환 작업이 완료되었습니다.")
    print("다음 단계: Xcode에서 .mlpackage를 타겟 리소스로 추가 (빌드 시 .mlmodelc로 자동 컴파일)")


if __name__ == "__main__":
    main()
