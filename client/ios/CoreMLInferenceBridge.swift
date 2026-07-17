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

  // 2026-07-07 실기기(TH iPhone) 재검증 결과: raw tensor 파싱 아키텍처로 전환한
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
      // object_detection (필수) - 2026-07-14부터 coremltools NMS 파이프라인 산출물
      // ("confidence"/"coordinates" 2-출력, runDetection에서 분기 처리) 사용
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
        let detPrediction = try self.predictRaw(model: detModel, cgImage: cgImage)
        let detResults = self.runDetection(prediction: detPrediction, modelType: "object_detection")
        let detTime = CFAbsoluteTimeGetCurrent()
        let detLatency = (detTime - startTime) * 1000.0

        var segResults: [[String: Any]] = []
        var segLatency = 0.0
        // 2026-07-13 추가: 서버 server/detection/surface_departure.py와 동일 목적(사용자
        // 발밑 근사 기준점이 roadway/caution 마스크 안에 있는지)을 온디바이스에서도 계산한다.
        // 아직 반사(reflex) 경보/햅틱에는 연결하지 않는다 - 이중 경로 원칙상 새 반사 트리거는
        // 실기기 노이즈 검증(단일 기준점이 세그멘테이션 경계에서 얼마나 흔들리는지)을 먼저
        // 거쳐야 하며, 이 값은 우선 JS 측에 로그용으로만 전달한다.
        var isDepartingSidewalk = false

        // segmentation 모델이 로드된 경우에만 실행
        if let segModel = self.segModel {
          let segStartTime = CFAbsoluteTimeGetCurrent()
          let segPrediction = try self.predictRaw(model: segModel, cgImage: cgImage)
          segResults = self.runDetection(prediction: segPrediction, modelType: "segmentation")
          isDepartingSidewalk = self.computeSidewalkDeparture(prediction: segPrediction)
          segLatency = (CFAbsoluteTimeGetCurrent() - segStartTime) * 1000.0
        }

        // docs/design/indoor_fp_mitigation_design.md §4: isLikelyIndoor 판정 + top-5
        // identifier+confidence를 함께 반환한다(§4.4 게이트는 JS 측 CameraView.tsx에서 결합).
        let sceneStartTime = CFAbsoluteTimeGetCurrent()
        let sceneResult = self.classifyScene(cgImage: cgImage)
        let sceneLatency = (CFAbsoluteTimeGetCurrent() - sceneStartTime) * 1000.0

        let totalLatency = detLatency + segLatency + sceneLatency
        print("[CoreMLBridge] 벤치마크 - 탐지(det): \(String(format: "%.2f", detLatency))ms | 분할(seg): \(String(format: "%.2f", segLatency))ms | 씬분류(scene): \(String(format: "%.2f", sceneLatency))ms | 총추론: \(String(format: "%.2f", totalLatency))ms")
        if isDepartingSidewalk {
          print("[CoreMLBridge][SurfaceDeparture] 보도 이탈 판정(온디바이스, 단일 프레임)")
        }

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
            "scene": sceneResult as NSDictionary,
            "surfaceDeparture": isDepartingSidewalk
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
  // 입력 이미지 640x640 리사이즈 후 CoreML 추론을 1회 실행한다. det/seg 각 프레임당
  // 정확히 한 번만 호출해야 한다(segmentation은 박스 파싱과 이탈 판정이 이 결과를
  // 공유하므로, 중복 호출하면 추론 비용이 2배가 된다).
  private func predictRaw(model: MLModel, cgImage: CGImage) throws -> MLFeatureProvider {
    let inputFeature = try prepareInput(cgImage: cgImage, expectedSize: 640)
    return try model.prediction(from: inputFeature)
  }

  private func runDetection(prediction: MLFeatureProvider, modelType: String) -> [[String: Any]] {
    // 2026-07-14: object_detection260714.pt는 end2end(NMS-free one2one) 헤드가 아닌
    // 표준 헤드라, coremltools의 Vision 호환 NMS 파이프라인(nms=True)으로 변환한다.
    // 이 경로는 출력이 이름 있는 2개 배열("confidence"[N,80(29+패딩)], "coordinates"[N,4])
    // 로 나오며 NMS가 이미 CoreML 그래프 내부에서 끝난 상태다(Apple 표준 iOS Detection
    // Model 포맷, VNRecognizedObjectObservation과 동일 계약).
    if let confidence = prediction.featureValue(for: "confidence")?.multiArrayValue,
       let coordinates = prediction.featureValue(for: "coordinates")?.multiArrayValue {
      return parsePipelineOutput(confidence: confidence, coordinates: coordinates, modelType: modelType)
    }

    // segmentation 모델은 출력이 2개다: 박스 목록 텐서([1,300,38] 또는 [1,40,8400])와
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

  // coremltools NMS 파이프라인 출력 파싱. confidence: [numBoxes, nc(80 패딩)],
  // coordinates: [numBoxes, 4](cx,cy,w,h, 0~1 정규화). NMS가 이미 완료된 상태라
  // 여기서는 클래스별 최댓값 선택 + 픽셀 좌표 환산만 한다(IoU 억제 불필요).
  private func parsePipelineOutput(
    confidence: MLMultiArray,
    coordinates: MLMultiArray,
    modelType: String
  ) -> [[String: Any]] {
    let confShape = confidence.shape.map { $0.intValue }
    let coordShape = coordinates.shape.map { $0.intValue }
    guard confShape.count == 2, coordShape.count == 2, confShape[0] == coordShape[0] else {
      print("[CoreMLBridge] 파이프라인 출력 shape 불일치: conf=\(confShape) coord=\(coordShape)")
      return []
    }

    let numBoxes = confShape[0]
    let nc = confShape[1]
    let activeClassNames = (modelType == "segmentation") ? segClassNames : classNames
    let numClasses = activeClassNames.count

    let confPtr = UnsafeMutablePointer<Float32>(confidence.dataPointer.assumingMemoryBound(to: Float32.self))
    let confStrides = confidence.strides.map { $0.intValue }
    let coordPtr = UnsafeMutablePointer<Float32>(coordinates.dataPointer.assumingMemoryBound(to: Float32.self))
    let coordStrides = coordinates.strides.map { $0.intValue }

    var results: [[String: Any]] = []
    for i in 0..<numBoxes {
      let confBase = i * confStrides[0]
      var bestClassId = -1
      var bestScore: Float32 = -1
      // 29~79는 ultralytics의 80배수 패딩 클래스(항상 0)이므로 실제 클래스 범위만 본다.
      for c in 0..<min(nc, numClasses) {
        let score = confPtr[confBase + c * confStrides[1]]
        if score > bestScore {
          bestScore = score
          bestClassId = c
        }
      }
      let conf = Double(bestScore)
      if conf < confThreshold || bestClassId < 0 { continue }

      // coordinates는 0~1 정규화 값(IOSDetectModel의 self.normalize = 1/640)이므로,
      // 클라이언트가 기대하는 640 픽셀 단위로 되돌린다(prepareInput의 expectedSize와 동일 값).
      let coordBase = i * coordStrides[0]
      let cx = Double(coordPtr[coordBase + 0 * coordStrides[1]]) * 640.0
      let cy = Double(coordPtr[coordBase + 1 * coordStrides[1]]) * 640.0
      let w = Double(coordPtr[coordBase + 2 * coordStrides[1]]) * 640.0
      let h = Double(coordPtr[coordBase + 3 * coordStrides[1]]) * 640.0
      let className = activeClassNames[bestClassId] ?? "unknown"

      results.append([
        "model": modelType,
        "className": className,
        "confidence": conf,
        "bbox": [
          "x": cx - w / 2.0,
          "y": cy - h / 2.0,
          "w": w,
          "h": h
        ]
      ])
    }

    results.sort { (a, b) -> Bool in
      let confA = a["confidence"] as? Double ?? 0.0
      let confB = b["confidence"] as? Double ?? 0.0
      return confA > confB
    }
    return results
  }

  // =========================================================================
  // 👨‍💻 HARD CODE 영역 시작: 온디바이스 보도 이탈 판정 (프로토타입 마스크 내적) 👨‍💻
  // 💡 [면접 대비 주석]
  // 질문: 서버는 point-in-polygon인데 온디바이스는 왜 다른 방식인가요?
  // 답변: 서버(yolo_segmentor.py)는 ultralytics가 이미 폴리곤(mask.xy)으로 뽑아준 결과를
  // 받지만, CoreML end2end export는 폴리곤을 주지 않고 YOLOv8-seg 원형 그대로
  // "인스턴스별 마스크 계수 32개(박스 텐서의 6번 인덱스 이후) + 프로토타입 마스크
  // [1,32,160,160]"을 준다. 실제 마스크는 sigmoid(계수·프로토타입)로 복원되는데,
  // 우리에게 필요한 건 발밑 기준점 딱 한 픽셀의 안/밖 여부뿐이므로 160x160 래스터
  // 전체를 복원할 필요가 없다 - 기준점 좌표에서만 32차원 내적을 계산하면
  // 인스턴스당 연산 32회로 끝난다(폴리곤 추출·레이캐스팅보다 오히려 더 가볍다).
  // =========================================================================

  // 사용자 발밑 근사 기준점(서버 surface_departure.py REFERENCE_POINT_*_RATIO와 동일 관례).
  private let departureReferenceXRatio: Double = 0.5
  private let departureReferenceYRatio: Double = 0.9

  // segClassNames 기준 caution=1, roadway=2. server DEPARTURE_SURFACE_CLASSES와 동일 근거.
  private let departureSurfaceClassIds: Set<Int> = [1, 2]

  private func computeSidewalkDeparture(prediction: MLFeatureProvider) -> Bool {
    let arrays = prediction.featureNames.lazy
      .compactMap({ prediction.featureValue(for: $0)?.multiArrayValue })

    guard let boxArray = arrays.first(where: { $0.shape.count == 3 }),
          let protoArray = arrays.first(where: { $0.shape.count == 4 }) else {
      return false
    }

    let boxShape = boxArray.shape.map { $0.intValue }
    let protoShape = protoArray.shape.map { $0.intValue }
    // boxShape: [1, numBoxes, 38] (6 + 32 마스크계수). protoShape: [1, 32, protoH, protoW].
    guard boxShape.count == 3, boxShape[2] == 38,
          protoShape.count == 4, protoShape[1] == 32 else {
      return false
    }

    let numBoxes = boxShape[1]
    let protoHeight = protoShape[2]
    let protoWidth = protoShape[3]
    let refX = min(protoWidth - 1, max(0, Int(Double(protoWidth) * departureReferenceXRatio)))
    let refY = min(protoHeight - 1, max(0, Int(Double(protoHeight) * departureReferenceYRatio)))

    let boxPtr = UnsafeMutablePointer<Float32>(boxArray.dataPointer.assumingMemoryBound(to: Float32.self))
    let boxStrides = boxArray.strides.map { $0.intValue }
    let protoPtr = UnsafeMutablePointer<Float32>(protoArray.dataPointer.assumingMemoryBound(to: Float32.self))
    let protoStrides = protoArray.strides.map { $0.intValue }

    for i in 0..<numBoxes {
      let baseOffset = i * boxStrides[1]
      let confidence = Double(boxPtr[baseOffset + 4 * boxStrides[2]])
      if confidence < confThreshold { continue }
      let classId = Int(boxPtr[baseOffset + 5 * boxStrides[2]].rounded())
      guard departureSurfaceClassIds.contains(classId) else { continue }

      // mask = sigmoid(coeff · prototype[:, refY, refX]) - 기준점 한 픽셀만 복원.
      var dot: Float32 = 0.0
      for c in 0..<32 {
        let coeff = boxPtr[baseOffset + (6 + c) * boxStrides[2]]
        let protoOffset = c * protoStrides[1] + refY * protoStrides[2] + refX * protoStrides[3]
        dot += coeff * protoPtr[protoOffset]
      }
      let maskValue = 1.0 / (1.0 + exp(-Double(dot)))
      if maskValue > 0.5 {
        return true
      }
    }
    return false
  }

  // =========================================================================
  // 👨‍💻 HARD CODE 영역 끝
  // =========================================================================

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

    let ptr = UnsafeMutablePointer<Float32>(multiArray.dataPointer.assumingMemoryBound(to: Float32.self))
    let strides = multiArray.strides.map { $0.intValue }

    let activeClassNames = (modelType == "segmentation") ? segClassNames : classNames
    let numClasses = activeClassNames.count
    let maskCoeffs = 32
    let denseSegAttrs = 4 + numClasses + maskCoeffs // seg raw: xywh + classes + mask

    // ultralytics CoreML segment 기본 export는 [1, C, N](channels-first)이다.
    // 예: [1, 40, 8400] = (4 xywh + 4 class + 32 mask) × 8400 anchors.
    // 기존 end2end/[boxes, attrs] 포맷([1, 300, 38])과 구분해 해석한다.
    let channelsFirst =
      shape[1] <= denseSegAttrs && shape[2] > shape[1]

    var attrsPerBox = channelsFirst ? shape[1] : shape[2]
    var numBoxes = channelsFirst ? shape[2] : shape[1]

    var results: [[String: Any]] = []

    if channelsFirst && (attrsPerBox == 4 + numClasses || attrsPerBox == denseSegAttrs) {
      // channels-first 밀집: value(c, i) at [0, c, i], box=정규화 xywh(0~1)
      for i in 0..<numBoxes {
        var bestClassId = -1
        var bestScore: Float32 = -1
        for c in 0..<numClasses {
          let score = ptr[0 * strides[0] + (4 + c) * strides[1] + i * strides[2]]
          if score > bestScore {
            bestScore = score
            bestClassId = c
          }
        }
        let confidence = Double(bestScore)
        if confidence < confThreshold || bestClassId < 0 { continue }

        let cx = Double(ptr[0 * strides[0] + 0 * strides[1] + i * strides[2]]) * 640.0
        let cy = Double(ptr[0 * strides[0] + 1 * strides[1] + i * strides[2]]) * 640.0
        let w = Double(ptr[0 * strides[0] + 2 * strides[1] + i * strides[2]]) * 640.0
        let h = Double(ptr[0 * strides[0] + 3 * strides[1] + i * strides[2]]) * 640.0
        if w <= 1 || h <= 1 { continue }
        let className = activeClassNames[bestClassId] ?? "unknown"

        results.append([
          "model": modelType,
          "className": className,
          "confidence": confidence,
          "bbox": [
            "x": cx - w / 2.0,
            "y": cy - h / 2.0,
            "w": w,
            "h": h
          ]
        ])
      }
    } else if attrsPerBox == 4 + numClasses {
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
      print("[CoreMLBridge] 예상치 못한 출력 shape=\(shape) attrsPerBox=\(attrsPerBox) numBoxes=\(numBoxes)")
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
