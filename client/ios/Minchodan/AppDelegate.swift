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
    // 2026-07-13: 실기기가 Wi-Fi를 벗어나면(Tailscale 경유 LTE/핫스팟) RCTBundleURLProvider의
    // Bonjour 자동탐색이 실패해 jsLocation이 nil로 남고 "No script URL provided"가 발생했다.
    // jsLocation을 명시적으로 지정해 자동탐색을 우회한다. METRO_BUNDLER_HOST 환경변수로
    // 재빌드 없이 덮어쓸 수 있다(기본값은 이 Mac의 Tailscale IP).
    let host = ProcessInfo.processInfo.environment["METRO_BUNDLER_HOST"] ?? "100.92.150.34:8081"
    RCTBundleURLProvider.sharedSettings().jsLocation = host
    return RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: ".expo/.virtual-metro-entry")
#else
    return Bundle.main.url(forResource: "main", withExtension: "jsbundle")
#endif
  }
}
