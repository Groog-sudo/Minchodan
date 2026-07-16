// Siri/App Shortcuts 전화 연결 Intent (iOS 16+).
import AppIntents

@available(iOS 16.0, *)
struct MinchodanDialIntent: AppIntent {
  static var title: LocalizedStringResource = "전화 연결"
  static var description = IntentDescription("음성 명령으로 전화를 연결합니다.")
  static var openAppWhenRun: Bool = false

  @Parameter(title: "전화번호")
  var phoneNumber: String

  @Parameter(title: "연락처 이름")
  var contactName: String?

  static var parameterSummary: some ParameterSummary {
    Summary("\(\.$contactName) \(\.$phoneNumber) 연결") {
      \.$contactName
      \.$phoneNumber
    }
  }

  func perform() async throws -> some IntentResult & ProvidesDialog {
    let cleaned = phoneNumber.replacingOccurrences(
      of: "[^0-9+]",
      with: "",
      options: .regularExpression
    )
    guard !cleaned.isEmpty else {
      return .result(dialog: IntentDialog("전화번호를 확인할 수 없습니다."))
    }

    await MainActor.run {
      MinchodanSiriDialer.openShortcutsDial(phoneNumber: cleaned)
    }
    return .result(dialog: IntentDialog("전화를 연결합니다."))
  }
}
