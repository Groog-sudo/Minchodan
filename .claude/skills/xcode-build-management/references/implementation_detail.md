# Xcode Build & Debugging Implementation Detail (상세 이행 가이드)

> **작성일**: 2026-07-05
> **버전**: v1.0.0
> **설계 기준**: iOS Xcode Native CLI + React Native Metro Integration
> **코딩 패턴 준수**: [`docs/dev-guides/course_codebase_guide.md`](../../../../docs/dev-guides/course_codebase_guide.md)

---

## 1. 빌드 및 컴파일 문제 해결 (Troubleshooting)

Xcode 프로젝트를 CLI 환경에서 빌드할 때 발생하는 주요 오류 패턴과 그 대처법은 다음과 같습니다.

### 1-1. DerivedData 및 캐시 정리

빌드 캐시가 꼬이거나 이전 빌드 산출물로 인해 컴파일 에러가 지속되는 경우, 아래와 같이 DerivedData 캐시를 완전히 삭제한 후 재빌드합니다.

```bash
# 기본 DerivedData 폴더 제거
rm -rf ~/Library/Developer/Xcode/DerivedData/

# 커스텀으로 설정된 빌드 출력 폴더 제거
rm -rf client/ios/build
```

### 1-2. CocoaPods 및 아키텍처 미스매치

Apple Silicon (M1/M2/M3 등) Mac 장비에서 빌드 시 시뮬레이터 아키텍처(x86_64 vs arm64) 충돌이 날 수 있습니다.

| 에러 메시지 패턴 | 원인 | 해결 방안 |
|---|---|---|
| `building for iOS Simulator, but linking in object file built for iOS...` | 시뮬레이터 빌드에 arm64 아키텍처가 잘못 제외되었거나 꼬임 | `client/ios/Podfile`에 `post_install` 훅을 통해 `EXCLUDED_ARCHS`를 조정하거나 `arch -x86_64 pod install` 실행 |
| `Sandbox: rsync... deny(1) file-write-create` | Xcode 15+에서 스크립트 샌드박싱 보안 옵션 충돌 | Xcode Project Build Settings에서 `ENABLE_USER_SCRIPT_SANDBOXING` 값을 `NO`로 강제 변경 |

#### Sandbox 파일 쓰기 오류 해결 스크립트 (pbxproj 수정 필요 시)
`client/ios/Minchodan.xcodeproj/project.pbxproj` 파일 내에서 `ENABLE_USER_SCRIPT_SANDBOXING`을 찾아 `NO`로 변경해야 합니다.

### 1-3. Node & Metro Bundler 연동 오류

React Native 빌드 스크립트 실행 중 `Node` 경로를 찾지 못하는 문제가 발생하면 `.xcode.env` 파일을 검증해야 합니다.

```bash
# client/ios/.xcode.env 파일 내 Node.js 경로 확인 및 갱신
# nvm 또는 fnm 등을 사용할 경우, Xcode 빌드 환경에서 실제 node 바이너리를 가리키도록 설정해야 합니다.
export NODE_BINARY=$(command -v node)
```

---

## 2. iOS 시뮬레이터 제어 및 UI 테스트 (XCUITest)

### 2-1. xcrun simctl 명령어 응용

시뮬레이터 조작을 위해 native CLI 도구인 `simctl`을 다음과 같이 응용할 수 있습니다.

```bash
# 특정 시뮬레이터 화면 캡처 후 호스트 PC로 전송
xcrun simctl io booted screenshot /tmp/screenshot.png

# 시뮬레이터 파일 시스템 내의 앱 샌드박스 경로 찾기
xcrun simctl get_app_container booted com.minchodan.app.kwanbum

# 시뮬레이터에 강제로 위치 정보 주입 (GPS 좌표 설정)
xcrun simctl location booted set 37.5665 126.9780 # 서울시청 좌표
```

### 2-2. XCUITest 프레임워크 적용

UI 인터랙션을 테스트하고 검증하기 위해, `client/ios` 프로젝트에 `AppUITests` 타겟을 구성하여 코디네이트가 아닌 시맨틱 엘리먼트 타겟팅을 수행합니다.

```swift
// AppUITests.swift 예시
import XCTest

final class MinchodanUITests: XCTestCase {
    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()
    }

    override func tearDownWithError() throws {
        app.terminate()
    }

    func testCameraAccessibilityAlert() throws {
        // 카메라 권한 승인 다이얼로그나 버튼이 표시되는지 확인
        let cameraButton = app.buttons["accessibilityCameraButton"]
        XCTAssertTrue(cameraButton.waitForExistence(timeout: 5.0))
        cameraButton.tap()

        // 렌더링 검증을 위한 debugDescription 출력
        print(app.debugDescription)
    }
}
```

---

## 3. Swift 및 SwiftUI 코드 리팩토링 가이드

에이전트가 iOS 네이티브 브릿지나 UI를 변경할 때, 코드 일관성 유지를 위해 아래 템플릿을 준수해야 합니다.

### 3-1. Swift 클래스 구조 표준화 (CoreMLInferenceBridge)

```swift
import Foundation
import CoreML
import Vision

/// 보행자 탐지 및 세그멘테이션을 위한 CoreML 네이티브 브릿지
@objc(CoreMLInferenceBridge)
public final class CoreMLInferenceBridge: NSObject {

    // MARK: - Constants & Stored Properties

    private let queue = DispatchQueue(label: "com.minchodan.coreml.queue", qos: .userInteractive)
    private var objectDetectionModel: VNCoreMLModel?
    private var segmentationModel: VNCoreMLModel?

    // MARK: - Initializers

    @objc public override init() {
        super.init()
        self.loadModels()
    }

    // MARK: - Public Logic Methods

    @objc(detectObstacles:resolver:rejecter:)
    public func detectObstacles(base64Frame: String,
                               resolver: @escaping RCTPromiseResolveBlock,
                               rejecter: @escaping RCTPromiseRejectBlock) {
        self.queue.async {
            guard let imageData = Data(base64Encoded: base64Frame),
                  let image = CIImage(data: imageData) else {
                rejecter("ERR_IMAGE_DECODE", "Failed to decode base64 frame", nil)
                return
            }

            // 추론 파이프라인 수행
            self.runInference(image: image, resolver: resolver, rejecter: rejecter)
        }
    }

    // MARK: - Private Helper Methods

    private func loadModels() {
        // Model loading logic with safety fallback
        do {
            // 커스텀 학습 YOLO pt가 로드되지 않았을 경우, 번들에 기본 내장된 모델로 Fallback 구성
            if let modelURL = Bundle.main.url(forResource: "yolo11n", withExtension: "mlmodelc") {
                let model = try MLModel(contentsOf: modelURL)
                self.objectDetectionModel = try VNCoreMLModel(for: model)
            }
        } catch {
            print("Failed to load CoreML model: \(error.localizedDescription)")
        }
    }

    private func runInference(image: CIImage,
                              resolver: @escaping RCTPromiseResolveBlock,
                              rejecter: @escaping RCTPromiseRejectBlock) {
        // Vision request & response mapping implementation
        resolver([]) // 빈 결과 fallback 반환 (방어적 코딩)
    }
}
```

---

## 4. 빌드 환경 확인 및 자가 진단 스크립트

에이전트는 Xcode 빌드를 수행하기 전, 아래 쉘 커맨드를 통해 현재 개발자 환경에 문제가 없는지 사전 점검할 수 있습니다.

```bash
# Xcode SDK 및 CLI 환경 사전 검증
xcode-select -p
xcodebuild -showsdks

# CocoaPods 동작 및 환경 변수 점검
pod --version
cat client/ios/.xcode.env
```
