// 실제 Xcode 빌드 타겟 파일 (project.pbxproj의 "Minchodan" 그룹에 path 속성이 없어
// 이 파일의 fileRef가 SRCROOT 바로 아래, 즉 이 경로로 resolve된다. .d 의존성 파일로 확인함, 2026-07-06).
// client/ios/Minchodan/CoreMLInferenceBridge.swift 는 프로젝트에 실제로 연결되지 않은 미사용 사본이다.

import Foundation
import CoreML
import Vision
import UIKit
import React

// YOLO26n end2end CoreML 산출물의 raw tensor 출력 [1, 300, 6] 파싱.
// 각 박스: (cx, cy, w, h, confidence, class_id) - 정규화된 0~1 좌표계.
// end2end 모델은 NMS 내장, confidence < threshold 박스는 패딩.
@objc(CoreMLInferenceBridge)
class CoreMLInferenceBridge: NSObject {
  private var segModel: MLModel?
  private var detModel: MLModel?

  // confidence 임계값 (패딩 박스 및 노이즈 필터링).
  // 실제 표시/경보 기준 임계값은 앱 UI(CameraView.tsx)에서 사용자가 조절하므로,
  // 여기서는 조절 가능 범위를 넓게 확보하기 위해 낮은 하한값만 둔다.
  private let confThreshold: Double = 0.05
  // Object Detection 29 커스텀 클래스 라벨 (det_best_20260705.mlpackage 기준)
  private let classNames: [Int: String] = [
    0: "barricade", 1: "bench", 2: "bicycle", 3: "bollard", 4: "bus",
    5: "car", 6: "carrier", 7: "cat", 8: "chair", 9: "dog",
    10: "fire_hydrant", 11: "kiosk", 12: "motorcycle", 13: "movable_signage",
    14: "parking_meter", 15: "person", 16: "pole", 17: "potted_plant",
    18: "power_controller", 19: "scooter", 20: "stop", 21: "stroller",
    22: "table", 23: "traffic_light", 24: "traffic_light_controller",
    25: "traffic_sign", 26: "tree_trunk", 27: "truck", 28: "wheelchair"
  ]

  // Segmentation 4 클래스 라벨 (segmentation.pt 기준)
  private let segClassNames: [Int: String] = [
    0: "sidewalk_normal",
    1: "caution",
    2: "roadway",
    3: "braille_normal"
  ]

  @objc
  func loadModels(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    do {
      let config = MLModelConfiguration()
      // 2026-07-07 실기기(고태현 iPhone) 재검증 결과: raw tensor 파싱 아키텍처로 전환한
      // 뒤에도 .cpuAndGPU 설정 시 첫 프레임 추론 직후 크래시(백색 화면 후 프로세스 종료,
      // PID 재기동 반복)가 동일하게 재현됨을 확인함. GPU(Metal) 경로의 MLIR pass manager
      // failed 문제가 raw tensor 파싱과 무관하게 지속되는 것으로 판단, CPU 전용으로 재확정.
      config.computeUnits = .cpuOnly

      // object_detection (필수) - end2end raw tensor 모델
      guard let detURL = Bundle.main.url(forResource: "object_detection", withExtension: "mlmodelc") else {
        reject("FILE_NOT_FOUND", "object_detection.modelc 에셋을 Bundle에서 찾을 수 없습니다.", nil)
        return
      }
      self.detModel = try MLModel(contentsOf: detURL, configuration: config)

      // segmentation (선택) - 현재 미번들이면 nil로 두고 det만 동작
      // 다음 세션에서 segmentation.mlmodelc 추가 시 자동 활성화
      if let segURL = Bundle.main.url(forResource: "segmentation", withExtension: "mlmodelc") {
        self.segModel = try MLModel(contentsOf: segURL, configuration: config)
        print("[CoreMLBridge] segmentation 모델 로드 완료")
      } else {
        print("[CoreMLBridge] segmentation.mlmodelc 미번들 - det-only 모드로 기동")
      }

      print("[CoreMLBridge] object_detection 모델 로드 완료 (CPU 전용 모드, GPU 크래시 회피)")
      let statusDict: [String: Any] = [
        "det": true,
        "seg": self.segModel != nil
      ]
      resolve(statusDict as NSDictionary)
    } catch {
      reject("LOAD_ERROR", "CoreML 모델 로드 실패: \(error.localizedDescription)", error as NSError)
    }
  }

  @objc
  func detectFrame(_ base64Image: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    guard let detModel = self.detModel else {
      reject("NOT_LOADED", "CoreML detection 모델이 로드되지 않았습니다.", nil)
      return
    }

    // cgImage는 EXIF 방향 정보(imageOrientation)를 반영하지 않으므로,
    // 회전된 상태 그대로 모델에 들어가 완전히 다른(엉뚱한) 클래스로 오탐지되는 원인이 된다.
    // 반드시 방향이 정규화된(.up) cgImage를 사용해야 한다.
    guard let imageData = Data(base64Encoded: base64Image),
          let image = UIImage(data: imageData),
          let cgImage = image.normalizedCGImage() else {
      reject("INVALID_IMAGE", "전송된 base64 이미지 디코딩 실패", nil)
      return
    }

    // 메인 UI 스레드 블로킹 방지를 위한 백그라운드 실시간 처리
    DispatchQueue.global(qos: .userInteractive).async {
      do {
        let startTime = CFAbsoluteTimeGetCurrent()
        let detResults = try self.runDetection(model: detModel, cgImage: cgImage, modelType: "object_detection")
        let detTime = CFAbsoluteTimeGetCurrent()
        let detLatency = (detTime - startTime) * 1000.0

        var segResults: [[String: Any]] = []
        var segLatency = 0.0

        // segmentation 모델이 로드된 경우에만 실행
        if let segModel = self.segModel {
          let segStartTime = CFAbsoluteTimeGetCurrent()
          segResults = try self.runDetection(model: segModel, cgImage: cgImage, modelType: "segmentation")
          segLatency = (CFAbsoluteTimeGetCurrent() - segStartTime) * 1000.0
        }

        let totalLatency = detLatency + segLatency
        print("[CoreMLBridge] 벤치마크 - 탐지(det): \(String(format: "%.2f", detLatency))ms | 분할(seg): \(String(format: "%.2f", segLatency))ms | 총추론: \(String(format: "%.2f", totalLatency))ms")

        DispatchQueue.main.async {
          let benchmarkDict: [String: Any] = [
            "det_ms": detLatency,
            "seg_ms": segLatency,
            "total_ms": totalLatency
          ]
          let responseDict: [String: Any] = [
            "seg": segResults as NSArray,
            "det": detResults as NSArray,
            "benchmark": benchmarkDict as NSDictionary
          ]
          resolve(responseDict as NSDictionary)
        }
      } catch {
        DispatchQueue.main.async {
          reject("EXEC_ERROR", "추론 실행 오류: \(error.localizedDescription)", error as NSError)
        }
      }
    }
  }

  // end2end YOLO 모델 추론 및 raw tensor [1, 300, attrsPerBox] 파싱
  private func runDetection(model: MLModel, cgImage: CGImage, modelType: String) throws -> [[String: Any]] {
    // 입력 이미지 640x640 리사이즈 (CoreML ImageType 자동 처리)
    let inputFeature = try prepareInput(cgImage: cgImage, expectedSize: 640)
    let prediction = try model.prediction(from: inputFeature)

    // raw tensor 출력 추출 (출력 이름은 모델마다 상이 - 첫 출력 사용)
    guard let outputName = prediction.featureNames.first,
          let outputMultiArray = prediction.featureValue(for: outputName)?.multiArrayValue else {
      print("[CoreMLBridge] 출력 tensor 추출 실패: \(prediction.featureNames)")
      return []
    }

    return parseYoloOutput(multiArray: outputMultiArray, modelType: modelType)
  }

  // CGImage -> CVPixelBuffer (640x640 RGB) 변환
  private func prepareInput(cgImage: CGImage, expectedSize: Int) throws -> MLFeatureProvider {
    let attrs: [CFString: Any] = [
      kCVPixelBufferCGImageCompatibilityKey: kCFBooleanTrue!,
      kCVPixelBufferCGBitmapContextCompatibilityKey: kCFBooleanTrue!,
      kCVPixelBufferIOSurfacePropertiesKey: [:] as AnyObject
    ]

    var pixelBuffer: CVPixelBuffer?
    let status = CVPixelBufferCreate(
      kCFAllocatorDefault,
      expectedSize,
      expectedSize,
      kCVPixelFormatType_32BGRA,
      attrs as CFDictionary,
      &pixelBuffer
    )
    guard status == kCVReturnSuccess, let buffer = pixelBuffer else {
      throw NSError(domain: "CoreMLBridge", code: 1, userInfo: [NSLocalizedDescriptionKey: "PixelBuffer 생성 실패"])
    }

    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }

    let context = CGContext(
      data: CVPixelBufferGetBaseAddress(buffer),
      width: expectedSize,
      height: expectedSize,
      bitsPerComponent: 8,
      bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
      space: CGColorSpaceCreateDeviceRGB(),
      bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue
    )
    context?.interpolationQuality = .high
    context?.draw(cgImage, in: CGRect(x: 0, y: 0, width: expectedSize, height: expectedSize))

    // Vision 호환 입력을 위해 MLFeatureValue로 래핑
    let featureValue = MLFeatureValue(pixelBuffer: buffer)
    let inputName = "image" // YOLO CoreML 입력 이름 고정
    return try MLDictionaryFeatureProvider(dictionary: [inputName: featureValue])
  }

  // YOLO end2end raw tensor [1, 300, attrsPerBox] 파싱
  // 각 행의 구조: (중앙x, 중앙y, 너비, 높이, 신뢰도, 클래스ID)
  private func parseYoloOutput(multiArray: MLMultiArray, modelType: String) -> [[String: Any]] {
    let shape = multiArray.shape.map { $0.intValue }
    guard shape.count == 3 else {
      print("[CoreMLBridge] 예상치 못한 출력 shape 차원: \(shape)")
      return []
    }

    let attrsPerBox = shape[2]
    guard attrsPerBox == 6 || attrsPerBox == 38 else {
      print("[CoreMLBridge] 예상치 못한 출력 attrsPerBox: \(attrsPerBox)")
      return []
    }

    let numBoxes = shape[1]
    let ptr = UnsafeMutablePointer<Float32>(multiArray.dataPointer.assumingMemoryBound(to: Float32.self))
    let strides = multiArray.strides.map { $0.intValue }

    var results: [[String: Any]] = []

    let activeClassNames = (modelType == "segmentation") ? segClassNames : classNames
    let numClasses = activeClassNames.count

    for i in 0..<numBoxes {
      // [1, i, col] 인덱스 계산 (strides[0]은 텐서의 바운딩 박스 단위 이동폭)
      let baseOffset = i * strides[1]
      let cx = Double(ptr[baseOffset + 0 * strides[2]])
      let cy = Double(ptr[baseOffset + 1 * strides[2]])
      let w = Double(ptr[baseOffset + 2 * strides[2]])
      let h = Double(ptr[baseOffset + 3 * strides[2]])
      let confidence = Double(ptr[baseOffset + 4 * strides[2]])
      let classId = Int(ptr[baseOffset + 5 * strides[2]].rounded())

      // confidence 임계값 필터링 (패딩 박스 제거)
      if confidence < confThreshold { continue }
      if classId < 0 || classId >= numClasses { continue }

      // 클라이언트(CameraView.tsx)는 bbox 전체(x,y,w,h)를 640x640 픽셀 단위로 취급하여
      // FRAME_SIZE(640)로 나눠 화면 비율(%)과 위험도 area ratio를 계산한다.
      // x,y만 정규화하고 w,h는 원본 픽셀값으로 남기면 단위가 섞여 박스 위치가 다 뭉치므로,
      // (cx, cy, w, h) 중심점 좌표를 좌상단 기준 (x, y, w, h)로만 변환하고 픽셀 단위를 유지한다.
      let x = cx - w / 2.0
      let y = cy - h / 2.0
      let className = activeClassNames[classId] ?? "unknown"

      results.append([
        "model": modelType,
        "className": className,
        "confidence": confidence,
        "bbox": [
          "x": x,
          "y": y,
          "w": w,
          "h": h
        ]
      ])
    }

    // 신뢰도 기준 역순 정렬
    results.sort { (a, b) -> Bool in
      let confA = a["confidence"] as? Double ?? 0.0
      let confB = b["confidence"] as? Double ?? 0.0
      return confA > confB
    }

    return results
  }
}

private extension UIImage {
  // imageOrientation을 픽셀 데이터에 반영해 방향이 정규화된(.up) CGImage를 반환한다.
  // UIImage.cgImage는 회전 메타데이터를 무시한 원본 센서 방향 그대로이므로,
  // 세로로 촬영된 사진을 그대로 쓰면 모델이 90도 회전된 이미지를 받게 된다.
  func normalizedCGImage() -> CGImage? {
    if imageOrientation == .up {
      return cgImage
    }
    let renderer = UIGraphicsImageRenderer(size: size)
    let normalized = renderer.image { _ in
      draw(in: CGRect(origin: .zero, size: size))
    }
    return normalized.cgImage
  }
}
