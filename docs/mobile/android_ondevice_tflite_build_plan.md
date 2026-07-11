# Android 온디바이스 TFLite 추론 및 빌드 구성 계획

현재 Minchodan 프로젝트에서 `client/ios`를 참고하여 `client/android`가 정상적으로 동작하도록 네이티브 빌드 설정을 구성합니다. Android 환경에서는 `react-native-fast-tflite`를 사용하여 `.tflite` 형식의 온디바이스 모델(장애물 탐지 및 노면 분할)을 구동하게 되며, 이를 위해 빌드 시 에셋 압축 해제 패키징 설정이 필수적입니다.

## User Review Required

> [!IMPORTANT]
> **TFLite 모델 에셋 패키징 (aaptOptions) 설정 필요**
> `.tflite` 모델 파일이 Android APK로 빌드될 때 기본값으로 압축되면, `react-native-fast-tflite` 라이브러리의 C++ 엔진이 메모리 맵(`mmap`) 방식으로 파일을 로드할 수 없어 런타임 오류가 발생합니다.
> 이를 방지하기 위해 `client/android/app/build.gradle`에 `aaptOptions { noCompress "tflite" }` 설정을 적용하여 `.tflite` 파일이 무압축 상태로 APK에 빌드되도록 설정해야 합니다.

## Open Questions

- 현재 빌드 테스트가 백그라운드에서 실행 중입니다. NDK 또는 JDK 관련 빌드 에러가 포착될 경우, 추가적인 NDK 버전 고정이나 Gradle 변수 설정이 필요할 수 있으며, 이 경우 본 계획서를 업데이트하여 추가 검토를 요청하겠습니다.

## Proposed Changes

### client/android

---

#### [MODIFY] [build.gradle](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/client/android/app/build.gradle)

`client/android/app/build.gradle`의 `android` 블록 내부에 `aaptOptions` 블록을 추가하여 `.tflite` 에셋 압축을 방지합니다.

```diff
     androidResources {
         ignoreAssetsPattern '!.svn:!.git:!.ds_store:!*.scc:!CVS:!thumbs.db:!picasa.ini:!*~'
     }
+
+    aaptOptions {
+        noCompress "tflite"
+    }
 }
```

## Verification Plan

### Automated Tests
- `client/android` 폴더에서 `.\gradlew.bat assembleDebug`를 실행하여 Gradle 빌드가 최종 성공(SUCCESSFUL)하는지 검증합니다.

### Manual Verification
- 에뮬레이터나 실기기에 앱을 배포한 후 로그에 `[TFLiteDetector] 듀얼 TFLite 모델 로드 성공`이 출력되는지 확인하고, 카메라 권한 부여 이후 온디바이스 모델 추론 결과(BBox 등)가 올바르게 렌더링되는지 확인합니다.
