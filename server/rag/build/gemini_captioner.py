import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import base64
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def generate_caption(image_path: str) -> str:
    """
    Gemini 2.5 Flash Lite VLM을 사용하여 보행 환경 이미지의 한글 상황 묘사 캡션을 생성합니다.

    Args:
        image_path: 캡셔닝할 이미지 파일 경로

    Returns:
        한글 상황 묘사 캡션 문자열

    Raises:
        ValueError: GOOGLE_API_KEY 미설정 시 명확한 에러 메시지와 함께 발생 (비협상 가드)
        FileNotFoundError: 이미지 파일이 없을 경우 발생
        RuntimeError: API 호출 실패 및 네트워크 오류 발생 시 발생
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_KEY_HERE":
        raise ValueError(
            "GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. .env 파일을 확인해 주세요."
        )

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"캡셔닝할 이미지가 존재하지 않습니다: {image_path}")

    try:
        # 이미지 파일을 읽어서 base64 인코딩
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        # TODO(human-decision): gemini-2.5-flash-lite 성능 검증 후 필요시 gemini-2.5-flash로 업그레이드 검토
        # 기본값으로 gemini-2.5-flash-lite를 사용
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite", google_api_key=api_key, temperature=0.2
        )

        prompt = (
            "당신은 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼의 상황 캡셔닝 모델입니다. "
            "이 보행자 전방 카메라 이미지에 나타난 상황과 위험 요소를 한국어 1~2문장으로 사실적이고 간결하게 설명해 주세요. "
            "추측하지 말고 보이는 장애물과 바닥 상태만 명확히 언급해 주세요."
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_data}"},
            ]
        )

        response = llm.invoke([message])
        caption = response.content
        if not caption:
            raise RuntimeError("Gemini VLM이 빈 응답을 반환했습니다.")

        return str(caption).strip()

    except Exception as e:
        raise RuntimeError(f"Gemini API 호출 중 오류가 발생했습니다: {e}") from e


if __name__ == "__main__":
    print("gemini_captioner.py 스모크 테스트 실행")

    # [DUMMY DATA] 설명: 실제 Gemini Vision API 응답 / 주의: 한글 상황 묘사 1~2문장의 가짜 캡션 문자열 반환
    dummy_image = "temp_smoke_img.jpg"
    import numpy as np
    from PIL import Image

    # 더미 이미지 생성
    data = np.zeros((100, 100, 3), dtype=np.uint8)
    data[:, :] = [0, 255, 0]
    Image.fromarray(data).save(dummy_image)

    try:
        caption = generate_caption(dummy_image)
        print(f"캡션 결과: {caption}")
    except ValueError as ve:
        # GOOGLE_API_KEY가 없을 경우 스모크 테스트용 Mock 폴백 작동
        print(f"가드레일 정상 작동: {ve}")
        print("API Key 미설정 상태이므로 Mock 응답으로 대체하여 출력합니다.")
        mock_response = "초록색 블록 노면이 펼쳐져 있으며 장애물은 감지되지 않는 안전한 환경입니다."
        print(f"Mock 캡션 결과: {mock_response}")
    except Exception as e:
        print(f"기타 오류 발생: {e}")
    finally:
        if os.path.exists(dummy_image):
            os.remove(dummy_image)
