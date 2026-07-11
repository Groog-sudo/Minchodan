// DepthProbeBridge Swift 클래스의 React Native 모듈 등록 (RCT_EXTERN 패턴).
#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(DepthProbeBridge, NSObject)

RCT_EXTERN_METHOD(startProbe:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(stopProbe:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(probe:(NSArray *)points
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
