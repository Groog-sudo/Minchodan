// AVAudioSession 모드 전환 브릿지 (2026-07-11, Mitos 로드맵 우선순위 4: AEC 검증).
// STT 녹음 구간에서 세션 모드를 .voiceChat으로 전환하면 iOS가 VoiceProcessingIO의
// AEC(에코 캔슬레이션)를 활성화해, 녹음 중 스피커로 나가는 반사 비프/신호음이
// 마이크 입력에서 상쇄된다(음향 블리드로 인한 STT 오염의 근본 대책 후보).
// 파일 위치 주의: 신규 네이티브 브릿지는 client/ios/ 루트에 두어야 빌드에 반영된다
// (CoreMLInferenceBridge.swift 상단 주석 참조 - Minchodan/ 서브폴더는 함정).

import AVFoundation
import Foundation
import React

@objc(AudioSessionBridge)
class AudioSessionBridge: NSObject {
  // 전환 직전 세션 설정을 보존해 STT 종료 시 원상 복구한다.
  // expo-audio가 초기화한 설정(mixWithOthers 등)을 그대로 되돌리기 위함이다.
  private static var savedCategory: AVAudioSession.Category?
  private static var savedMode: AVAudioSession.Mode?
  private static var savedOptions: AVAudioSession.CategoryOptions?

  @objc static func requiresMainQueueSetup() -> Bool {
    return false
  }

  private func sessionInfo(_ session: AVAudioSession) -> [String: Any] {
    return [
      "category": session.category.rawValue,
      "mode": session.mode.rawValue,
      // voiceChat 모드는 iOS가 VoiceProcessingIO(AEC 포함)를 붙이는 조건이므로
      // 이 값이 true면 AEC 활성으로 간주한다(실청취 검증은 실기기에서 수행).
      "voiceProcessingActive": session.mode == .voiceChat,
      "outputRoute": session.currentRoute.outputs.map { $0.portType.rawValue }.joined(separator: ","),
    ]
  }

  @objc func setVoiceProcessing(
    _ enabled: Bool,
    resolver resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    let session = AVAudioSession.sharedInstance()
    do {
      if enabled {
        if AudioSessionBridge.savedCategory == nil {
          AudioSessionBridge.savedCategory = session.category
          AudioSessionBridge.savedMode = session.mode
          AudioSessionBridge.savedOptions = session.categoryOptions
        }
        // .defaultToSpeaker 필수: voiceChat 기본 라우팅은 수화부(리시버)라서
        // 이 옵션이 없으면 반사 비프/안내 음성이 귀에 대야 들리는 수준으로 작아진다.
        // .allowBluetooth(HFP)는 골전도/오픈이어 헤드셋 마이크 사용을 허용한다.
        try session.setCategory(
          .playAndRecord,
          mode: .voiceChat,
          options: [.defaultToSpeaker, .allowBluetooth, .allowBluetoothA2DP]
        )
      } else {
        let category = AudioSessionBridge.savedCategory ?? .playAndRecord
        let savedMode = AudioSessionBridge.savedMode ?? .default
        // 저장된 모드가 voiceChat이면(비정상 종료 후 재저장 등) default로 강등해
        // 복구가 다시 AEC 모드로 돌아가는 순환을 방지한다.
        let mode: AVAudioSession.Mode = savedMode == .voiceChat ? .default : savedMode
        let options = AudioSessionBridge.savedOptions
          ?? [.defaultToSpeaker, .allowBluetoothA2DP, .mixWithOthers]
        try session.setCategory(category, mode: mode, options: options)
        AudioSessionBridge.savedCategory = nil
        AudioSessionBridge.savedMode = nil
        AudioSessionBridge.savedOptions = nil
      }
      try session.setActive(true)
      resolve(sessionInfo(session))
    } catch {
      reject("audio_session_error", "오디오 세션 전환 실패: \(error.localizedDescription)", error)
    }
  }

  // 검증용: 현재 세션 상태 조회. expo-audio recorder가 record() 시점에 세션을
  // 다시 만지는지(voiceChat이 덮이는지) 실기기 로그로 확인하기 위해 노출한다.
  @objc func getSessionInfo(
    _ resolve: @escaping RCTPromiseResolveBlock,
    rejecter reject: @escaping RCTPromiseRejectBlock
  ) {
    resolve(sessionInfo(AVAudioSession.sharedInstance()))
  }
}
