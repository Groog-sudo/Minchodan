// PhoneDialBridge Swift 클래스의 React Native 모듈 등록 (RCT_EXTERN 패턴).
#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(PhoneDialBridge, NSObject)

RCT_EXTERN_METHOD(placeCall:(NSString *)phoneNumber
                  contactName:(NSString *)contactName
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
