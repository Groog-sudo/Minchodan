package com.minchodan.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Base64
import android.util.Log
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.label.ImageLabeling
import com.google.mlkit.vision.label.defaults.ImageLabelerOptions

/**
 * iOS VNClassifyImageRequest(CoreMLInferenceBridge.classifyScene)의 Android 대응.
 * ML Kit Image Labeling(온디바이스)으로 top labels를 얻고,
 * docs/design/indoor_fp_mitigation_design.md §4와 같은 정책으로 isLikelyIndoor를 산출한다.
 *
 * ML Kit taxonomy는 Apple Vision과 다르므로 identifier 집합을 Android용으로 별도 유지한다.
 * 실패 시 허용적 폴백(isLikelyIndoor=false) — 기존 co-occurrence 게이트만으로 동작.
 */
class SceneClassifyBridgeModule(reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    private val labeler = ImageLabeling.getClient(
        ImageLabelerOptions.Builder()
            .setConfidenceThreshold(0.05f)
            .build()
    )

    private val outdoorPositiveIdentifiers = setOf(
        "outdoor", "sky", "cloud", "plant", "tree", "grass", "flower",
        "street", "road", "sidewalk", "path", "highway", "bridge",
        "mountain", "hill", "park", "field", "lawn", "asphalt",
        "vehicle", "car", "bicycle", "motorcycle", "bus", "truck"
    )

    private val indoorPositiveIdentifiers = setOf(
        "indoor", "furniture", "chair", "table", "desk", "couch", "sofa",
        "shelf", "cabinet", "lamp", "ceiling", "room", "office",
        "computer", "laptop", "keyboard", "monitor", "screen",
        "bed", "bathroom", "kitchen", "door"
    )

    override fun getName(): String = "SceneClassifyBridgeModule"

    @ReactMethod
    fun classifyScene(base64Image: String, promise: Promise) {
        var working: Bitmap? = null
        try {
            val clean = base64Image
                .substringAfter("base64,", base64Image)
                .trim()
            val bytes = Base64.decode(clean, Base64.DEFAULT)
            val decoded = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            if (decoded == null) {
                promise.resolve(permissiveFallback())
                return
            }
            working = scaleDown(decoded, 640)
            if (working !== decoded) {
                decoded.recycle()
            }
            val image = InputImage.fromBitmap(working, 0)
            val toRecycle = working
            labeler.process(image)
                .addOnSuccessListener { labels ->
                    toRecycle.recycle()
                    if (labels.isEmpty()) {
                        promise.resolve(permissiveFallback())
                        return@addOnSuccessListener
                    }
                    val top5 = labels.sortedByDescending { it.confidence }.take(5)
                    val topLabels = Arguments.createArray()
                    for (label in top5) {
                        val row = Arguments.createMap()
                        row.putString("identifier", label.text.lowercase())
                        row.putDouble("confidence", label.confidence.toDouble())
                        topLabels.pushMap(row)
                    }
                    val outdoorEvidence = top5.firstOrNull {
                        outdoorPositiveIdentifiers.contains(it.text.lowercase())
                    }
                    val indoorEvidence = top5.firstOrNull {
                        indoorPositiveIdentifiers.contains(it.text.lowercase())
                    }

                    val isLikelyIndoor: Boolean
                    val confidence: Double
                    when {
                        outdoorEvidence != null && indoorEvidence == null -> {
                            isLikelyIndoor = false
                            confidence = outdoorEvidence.confidence.toDouble()
                        }
                        outdoorEvidence != null && indoorEvidence != null -> {
                            if (outdoorEvidence.confidence > indoorEvidence.confidence) {
                                isLikelyIndoor = false
                                confidence = outdoorEvidence.confidence.toDouble()
                            } else {
                                isLikelyIndoor = true
                                confidence = indoorEvidence.confidence.toDouble()
                            }
                        }
                        indoorEvidence != null -> {
                            isLikelyIndoor = true
                            confidence = indoorEvidence.confidence.toDouble()
                        }
                        else -> {
                            // 확정 증거 없음 → 보수적 실내 (반사 억제 방향)
                            isLikelyIndoor = true
                            confidence = 0.0
                        }
                    }

                    val result = Arguments.createMap()
                    result.putBoolean("isLikelyIndoor", isLikelyIndoor)
                    result.putDouble("confidence", confidence)
                    result.putArray("topLabels", topLabels)
                    promise.resolve(result)
                }
                .addOnFailureListener { err ->
                    toRecycle.recycle()
                    Log.w(TAG, "ML Kit 실패, 허용적 폴백: ${err.message}")
                    promise.resolve(permissiveFallback())
                }
        } catch (e: Exception) {
            working?.recycle()
            Log.w(TAG, "decode/classify 예외: ${e.message}")
            promise.resolve(permissiveFallback())
        }
    }

    private fun permissiveFallback() = Arguments.createMap().apply {
        putBoolean("isLikelyIndoor", false)
        putDouble("confidence", 0.0)
        putArray("topLabels", Arguments.createArray())
    }

    private fun scaleDown(src: Bitmap, maxSide: Int): Bitmap {
        val w = src.width
        val h = src.height
        val longest = maxOf(w, h)
        if (longest <= maxSide) return src
        val scale = maxSide.toFloat() / longest.toFloat()
        val nw = (w * scale).toInt().coerceAtLeast(1)
        val nh = (h * scale).toInt().coerceAtLeast(1)
        return Bitmap.createScaledBitmap(src, nw, nh, true)
    }

    companion object {
        private const val TAG = "SceneClassify"
    }
}
