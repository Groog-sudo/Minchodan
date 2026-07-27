package com.minchodan.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.media.Image
import android.util.Base64
import android.util.Log
import com.mrousavy.camera.core.types.Orientation
import com.mrousavy.camera.frameprocessors.Frame
import com.mrousavy.camera.frameprocessors.FrameProcessorPlugin
import com.mrousavy.camera.frameprocessors.VisionCameraProxy
import java.io.ByteArrayOutputStream
import kotlin.system.measureTimeMillis

class ReflexFrameProcessorPlugin(proxy: VisionCameraProxy, options: Map<String, Any>?) :
    FrameProcessorPlugin() {

    private companion object {
        const val TAG = "ReflexFrameProcessor"
    }

    override fun callback(frame: Frame, arguments: Map<String, Any>?): Any? {
        val image = frame.image ?: run {
            Log.w(TAG, "callback: frame.image is null")
            return null
        }

        try {
            var bitmap: Bitmap? = null
            var rotatedBitmap: Bitmap? = null
            var croppedBitmap: Bitmap? = null
            var scaledBitmap: Bitmap? = null
            var rotationDegrees = 0f
            var jpegBytes = ByteArray(0)

            val totalMs = measureTimeMillis {
                bitmap = imageToBitmap(image)
                if (bitmap == null) {
                    Log.w(TAG, "callback: imageToBitmap returned null format=${image.format}")
                    return null
                }

                val matrix = Matrix()
                // vision-camera orientation + iOS와 동일하게 추가 180도 보정.
                // Xiaomi 등 Android 실기기에서 센서 orientation만 적용하면 콘솔/저장
                // JPEG가 정확히 180도 뒤집히는 것이 실측됨(2026-07-24).
                rotationDegrees = when (frame.orientation) {
                    Orientation.PORTRAIT -> 0f
                    Orientation.PORTRAIT_UPSIDE_DOWN -> 180f
                    Orientation.LANDSCAPE_LEFT -> 90f
                    Orientation.LANDSCAPE_RIGHT -> 270f
                    else -> 0f
                }
                rotationDegrees = (rotationDegrees + 180f) % 360f
                if (rotationDegrees != 0f) {
                    matrix.postRotate(rotationDegrees)
                }

                rotatedBitmap = Bitmap.createBitmap(
                    bitmap!!, 0, 0, bitmap!!.width, bitmap!!.height, matrix, true
                )

                val width = rotatedBitmap!!.width
                val height = rotatedBitmap!!.height
                val cropSize = minOf(width, height)
                val originX = (width - cropSize) / 2
                val originY = (height - cropSize) / 2

                croppedBitmap = Bitmap.createBitmap(
                    rotatedBitmap!!, originX, originY, cropSize, cropSize
                )

                scaledBitmap = Bitmap.createScaledBitmap(croppedBitmap!!, 640, 640, true)

                val outputStream = ByteArrayOutputStream()
                // 콘솔 Live Feed 가독성: 50은 640x640에서 ~6KB로 과도하게 뭉개짐
                scaledBitmap!!.compress(Bitmap.CompressFormat.JPEG, 70, outputStream)
                jpegBytes = outputStream.toByteArray()
            }

            Log.d(
                TAG,
                "callback ok orientation=${frame.orientation} rotation=$rotationDegrees " +
                    "src=${bitmap!!.width}x${bitmap!!.height} " +
                    "rot=${rotatedBitmap!!.width}x${rotatedBitmap!!.height} " +
                    "jpeg=${jpegBytes.size}B total=${totalMs}ms"
            )

            if (bitmap != null && bitmap !== rotatedBitmap) {
                bitmap.recycle()
            }
            rotatedBitmap?.recycle()
            croppedBitmap?.recycle()
            scaledBitmap?.recycle()

            return Base64.encodeToString(jpegBytes, Base64.NO_WRAP)
        } catch (e: Exception) {
            Log.e(TAG, "callback failed: ${e.message}", e)
            return null
        }
    }

    private fun imageToBitmap(image: Image): Bitmap? {
        if (image.format != ImageFormat.YUV_420_888) {
            Log.w(TAG, "imageToBitmap: unsupported image format=${image.format}")
            return null
        }

        return try {
            val yBuffer = image.planes[0].buffer
            val uBuffer = image.planes[1].buffer
            val vBuffer = image.planes[2].buffer

            val ySize = yBuffer.remaining()
            val uSize = uBuffer.remaining()
            val vSize = vBuffer.remaining()

            val nv21 = ByteArray(ySize + uSize + vSize)

            yBuffer.get(nv21, 0, ySize)
            vBuffer.get(nv21, ySize, vSize)
            uBuffer.get(nv21, ySize + vSize, uSize)

            // 센서 풀해상도(예: 4032x3024)를 quality=100으로 JPEG 인코딩한 뒤 다시
            // 디코딩하는 왕복 비용이 실측 프레임당 1.4~1.5초까지 걸려 반사 FPS가
            // 8fps 목표에서 0.7fps로 붕괴하는 원인이었다(2026-07-24, Xiaomi 12).
            // 최종 출력이 640x640/quality=70뿐이므로: (1) 정사각 중앙 영역만 인코딩해
            // 여백 화소를 버리고, (2) 중간 품질을 낮추고, (3) inSampleSize로 디코딩
            // 자체를 다운샘플링해 불필요한 풀해상도 디코딩 비용을 없앤다.
            val cropSize = minOf(image.width, image.height)
            val cropLeft = (image.width - cropSize) / 2
            val cropTop = (image.height - cropSize) / 2
            val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(
                Rect(cropLeft, cropTop, cropLeft + cropSize, cropTop + cropSize),
                80,
                out,
            )
            val imageBytes = out.toByteArray()

            val boundsOptions = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size, boundsOptions)
            var sampleSize = 1
            while (boundsOptions.outWidth / (sampleSize * 2) >= 640) {
                sampleSize *= 2
            }
            val decodeOptions = BitmapFactory.Options().apply { inSampleSize = sampleSize }
            BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size, decodeOptions)
        } catch (e: Exception) {
            Log.e(TAG, "imageToBitmap failed: ${e.message}", e)
            null
        }
    }
}
