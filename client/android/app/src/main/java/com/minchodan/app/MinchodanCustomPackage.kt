package com.minchodan.app

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager
import java.util.ArrayList

class MinchodanCustomPackage : ReactPackage {

    override fun createNativeModules(reactContext: ReactApplicationContext): List<NativeModule> {
        val modules = ArrayList<NativeModule>()
        modules.add(AudioSessionBridgeModule(reactContext))
        modules.add(SceneClassifyBridgeModule(reactContext))
        modules.add(PhoneDialBridgeModule(reactContext))
        // iOS CoreMLInferenceBridge 대응 온디바이스 추론 브릿지 (2026-07-28).
        modules.add(TFLiteInferenceBridgeModule(reactContext))
        // ADPF 발열 헤드룸 - 동적 FPS 컨트롤러 입력 (2026-07-29, 핸드오프 §5.8).
        modules.add(ThermalBridgeModule(reactContext))
        return modules
    }

    override fun createViewManagers(reactContext: ReactApplicationContext): List<ViewManager<*, *>> {
        return emptyList()
    }
}
