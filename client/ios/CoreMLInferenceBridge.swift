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

  // confidence 임계값 (패딩 박스 및 노이즈 필터링)
  private let confThreshold: Double = 0.25
  // COCO 80 클래스 라벨 (object_detection.pt 기준)
  private let classNames: [Int: String] = [
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
    20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
    25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
    30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite",
    34: "baseball bat", 35: "baseball glove", 36: "skateboard",
    37: "surfboard", 38: "tennis racket", 39: "bottle", 40: "wine glass",
    41: "cup", 42: "fork", 43: "knife", 44: "spoon", 45: "bowl",
    46: "banana", 47: "apple", 48: "sandwich", 49: "orange",
    50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza", 54: "donut",
    55: "cake", 56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
    60: "dining table", 61: "toilet", 62: "tv", 63: "laptop", 64: "mouse",
    65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
    69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
    74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear",
    78: "hair drier", 79: "toothbrush"
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
      // ANE(Apple Neural Engine) 하드웨어 가속 바인딩 (시뮬레이터는 CPU/GPU 폴백)
      config.computeUnits = .all

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

      print("[CoreMLBridge] object_detection 모델 로드 완료 (Neural Engine 활성화)")
      resolve([
        "det": true,
        "seg": self.segModel != nil
      ] as [String : Any])
    } catch {
      reject("LOAD_ERROR", "CoreML 모델 로드 실패: \(error.localizedDescription)", error)
    }
  }

  @objc
  func detectFrame(_ base64Image: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    guard let detModel = self.detModel else {
      reject("NOT_LOADED", "CoreML detection 모델이 로드되지 않았습니다.", nil)
      return
    }

    guard let imageData = Data(base64Encoded: base64Image),
          let image = UIImage(data: imageData),
          let cgImage = image.cgImage else {
      reject("INVALID_IMAGE", "전송된 base64 이미지 디코딩 실패", nil)
      return
    }

    // 메인 UI 스레드 블로킹 방지를 위한 백그라운드 실시간 처리
    DispatchQueue.global(qos: .userInteractive).async {
      do {
        let detResults = try self.runDetection(model: detModel, cgImage: cgImage, modelType: "object_detection")
        var segResults: [[String: Any]] = []

        // segmentation 모델이 로드된 경우에만 실행
        if let segModel = self.segModel {
          segResults = try self.runDetection(model: segModel, cgImage: cgImage, modelType: "segmentation")
        }

        DispatchQueue.main.async {
          resolve([
            "seg": segResults,
            "det": detResults
          ])
        }
      } catch {
        DispatchQueue.main.async {
          reject("EXEC_ERROR", "추론 실행 오류: \(error.localizedDescription)", error)
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
  // 각 행: (cx, cy, w, h, confidence, class_id, ...)
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
      // [1, i, col] 인덱스 계산 (strides[0]은 보통 300*attrsPerBox)
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

      // YOLO26n end2end 산출물은 픽셀 단위(0~640) 좌표 -> 0~1 정규화
      // 이후 cx,cy,w,h -> x,y,w,h (RN 좌표계, origin=좌상단)
      let imgSize = 640.0 // 입력 이미지 640x640 고정
      let nx = cx / imgSize
      let ny = cy / imgSize
      let nw = w / imgSize
      let nh = h / imgSize
      let x = nx - nw / 2.0
      let y = ny - nh / 2.0
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
