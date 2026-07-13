// LiDAR 실거리 프로브 브릿지 (2026-07-11 프로토타입, Mitos 로드맵 §2 "거리 추정 휴리스틱").
// 목적: bbox 면적/하단 y 기반 의사 거리를 대체할 실측 거리(LiDAR + AVCaptureDepthDataOutput)의
// 정확도·지연·유효 범위를 실기기에서 검증한다.
// 제약(프로토타입 단계): 이 모듈은 자체 AVCaptureSession으로 후면 LiDAR 심도 카메라를
// 점유하므로 vision-camera 세션과 동시에 돌 수 없다. JS 측(CameraView)이 거리 측정 모드
// 진입 시 카메라(isActive=false)를 내리고 startProbe()를 호출하는 배타 전환 방식으로 쓴다.
// 대신 같은 네이티브 세션에서 video+depth를 동기화해, JS에는 depth 값과 같은 좌표계의
// 1:1 프리뷰 이미지를 함께 내려보낸다. 이 프리뷰 위의 중앙/하단/발밑 점이 실제 샘플링
// 좌표와 일치해야 줄자 실측 비교가 가능하다.
// 상시 융합(탐지 bbox + depth 동시)은 vision-camera 세션에 depth 출력을 붙이는 후속 단계다.
// 파일 위치 주의: 신규 네이티브 브릿지는 client/ios/ 루트에 두어야 빌드에 반영된다.

import AVFoundation
import CoreImage
import Foundation
import React
import UIKit

@objc(DepthProbeBridge)
class DepthProbeBridge: NSObject, AVCaptureDataOutputSynchronizerDelegate {
  private let session = AVCaptureSession()
  private let videoOutput = AVCaptureVideoDataOutput()
  private let depthOutput = AVCaptureDepthDataOutput()
  private let queue = DispatchQueue(label: "minchodan.depthprobe")
  private let ciContext = CIContext()
  private var synchronizer: AVCaptureDataOutputSynchronizer?
  private var latestDepth: AVDepthData?
  private var latestVideoBuffer: CVPixelBuffer?
  private var latestSynchronizedAt: Double = 0
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
    // 계측 프리뷰와 심도 샘플링 전용이므로 VGA 프리셋으로 충분(전력/발열 최소화).
    session.sessionPreset = .vga640x480
    let input = try AVCaptureDeviceInput(device: device)
    videoOutput.videoSettings = [
      kCVPixelBufferPixelFormatTypeKey as String: Int(kCVPixelFormatType_32BGRA)
    ]
    videoOutput.alwaysDiscardsLateVideoFrames = true

    guard
      session.canAddInput(input),
      session.canAddOutput(videoOutput),
      session.canAddOutput(depthOutput)
    else {
      session.commitConfiguration()
      throw NSError(
        domain: "DepthProbe", code: 2,
        userInfo: [NSLocalizedDescriptionKey: "비디오/심도 입출력 구성 실패"]
      )
    }
    session.addInput(input)
    session.addOutput(videoOutput)
    session.addOutput(depthOutput)
    // 홀 필링 스무딩: 반사율 낮은 표면(유리/검정 차체)의 NaN 구멍을 주변값으로 보간.
    depthOutput.isFilteringEnabled = true
    if let conn = videoOutput.connection(with: .video) {
      if conn.isVideoOrientationSupported {
        conn.videoOrientation = .portrait
      }
      if conn.isVideoMirroringSupported {
        conn.isVideoMirrored = false
      }
    }
    if let conn = depthOutput.connection(with: .depthData), conn.isVideoOrientationSupported {
      // 세로 화면(portrait) 좌표계로 통일해 JS의 정규화 좌표를 그대로 쓸 수 있게 한다.
      conn.videoOrientation = .portrait
    }
    let sync = AVCaptureDataOutputSynchronizer(dataOutputs: [videoOutput, depthOutput])
    sync.setDelegate(self, queue: queue)
    synchronizer = sync
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
      self.latestVideoBuffer = nil
      self.latestSynchronizedAt = 0
      resolve(["running": false])
    }
  }

  func dataOutputSynchronizer(
    _ synchronizer: AVCaptureDataOutputSynchronizer,
    didOutput synchronizedDataCollection: AVCaptureSynchronizedDataCollection
  ) {
    guard
      let syncedDepth = synchronizedDataCollection.synchronizedData(for: depthOutput)
        as? AVCaptureSynchronizedDepthData,
      !syncedDepth.depthDataWasDropped
    else {
      return
    }
    latestDepth = syncedDepth.depthData

    if
      let syncedVideo = synchronizedDataCollection.synchronizedData(for: videoOutput)
        as? AVCaptureSynchronizedSampleBufferData,
      !syncedVideo.sampleBufferWasDropped,
      let pixelBuffer = CMSampleBufferGetImageBuffer(syncedVideo.sampleBuffer)
    {
      latestVideoBuffer = pixelBuffer
    }
    latestSynchronizedAt = Date().timeIntervalSince1970
  }

  private func squareCropPoint(nx: Double, ny: Double, width: Int, height: Int) -> (Int, Int) {
    let cropSize = Double(min(width, height))
    let originX = (Double(width) - cropSize) / 2.0
    let originY = (Double(height) - cropSize) / 2.0
    let x = originX + min(1.0, max(0.0, nx)) * (cropSize - 1.0)
    let y = originY + min(1.0, max(0.0, ny)) * (cropSize - 1.0)
    return (Int(x.rounded()), Int(y.rounded()))
  }

  private func makePreviewUri(from pixelBuffer: CVPixelBuffer) -> (uri: String, width: Int, height: Int)? {
    let source = CIImage(cvPixelBuffer: pixelBuffer)
    let extent = source.extent
    let cropSize = min(extent.width, extent.height)
    guard cropSize > 0 else { return nil }

    let cropRect = CGRect(
      x: extent.origin.x + (extent.width - cropSize) / 2.0,
      y: extent.origin.y + (extent.height - cropSize) / 2.0,
      width: cropSize,
      height: cropSize
    )
    let cropped = source.cropped(to: cropRect)
    let targetSize: CGFloat = 640
    let scale = targetSize / cropSize
    let resized = cropped
      .transformed(by: CGAffineTransform(scaleX: scale, y: scale))
      .transformed(
        by: CGAffineTransform(
          translationX: -cropped.extent.origin.x * scale,
          y: -cropped.extent.origin.y * scale
        )
      )

    guard
      let cgImage = ciContext.createCGImage(
        resized,
        from: CGRect(x: 0, y: 0, width: targetSize, height: targetSize)
      ),
      let jpegData = UIImage(cgImage: cgImage).jpegData(compressionQuality: 0.55)
    else {
      return nil
    }
    return ("data:image/jpeg;base64,\(jpegData.base64EncodedString())", Int(targetSize), Int(targetSize))
  }

  // 정규화 좌표(x, y in 0~1, portrait 기준) 목록의 실거리(m)를 최신 심도 맵에서 샘플링한다.
  // 각 점은 5x5 이웃 미디언으로 노이즈를 완화하고, 유효 샘플이 없으면 meters=null.
  // 좌표는 JS의 1:1 계측 프리뷰와 동일한 center square crop 기준으로 해석한다.
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
      let preview = self.latestVideoBuffer.flatMap { self.makePreviewUri(from: $0) }

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
        let (cx, cy) = self.squareCropPoint(nx: nx, ny: ny, width: width, height: height)
        var neighborhood: [Float] = []
        for dy in -2...2 {
          for dx in -2...2 {
            if let v = depthAt(cx + dx, cy + dy) {
              neighborhood.append(v)
            }
          }
        }
        neighborhood.sort()
        let meters: Any =
          neighborhood.isEmpty ? NSNull() : Double(neighborhood[neighborhood.count / 2])
        samples.append(["x": nx, "y": ny, "meters": meters, "sampleCount": neighborhood.count])
      }

      var payload: [String: Any] = [
        "ready": true,
        "width": width,
        "height": height,
        "accuracy": depthData.depthDataAccuracy == .absolute ? "absolute" : "relative",
        "filtered": depthData.isDepthDataFiltered,
        "synchronizedAt": self.latestSynchronizedAt,
        "samples": samples,
      ]
      if let preview {
        payload["previewUri"] = preview.uri
        payload["previewWidth"] = preview.width
        payload["previewHeight"] = preview.height
      }
      resolve(payload)
    }
  }

  // 640x640 모델 입력 좌표계 bbox 목록의 중앙 50% 영역에서 7x7 depth grid를 샘플링한다.
  // 현재 프로브 모드는 탐지와 배타 실행되므로 정식 경로가 아니지만, 추후 같은 세션에서
  // video+depth가 동기화되면 이 정책을 그대로 객체별 distanceMeters 계산에 재사용한다.
  @objc func probeBoxes(
    _ boxes: NSArray,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    queue.async {
      guard let raw = self.latestDepth else {
        resolve(["ready": false, "distances": []])
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
        resolve(["ready": false, "distances": []])
        return
      }
      let rowBytes = CVPixelBufferGetBytesPerRow(map)

      func depthAt(_ px: Int, _ py: Int) -> Float? {
        guard px >= 0, px < width, py >= 0, py < height else { return nil }
        let rowPtr = base.advanced(by: py * rowBytes).assumingMemoryBound(to: Float32.self)
        let value = rowPtr[px]
        return (value.isFinite && value > 0) ? value : nil
      }

      func percentile(_ values: [Float], ratio: Double) -> Double? {
        guard !values.isEmpty else { return nil }
        let sorted = values.sorted()
        let position = Double(sorted.count - 1) * ratio
        let lowerIndex = Int(floor(position))
        let upperIndex = Int(ceil(position))
        if lowerIndex == upperIndex {
          return Double(sorted[lowerIndex])
        }
        let lower = Double(sorted[lowerIndex])
        let upper = Double(sorted[upperIndex])
        return lower + (upper - lower) * (position - Double(lowerIndex))
      }

      let modelFrameSize = 640.0
      let gridCount = 7
      let minimumValidSamples = 8
      var distances: [[String: Any]] = []

      for (index, candidate) in boxes.enumerated() {
        guard let box = candidate as? NSDictionary else {
          distances.append(["index": index, "meters": NSNull(), "sampleCount": 0])
          continue
        }
        let x = (box["x"] as? Double) ?? 0.0
        let y = (box["y"] as? Double) ?? 0.0
        let w = max(0.0, (box["w"] as? Double) ?? 0.0)
        let h = max(0.0, (box["h"] as? Double) ?? 0.0)
        if w <= 1.0 || h <= 1.0 {
          distances.append(["index": index, "meters": NSNull(), "sampleCount": 0])
          continue
        }

        let sampleMinX = max(0.0, x + w * 0.25)
        let sampleMaxX = min(modelFrameSize - 1.0, x + w * 0.75)
        let sampleMinY = max(0.0, y + h * 0.25)
        let sampleMaxY = min(modelFrameSize - 1.0, y + h * 0.75)
        var validDepths: [Float] = []

        for gy in 0..<gridCount {
          let yRatio = gridCount == 1 ? 0.5 : Double(gy) / Double(gridCount - 1)
          let sampleY = sampleMinY + (sampleMaxY - sampleMinY) * yRatio
          for gx in 0..<gridCount {
            let xRatio = gridCount == 1 ? 0.5 : Double(gx) / Double(gridCount - 1)
            let sampleX = sampleMinX + (sampleMaxX - sampleMinX) * xRatio
            let (depthX, depthY) = self.squareCropPoint(
              nx: sampleX / modelFrameSize,
              ny: sampleY / modelFrameSize,
              width: width,
              height: height
            )
            if let value = depthAt(depthX, depthY) {
              validDepths.append(value)
            }
          }
        }

        let meters: Any
        if validDepths.count < minimumValidSamples {
          meters = NSNull()
        } else if let p25 = percentile(validDepths, ratio: 0.25) {
          meters = p25
        } else {
          meters = NSNull()
        }
        distances.append([
          "index": index,
          "meters": meters,
          "sampleCount": validDepths.count,
        ])
      }

      resolve([
        "ready": true,
        "width": width,
        "height": height,
        "accuracy": depthData.depthDataAccuracy == .absolute ? "absolute" : "relative",
        "filtered": depthData.isDepthDataFiltered,
        "distances": distances,
      ])
    }
  }
}
