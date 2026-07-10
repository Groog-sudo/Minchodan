import sys
import os
import asyncio

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.tts.tts_service import get_tts_service

async def test():
    print("TTS 서비스 초기화 중...")
    service = get_tts_service()
    print(f"로드된 서비스: {service.__class__.__name__}")
    
    text = "안녕하세요. 시각장애인 보행 보조 시스템 민초단입니다. 전방에 볼라드가 있으니 우측으로 우회하세요."
    print(f"음성 합성 테스트 시작: '{text}'")
    
    # generate 테스트
    audio_data = await service.generate(text, voice="ko", speed=1.0)
    
    if audio_data:
        print(f"음성 합성 성공! 크기: {len(audio_data)} bytes")
        output_file = "test_output.wav"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        print(f"테스트 음성 파일 저장 완료: {output_file}")
    else:
        print("음성 합성 실패")

if __name__ == "__main__":
    asyncio.run(test())
