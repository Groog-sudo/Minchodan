// STT dial_action iOS Siri/Shortcuts 전화 연결 브릿지 (2026-07-16).
// tel: 전화 앱 열기 대신 App Intent + Shortcuts( MinchodanDial ) 경로를 사용한다.
// Android는 PhoneDialBridgeModule ACTION_CALL.

import Foundation
import React
import UIKit

@objc(PhoneDialBridge)
class PhoneDialBridge: NSObject {
  @objc static func requiresMainQueueSetup() -> Bool {
    return true
  }

  @objc func placeCall(
    _ phoneNumber: String,
    contactName: NSString?,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    let cleaned = phoneNumber.replacingOccurrences(
      of: "[^0-9+]",
      with: "",
      options: .regularExpression
    )
    guard !cleaned.isEmpty else {
      reject("invalid_number", "전화번호가 비어 있습니다", nil)
      return
    }

    let label = (contactName as String?)?.trimmingCharacters(in: .whitespacesAndNewlines)

    if #available(iOS 16.0, *) {
      Task { @MainActor in
        do {
          try await MinchodanSiriDialer.performAppIntent(
            phoneNumber: cleaned,
            contactName: label
          )
          resolve([
            "mode": "siri_app_intent",
            "phoneNumber": cleaned,
          ])
        } catch {
          MinchodanSiriDialer.openShortcutsDial(phoneNumber: cleaned)
          resolve([
            "mode": "siri_shortcuts",
            "phoneNumber": cleaned,
          ])
        }
      }
      return
    }

    MinchodanSiriDialer.openShortcutsDial(phoneNumber: cleaned)
    resolve([
      "mode": "siri_shortcuts",
      "phoneNumber": cleaned,
    ])
  }
}
