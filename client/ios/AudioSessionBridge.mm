// AudioSessionBridge Swift 클래스의 React Native 모듈 등록 (RCT_EXTERN 패턴).
#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(AudioSessionBridge, NSObject)

RCT_EXTERN_METHOD(setVoiceProcessing:(BOOL)enabled
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(getSessionInfo:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
