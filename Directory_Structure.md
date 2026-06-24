<!-- Directory_Structure.md -->

### 임시 디렉토리 구조

```shell
guidedog-ai/
│
├── server/                          # GPU 서버 (FastAPI)
│   ├── main.py                      # FastAPI 앱 진입점, CORS, 라우터 등록
│   ├── config.py                    # 환경변수 (LLM_PROVIDER, Redis URL 등)
│   ├── requirements.txt
│   ├── verify_gpu.py                # [부록C] sm_120 / CUDA 12.8 검증 스크립트
│   │
│   ├── api/                         # ─── 1단계: 통신망 ───
│   │   ├── ws_router.py             # APIRouter + WebSocket /ws/detect
│   │   ├── session_manager.py       # device_token 검증, session_id 발급
│   │   └── heartbeat.py             # 5초 ping/pong asyncio 루프
│   │
│   ├── capture/                     # ─── 2단계: 프레임 수신 ───
│   │   ├── frame_decoder.py         # base64 → np.frombuffer → cv2.imdecode → resize(640,640)
│   │   └── stream_splitter.py       # 반사 스트림(8~10fps) / 인지 스트림(1~2fps) 분기
│   │
│   ├── detection/                   # ─── 3단계: 탐지·분할·게이트 ───
│   │   ├── yolo_detector.py         # YOLO26 predict(conf=0.35), boxes 파싱
│   │   ├── segformer_segmentor.py   # SegFormer 의미분할 마스크 생성
│   │   ├── bytetrack_tracker.py     # ByteTrack update() → track_id 부여
│   │   │
│   │   ├── gates/
│   │   │   ├── reflex_gate.py       # Reflex Risk Gate: 고위험 클래스 + 근접 → alert_id+방향
│   │   │   └── surface_gate.py      # Surface Fast-Alert Gate: P0 노면 하단 검출 → alert_id
│   │   │
│   │   └── schemas.py               # DetectionResult, SurfaceResult, RiskEvent 타입
│   │
│   ├── rag/                         # ─── 4·5단계: Vector DB 구축·검색 ───
│   │   ├── build/                   # 오프라인 배치 (4단계)
│   │   │   ├── frame_extractor.py   # 영상 → 1fps 프레임 추출
│   │   │   ├── dedup_phash.py       # pHash 중복 제거
│   │   │   ├── llava_captioner.py   # Ollama(Llava) 한글 캡셔닝
│   │   │   └── db_builder.py        # Chroma.from_documents(persist_directory)
│   │   │
│   │   ├── retriever.py             # 5단계: similarity_search_with_score(k=5)
│   │   ├── fallback.py              # 유사도 미달 시 룰 기반 fallback 문자열
│   │   └── vector_db_factory.py     # [추상화] Chroma ↔ Qdrant 핫스왑
│   │
│   ├── orchestration/               # ─── 6단계: LangGraph L1/L2/L3 ───
│   │   ├── state.py                 # OrchState TypedDict (event, risk_level, rag_context)
│   │   ├── graph.py                 # StateGraph 조립, 노드 등록, 엣지 정의
│   │   ├── nodes/
│   │   │   ├── l1_classifier.py     # L1: 룰 기반 위험도 분류 (mid/low만 진입)
│   │   │   ├── l2_generator.py      # L2: ChatOllama(Gemma2) ainvoke — 20자/방향 포함
│   │   │   ├── l3_validator.py      # L3: 길이·방향 키워드 검증, RETRY(최대 1회)
│   │   │   └── fallback_node.py     # 최종 실패 → 고정 문장("전방 주의, 천천히 멈추세요")
│   │   └── llm_client_factory.py    # [추상화] BaseChatModel — Ollama ↔ gpt-4o-mini 핫스왑
│   │
│   ├── tts/                         # ─── 7단계: 음성 출력 (서버 측) ───
│   │   ├── realtime_tts.py          # 인지 경로: Kokoro/Coqui generate() → base64 MP3
│   │   ├── reflex_clip_sender.py    # 반사 경로: alert_id → 사전합성 클립 WS 고우선 전송
│   │   ├── suppressor.py            # Redis setex(suppress:…, 60) 중복 억제
│   │   └── tts_service.py           # [추상화] TTSService — 출력 MP3/WAV 규격 통일
│   │
│   ├── bus/                         # Redis Streams 인터페이스
│   │   ├── redis_client.py          # aioredis 연결 풀
│   │   ├── producer.py              # xadd("risk.events", …) — 인지 경로 발행
│   │   └── consumer.py              # xread 구독 — orchestration 진입
│   │
│   └── models/                      # 모델 파일 저장소 (git-ignore)
│       ├── yolo26/
│       │   ├── det_weights.pt       # YOLO26 Detection 가중치
│       │   └── seg_weights.pt       # YOLO26-Seg (SegFormer 대체 옵션)
│       └── segformer/
│           └── segformer_weights/   # SegFormer 체크포인트
│
├── data/                            # ─── 학습·RAG 데이터 ───
│   ├── raw/                         # AI Hub 보행자 데이터셋 (dataSetSn=18) 원본
│   ├── frames/                      # 영상 → 1fps 추출 프레임
│   ├── deduped/                     # pHash 중복 제거 후 프레임
│   ├── captions/                    # Llava 캡셔닝 결과 JSON
│   ├── chroma_db/                   # ChromaDB persist 디렉토리 (4단계 산출물)
│   └── reflex_clips/                # 사전합성 반사 음성 클립 (alert_id별 MP3)
│       ├── high_front.mp3
│       ├── high_left.mp3
│       └── ...
│
├── training/                        # ─── 모델 학습 (오프라인) ───
│   ├── datasets/
│   │   ├── detection/               # YOLO26 학습 데이터 (labels/images)
│   │   │   ├── images/
│   │   │   └── labels/
│   │   └── segmentation/            # SegFormer 학습 데이터 (마스크)
│   │       ├── images/
│   │       └── masks/
│   ├── configs/
│   │   ├── yolo26_det.yaml          # 클래스: braille_normal, braille_damaged, crosswalk …
│   │   └── segformer_seg.yaml       # sidewalk_normal, sidewalk_damaged, roadway …
│   ├── train_detection.py
│   ├── train_segmentation.py
│   └── export_tensorrt.py           # TRT 엔진 빌드 (데모 머신에서 실행)
│
├── client/                          # ─── React Native 앱 (thin client) ───
│   ├── App.tsx
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts      # 1단계: WS 연결·hello/welcome 핸드셰이크
│   │   │   └── useCamera.ts         # 2단계: useCameraDevice('back') + 이중 타이머
│   │   ├── services/
│   │   │   ├── frameCapture.ts      # takePhoto({qualityPrioritization:'speed'}) → base64
│   │   │   ├── audioPlayer.ts       # 7단계: decodeAudioData() Web Audio 재생
│   │   │   └── reflexClipPlayer.ts  # 반사 클립 즉시 재생 (선점 로직)
│   │   ├── components/
│   │   │   └── CameraView.tsx       # 카메라 프리뷰 (운영자용)
│   │   └── utils/
│   │       └── haptics.ts           # Haptics + announceForAccessibility
│   ├── assets/
│   │   └── reflex_clips/            # 사전합성 클립 앱 번들 (server/data와 동기화)
│   └── package.json
│
├── console/                         # ─── React 운영자 모니터링 콘솔 ───
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DetectionFeed.tsx    # 탐지 결과 실시간 피드
│   │   │   ├── RiskEventLog.tsx     # Redis risk.events 스트림 뷰
│   │   │   └── SessionStatus.tsx    # WS 세션 상태
│   │   └── hooks/
│   │       └── useSSE.ts            # SSE or WS 서버 구독
│   └── package.json
│
├── scripts/                         # ─── 유틸리티 스크립트 ───
│   ├── verify_gpu.py                # sm_120 + CUDA 12.8 + GPU 1-step 연산 검증
│   ├── build_chroma.sh              # 4단계 오프라인 DB 빌드 실행 쇼트컷
│   └── eval_hitrate.py              # Top-5 hit-rate 평가 (완료 기준 ≥ 0.6)
│
├── tests/
│   ├── test_ws_echo.py              # 1단계: RTT < 100ms echo 검증
│   ├── test_frame_decode.py         # 2단계: 캡처→수신 < 50ms 검증
│   ├── test_detection.py            # 3단계: conf≈0.87, track_id, < 80ms 검증
│   ├── test_rag_retrieval.py        # 5단계: kickboard 쿼리 < 50ms 검증
│   ├── test_langgraph.py            # 6단계: bollard 주입 → 20자/방향 포함 검증
│   └── test_tts_reflex.py           # 7단계: 반사 클립 선점 재생 검증
│
├── docker/                          # ─── Docker Build & Setting ───
│   ├── .dockerignore                #  컨테이너 생성 시 예외 파일 작성
│   ├── docker-compose.yml           # Redis + Ollama + FastAPI 컨테이너 구성
│   ├── linux_Docker_Build.sh        # Linux OS에서 Docker Image 생성 자동화 파일
│   ├── macOS_Docker_Build.sh        # MacOS에서 Docker Image 생성 자동화 파일
│   ├── windows_Docker_Build.bat      # windows OS에서 Docker Image 생성 자동화 파일
│   └── Dockerfile                   #  컨테이너 구성
├── .env.example                     # LLM_PROVIDER, REDIS_URL, CHROMA_PATH 등
└── README.md
```
