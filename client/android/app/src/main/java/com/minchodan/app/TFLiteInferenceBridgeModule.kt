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
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
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
    private var gpuActive = false

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
            isLoaded = detInterpreter != null || segInterpreter != null

            if (!isLoaded) {
                promise.reject("LOAD_ERROR", "det/seg 인터프리터를 모두 생성하지 못했습니다.", null)
                return
            }

            Log.i(
                TAG,
                "모델 로드 완료 det=${detInterpreter != null} seg=${segInterpreter != null} gpu=$useGpu"
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
            putString("engine", if (gpuActive) "TFLite GPU(FP16)" else "TFLite CPU(XNNPACK)")
        }

    /** GPU delegate로 먼저 시도하고 실패하면 CPU로 재시도한다(부분 실패가 전체 실패가 되지 않게). */
    private fun createInterpreter(assetName: String, useGpu: Boolean): Interpreter? {
        val buffer = try {
            loadModelBuffer(assetName)
        } catch (e: Throwable) {
            Log.e(TAG, "$assetName 자산 로드 실패: ${e.message}")
            return null
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
                runBothAndResolve(input, prepMs, promise)
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

                val input = toNormalizedHwcBuffer(bitmap)
                val prepMs = (System.nanoTime() - prepStart) / 1_000_000.0
                runBothAndResolve(input, prepMs, promise)
            } catch (e: Throwable) {
                Log.e(TAG, "detectFrame 실패: ${e.message}", e)
                promise.reject("EXEC_ERROR", "추론 실행 오류: ${e.message}", e)
            } finally {
                bitmap?.recycle()
            }
        }
    }

    private fun runBothAndResolve(input: ByteBuffer, prepMs: Double, promise: Promise) {
        try {
            val detStart = System.nanoTime()
            val det = runModel(
                detInterpreter,
                input,
                AIHUB_CLASS_NAMES,
                DET_CONF_THRESHOLD,
                LEGACY_DET_ATTRS,
                "object_detection"
            )
            val detMs = (System.nanoTime() - detStart) / 1_000_000.0

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
            val seg: List<Detection>
            if (runSeg) {
                input.rewind()
                val segStart = System.nanoTime()
                seg = runModel(
                    segInterpreter,
                    input,
                    SEG_CLASS_NAMES,
                    SEG_CONF_THRESHOLD,
                    LEGACY_SEG_ATTRS,
                    "segmentation"
                )
                segMs = (System.nanoTime() - segStart) / 1_000_000.0
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
    private fun toNormalizedHwcBuffer(src: Bitmap): ByteBuffer {
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

        return pixelsToNormalizedHwcBuffer(pixels)
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

    private fun runModel(
        interpreter: Interpreter?,
        input: ByteBuffer,
        names: Array<String>,
        confThreshold: Float,
        legacyAttrs: Int,
        label: String
    ): List<Detection> {
        if (interpreter == null) return emptyList()
        return try {
            val outTensor = interpreter.getOutputTensor(0)
            val outLength = outTensor.shape().fold(1) { acc, d -> acc * d }
            val outBuffer = ByteBuffer
                .allocateDirect(outLength * 4)
                .order(ByteOrder.nativeOrder())

            interpreter.run(input, outBuffer)

            outBuffer.rewind()
            val out = FloatArray(outLength)
            outBuffer.asFloatBuffer().get(out)

            decodeDense(out, names, confThreshold, label)
                ?: decodeLegacy(out, names, confThreshold, legacyAttrs, label)
        } catch (e: Throwable) {
            Log.e(TAG, "$label 추론 에러: ${e.message}", e)
            emptyList()
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

        val results = ArrayList<Detection>(16)
        for (i in 0 until NUM_ANCHORS) {
            var bestClassId = -1
            var bestScore = confThreshold

            for (c in 0 until nc) {
                val score = out[(4 + c) * NUM_ANCHORS + i]
                if (score > bestScore) {
                    bestScore = score
                    bestClassId = c
                }
            }
            if (bestClassId < 0) continue

            val cx = out[i] * INPUT_SIZE
            val cy = out[NUM_ANCHORS + i] * INPUT_SIZE
            val w = out[2 * NUM_ANCHORS + i] * INPUT_SIZE
            val h = out[3 * NUM_ANCHORS + i] * INPUT_SIZE
            if (w <= 2f || h <= 2f || w >= 638f || h >= 638f) continue

            results.add(
                Detection(
                    model = label,
                    className = names.getOrElse(bestClassId) { "cls_$bestClassId" },
                    confidence = bestScore,
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
