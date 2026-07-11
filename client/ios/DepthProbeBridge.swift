// LiDAR 실거리 프로브 브릿지 (2026-07-11 프로토타입, Mitos 로드맵 §2 "거리 추정 휴리스틱").
// 목적: bbox 면적/하단 y 기반 의사 거리를 대체할 실측 거리(LiDAR + AVCaptureDepthDataOutput)의
// 정확도·지연·유효 범위를 실기기에서 검증한다.
// 제약(프로토타입 단계): 이 모듈은 자체 AVCaptureSession으로 후면 LiDAR 심도 카메라를
// 점유하므로 vision-camera 세션과 동시에 돌 수 없다. JS 측(CameraView)이 거리 측정 모드
// 진입 시 카메라(isActive=false)를 내리고 startProbe()를 호출하는 배타 전환 방식으로 쓴다.
// 상시 융합(탐지 bbox + depth 동시)은 vision-camera 세션에 depth 출력을 붙이는 후속 단계다.
// 파일 위치 주의: 신규 네이티브 브릿지는 client/ios/ 루트에 두어야 빌드에 반영된다.

import AVFoundation
import Foundation
import React

@objc(DepthProbeBridge)
class DepthProbeBridge: NSObject, AVCaptureDepthDataOutputDelegate {
  private let session = AVCaptureSession()
  private let depthOutput = AVCaptureDepthDataOutput()
  private let queue = DispatchQueue(label: "minchodan.depthprobe")
  private var latestDepth: AVDepthData?
  private var configured = false

  @objc static func requiresMainQueueSetup() -> Bool {
    return false
  }

  private func configureIfNeeded() throws {
    if configured { return }
    guard
      let device = AVCaptureDevice.default(.builtInLiDARDepthCamera, for: .video, position: .back)
    else {
      throw NSError(
        domain: "DepthProbe", code: 1,
        userInfo: [NSLocalizedDescriptionKey: "LiDAR 심도 카메라 없음(iPhone 12 Pro 이상 Pro 계열 전용)"]
      )
    }

    session.beginConfiguration()
    // 심도 샘플링 전용이므로 저해상 비디오 프리셋으로 충분(전력/발열 최소화).
    session.sessionPreset = .vga640x480
    let input = try AVCaptureDeviceInput(device: device)
    guard session.canAddInput(input), session.canAddOutput(depthOutput) else {
      session.commitConfiguration()
      throw NSError(
        domain: "DepthProbe", code: 2,
        userInfo: [NSLocalizedDescriptionKey: "심도 입출력 구성 실패"]
      )
    }
    session.addInput(input)
    session.addOutput(depthOutput)
    // 홀 필링 스무딩: 반사율 낮은 표면(유리/검정 차체)의 NaN 구멍을 주변값으로 보간.
    depthOutput.isFilteringEnabled = true
    depthOutput.setDelegate(self, callbackQueue: queue)
    if let conn = depthOutput.connection(with: .depthData), conn.isVideoOrientationSupported {
      // 세로 화면(portrait) 좌표계로 통일해 JS의 정규화 좌표를 그대로 쓸 수 있게 한다.
      conn.videoOrientation = .portrait
    }
    session.commitConfiguration()
    configured = true
  }

  @objc func startProbe(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    queue.async {
      do {
        try self.configureIfNeeded()
        if !self.session.isRunning {
          self.session.startRunning()
        }
        resolve(["running": self.session.isRunning])
      } catch {
        reject("depth_probe_start_error", error.localizedDescription, error)
      }
    }
  }

  @objc func stopProbe(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    queue.async {
      if self.session.isRunning {
        self.session.stopRunning()
      }
      self.latestDepth = nil
      resolve(["running": false])
    }
  }

  func depthDataOutput(
    _ output: AVCaptureDepthDataOutput,
    didOutput depthData: AVDepthData,
    timestamp: CMTime,
    connection: AVCaptureConnection
  ) {
    latestDepth = depthData
  }

  // 정규화 좌표(x, y in 0~1, portrait 기준) 목록의 실거리(m)를 최신 심도 맵에서 샘플링한다.
  // 각 점은 3x3 이웃 미디언으로 노이즈를 완화하고, 유효 샘플이 없으면 meters=null.
  @objc func probe(
    _ points: NSArray,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    queue.async {
      guard let raw = self.latestDepth else {
        resolve(["ready": false, "samples": []])
        return
      }
      let depthData =
        raw.depthDataType == kCVPixelFormatType_DepthFloat32
        ? raw : raw.converting(toDepthDataType: kCVPixelFormatType_DepthFloat32)
      let map = depthData.depthDataMap
      CVPixelBufferLockBaseAddress(map, .readOnly)
      defer { CVPixelBufferUnlockBaseAddress(map, .readOnly) }

      let width = CVPixelBufferGetWidth(map)
      let height = CVPixelBufferGetHeight(map)
      guard width > 0, height > 0, let base = CVPixelBufferGetBaseAddress(map) else {
        resolve(["ready": false, "samples": []])
        return
      }
      let rowBytes = CVPixelBufferGetBytesPerRow(map)

      func depthAt(_ px: Int, _ py: Int) -> Float? {
        guard px >= 0, px < width, py >= 0, py < height else { return nil }
        let rowPtr = base.advanced(by: py * rowBytes).assumingMemoryBound(to: Float32.self)
        let value = rowPtr[px]
        return (value.isFinite && value > 0) ? value : nil
      }

      var samples: [[String: Any]] = []
      for case let point as NSDictionary in points {
        let nx = (point["x"] as? Double) ?? 0.5
        let ny = (point["y"] as? Double) ?? 0.5
        let cx = Int((nx * Double(width - 1)).rounded())
        let cy = Int((ny * Double(height - 1)).rounded())
        var neighborhood: [Float] = []
        for dy in -1...1 {
          for dx in -1...1 {
            if let v = depthAt(cx + dx, cy + dy) {
              neighborhood.append(v)
            }
          }
        }
        neighborhood.sort()
        let meters: Any =
          neighborhood.isEmpty ? NSNull() : Double(neighborhood[neighborhood.count / 2])
        samples.append(["x": nx, "y": ny, "meters": meters])
      }

      resolve([
        "ready": true,
        "width": width,
        "height": height,
        "accuracy": depthData.depthDataAccuracy == .absolute ? "absolute" : "relative",
        "filtered": depthData.isDepthDataFiltered,
        "samples": samples,
      ])
    }
  }
}
