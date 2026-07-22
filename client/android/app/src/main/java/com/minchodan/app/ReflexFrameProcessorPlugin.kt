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
                rotationDegrees = when (frame.orientation) {
                    Orientation.PORTRAIT -> 0f
                    Orientation.PORTRAIT_UPSIDE_DOWN -> 180f
                    Orientation.LANDSCAPE_LEFT -> 90f
                    Orientation.LANDSCAPE_RIGHT -> 270f
                    else -> 0f
                }
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
                scaledBitmap!!.compress(Bitmap.CompressFormat.JPEG, 50, outputStream)
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

            val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, yuvImage.width, yuvImage.height), 100, out)
            val imageBytes = out.toByteArray()
            BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
        } catch (e: Exception) {
            Log.e(TAG, "imageToBitmap failed: ${e.message}", e)
            null
        }
    }
}
