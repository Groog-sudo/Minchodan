#import <React/RCTBridgeModule.h>

@interface RCT_EXTERN_MODULE(CoreMLInferenceBridge, NSObject)

RCT_EXTERN_METHOD(loadModels:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

RCT_EXTERN_METHOD(detectFrame:(NSString *)base64Image
                  resolver:(RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)

@end
