// 실제 Xcode 빌드 타겟 파일. CoreMLInferenceBridge.swift와 동일한 이유로 반드시
// client/ios/ 루트(서브폴더 아님)에 둬야 pbxproj group path가 SRCROOT 바로 아래로
// resolve되어 실제 빌드에 반영된다(2026-07-08 CoreMLInferenceBridge.swift 주석 참조).
//
// [2026-07-09 도입] 반사 경로 카메라 캡처를 takePhoto()(AVCapturePhotoOutput 정지사진
// 반복 촬영) 방식에서 VisionCamera Frame Processor(연속 비디오 스트림, AVCaptureVideoDataOutput
// 기반) 방식으로 전환하기 위한 플러그인. 원인: 실기기 시스템 로그(log collect --device)
// 분석 결과 enableShutterSound:false로도 AVCapturePhotoOutput.capturePhoto()가 촬영마다
// AVAudioSessionInterruption 알림을 유발해(~300~400ms 간격 = takePhoto 주기와 일치) 동시
// 재생 중인 TTS 안내 음성을 순간 끊는 것이 확인됐다.
//
// 이 플러그인은 카메라 원본 CVPixelBuffer를 client/src/hooks/useCamera.ts의 기존
// captureRealFrame()과 동일한 규칙(중앙 정사각형 크롭 + 640x640 리사이즈 + JPEG quality 0.5)으로
// 가공해 base64로 반환하는 역할만 한다. CoreMLInferenceBridge.swift(모델 로드/추론/파싱)는
// 이 파일에서 전혀 참조하지 않으며 무변경 상태를 유지한다 - 반사 게이트 판정에 쓰이는
// 추론 코드 경로는 기존과 완전히 동일하게, "입력 JPEG를 어떻게 만드는가"만 바뀐다.

import CoreImage
import Foundation
import ImageIO
import UIKit
import VisionCamera

@objc(ReflexFrameProcessorPlugin)
public class ReflexFrameProcessorPlugin: FrameProcessorPlugin {
  // CIContext는 생성 비용이 커 인스턴스당 1회만 만들어 재사용한다(프레임마다 생성 금지).
  private let ciContext = CIContext()

  public override init(proxy: VisionCameraProxyHolder, options: [AnyHashable: Any]! = [:]) {
    super.init(proxy: proxy, options: options)
  }

  public override func callback(_ frame: Frame, withArguments arguments: [AnyHashable: Any]?) -> Any? {
    guard let pixelBuffer = CMSampleBufferGetImageBuffer(frame.buffer) else {
      return nil
    }

    let sourceImage = CIImage(cvPixelBuffer: pixelBuffer)

    // frame.orientation(UIImage.Orientation)을 CGImagePropertyOrientation으로 변환해
    // 픽셀 데이터에 회전을 실제로 반영한다(oriented() 호출 후의 extent가 화면에 보이는
    // 방향 기준 너비/높이가 되므로, useCamera.ts가 photo.orientation으로 수동 보정하던
    // isRotated90 분기가 여기서는 필요 없다). 암시적 UIImage.Orientation -> CGImagePropertyOrientation
    // 변환 이니셜라이저가 이 SDK 조합에서 인식되지 않아(rawValue: 쪽으로 오버로드 해석되는
    // 컴파일 오류 실측) 수동 매핑한다.
    let cgOrientation = ReflexFrameProcessorPlugin.cgImageOrientation(from: frame.orientation)
    // 2026-07-12 실기기 실측: frame.orientation 기준 보정만 적용하면 저장된 프레임이
    // 실제 폰 방향(노치 위, 정자세) 대비 180도 뒤집혀 나온다(손 피사체로 반복 확인,
    // Info.plist UISupportedInterfaceOrientations에서 PortraitUpsideDown 제거로도
    // 미해결). react-native-vision-camera 4.7.3의 CMAccelerometerData+deviceOrientation.swift
    // 가속도계 부호 판정이 이 기기 조합에서 반대로 보고되는 것으로 추정되며, 라이브러리
    // 내부(node_modules) 수정은 재설치 시 유실되므로 여기서 180도 보정 회전을 추가한다.
    let oriented = sourceImage.oriented(cgOrientation).oriented(.down)

    // 중앙 정사각형 크롭 (미리보기와 모델 입력 기하 구조를 일치시켜 bbox 정합 유지,
    // captureRealFrame()의 크롭 규칙과 동일).
    let extent = oriented.extent
    let cropSize = min(extent.width, extent.height)
    let originX = extent.origin.x + (extent.width - cropSize) / 2.0
    let originY = extent.origin.y + (extent.height - cropSize) / 2.0
    let cropped = oriented.cropped(to: CGRect(x: originX, y: originY, width: cropSize, height: cropSize))

    // 640x640 리사이즈.
    let targetSize: CGFloat = 640
    let scale = targetSize / cropSize
    let resized = cropped
      .transformed(by: CGAffineTransform(scaleX: scale, y: scale))
      .transformed(by: CGAffineTransform(translationX: -cropped.extent.origin.x * scale, y: -cropped.extent.origin.y * scale))

    guard let cgImage = ciContext.createCGImage(resized, from: CGRect(x: 0, y: 0, width: targetSize, height: targetSize)) else {
      return nil
    }

    // captureRealFrame()의 compress:0.5(JPEG quality 0.5)와 동일한 압축률 유지.
    guard let jpegData = UIImage(cgImage: cgImage).jpegData(compressionQuality: 0.5) else {
      return nil
    }

    return jpegData.base64EncodedString()
  }

  private static func cgImageOrientation(from uiOrientation: UIImage.Orientation) -> CGImagePropertyOrientation {
    switch uiOrientation {
    case .up: return .up
    case .upMirrored: return .upMirrored
    case .down: return .down
    case .downMirrored: return .downMirrored
    case .left: return .left
    case .leftMirrored: return .leftMirrored
    case .right: return .right
    case .rightMirrored: return .rightMirrored
    @unknown default: return .up
    }
  }
}
