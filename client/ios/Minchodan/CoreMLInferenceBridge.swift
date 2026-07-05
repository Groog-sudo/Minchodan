import Foundation
import CoreML
import Vision
import UIKit
import React

@objc(CoreMLInferenceBridge)
class CoreMLInferenceBridge: NSObject {
  private var segModel: VNCoreMLModel?
  private var detModel: VNCoreMLModel?

  @objc
  func loadModels(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    do {
      // Xcode 빌드 시 컴파일되어 포함될 modelc 경로 확인
      guard let segURL = Bundle.main.url(forResource: "segmentation", withExtension: "modelc") else {
        reject("FILE_NOT_FOUND", "segmentation.modelc 에셋을 Bundle에서 찾을 수 없습니다.", nil)
        return
      }
      guard let detURL = Bundle.main.url(forResource: "object_detection", withExtension: "modelc") else {
        reject("FILE_NOT_FOUND", "object_detection.modelc 에셋을 Bundle에서 찾을 수 없습니다.", nil)
        return
      }

      let config = MLModelConfiguration()
      // ANE(Apple Neural Engine) 하드웨어 가속 강제 바인딩
      config.computeUnits = .all

      let compiledSeg = try MLModel(contentsOf: segURL, configuration: config)
      let compiledDet = try MLModel(contentsOf: detURL, configuration: config)

      self.segModel = try VNCoreMLModel(for: compiledSeg)
      self.detModel = try VNCoreMLModel(for: compiledDet)
      resolve(true)
    } catch {
      reject("LOAD_ERROR", "CoreML 모델 로드 실패: \(error.localizedDescription)", error)
    }
  }

  @objc
  func detectFrame(_ base64Image: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
    guard let segModel = self.segModel, let detModel = self.detModel else {
      reject("NOT_LOADED", "CoreML 모델이 로드되지 않았습니다.", nil)
      return
    }

    guard let imageData = Data(base64Encoded: base64Image),
          let image = UIImage(data: imageData),
          let cgImage = image.cgImage else {
      reject("INVALID_IMAGE", "전송된 base64 이미지 디코딩 실패", nil)
      return
    }

    var segResults: [[String: Any]] = []
    var detResults: [[String: Any]] = []
    let group = DispatchGroup()

    // 1. 노면 Segmentation 분석 리퀘스트
    let segRequest = VNCoreMLRequest(model: segModel) { request, error in
      if let results = request.results as? [VNRecognizedObjectObservation] {
        segResults = results.map { self.parseObservation($0, modelName: "segmentation") }
      }
      group.leave()
    }
    segRequest.imageCropAndScaleOption = .scaleFill

    // 2. 장애물 Object Detection 분석 리퀘스트
    let detRequest = VNCoreMLRequest(model: detModel) { request, error in
      if let results = request.results as? [VNRecognizedObjectObservation] {
        detResults = results.map { self.parseObservation($0, modelName: "object_detection") }
      }
      group.leave()
    }
    detRequest.imageCropAndScaleOption = .scaleFill

    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

    group.enter()
    group.enter()

    // 메인 UI 스레드 블로킹 방지를 위한 백그라운드 실시간 처리
    var totalLatency = 0.0
    DispatchQueue.global(qos: .userInteractive).async {
      do {
        let startTime = CFAbsoluteTimeGetCurrent()
        try handler.perform([segRequest, detRequest])
        totalLatency = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0
        print("[CoreMLBridge] 벤치마크 (Vision) - 총추론: \(String(format: "%.2f", totalLatency))ms")
      } catch {
        reject("EXEC_ERROR", "추론 실행 오류: \(error.localizedDescription)", error)
      }
    }

    group.notify(queue: .main) {
      resolve([
        "seg": segResults,
        "det": detResults,
        "benchmark": [
          "total_ms": totalLatency
        ]
      ])
    }
  }

  private func parseObservation(_ observation: VNRecognizedObjectObservation, modelName: String) -> [String: Any] {
    let label = observation.labels.first?.identifier ?? "unknown"
    let confidence = observation.labels.first?.confidence ?? 0.0
    let bounds = observation.boundingBox // 0.0 ~ 1.0 정규화된 경계 박스 좌표

    return [
      "model": modelName,
      "className": label,
      "confidence": Double(confidence),
      "bbox": [
        "x": Double(bounds.origin.x),
        "y": Double(1.0 - bounds.origin.y - bounds.size.height), // iOS 뷰 좌표계(origin=좌하단) -> React Native 좌표계(origin=좌상단) 일치화
        "w": Double(bounds.size.width),
        "h": Double(bounds.size.height)
      ]
    ]
  }
}
