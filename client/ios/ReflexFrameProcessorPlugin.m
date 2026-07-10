// ReflexFrameProcessorPlugin.swift를 VisionCamera Frame Processor 런타임에 "reflexFrameCapture"
// 이름으로 등록한다. VISION_EXPORT_SWIFT_FRAME_PROCESSOR가 __attribute__((constructor))로
// 앱 기동 시 자동 등록 코드를 생성하므로, JS에서는
// VisionCameraProxy.initFrameProcessorPlugin("reflexFrameCapture")로 인스턴스를 얻는다.

#import <VisionCamera/FrameProcessorPlugin.h>
#import "Minchodan-Swift.h"

VISION_EXPORT_SWIFT_FRAME_PROCESSOR(ReflexFrameProcessorPlugin, reflexFrameCapture)
