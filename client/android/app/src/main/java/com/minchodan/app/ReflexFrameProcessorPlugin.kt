package com.minchodan.app

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import android.media.Image
import android.util.Base64
import com.mrousavy.camera.core.types.Orientation
import com.mrousavy.camera.frameprocessors.Frame
import com.mrousavy.camera.frameprocessors.FrameProcessorPlugin
import com.mrousavy.camera.frameprocessors.VisionCameraProxy
import java.io.ByteArrayOutputStream

class ReflexFrameProcessorPlugin(proxy: VisionCameraProxy, options: Map<String, Any>?) :
    FrameProcessorPlugin() {

    override fun callback(frame: Frame, arguments: Map<String, Any>?): Any? {
        val image = frame.image ?: return null
        
        try {
            val bitmap = imageToBitmap(image) ?: return null
            
            // 1. 회전 보정
            val matrix = Matrix()
            // frame.orientation (portrait, landscape 등)에 맞춰 각도 매핑
            val rotationDegrees = when (frame.orientation) {
                Orientation.PORTRAIT -> 90f
                Orientation.PORTRAIT_UPSIDE_DOWN -> 270f
                Orientation.LANDSCAPE_LEFT -> 180f
                Orientation.LANDSCAPE_RIGHT -> 0f
                else -> 0f
            }
            if (rotationDegrees != 0f) {
                matrix.postRotate(rotationDegrees)
            }
            
            val rotatedBitmap = Bitmap.createBitmap(
                bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true
            )
            
            // 2. 중앙 정삼각형 크롭
            val width = rotatedBitmap.width
            val height = rotatedBitmap.height
            val cropSize = Math.min(width, height)
            val originX = (width - cropSize) / 2
            val originY = (height - cropSize) / 2
            
            val croppedBitmap = Bitmap.createBitmap(
                rotatedBitmap, originX, originY, cropSize, cropSize
            )
            
            // 3. 640x640 리사이즈
            val scaledBitmap = Bitmap.createScaledBitmap(croppedBitmap, 640, 640, true)
            
            // 4. JPEG 압축 및 Base64 인코딩 (iOS와 동일한 0.5/50% 퀄리티)
            val outputStream = ByteArrayOutputStream()
            scaledBitmap.compress(Bitmap.CompressFormat.JPEG, 50, outputStream)
            val jpegBytes = outputStream.toByteArray()
            
            // 리소스 정리
            if (bitmap != rotatedBitmap) bitmap.recycle()
            rotatedBitmap.recycle()
            croppedBitmap.recycle()
            scaledBitmap.recycle()
            
            return Base64.encodeToString(jpegBytes, Base64.NO_WRAP)
        } catch (e: Exception) {
            e.printStackTrace()
            return null
        }
    }

    private fun imageToBitmap(image: Image): Bitmap? {
        if (image.format == ImageFormat.YUV_420_888) {
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
            return BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
        }
        return null
    }
}
