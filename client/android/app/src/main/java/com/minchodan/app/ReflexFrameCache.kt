package com.minchodan.app

/**
 * 프레임 프로세서(ReflexFrameProcessorPlugin)와 추론 브릿지(TFLiteInferenceBridgeModule)
 * 사이의 네이티브-네이티브 프레임 전달 지점.
 *
 * 2026-07-28: 이전에는 플러그인이 640x640 비트맵을 JPEG로 압축 → base64로 JS에 넘기고,
 * JS가 그 base64를 다시 브릿지로 넘겨 네이티브가 Base64.decode → BitmapFactory.decode →
 * getPixels로 되돌렸다. 같은 프로세스 안에서 방금 만든 픽셀을 인코딩·디코딩으로 왕복시킨
 * 셈이라, 추론 지연 107ms 중 상당 부분이 이 복원 비용이었다.
 *
 * 여기서는 플러그인이 이미 확보한 640x640 ARGB 픽셀을 그대로 보관하고, 브릿지가 그것을
 * 직접 읽는다. base64는 서버 전송·콘솔 Live Feed용 JPEG 경로에만 남는다.
 *
 * 프레임 프로세서 스레드가 쓰고 RN 네이티브 모듈 스레드가 읽으므로 참조 교체만 동기화한다.
 * 픽셀 배열은 매 프레임 새로 할당해 넣고 이후 변경하지 않으므로(불변 취급) 읽는 쪽이
 * 부분적으로 갱신된 배열을 보는 일은 없다.
 */
object ReflexFrameCache {

    @Volatile
    private var latest: IntArray? = null

    @Volatile
    private var latestSequence: Long = 0L

    val sequence: Long
        get() = latestSequence

    /** 플러그인이 프레임마다 호출한다. size는 항상 SIDE * SIDE 여야 한다. */
    fun put(pixels: IntArray) {
        latest = pixels
        latestSequence += 1
    }

    /** 브릿지가 추론 직전에 호출한다. 아직 프레임이 없으면 null. */
    fun snapshot(): IntArray? = latest

    fun clear() {
        latest = null
    }

    const val SIDE = 640
}
