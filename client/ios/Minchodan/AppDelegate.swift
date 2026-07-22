internal import Expo
import React
import ReactAppDependencyProvider

@main
class AppDelegate: ExpoAppDelegate {
  var window: UIWindow?

  var reactNativeDelegate: ExpoReactNativeFactoryDelegate?
  var reactNativeFactory: RCTReactNativeFactory?

  public override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    let delegate = ReactNativeDelegate()
    let factory = ExpoReactNativeFactory(delegate: delegate)
    delegate.dependencyProvider = RCTAppDependencyProvider()

    reactNativeDelegate = delegate
    reactNativeFactory = factory

#if DEBUG
    // expo-dev-launcher가 bridge.bundleURL을 직접 채우면 ReactNativeDelegate.bundleURL()이
    // 호출되지 않아 그 안의 설정이 반영되지 않는다. Metro는 평문 HTTP만 서빙하므로,
    // NSUserDefaults에 과거 세션에서 남은 packagerScheme=https(재설치 후에도 유지됨)로
    // 번들 요청이 TLS로 나가 실패하는 것을 막기 위해 앱 시작 시 무조건 http로 고정한다.
    RCTBundleURLProvider.sharedSettings().packagerScheme = "http"
    if let host = ProcessInfo.processInfo.environment["METRO_BUNDLER_HOST"], !host.isEmpty {
      RCTBundleURLProvider.sharedSettings().jsLocation = host
    }
#endif

#if os(iOS) || os(tvOS)
    window = UIWindow(frame: UIScreen.main.bounds)
    factory.startReactNative(
      withModuleName: "main",
      in: window,
      launchOptions: launchOptions)
#endif

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  // 앱 딥링킹(Deep Linking) API 제어
  public override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey: Any] = [:]
  ) -> Bool {
    return super.application(app, open: url, options: options) || RCTLinkingManager.application(app, open: url, options: options)
  }

  // 유니버설 링크(Universal Links) 제어
  public override func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
  ) -> Bool {
    let result = RCTLinkingManager.application(application, continue: userActivity, restorationHandler: restorationHandler)
    return super.application(application, continue: userActivity, restorationHandler: restorationHandler) || result
  }
}

class ReactNativeDelegate: ExpoReactNativeFactoryDelegate {
  // Expo의 설정 플러그인(config-plugins)을 위한 네이티브 확장 지점

  override func sourceURL(for bridge: RCTBridge) -> URL? {
    // expo-dev-client 빌드 시 정확한 개발 서버(Metro) JS 번들 URL을 반환하기 위해 필요
    bridge.bundleURL ?? bundleURL()
  }

  override func bundleURL() -> URL? {
#if DEBUG
    // 개인 개발 PC 주소는 소스에 폴백으로 저장하지 않는다. Tailscale Metro를 쓸 때만
    // 로컬 Xcode 환경의 METRO_BUNDLER_HOST에 MagicDNS 또는 개인 주소를 지정한다.
    if let host = ProcessInfo.processInfo.environment["METRO_BUNDLER_HOST"], !host.isEmpty {
      RCTBundleURLProvider.sharedSettings().jsLocation = host
    }
    // Metro는 평문 HTTP만 서빙한다. 이전 세션에서 NSUserDefaults에 남은 packagerScheme=https가
    // 재설치 후에도 유지되어 번들 요청이 TLS로 나가 실패하는 사례가 있어 매 실행마다 http로 고정한다.
    RCTBundleURLProvider.sharedSettings().packagerScheme = "http"
    return RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: ".expo/.virtual-metro-entry")
#else
    return Bundle.main.url(forResource: "main", withExtension: "jsbundle")
#endif
  }
}
