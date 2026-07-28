package com.minchodan.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.PixelFormat
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
import java.nio.ByteBuffer
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

                // 2026-07-28: 추론 브릿지가 base64를 다시 디코드하지 않도록, 여기서 확보한
                // 640x640 ARGB 픽셀을 그대로 네이티브 캐시에 넘긴다(ReflexFrameCache).
                // getPixels 자체는 수 ms지만, 브릿지 쪽 Base64.decode + BitmapFactory.decode
                // + getPixels 왕복을 통째로 없앤다.
                val pixels = IntArray(ReflexFrameCache.SIDE * ReflexFrameCache.SIDE)
                scaledBitmap!!.getPixels(
                    pixels, 0, ReflexFrameCache.SIDE, 0, 0,
                    ReflexFrameCache.SIDE, ReflexFrameCache.SIDE
                )
                ReflexFrameCache.put(pixels)

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
        // 2026-07-28: pixelFormat="rgb" 경로. VisionCamera가 RGBA_8888로 프레임을 주면
        // YUV -> JPEG -> 디코드 왕복이 통째로 불필요하다. Xiaomi 12 실측에서 플러그인
        // 콜백이 프레임당 중앙값 77ms였고 그 대부분이 이 왕복(JPEG 인코딩 2회 +
        // 디코딩 2회)이었다. 카메라는 20fps를 공급하는데 콜백은 4.1회/초에 그쳤다.
        // 기기가 rgb를 지원하지 않으면 아래 YUV 경로가 그대로 동작한다(JS에서
        // pixelFormat만 되돌리면 복구되도록 두 경로를 모두 유지).
        if (image.format == PixelFormat.RGBA_8888) {
            return rgbaImageToBitmap(image)
        }

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

    /**
     * RGBA_8888 프레임을 Bitmap으로 복사한다. plane rowStride가 width*4보다 클 수 있어
     * (하드웨어 정렬 패딩) 그대로 copyPixelsFromBuffer 하면 이미지가 어긋난다.
     * 패딩이 있으면 행 단위로 잘라 붙인다.
     */
    private fun rgbaImageToBitmap(image: Image): Bitmap? {
        return try {
            val plane = image.planes[0]
            val rowStride = plane.rowStride
            val pixelStride = plane.pixelStride
            val width = image.width
            val height = image.height
            val rowBytes = width * pixelStride

            val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            val src = plane.buffer

            if (rowStride == rowBytes) {
                src.rewind()
                bitmap.copyPixelsFromBuffer(src)
            } else {
                val packed = ByteBuffer.allocateDirect(rowBytes * height)
                val row = ByteArray(rowBytes)
                for (y in 0 until height) {
                    src.position(y * rowStride)
                    src.get(row, 0, rowBytes)
                    packed.put(row)
                }
                packed.rewind()
                bitmap.copyPixelsFromBuffer(packed)
            }
            bitmap
        } catch (e: Exception) {
            Log.e(TAG, "rgbaImageToBitmap failed: ${e.message}", e)
            null
        }
    }
}
