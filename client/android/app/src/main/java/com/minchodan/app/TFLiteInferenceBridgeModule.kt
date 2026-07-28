package com.minchodan.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Handler
import android.os.HandlerThread
import android.util.Base64
import android.util.Log
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.DataType
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import org.tensorflow.lite.nnapi.NnApiDelegate
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * iOS CoreMLInferenceBridge.swift의 Android 대응 온디바이스 추론 브릿지.
 *
 * 배경(2026-07-28): Android는 이 모듈이 없어 JS의 TFLiteDetector(react-native-fast-tflite)를
 * 썼고, 그 입력 계약이 float32라서 프레임마다 JS에서 JPEG 디코드 + 640x640x3 Float32Array
 * (약 4.7MiB) 생성을 수행했다. Xiaomi 12 실측에서 이 한 번이 JS 스레드를 약 900ms 점유해
 * 캡처·WS 송신·콘솔 Live Feed가 전부 약 1.05fps로 묶였다(목표 8fps=125ms).
 * iOS는 CoreML 브릿지가 base64를 직접 소비해 requiresFloat32=false로 이 비용이 0이다.
 * 본 모듈은 그 구조를 Android 런타임(TFLite Interpreter)으로 옮겨 동일 선상에 맞춘다.
 *
 * 계약은 JS TFLiteDetector(tfliteDetector.ts)와 동일하게 유지한다.
 *   - 입력: 640x640x3 HWC float32, 0~1 정규화 (Ultralytics 표준)
 *   - det dense head [1, 4+29, 8400] / seg dense head [1, 4+4(+32), 8400] channels-first
 *   - 임계값 det 0.50 / seg 0.35, NMS IoU 0.45 (클래스별)
 *   - legacy nms=True export [1,300,6] 폴백 유지
 */
class TFLiteInferenceBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private var detInterpreter: Interpreter? = null
    private var segInterpreter: Interpreter? = null
    // 💡 [면접 대비 주석] 델리게이트는 인터프리터마다 별도 인스턴스를 쓴다 (2026-07-28).
    // TFLite는 하나의 delegate 인스턴스를 여러 Interpreter에 공유하는 것을 지원하지 않는다.
    // 초기 구현이 det/seg에 같은 GpuDelegate를 넘겨 seg 쪽이 조용히 CPU로 떨어지거나
    // 정의되지 않은 동작을 할 여지가 있었다. 사용한 델리게이트는 close() 대상으로 모두 보관한다.
    private val gpuDelegates = mutableListOf<GpuDelegate>()
    private val nnApiDelegates = mutableListOf<NnApiDelegate>()
    private var gpuActive = false
    private var engineLabel = "CPU(XNNPACK)"

    @Volatile
    private var isLoaded = false

    // seg 주기 분리용(위 runBothAndResolve 주석 참조). 추론은 inferenceHandler 단일
    // 스레드에서만 실행되므로 동기화 없이 안전하다.
    private var inferenceTick = 0L
    private var lastSegResult: List<Detection> = emptyList()

    // 💡 [면접 대비 주석] 추론 전용 백그라운드 스레드.
    // iOS CoreMLInferenceBridge.swift의 DispatchQueue.global(qos: .userInteractive).async {} 에 대응한다.
    //
    // RN Android는 @ReactMethod가 단일 "Native Modules Queue Thread"에서 실행된다(공식 문서).
    // 추론(det+seg 약 100ms)을 그 스레드에서 동기 실행하면, 같은 시점에 들어오는 다른
    // @ReactMethod 호출(SceneClassifyBridgeModule.classifyScene 등)이 전부 직렬화되어 밀린다.
    // localDetectorSelect.android.ts의 Promise.all([runNativeDetect, classifyScene])는
    // JS상에서는 병렬처럼 보이지만 두 호출이 같은 단일 스레드를 공유하므로 실제로는 직렬 실행된다.
    //
    // 추론을 이 전용 스레드로 옮기면 네이티브 모듈 스레드가 즉시 해방되어 씬 분류의 동기 부분
    // (base64 디코드 + bitmap 생성)과 TFLite 추론이 진정 병렬로 실행된다.
    // HandlerThread는 단일 루퍼를 쓰므로 scratchFloats/inputBuffer 인스턴스 재사용이 안전하다
    // (추론 작업은 항상 이 스레드에서 순차 실행됨).
    private val inferenceThread = HandlerThread("TFLiteInference").apply { start() }
    private val inferenceHandler = Handler(inferenceThread.looper)

    // 입력 전처리 재사용 버퍼. 추론은 inferenceHandler(단일 스레드)에서만 실행되므로
    // 인스턴스 단위 재사용이 안전하다(프레임마다 4.7MiB 재할당 제거).
    private val scratchFloats = FloatArray(INPUT_SIZE * INPUT_SIZE * 3)
    private val inputBuffer: ByteBuffer = ByteBuffer
        .allocateDirect(INPUT_SIZE * INPUT_SIZE * 3 * 4)
        .order(ByteOrder.nativeOrder())

    // 💡 [면접 대비 주석] 출력 버퍼도 입력과 동일하게 재사용한다 (2026-07-28).
    // 입력 버퍼는 재사용 처리가 되어 있었지만 출력은 매 프레임 새로 할당하고 있었다.
    // det 출력 [1,33,8400] = 277,200 float = 1.11MB, seg 출력 [1,40,8400] = 1.34MB로,
    // seg가 도는 프레임마다 2.45MB를 allocateDirect(native malloc)로 새로 잡고 같은 크기의
    // FloatArray까지 새로 만들어 GC 압력을 유발했다. det/seg는 출력 크기가 다르므로
    // 모델별로 분리 보관한다. 추론은 inferenceHandler 단일 스레드 전용이라 동기화 불필요.
    private val detOutScratch = OutputScratch()
    private val segOutScratch = OutputScratch()

    // 💡 [면접 대비 주석] INT8 full-integer 양자화 모델 지원 (2026-07-28).
    // FP16 export는 내부만 반정밀도로 두고 입출력은 float32를 유지하지만, HTP(NPU)를
    // 노린 full_integer_quant는 입출력 텐서 자체가 int8이다. float32 버퍼를 그대로
    // 넘기면 형 불일치로 실패하므로, 모델별 양자화 파라미터를 읽어 입력은 양자화하고
    // 출력은 역양자화한다. 이 정보는 모델마다 다르므로(det만 INT8, seg는 FP16 같은
    // 혼용이 가능하다) 인터프리터별로 보관한다.
    private var detQuant = QuantSpec.FLOAT
    private var segQuant = QuantSpec.FLOAT

    // int8 입력용 버퍼. float32 대비 1/4 크기(640*640*3 바이트)다.
    private val int8InputBuffer: ByteBuffer = ByteBuffer
        .allocateDirect(INPUT_SIZE * INPUT_SIZE * 3)
        .order(ByteOrder.nativeOrder())

    /** 모델 입출력 텐서의 양자화 규격. */
    private class QuantSpec(
        val inputIsInt8: Boolean,
        val inputScale: Float,
        val inputZeroPoint: Int,
        val outputIsInt8: Boolean,
        val outputScale: Float,
        val outputZeroPoint: Int
    ) {
        /**
         * 0~255 픽셀값을 곧바로 int8 양자화값으로 바꾸는 계수.
         * 원식은 q = round((p/255) / scale) + zp 이므로 계수는 1 / (255 * scale)이다.
         * ultralytics full_integer_quant는 scale이 정확히 1/255, zp가 -128로 나와
         * 실제로는 q = p - 128 한 번의 뺄셈으로 끝난다.
         */
        val inputMultiplier: Float =
            if (inputIsInt8 && inputScale > 0f) 1f / (255f * inputScale) else 0f

        companion object {
            val FLOAT = QuantSpec(false, 0f, 0, false, 0f, 0)
        }
    }

    // decodeDense의 앵커별 최대 점수 누산용. det/seg 모두 NUM_ANCHORS 고정이라 공유한다.
    private val bestScorePerAnchor = FloatArray(NUM_ANCHORS)
    private val bestClassPerAnchor = IntArray(NUM_ANCHORS)

    /** 모델 출력 텐서 크기에 맞춰 direct 버퍼와 FloatArray를 1회만 할당해 재사용한다. */
    private class OutputScratch {
        private var buffer: ByteBuffer? = null
        private var floats: FloatArray? = null
        private var rawBytes: ByteArray? = null

        // TFLite는 출력 ByteBuffer 크기가 텐서 바이트 수와 정확히 일치할 것을 요구하므로
        // "충분히 큼"이 아니라 정확 일치일 때만 재사용한다. int8 출력은 요소당 1바이트다.
        fun buffer(length: Int, bytesPerElement: Int): ByteBuffer {
            val bytes = length * bytesPerElement
            val cur = buffer
            if (cur != null && cur.capacity() == bytes) {
                cur.clear()
                return cur
            }
            val next = ByteBuffer.allocateDirect(bytes).order(ByteOrder.nativeOrder())
            buffer = next
            return next
        }

        fun floats(length: Int): FloatArray {
            val cur = floats
            if (cur != null && cur.size == length) return cur
            val next = FloatArray(length)
            floats = next
            return next
        }

        /** int8 출력을 벌크로 받아둘 바이트 배열(역양자화 전 단계). */
        fun bytes(length: Int): ByteArray {
            val cur = rawBytes
            if (cur != null && cur.size == length) return cur
            val next = ByteArray(length)
            rawBytes = next
            return next
        }
    }

    override fun getName(): String = "TFLiteInferenceBridge"

    // ---------------------------------------------------------------- load

    @ReactMethod
    fun loadModels(promise: Promise) {
        try {
            if (isLoaded) {
                promise.resolve(statusMap(detInterpreter != null, segInterpreter != null))
                return
            }

            // GPU delegate는 기기별로 지원 여부가 갈린다. 미지원이면 조용히 CPU(XNNPACK)로 간다.
            // CompatibilityList 자체가 예외를 던지는 단말이 있어 통째로 감싼다.
            val useGpu = try {
                CompatibilityList().isDelegateSupportedOnThisDevice
            } catch (e: Throwable) {
                Log.w(TAG, "GPU delegate 지원 조회 실패, CPU로 진행: ${e.message}")
                false
            }

            detInterpreter = createInterpreter(DET_ASSET, useGpu)
            segInterpreter = createInterpreter(SEG_ASSET, useGpu)
            detQuant = readQuantSpec(detInterpreter, "object_detection")
            segQuant = readQuantSpec(segInterpreter, "segmentation")
            isLoaded = detInterpreter != null || segInterpreter != null

            if (!isLoaded) {
                promise.reject("LOAD_ERROR", "det/seg 인터프리터를 모두 생성하지 못했습니다.", null)
                return
            }

            Log.i(
                TAG,
                "모델 로드 완료 det=${detInterpreter != null} seg=${segInterpreter != null} " +
                    "gpu=$useGpu engine=$engineLabel"
            )
            promise.resolve(statusMap(detInterpreter != null, segInterpreter != null))
        } catch (e: Throwable) {
            Log.e(TAG, "loadModels 실패: ${e.message}", e)
            promise.reject("LOAD_ERROR", "TFLite 모델 로드 실패: ${e.message}", e)
        }
    }

    private fun statusMap(det: Boolean, seg: Boolean): WritableMap =
        Arguments.createMap().apply {
            putBoolean("det", det)
            putBoolean("seg", seg)
            putString("engine", "TFLite $engineLabel")
        }

    /** 인터프리터의 입출력 텐서에서 양자화 규격을 읽는다. float 모델이면 FLOAT을 돌려준다. */
    private fun readQuantSpec(interpreter: Interpreter?, label: String): QuantSpec {
        if (interpreter == null) return QuantSpec.FLOAT
        return try {
            val inTensor = interpreter.getInputTensor(0)
            val outTensor = interpreter.getOutputTensor(0)
            val inInt8 = inTensor.dataType() == DataType.INT8
            val outInt8 = outTensor.dataType() == DataType.INT8
            if (!inInt8 && !outInt8) {
                Log.i(TAG, "$label 입출력 float32 (양자화 변환 없음)")
                return QuantSpec.FLOAT
            }
            val inParams = inTensor.quantizationParams()
            val outParams = outTensor.quantizationParams()
            Log.i(
                TAG,
                "$label INT8 양자화 감지 - 입력(scale=${inParams.scale}, zp=${inParams.zeroPoint}) " +
                    "출력(scale=${outParams.scale}, zp=${outParams.zeroPoint})"
            )
            QuantSpec(
                inputIsInt8 = inInt8,
                inputScale = inParams.scale,
                inputZeroPoint = inParams.zeroPoint,
                outputIsInt8 = outInt8,
                outputScale = outParams.scale,
                outputZeroPoint = outParams.zeroPoint
            )
        } catch (e: Throwable) {
            Log.w(TAG, "$label 양자화 규격 조회 실패, float로 진행: ${e.message}")
            QuantSpec.FLOAT
        }
    }

    /**
     * 모델이 INT8 양자화본인지 델리게이트 선택 전에 미리 확인한다.
     *
     * 델리게이트 선택이 dtype에 달려 있는데(INT8은 GPU가 아니라 NNAPI/HTP로 가야 한다),
     * dtype은 인터프리터를 만들어야 읽을 수 있다. 델리게이트 없는 가벼운 인터프리터를
     * 한 번 만들어 확인하고 즉시 닫는다. 로드 시 1회 비용이라 런타임에는 영향이 없다.
     */
    private fun probeIsInt8(assetName: String): Boolean = try {
        val probeBuffer = loadModelBuffer(assetName)
        Interpreter(probeBuffer, Interpreter.Options().setNumThreads(1)).use {
            it.getInputTensor(0).dataType() == DataType.INT8
        }
    } catch (e: Throwable) {
        Log.w(TAG, "$assetName INT8 사전 판별 실패, float 가정: ${e.message}")
        false
    }

    /**
     * 델리게이트를 골라 인터프리터를 만든다. 부분 실패가 전체 실패가 되지 않도록 단계 폴백한다.
     *
     * 💡 [면접 대비 주석] 모델 정밀도에 따라 가속기를 달리 고른다 (2026-07-28).
     * TFLite GPU 델리게이트는 float 연산에 맞춰져 있어 int8 모델을 제대로 가속하지 못한다.
     * 반대로 Snapdragon HTP(NPU)는 int8에서 이득이 나는 구조라, 2026-07-28에 FP32 모델로
     * NNAPI를 시험했을 때 det ~235ms로 GPU(38.9ms)보다 6배 느렸다(핸드오프 6.3).
     * 그래서 INT8 모델일 때만 NNAPI를 1순위로 쓰고, float 모델은 기존대로 GPU를 쓴다.
     */
    private fun createInterpreter(assetName: String, useGpu: Boolean): Interpreter? {
        val isInt8 = probeIsInt8(assetName)
        val buffer = try {
            loadModelBuffer(assetName)
        } catch (e: Throwable) {
            Log.e(TAG, "$assetName 자산 로드 실패: ${e.message}")
            return null
        }

        if (isInt8) {
            try {
                val options = NnApiDelegate.Options().apply {
                    setExecutionPreference(
                        NnApiDelegate.Options.EXECUTION_PREFERENCE_SUSTAINED_SPEED
                    )
                    setAllowFp16(true)
                }
                val delegate = NnApiDelegate(options)
                val interpreter = Interpreter(buffer, Interpreter.Options().addDelegate(delegate))
                nnApiDelegates.add(delegate)
                engineLabel = "NNAPI(NPU INT8)"
                Log.i(TAG, "$assetName NNAPI delegate(INT8, sustained) 적용")
                return interpreter
            } catch (e: Throwable) {
                Log.w(TAG, "$assetName NNAPI delegate 실패, CPU 폴백: ${e.message}")
            }
            // INT8은 GPU를 건너뛰고 바로 CPU로 간다. XNNPACK은 int8 커널을 갖추고 있다.
            return try {
                engineLabel = "CPU(XNNPACK INT8)"
                Log.i(TAG, "$assetName CPU(XNNPACK INT8, threads=$CPU_THREADS) 적용")
                Interpreter(buffer, Interpreter.Options().setNumThreads(CPU_THREADS))
            } catch (e: Throwable) {
                Log.e(TAG, "$assetName CPU 인터프리터 생성 실패: ${e.message}")
                null
            }
        }

        if (useGpu) {
            try {
                // precisionLossAllowed=true: FP32 가중치를 GPU에서 FP16으로 연산한다.
                // iOS는 CoreML FP16+ANE로 det 6~14ms인데 Android는 FP32 GPU에서 42~52ms였다
                // (2026-07-28 실측, 약 3~7배 격차). 모델 재export 없이 얻을 수 있는 가장 큰 지렛대.
                // SUSTAINED_SPEED: 단발 지연보다 연속 추론 처리량을 우선한다(보행 중 상시 추론).
                val options = GpuDelegate.Options().apply {
                    setPrecisionLossAllowed(true)
                    setInferencePreference(
                        GpuDelegate.Options.INFERENCE_PREFERENCE_SUSTAINED_SPEED
                    )
                }
                val delegate = GpuDelegate(options)
                val interpreter = Interpreter(buffer, Interpreter.Options().addDelegate(delegate))
                gpuDelegates.add(delegate)
                gpuActive = true
                engineLabel = "GPU(FP16)"
                Log.i(TAG, "$assetName GPU delegate(FP16, sustained) 적용")
                return interpreter
            } catch (e: Throwable) {
                Log.w(TAG, "$assetName GPU delegate 실패, CPU 폴백: ${e.message}")
            }
        }

        return try {
            Log.i(TAG, "$assetName CPU(XNNPACK, threads=$CPU_THREADS) 적용")
            Interpreter(buffer, Interpreter.Options().setNumThreads(CPU_THREADS))
        } catch (e: Throwable) {
            Log.e(TAG, "$assetName CPU 인터프리터 생성 실패: ${e.message}")
            null
        }
    }

    /**
     * APK assets의 .tflite를 mmap으로 연다. build.gradle의 noCompress "tflite" 덕분에
     * 무압축 저장되어 startOffset/declaredLength 기반 매핑이 성립한다.
     */
    private fun loadModelBuffer(assetName: String): ByteBuffer {
        val fd = reactApplicationContext.assets.openFd(assetName)
        FileInputStream(fd.fileDescriptor).use { input ->
            return input.channel.map(
                FileChannel.MapMode.READ_ONLY,
                fd.startOffset,
                fd.declaredLength
            )
        }
    }

    // ------------------------------------------------------------- inference

    /**
     * base64 없이 ReflexFrameCache의 640x640 ARGB 픽셀을 직접 소비하는 경로 (2026-07-28).
     *
     * detectFrame(base64)은 플러그인이 방금 인코딩한 JPEG을 Base64.decode →
     * BitmapFactory.decode → getPixels로 되돌리는 왕복을 포함했다. 같은 프로세스 안에서
     * 이미 픽셀을 갖고 있으므로 그 복원 전체를 생략한다. 프레임이 아직 없으면 NO_FRAME으로
     * 거절해 JS가 base64 경로로 폴백하게 한다.
     */
    @ReactMethod
    fun detectFrameCached(promise: Promise) {
        if (!isLoaded) {
            promise.reject("NOT_LOADED", "TFLite 모델이 로드되지 않았습니다.", null)
            return
        }
        val pixels = ReflexFrameCache.snapshot()
        if (pixels == null || pixels.size != INPUT_SIZE * INPUT_SIZE) {
            promise.reject("NO_FRAME", "네이티브 프레임 캐시가 비어 있습니다.", null)
            return
        }
        // 전처리 + 추론을 백그라운드로 디스패치한다. 메서드는 즉시 리턴해 네이티브 모듈
        // 스레드를 해방한다(위 inferenceThread 주석 참조). promise.resolve/reject는
        // 어느 스레드에서든 호출 가능하며 JS 스레드로 자동 디스패치된다.
        inferenceHandler.post {
            try {
                val prepStart = System.nanoTime()
                val input = pixelsToNormalizedHwcBuffer(pixels)
                val prepMs = (System.nanoTime() - prepStart) / 1_000_000.0
                runBothAndResolve(pixels, input, prepMs, promise)
            } catch (e: Throwable) {
                Log.e(TAG, "detectFrameCached 실패: ${e.message}", e)
                promise.reject("EXEC_ERROR", "추론 실행 오류: ${e.message}", e)
            }
        }
    }

    @ReactMethod
    fun detectFrame(base64Image: String, promise: Promise) {
        if (!isLoaded) {
            promise.reject("NOT_LOADED", "TFLite 모델이 로드되지 않았습니다.", null)
            return
        }

        // base64 디코드 + 전처리 + 추론을 백그라운드로 디스패치한다(detectFrameCached와 동일).
        inferenceHandler.post {
            var bitmap: Bitmap? = null
            try {
                val prepStart = System.nanoTime()
                bitmap = decodeBase64(base64Image)
                if (bitmap == null) {
                    promise.reject("INVALID_IMAGE", "base64 이미지 디코딩 실패", null)
                    return@post
                }

                val pixels = bitmapToSquarePixels(bitmap)
                val input = pixelsToNormalizedHwcBuffer(pixels)
                val prepMs = (System.nanoTime() - prepStart) / 1_000_000.0
                runBothAndResolve(pixels, input, prepMs, promise)
            } catch (e: Throwable) {
                Log.e(TAG, "detectFrame 실패: ${e.message}", e)
                promise.reject("EXEC_ERROR", "추론 실행 오류: ${e.message}", e)
            } finally {
                bitmap?.recycle()
            }
        }
    }

    private fun runBothAndResolve(
        pixels: IntArray,
        floatInput: ByteBuffer,
        prepMs: Double,
        promise: Promise
    ) {
        try {
            // det와 seg는 정밀도가 다를 수 있다(예: det만 INT8 실험본). 모델별로 규격에
            // 맞는 입력 버퍼를 고른다. float 모델끼리는 같은 버퍼를 그대로 공유한다.
            val detInput = inputFor(pixels, detQuant, floatInput)
            val detRun = runModel(
                detInterpreter,
                detInput,
                AIHUB_CLASS_NAMES,
                DET_CONF_THRESHOLD,
                LEGACY_DET_ATTRS,
                "object_detection",
                detOutScratch,
                detQuant
            )
            val det = detRun.detections
            val detMs = detRun.runMs + detRun.decodeMs

            // 💡 [면접 대비 주석] seg 주기 분리 (2026-07-28).
            // seg(노면 4클래스)는 온디바이스 안전 경로에 쓰이지 않는다.
            //   - pathObstacleDetector.analyze()는 model == "segmentation" 항목을 전부 건너뛴다.
            //   - CameraView 반사 후보 필터는 SAFE_SURFACE_CLASSES / GROUND_HAZARDS(= seg 4클래스)를
            //     모두 제외한다("노면은 인지 경로 전담" 정책, 2026-07-14).
            // 즉 온디바이스 seg의 유일한 소비처는 BBox 오버레이 표시다.
            //
            // 그런데 실측상 seg가 추론 시간의 절반을 차지한다(det 약 47ms / seg 약 59ms).
            // 매 프레임 돌리면 추론 주기가 약 310ms로 묶여 BBox 갱신이 초당 3.2회에 그치고,
            // 프리뷰(30fps)와의 격차가 "박스가 늦게 붙는" 체감을 만든다.
            // det를 매 프레임, seg를 SEG_EVERY_N 프레임마다 돌려 갱신률을 올린다.
            // seg를 건너뛴 프레임은 직전 결과를 그대로 재사용하므로 오버레이가 깜빡이지 않는다.
            val runSeg = (inferenceTick++ % SEG_EVERY_N) == 0L
            var segMs = 0.0
            var segRunMs = 0.0
            var segDecodeMs = 0.0
            val seg: List<Detection>
            if (runSeg) {
                val segInput = inputFor(pixels, segQuant, floatInput)
                segInput.rewind()
                val segRun = runModel(
                    segInterpreter,
                    segInput,
                    SEG_CLASS_NAMES,
                    SEG_CONF_THRESHOLD,
                    LEGACY_SEG_ATTRS,
                    "segmentation",
                    segOutScratch,
                    segQuant
                )
                seg = segRun.detections
                segRunMs = segRun.runMs
                segDecodeMs = segRun.decodeMs
                segMs = segRunMs + segDecodeMs
                lastSegResult = seg
            } else {
                seg = lastSegResult
            }

            val benchmark = Arguments.createMap().apply {
                putDouble("det_ms", detMs)
                putDouble("seg_ms", segMs)
                putBoolean("seg_fresh", runSeg)
                putDouble("prep_ms", prepMs)
                putDouble("scene_ms", 0.0)
                putDouble("total_ms", prepMs + detMs + segMs)
                // run = 가속기(GPU delegate) 실행, decode = JVM dense head 디코드 + NMS.
                // 최적화 방향(가속기 교체 vs 후처리 개선)을 가르는 분리 계측이다.
                putDouble("det_run_ms", detRun.runMs)
                putDouble("det_decode_ms", detRun.decodeMs)
                putDouble("seg_run_ms", segRunMs)
                putDouble("seg_decode_ms", segDecodeMs)
            }

            promise.resolve(
                Arguments.createMap().apply {
                    putArray("det", toWritableArray(det))
                    putArray("seg", toWritableArray(seg))
                    putMap("benchmark", benchmark)
                }
            )
        } catch (e: Throwable) {
            Log.e(TAG, "추론 실행 실패: ${e.message}", e)
            promise.reject("EXEC_ERROR", "추론 실행 오류: ${e.message}", e)
        }
    }

    private fun decodeBase64(base64Image: String): Bitmap? {
        val clean = base64Image.substringAfter("base64,", base64Image).trim()
        val bytes = Base64.decode(clean, Base64.DEFAULT)
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    /**
     * HWC RGB float32(0~1) 입력 버퍼. realFrameProvider.bilinearResizeHWC와 동일 계약.
     * 프레임 프로세서(ReflexFrameProcessorPlugin)가 이미 640x640 정사각으로 크롭·스케일해
     * 보내므로 대개 리사이즈가 생략된다. 그렇지 않은 입력은 센터 크롭 후 스케일한다.
     */
    private fun bitmapToSquarePixels(src: Bitmap): IntArray {
        val square = if (src.width == INPUT_SIZE && src.height == INPUT_SIZE) {
            src
        } else {
            val cropSize = min(src.width, src.height)
            val originX = max(0, (src.width - cropSize) / 2)
            val originY = max(0, (src.height - cropSize) / 2)
            val cropped = Bitmap.createBitmap(src, originX, originY, cropSize, cropSize)
            val scaled = Bitmap.createScaledBitmap(cropped, INPUT_SIZE, INPUT_SIZE, true)
            if (cropped !== src && cropped !== scaled) cropped.recycle()
            scaled
        }

        val pixels = IntArray(INPUT_SIZE * INPUT_SIZE)
        square.getPixels(pixels, 0, INPUT_SIZE, 0, 0, INPUT_SIZE, INPUT_SIZE)
        if (square !== src) square.recycle()

        return pixels
    }

    /**
     * ARGB IntArray → HWC RGB float32(0~1) 다이렉트 버퍼.
     *
     * 2026-07-28: 이전에는 픽셀당 putFloat 3회(총 약 123만 회)를 돌렸다. putFloat은 호출마다
     * 경계 검사와 position 갱신을 수반해 이 규모에서 무시할 수 없다. FloatArray를 먼저
     * 채운 뒤 FloatBuffer.put(array)로 한 번에 넘겨 벌크 복사로 바꾼다. 입력 버퍼는
     * 프레임마다 새로 만들지 않고 재사용해 4.7MiB 다이렉트 할당과 GC 압력도 없앤다.
     */
    private fun pixelsToNormalizedHwcBuffer(pixels: IntArray): ByteBuffer {
        val floats = scratchFloats
        var i = 0
        for (pixel in pixels) {
            floats[i] = ((pixel shr 16) and 0xFF) * INV_255
            floats[i + 1] = ((pixel shr 8) and 0xFF) * INV_255
            floats[i + 2] = (pixel and 0xFF) * INV_255
            i += 3
        }

        val buffer = inputBuffer
        buffer.rewind()
        buffer.asFloatBuffer().put(floats)
        buffer.rewind()
        return buffer
    }

    /**
     * ARGB IntArray → HWC RGB int8 다이렉트 버퍼 (full-integer 양자화 모델용).
     *
     * q = round((p/255) / scale) + zp 를 계수 하나로 접어 q = round(p * mul) + zp로 계산한다.
     * ultralytics full_integer_quant는 scale=1/255, zp=-128로 나오므로 mul이 정확히 1이 되어
     * 사실상 q = p - 128 이다. float32 경로(123만 회 float 쓰기)보다 오히려 싸다.
     */
    private fun pixelsToInt8HwcBuffer(pixels: IntArray, spec: QuantSpec): ByteBuffer {
        val buffer = int8InputBuffer
        buffer.rewind()
        val mul = spec.inputMultiplier
        val zp = spec.inputZeroPoint
        for (pixel in pixels) {
            buffer.put(quantizeChannel((pixel shr 16) and 0xFF, mul, zp))
            buffer.put(quantizeChannel((pixel shr 8) and 0xFF, mul, zp))
            buffer.put(quantizeChannel(pixel and 0xFF, mul, zp))
        }
        buffer.rewind()
        return buffer
    }

    private fun quantizeChannel(value: Int, mul: Float, zeroPoint: Int): Byte {
        val q = (value * mul).roundToInt() + zeroPoint
        return q.coerceIn(-128, 127).toByte()
    }

    /** 모델 규격에 맞는 입력 버퍼를 고른다. */
    private fun inputFor(pixels: IntArray, spec: QuantSpec, floatBuffer: ByteBuffer): ByteBuffer =
        if (spec.inputIsInt8) pixelsToInt8HwcBuffer(pixels, spec) else floatBuffer

    /**
     * 모델 1회 실행 결과와 구간별 지연.
     *
     * 💡 [면접 대비 주석] run/decode 분리 계측 (2026-07-28).
     * 기존에는 `det_ms` 하나로 "가속기 실행 + JVM 후처리"를 뭉쳐서 쟀기 때문에,
     * 35ms 중 GPU 몫이 얼마인지 알 수 없어 최적화 방향(가속기 교체 vs 후처리 개선)을
     * 정할 수 없었다. iOS는 CoreML을 nms=True로 export해 디코딩·NMS까지 ANE 그래프
     * 안에서 처리하지만, Android는 NNAPI/GPU 호환을 위해 nms=False로 뽑아 디코딩·NMS를
     * JVM으로 끄집어냈다. 두 플랫폼 수치를 비교하려면 이 분리가 전제다.
     */
    private data class ModelRun(
        val detections: List<Detection>,
        val runMs: Double,
        val decodeMs: Double
    )

    private fun runModel(
        interpreter: Interpreter?,
        input: ByteBuffer,
        names: Array<String>,
        confThreshold: Float,
        legacyAttrs: Int,
        label: String,
        scratch: OutputScratch,
        spec: QuantSpec
    ): ModelRun {
        if (interpreter == null) return ModelRun(emptyList(), 0.0, 0.0)
        return try {
            val outTensor = interpreter.getOutputTensor(0)
            val outLength = outTensor.shape().fold(1) { acc, d -> acc * d }
            val outBuffer = scratch.buffer(outLength, if (spec.outputIsInt8) 1 else 4)

            val runStart = System.nanoTime()
            interpreter.run(input, outBuffer)
            val runMs = (System.nanoTime() - runStart) / 1_000_000.0

            val decodeStart = System.nanoTime()
            outBuffer.rewind()
            val out = scratch.floats(outLength)
            if (spec.outputIsInt8) {
                // 역양자화: f = (q - zp) * scale. dense head 디코드는 float 입력을 전제한다.
                // 다이렉트 ByteBuffer를 get(i)로 요소마다 읽으면 호출당 경계 검사가 붙어
                // 277,200개 기준 12.5ms까지 나왔다(2026-07-28 실측). 바이트 배열로 한 번에
                // 벌크 복사한 뒤 JVM 힙에서 변환한다(입력 버퍼 최적화와 같은 접근).
                val bytes = scratch.bytes(outLength)
                outBuffer.get(bytes, 0, outLength)
                val scale = spec.outputScale
                val zp = spec.outputZeroPoint
                for (i in 0 until outLength) {
                    out[i] = (bytes[i] - zp) * scale
                }
            } else {
                outBuffer.asFloatBuffer().get(out)
            }
            val detections = decodeDense(out, names, confThreshold, label)
                ?: decodeLegacy(out, names, confThreshold, legacyAttrs, label)
            val decodeMs = (System.nanoTime() - decodeStart) / 1_000_000.0

            ModelRun(detections, runMs, decodeMs)
        } catch (e: Throwable) {
            Log.e(TAG, "$label 추론 에러: ${e.message}", e)
            ModelRun(emptyList(), 0.0, 0.0)
        }
    }

    /**
     * channels-first dense head 디코드: [1, 4+nc(+32 mask), 8400].
     * 길이가 맞지 않으면 null을 반환해 legacy 경로로 넘긴다(tfliteDetector.ts와 동일 분기).
     */
    private fun decodeDense(
        out: FloatArray,
        names: Array<String>,
        confThreshold: Float,
        label: String
    ): List<Detection>? {
        val nc = names.size
        val boxAttrs = 4 + nc
        val withMask = boxAttrs + 32
        if (out.size != boxAttrs * NUM_ANCHORS && out.size != withMask * NUM_ANCHORS) {
            return null
        }

        // 💡 [면접 대비 주석] 클래스 우선 순차 스캔 (2026-07-28).
        // 기존 루프는 앵커 i를 바깥, 클래스 c를 안쪽에 두어 out[(4+c)*8400 + i]를 읽었다.
        // 이 접근은 한 앵커의 29개 클래스가 각각 8400 float(33,600바이트)씩 떨어져 있어
        // 8400 x 29 = 243,600회 접근이 사실상 전부 캐시 미스가 된다.
        // 루프를 뒤집으면 클래스 c 한 줄(8400 float = 33KB)을 순차 스캔하는 형태가 되어
        // 캐시 라인을 온전히 쓰고 JIT 벡터화도 받을 수 있다. 결과는 완전히 동일하다.
        val bestScore = bestScorePerAnchor
        val bestClass = bestClassPerAnchor
        java.util.Arrays.fill(bestScore, confThreshold)
        java.util.Arrays.fill(bestClass, -1)
        for (c in 0 until nc) {
            val base = (4 + c) * NUM_ANCHORS
            for (i in 0 until NUM_ANCHORS) {
                val score = out[base + i]
                if (score > bestScore[i]) {
                    bestScore[i] = score
                    bestClass[i] = c
                }
            }
        }

        val results = ArrayList<Detection>(16)
        for (i in 0 until NUM_ANCHORS) {
            val bestClassId = bestClass[i]
            if (bestClassId < 0) continue

            val cx = out[i] * INPUT_SIZE
            val cy = out[NUM_ANCHORS + i] * INPUT_SIZE
            val w = out[2 * NUM_ANCHORS + i] * INPUT_SIZE
            val h = out[3 * NUM_ANCHORS + i] * INPUT_SIZE
            // 하한만 둔다. 상한(w/h >= 638)을 두면 코앞의 벽·차량·사람처럼 화면을 가득
            // 채우는 박스가 버려지는데, 이는 반사 경로가 가장 먼저 경보해야 할 근접
            // 장애물이다(2026-07-28 회귀 제거).
            if (w <= 2f || h <= 2f) continue

            results.add(
                Detection(
                    model = label,
                    className = names.getOrElse(bestClassId) { "cls_$bestClassId" },
                    confidence = bestScore[i],
                    x = cx - w / 2f,
                    y = cy - h / 2f,
                    w = w,
                    h = h
                )
            )
        }
        return nonMaxSuppression(results)
    }

    /** legacy ultralytics nms=True export [1,300,6] = [x1,y1,x2,y2,score,classId] 픽셀 코너. */
    private fun decodeLegacy(
        out: FloatArray,
        names: Array<String>,
        confThreshold: Float,
        attrsPerBox: Int,
        label: String
    ): List<Detection> {
        if (attrsPerBox <= 0) return emptyList()
        val numBoxes = out.size / attrsPerBox
        val results = ArrayList<Detection>()
        for (i in 0 until numBoxes) {
            val off = i * attrsPerBox
            if (off + 5 >= out.size) break

            val x1 = min(out[off], out[off + 2])
            val y1 = min(out[off + 1], out[off + 3])
            val x2 = max(out[off], out[off + 2])
            val y2 = max(out[off + 1], out[off + 3])
            val w = x2 - x1
            val h = y2 - y1
            val score = out[off + 4]
            val clsId = kotlin.math.abs(out[off + 5]).roundToInt()

            if (score < confThreshold || clsId >= names.size) continue
            if (w <= 1f || h <= 1f) continue

            results.add(
                Detection(
                    model = label,
                    className = names.getOrElse(clsId) { "cls_$clsId" },
                    confidence = score,
                    x = x1,
                    y = y1,
                    w = w,
                    h = h
                )
            )
        }
        return nonMaxSuppression(results)
    }

    /** 클래스별 NMS. tfliteDetector.ts nonMaxSuppression과 동일 규칙(같은 className만 억제). */
    private fun nonMaxSuppression(boxes: List<Detection>): List<Detection> {
        val sorted = boxes.sortedByDescending { it.confidence }
        val keep = ArrayList<Detection>()
        for (box in sorted) {
            var shouldKeep = true
            for (kept in keep) {
                if (box.className == kept.className && iou(box, kept) > IOU_THRESHOLD) {
                    shouldKeep = false
                    break
                }
            }
            if (shouldKeep) keep.add(box)
        }
        return keep
    }

    private fun iou(a: Detection, b: Detection): Float {
        val x1 = max(a.x, b.x)
        val y1 = max(a.y, b.y)
        val x2 = min(a.x + a.w, b.x + b.w)
        val y2 = min(a.y + a.h, b.y + b.h)
        val intersection = max(0f, x2 - x1) * max(0f, y2 - y1)
        val union = a.w * a.h + b.w * b.h - intersection
        return if (union <= 0f) 0f else intersection / union
    }

    private fun toWritableArray(items: List<Detection>) = Arguments.createArray().apply {
        for (item in items) {
            pushMap(
                Arguments.createMap().apply {
                    putString("model", item.model)
                    putString("className", item.className)
                    putDouble("confidence", item.confidence.toDouble())
                    putMap(
                        "bbox",
                        Arguments.createMap().apply {
                            putDouble("x", item.x.toDouble())
                            putDouble("y", item.y.toDouble())
                            putDouble("w", item.w.toDouble())
                            putDouble("h", item.h.toDouble())
                        }
                    )
                }
            )
        }
    }

    override fun invalidate() {
        super.invalidate()
        isLoaded = false
        // 대기 중인 추론 작업을 취소하고 스레드를 종료한다(reload/앱 종료 시 누수 방지).
        inferenceHandler.removeCallbacksAndMessages(null)
        inferenceThread.quitSafely()
        ReflexFrameCache.clear()
        detInterpreter?.close()
        detInterpreter = null
        segInterpreter?.close()
        segInterpreter = null
        for (delegate in nnApiDelegates) {
            try {
                delegate.close()
            } catch (e: Throwable) {
                Log.w(TAG, "NNAPI delegate close 실패: ${e.message}")
            }
        }
        nnApiDelegates.clear()
        for (delegate in gpuDelegates) {
            try {
                delegate.close()
            } catch (e: Throwable) {
                Log.w(TAG, "GPU delegate close 실패: ${e.message}")
            }
        }
        gpuDelegates.clear()
        gpuActive = false
    }

    private data class Detection(
        val model: String,
        val className: String,
        val confidence: Float,
        val x: Float,
        val y: Float,
        val w: Float,
        val h: Float
    )

    companion object {
        private const val TAG = "TFLiteInferenceBridge"

        private const val DET_ASSET = "yolo26n/object_detection.tflite"
        private const val SEG_ASSET = "yolo26n/segmentation.tflite"

        private const val INPUT_SIZE = 640
        private const val NUM_ANCHORS = 8400
        private const val CPU_THREADS = 4
        private const val INV_255 = 1.0f / 255.0f
        // seg를 몇 프레임마다 실행할지. 1이면 매 프레임(기존 동작).
        private const val SEG_EVERY_N = 3L

        // tfliteDetector.ts와 동일 임계값(SSOT 어긋나면 온디바이스/서버 판정이 갈린다).
        private const val DET_CONF_THRESHOLD = 0.50f
        private const val SEG_CONF_THRESHOLD = 0.35f
        private const val IOU_THRESHOLD = 0.45f

        // legacy nms=True export 폴백용 attrs (현행 자산은 dense head라 사용되지 않는다).
        private const val LEGACY_DET_ATTRS = 6
        private const val LEGACY_SEG_ATTRS = 38

        private val SEG_CLASS_NAMES = arrayOf(
            "sidewalk_normal", "caution", "roadway", "braille_normal"
        )

        private val AIHUB_CLASS_NAMES = arrayOf(
            "barricade", "bench", "bicycle", "bollard", "bus", "car", "carrier", "cat",
            "chair", "dog", "fire_hydrant", "kiosk", "motorcycle", "movable_signage",
            "parking_meter", "person", "pole", "potted_plant", "power_controller",
            "scooter", "stop", "stroller", "table", "traffic_light",
            "traffic_light_controller", "traffic_sign", "tree_trunk", "truck", "wheelchair"
        )
    }
}
