// 실제 Xcode 빌드 타겟 파일 (project.pbxproj의 "Minchodan" 그룹에 path 속성이 없어
// 이 파일의 fileRef가 SRCROOT 바로 아래, 즉 이 경로로 resolve된다. .d 의존성 파일로 확인함, 2026-07-06).
// 신규 네이티브 브릿지 파일(.swift/.mm)도 client/ios/Minchodan/ 서브폴더가 아니라
// 이 파일과 같은 client/ios/ 루트에 두어야 실제 빌드에 반영된다(2026-07-08: 동일 함정으로 생긴
// 미사용 사본 Minchodan/CoreMLInferenceBridge.mm 발견 및 제거 완료).

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

  // 2026-07-07 실기기(고태현 iPhone) 재검증 결과: raw tensor 파싱 아키텍처로 전환한
  // 뒤에도 .cpuAndGPU 설정 시 첫 프레임 추론 직후 크래시(백색 화면 후 프로세스 종료,
  // PID 재기동 반복)가 동일하게 재현됨을 확인함. GPU(Metal) 경로의 MLIR pass manager
  // failed 문제로 판단됨. 2026-07-11 모델을 FP16으로 재변환한 뒤, GPU를 배제하는
  // .cpuAndNeuralEngine을 우선 시도하고 실패 시에만 .cpuOnly로 폴백한다.
  private func loadModel(url: URL) throws -> MLModel {
    let aneConfig = MLModelConfiguration()
    aneConfig.computeUnits = .cpuAndNeuralEngine
    do {
      let model = try MLModel(contentsOf: url, configuration: aneConfig)
      print("[CoreMLBridge] \(url.lastPathComponent) - ANE 가속 모드로 로드 완료")
      return model
    } catch {
      print("[CoreMLBridge] \(url.lastPathComponent) - ANE 로드 실패(\(error.localizedDescription)), CPU 전용으로 폴백")
      let cpuConfig = MLModelConfiguration()
      cpuConfig.computeUnits = .cpuOnly
      return try MLModel(contentsOf: url, configuration: cpuConfig)
    }
  }

  @objc
  func loadModels(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    do {
      // object_detection (필수) - end2end raw tensor 모델
      guard let detURL = Bundle.main.url(forResource: "object_detection", withExtension: "mlmodelc") else {
        reject("FILE_NOT_FOUND", "object_detection.modelc 에셋을 Bundle에서 찾을 수 없습니다.", nil)
        return
      }
      self.detModel = try loadModel(url: detURL)

      // segmentation (선택) - 현재 미번들이면 nil로 두고 det만 동작
      // 다음 세션에서 segmentation.mlmodelc 추가 시 자동 활성화
      if let segURL = Bundle.main.url(forResource: "segmentation", withExtension: "mlmodelc") {
        self.segModel = try loadModel(url: segURL)
      } else {
        print("[CoreMLBridge] segmentation.mlmodelc 미번들 - det-only 모드로 기동")
      }

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

        // docs/design/indoor_fp_mitigation_design.md §4: isLikelyIndoor 판정 + top-5
        // identifier+confidence를 함께 반환한다(§4.4 게이트는 JS 측 CameraView.tsx에서 결합).
        let sceneStartTime = CFAbsoluteTimeGetCurrent()
        let sceneResult = self.classifyScene(cgImage: cgImage)
        let sceneLatency = (CFAbsoluteTimeGetCurrent() - sceneStartTime) * 1000.0

        let totalLatency = detLatency + segLatency + sceneLatency
        print("[CoreMLBridge] 벤치마크 - 탐지(det): \(String(format: "%.2f", detLatency))ms | 분할(seg): \(String(format: "%.2f", segLatency))ms | 씬분류(scene): \(String(format: "%.2f", sceneLatency))ms | 총추론: \(String(format: "%.2f", totalLatency))ms")

        DispatchQueue.main.async {
          let benchmarkDict: [String: Any] = [
            "det_ms": detLatency,
            "seg_ms": segLatency,
            "scene_ms": sceneLatency,
            "total_ms": totalLatency
          ]
          let responseDict: [String: Any] = [
            "seg": segResults as NSArray,
            "det": detResults as NSArray,
            "benchmark": benchmarkDict as NSDictionary,
            "scene": sceneResult as NSDictionary
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

  // docs/design/indoor_fp_mitigation_design.md §4 실내/실외 씬 분류기 게이트.
  // Vision 내장 VNClassifyImageRequest는 det/seg 모델과 완전히 독립된 Apple 사전학습
  // 분류기라 우리 모델의 도메인쉬프트를 공유하지 않는다. 키워드 집합은 실내 558건 +
  // 실내/실외 혼합 74건(2026-07-07) 실측 로그 분석으로 확정했다(§4.5 근거 참조).

  // "outdoor" 단독 confidence보다 신뢰도가 높은 실외 긍정 증거: 지면/초목/도로 계열
  // identifier. 실측 최대 confidence 0.66(grass/land), 0.48(foliage/plant), crosswalk
  // 등장(0.27) 시 실외로 확정해도 안전했다.
  private let outdoorPositiveIdentifiers: Set<String> = [
    "grass", "land", "path", "plant", "foliage", "crosswalk", "sand_dune", "sand"
  ]

  // "outdoor"가 등장해도 실내 천장 조명을 달/밤하늘로 오인하는 것으로 추정되는
  // 동반 identifier. 실내 558건 중 25%(139건)에서 이 조합으로 "outdoor" confidence가
  // 최대 0.71까지 나왔다 - outdoor 리터럴 단독으로는 신뢰 불가.
  private let indoorFalsePositiveIdentifiers: Set<String> = [
    "night_sky", "moon", "celestial_body"
  ]

  private func classifyScene(cgImage: CGImage) -> [String: Any] {
    do {
      let request = VNClassifyImageRequest()
      let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
      try handler.perform([request])

      guard let observations = request.results else {
        // 분류 실패(observations 없음) 시 판정 불가 상태이므로 §4.6 폴백 정책에 따라
        // isLikelyIndoor=false(허용적)로 반환해 기존 co-occurrence 게이트만으로 동작시킨다.
        return ["isLikelyIndoor": false, "confidence": 0.0, "topLabels": []]
      }

      let top5 = observations.prefix(5)
      let topLabels = top5.map { obs -> [String: Any] in
        ["identifier": obs.identifier, "confidence": Double(obs.confidence)]
      }
      let identifierSet = Set(top5.map { $0.identifier })

      let outdoorEvidence = top5.first { self.outdoorPositiveIdentifiers.contains($0.identifier) }
      let hasIndoorFPSignature = identifierSet.contains("outdoor")
        && !identifierSet.isDisjoint(with: self.indoorFalsePositiveIdentifiers)

      let isLikelyIndoor: Bool
      let indoorConfidence: Double
      if let outdoorEvidence {
        // 지면/초목/도로 identifier가 top-5에 있으면 실외로 확정한다.
        isLikelyIndoor = false
        indoorConfidence = Double(outdoorEvidence.confidence)
      } else if hasIndoorFPSignature {
        // "outdoor"가 나와도 night_sky/moon/celestial_body와 동반되면 조명 오탐으로 간주해 override.
        isLikelyIndoor = true
        indoorConfidence = Double(top5.first { $0.identifier == "outdoor" }?.confidence ?? 0.0)
      } else {
        // 확정적 실외 증거가 없으면 보수적으로 실내로 취급한다(반사 경보 억제 방향 기본값).
        isLikelyIndoor = true
        indoorConfidence = 0.0
      }

      return [
        "isLikelyIndoor": isLikelyIndoor,
        "confidence": indoorConfidence,
        "topLabels": topLabels
      ]
    } catch {
      print("[CoreMLBridge] 씬 분류 실패, 허용적 폴백 적용: \(error.localizedDescription)")
      return ["isLikelyIndoor": false, "confidence": 0.0, "topLabels": []]
    }
  }

  // end2end YOLO 모델 추론 및 raw tensor [1, 300, attrsPerBox] 파싱
  private func runDetection(model: MLModel, cgImage: CGImage, modelType: String) throws -> [[String: Any]] {
    // 입력 이미지 640x640 리사이즈 (CoreML ImageType 자동 처리)
    let inputFeature = try prepareInput(cgImage: cgImage, expectedSize: 640)
    let prediction = try model.prediction(from: inputFeature)

    // segmentation 모델은 출력이 2개다: [1, 300, 38](박스+마스크계수)와
    // [1, 32, 160, 160](프로토타입 마스크). featureNames는 Set 기반이라 순서가
    // 보장되지 않으므로 .first로 집으면 실기기에서 프로토 마스크 텐서를 집어
    // 파싱이 매 프레임 실패하는 문제가 있었다(2026-07-11 실기기 로그로 확인:
    // "예상치 못한 출력 shape 차원: [1, 32, 160, 160]" 반복 발생 - seg 결과 전체
    // 유실). 박스 목록 텐서(3차원)를 이름이 아니라 shape로 명시적으로 찾는다.
    guard let outputMultiArray = prediction.featureNames.lazy
      .compactMap({ prediction.featureValue(for: $0)?.multiArrayValue })
      .first(where: { $0.shape.count == 3 }) else {
      print("[CoreMLBridge] 박스 목록 tensor(3차원) 탐색 실패: \(prediction.featureNames)")
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

  // YOLO 출력 파싱. 두 가지 포맷을 지원한다:
  // 1) end2end 후처리 포맷 [1, 300, 6 또는 38] - (중앙x, 중앙y, 너비, 높이, 신뢰도, 클래스ID)
  //    (segmentation 모델, object_detection의 구 버전)
  // 2) 밀집(dense) raw 포맷 [1, numAnchors, 4+nc] - (x1, y1, x2, y2, class0..classN 확률)
  //    2026-07-11 opus 2순위: CoreML 그래프에서 TopK/Gather(ANE 미지원)를 제거하기 위해
  //    object_detection 모델의 top-k 선택 헤드를 export 시점에 빼고 밀집 텐서로 내보냄
  //    (scripts/convert_yolo_to_coreml.py --raw-head). 이미 anchor 디코딩·sigmoid까지
  //    끝난 절대좌표(x1,y1,x2,y2)이므로, 여기서는 클래스별 최댓값 확인 + 임계값 필터링 +
  //    신뢰도 정렬만 하면 된다(one2one 헤드가 NMS-free로 학습돼 있어 별도 IoU-NMS 불필요 -
  //    ultralytics postprocess()도 동일하게 단순 top-k만 수행).
  private func parseYoloOutput(multiArray: MLMultiArray, modelType: String) -> [[String: Any]] {
    let shape = multiArray.shape.map { $0.intValue }
    guard shape.count == 3 else {
      print("[CoreMLBridge] 예상치 못한 출력 shape 차원: \(shape)")
      return []
    }

    let attrsPerBox = shape[2]
    let numBoxes = shape[1]
    let ptr = UnsafeMutablePointer<Float32>(multiArray.dataPointer.assumingMemoryBound(to: Float32.self))
    let strides = multiArray.strides.map { $0.intValue }

    let activeClassNames = (modelType == "segmentation") ? segClassNames : classNames
    let numClasses = activeClassNames.count

    var results: [[String: Any]] = []

    if attrsPerBox == 4 + numClasses {
      // 밀집 raw 포맷: (x1, y1, x2, y2, class0..classN 확률)
      for i in 0..<numBoxes {
        let baseOffset = i * strides[1]
        var bestClassId = -1
        var bestScore: Float32 = -1
        for c in 0..<numClasses {
          let score = ptr[baseOffset + (4 + c) * strides[2]]
          if score > bestScore {
            bestScore = score
            bestClassId = c
          }
        }
        let confidence = Double(bestScore)
        if confidence < confThreshold { continue }

        let x1 = Double(ptr[baseOffset + 0 * strides[2]])
        let y1 = Double(ptr[baseOffset + 1 * strides[2]])
        let x2 = Double(ptr[baseOffset + 2 * strides[2]])
        let y2 = Double(ptr[baseOffset + 3 * strides[2]])
        let className = activeClassNames[bestClassId] ?? "unknown"

        results.append([
          "model": modelType,
          "className": className,
          "confidence": confidence,
          "bbox": [
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1
          ]
        ])
      }
    } else if attrsPerBox == 6 || attrsPerBox == 38 {
      // end2end 후처리 포맷: (중앙x, 중앙y, 너비, 높이, 신뢰도, 클래스ID) [+ 마스크계수 32개]
      for i in 0..<numBoxes {
        let baseOffset = i * strides[1]
        let cx = Double(ptr[baseOffset + 0 * strides[2]])
        let cy = Double(ptr[baseOffset + 1 * strides[2]])
        let w = Double(ptr[baseOffset + 2 * strides[2]])
        let h = Double(ptr[baseOffset + 3 * strides[2]])
        let confidence = Double(ptr[baseOffset + 4 * strides[2]])
        let classId = Int(ptr[baseOffset + 5 * strides[2]].rounded())

        if confidence < confThreshold { continue }
        if classId < 0 || classId >= numClasses { continue }

        // 클라이언트(CameraView.tsx)는 bbox 전체(x,y,w,h)를 640x640 픽셀 단위로 취급하여
        // FRAME_SIZE(640)로 나눠 화면 비율(%)과 위험도 area ratio를 계산한다.
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
    } else {
      print("[CoreMLBridge] 예상치 못한 출력 attrsPerBox: \(attrsPerBox)")
      return []
    }

    // 신뢰도 기준 역순 정렬 (raw 포맷은 top-k 선택이 아직 안 됐으므로 여기서 사실상 수행됨)
    results.sort { (a, b) -> Bool in
      let confA = a["confidence"] as? Double ?? 0.0
      let confB = b["confidence"] as? Double ?? 0.0
      return confA > confB
    }

    // raw 포맷은 8400개 앵커 전부를 훑으므로 임계값 통과 건수가 많을 수 있어 상한을 둔다
    // (postprocess()의 max_det=300과 동일한 상한).
    if attrsPerBox == 4 + numClasses && results.count > 300 {
      results.removeLast(results.count - 300)
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
