# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import pytest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.build.gemini_captioner import generate_caption
load_dotenv()


@patch("server.rag.build.gemini_captioner.ChatGoogleGenerativeAI")
def test_generate_caption_success(mock_chat, tmp_path):
    # ChatGoogleGenerativeAI 인스턴스와 invoke 메서드 Mocking
    mock_instance = MagicMock()
    mock_chat.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.content = "전방 보도블록 위에 전동 킥보드가 쓰러져 있습니다."
    mock_instance.invoke.return_value = mock_response
    
    img_path = str(tmp_path / "test.jpg")
    with open(img_path, "w") as f:
        f.write("fake image data")
        
    # GOOGLE_API_KEY 임시 주입
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_api_key_for_test"}):
        caption = generate_caption(img_path)
        
    assert caption == "전방 보도블록 위에 전동 킥보드가 쓰러져 있습니다."
    mock_chat.assert_called_once_with(
        model="gemini-2.5-flash-lite",
        google_api_key="fake_api_key_for_test",
        temperature=0.2
    )

def test_generate_caption_missing_key(tmp_path):
    img_path = str(tmp_path / "test.jpg")
    with open(img_path, "w") as f:
        f.write("fake image data")
        
    # GOOGLE_API_KEY 제거 상태에서 ValueError 발생 검증
    with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
        with pytest.raises(ValueError) as excinfo:
            generate_caption(img_path)
        assert "GOOGLE_API_KEY" in str(excinfo.value)

def test_generate_caption_file_not_found():
    # 파일이 존재하지 않는 경우 FileNotFoundError 발생 검증
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_api_key"}):
        with pytest.raises(FileNotFoundError):
            generate_caption("non_existent_image.jpg")
