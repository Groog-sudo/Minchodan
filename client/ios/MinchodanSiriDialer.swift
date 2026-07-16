// Siri Shortcuts 전화 연결 위임.
import UIKit

enum MinchodanSiriDialer {
  private static let shortcutName = "MinchodanDial"

  static func openShortcutsDial(phoneNumber: String) {
    let cleaned = phoneNumber.replacingOccurrences(
      of: "[^0-9+]",
      with: "",
      options: .regularExpression
    )
    guard !cleaned.isEmpty else {
      return
    }
    guard let encoded = cleaned.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
          let url = URL(string: "shortcuts://run-shortcut?input=text&text=\(encoded)&name=\(shortcutName)")
    else {
      return
    }
    UIApplication.shared.open(url, options: [:], completionHandler: nil)
  }

  @available(iOS 16.0, *)
  static func performAppIntent(phoneNumber: String, contactName: String?) async throws {
    var intent = MinchodanDialIntent()
    intent.phoneNumber = phoneNumber
    intent.contactName = contactName
    _ = try await intent.perform()
  }
}
