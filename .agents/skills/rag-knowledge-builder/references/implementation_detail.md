# RAG Knowledge Builder — 구현 상세 정보

이 문서에서는 `rag-knowledge-builder` 스킬의 구체적인 구현 코드와 디스크 상의 데이터베이스 구축 및 검증 절차를 다룹니다.

---

## 1. 스크립트 1: 프레임 추출 및 중복 제거 (`extract_frames.py`)

비디오 파일로부터 1fps 주기로 프레임을 추출하고, 유사도가 90% 이상인 인접 이미지를 `pHash`를 통해 제거하는 스크립트입니다.

```python
import os
import cv2
import imagehash
from PIL import Image

def get_image_hash(frame):
    # OpenCV BGR 프레임을 PIL 이미지로 변환하여 pHash 계산
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    return imagehash.phash(pil_img)

def extract_and_deduplicate(video_path, output_dir, similarity_threshold=10):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps) # 1초당 1프레임
    
    count = 0
    saved_count = 0
    last_hash = None
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % frame_interval == 0:
            current_hash = get_image_hash(frame)
            
            # 이전 이미지와 유사도 비교 (해밍 거리 기준)
            if last_hash is not None:
                distance = current_hash - last_hash
                if distance < similarity_threshold:
                    # 너무 유사한 프레임은 건너뜀
                    count += 1
                    continue
            
            output_path = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
            # 추론에 알맞게 640x640 크기로 조정하여 저장
            resized_frame = cv2.resize(frame, (640, 640))
            cv2.imwrite(output_path, resized_frame)
            last_hash = current_hash
            saved_count += 1
            
        count += 1
        
    cap.release()
    print(f"추출 및 중복 제거 완료: {video_path} -> {saved_count}개 프레임 저장됨.")

if __name__ == "__main__":
    video_dir = "data/raw_videos"
    output_dir = "data/extracted_frames"
    for file in os.listdir(video_dir):
        if file.endswith((".mp4", ".avi", ".mov")):
            extract_and_deduplicate(
                os.path.join(video_dir, file),
                output_dir
            )
```

---

## 2. 스크립트 2: RAG 인덱싱 및 로컬 VLM 캡셔닝 (`seed_rag.py`)

추출된 이미지 파일을 로컬 `llava` VLM에 입력하여 위험 상황 캡션을 생성하고, `nomic-embed-text` 임베딩을 이용해 ChromaDB 로컬 영구 저장소에 저장하는 스크립트입니다.

```python
import os
import glob
import base64
import requests
import json
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings import OllamaEmbeddings

# 1. Ollama 로컬 임베딩 설정
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 2. 로컬 VLM (Llava) 호출용 함수
def generate_vlm_caption(image_path):
    with open(image_path, "rb") as image_file:
        img_b64 = base64.b64encode(image_file.read()).decode('utf-8')
        
    url = "http://localhost:11434/api/generate"
    prompt = (
        "이 이미지에서 시각장애인 보행 중 부딪히거나 위험할 수 있는 요소(예: 킥보드, 볼라드, 계단, 차량 등)를 찾아내고, "
        "이를 회피하기 위한 행동 지침을 한국어로 명확히 1~2문장으로 기술해 주세요. "
        "반드시 '오른쪽', '왼쪽', '정지', '우회' 등의 명확한 방향을 언급하십시오."
    )
    
    payload = {
        "model": "llava:7b",
        "prompt": prompt,
        "images": [img_b64],
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()
    except Exception as e:
        print(f"VLM 생성 에러 ({image_path}): {e}")
    return "전방에 위험물이 있습니다. 천천히 멈추어 주의해 주세요."

# 3. ChromaDB 구축 메인 함수
def build_vector_db(frame_dir, db_dir):
    image_files = glob.glob(os.path.join(frame_dir, "*.jpg"))
    documents = []
    
    for idx, img_path in enumerate(image_files):
        print(f"[{idx+1}/{len(image_files)}] 캡셔닝 및 임베딩 진행 중: {os.path.basename(img_path)}")
        caption = generate_vlm_caption(img_path)
        
        # 메타데이터 생성 규칙 (파일명이나 사물에 따라 단순 분류)
        objects = []
        if "kickboard" in caption.lower() or "킥보드" in caption:
            objects.append("kickboard")
        if "bollard" in caption.lower() or "볼라드" in caption:
            objects.append("bollard")
        if "stair" in caption.lower() or "계단" in caption:
            objects.append("stair")
            
        doc = Document(
            page_content=caption,
            metadata={
                "source": img_path,
                "objects": json.dumps(objects),
                "risk_level": "mid" if len(objects) > 0 else "low"
            }
        )
        documents.append(doc)
        
    # ChromaDB 로컬 디스크 저장
    db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_dir
    )
    db.persist()
    print(f"ChromaDB 빌드 성공! 총 {len(documents)}개 수칙 저장됨 (경로: {db_dir})")

if __name__ == "__main__":
    frame_dir = "data/extracted_frames"
    db_dir = "./chroma_db"
    build_vector_db(frame_dir, db_dir)
```

---

## 3. 스크립트 3: Retrieval Hit-rate 평가 (`eval_rag.py`)

구축된 로컬 ChromaDB의 검색 성능을 검증하는 스크립트입니다. 테스트 쿼리를 던져 Top-5 유사 이미지/수칙의 재현율(Recall@5)이 0.6 이상인지 평가합니다.

```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

def evaluate_retrieval(db_dir):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    
    # 평가용 대표 테스트 쿼리셋
    eval_queries = [
        ("인도 위에 세워진 전동 킥보드 회피 방법", "kickboard"),
        ("도로 경계의 볼라드 피하기", "bollard"),
        ("내리막 계단 또는 지하도 계단 조심하기", "stair"),
        ("인도를 침범한 배달 오토바이 보행 수칙", "motorcycle")
    ]
    
    total = len(eval_queries)
    hits = 0
    
    for query, target_obj in eval_queries:
        # 유사도 검색 실행 (Top 5)
        results = db.similarity_search_with_score(query, k=5)
        
        # Top-5 내에 정답 객체 메타데이터가 존재하는지 확인
        hit_found = False
        for doc, score in results:
            metadata = doc.metadata
            objects = metadata.get("objects", "[]")
            if target_obj in objects:
                hit_found = True
                break
                
        if hit_found:
            hits += 1
            print(f"Query: '{query}' -> 성공 [Hit] (Score: {score:.4f})")
        else:
            print(f"Query: '{query}' -> 실패 [Miss]")
            
    hit_rate = hits / total
    print("-" * 40)
    print(f"최종 Hit-Rate (Top-5): {hit_rate:.2f} (목표 >= 0.60)")
    assert hit_rate >= 0.6, "RAG Retrieval 성능 검증 기준 미달!"

if __name__ == "__main__":
    db_dir = "./chroma_db"
    evaluate_retrieval(db_dir)
```
