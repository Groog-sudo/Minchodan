# 프로젝트 스캔 보고서

> **작성일**: 2026-06-30
> **버전**: v0.1.0
> **대상 루트**: `C:\Dev_task\workspace\Project\finally_project\AI_GilDang\Minchodan`

---

## 1. 요약

| 항목 | 값 |
| --- | --- |
| 전체 파일 수 | 177 |
| 문서 파일 수 | 68 |
| Python 파일 수 | 59 |

---

## 2. 폴더 트리

```text
Minchodan/
├── .agents/
│   └── skills/
│       ├── camera-frame-capture/
│       ├── llm-guidance-orchestrator/
│       ├── rag-knowledge-builder/
│       ├── rag-realtime-search/
│       ├── tts-voice-streamer/
│       ├── websocket-gateway/
│       └── yolo-obstacle-detection/
├── .claude/
│   └── skills/
│       ├── camera-frame-capture/
│       ├── llm-guidance-orchestrator/
│       ├── rag-knowledge-builder/
│       ├── rag-realtime-search/
│       ├── tts-voice-streamer/
│       ├── websocket-gateway/
│       └── yolo-obstacle-detection/
├── .github/
│   └── workflows/
│       └── lint.yml
├── client/
│   ├── assets/
│   │   └── reflex_clips/
│   └── src/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       └── utils/
├── console/
│   └── src/
│       ├── components/
│       └── hooks/
├── data/
│   ├── captions/
│   │   └── .gitkeep
│   ├── chroma_db/
│   │   └── .gitkeep
│   ├── deduped/
│   │   └── .gitkeep
│   ├── frames/
│   │   └── .gitkeep
│   ├── raw/
│   │   └── .gitkeep
│   └── reflex_clips/
│       └── .gitkeep
├── docker/
│   ├── .dockerignore
│   ├── .gitkeep
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── linux_docker_start.sh
│   ├── macos_docker_start.sh
│   └── windows_docker_start.bat
├── docs/
│   ├── changelogs/
│   │   ├── dg.md
│   │   ├── jh.md
│   │   ├── jy.md
│   │   ├── kb.md
│   │   ├── README.md
│   │   ├── TEMPLATE.md
│   │   └── th.md
│   ├── AGENTS.md
│   ├── antigravity_agent_prompt__4_5_final.md
│   ├── api_specification.md
│   ├── architecture.md
│   ├── behavior_and_risk_insight.md
│   ├── code_quality_guide.md
│   ├── course_codebase_guide.md
│   ├── deployment_guide.md
│   ├── dual_gemma4_latency_analysis.md
│   ├── environment_variables.md
│   ├── gemini_fallback_feasibility.md
│   ├── git_branching_strategy.md
│   ├── latency_impact_analysis.md
│   ├── minchodan_design_note.md
│   ├── pipeline_stage_design.md
│   ├── README.md
│   ├── stage2_capture_design.md
│   ├── stage3_detection_design.md
│   ├── stage4_5_data_replacement_guide.md
│   ├── stage4_5_directory_guide.md
│   ├── stage4_5_implementation_log.md
│   ├── stage4_5_rag_design.md
│   ├── stage4_5_test_guide.md
│   ├── stage6_orchestration_design.md
│   └── test_specification.md
├── scripts/
│   ├── .gitkeep
│   ├── download_pretrained_weights.py
│   ├── integration_test_pipeline.py
│   ├── postwork.bat
│   ├── postwork.ps1
│   ├── postwork.sh
│   ├── prework.bat
│   ├── prework.ps1
│   ├── prework.sh
│   ├── project_scan.py
│   ├── slack_publisher.py
│   └── verify_pretrained_weights.py
├── server/
│   ├── api/
│   │   ├── .gitkeep
│   │   └── monitor.py
│   ├── bus/
│   │   ├── .gitkeep
│   │   ├── __init__.py
│   │   ├── producer.py
│   │   └── redis_client.py
│   ├── capture/
│   │   ├── .gitkeep
│   │   ├── __init__.py
│   │   ├── frame_decoder.py
│   │   └── stream_splitter.py
│   ├── detection/
│   │   ├── gates/
│   │   ├── __init__.py
│   │   ├── bytetrack_tracker.py
│   │   ├── config.py
│   │   ├── detection_pipeline.py
│   │   ├── detector_interface.py
│   │   ├── mock_detector.py
│   │   ├── schemas.py
│   │   ├── yolo_detector.py
│   │   └── yolo_segmentor.py
│   ├── mcp/
│   │   ├── gpu_monitor.py
│   │   └── manager.py
│   ├── models/
│   │   └── yolo26n/
│   ├── orchestration/
│   │   ├── nodes/
│   │   ├── __init__.py
│   │   ├── graph.py
│   │   ├── llm_client_factory.py
│   │   └── state.py
│   ├── rag/
│   │   ├── build/
│   │   ├── shared/
│   │   ├── embedding_engine_factory.py
│   │   ├── fallback.py
│   │   ├── retriever.py
│   │   └── vector_db_factory.py
│   ├── tts/
│   │   └── .gitkeep
│   └── main.py
├── tests/
│   ├── .gitkeep
│   ├── test_db_builder.py
│   ├── test_dedup_phash.py
│   ├── test_detection.py
│   ├── test_e2e_pipeline.py
│   ├── test_embedding_engine_factory.py
│   ├── test_fallback.py
│   ├── test_frame_decode.py
│   ├── test_frame_extractor.py
│   ├── test_gemini_captioner.py
│   ├── test_langgraph.py
│   ├── test_mcp_gpu.py
│   ├── test_mcp_integration.py
│   ├── test_retriever.py
│   └── test_vector_db_factory.py
├── training/
│   ├── configs/
│   │   └── .gitkeep
│   └── datasets/
│       ├── detection/
│       └── segmentation/
├── .env.example
├── .gitignore
├── .jscpd.json
├── .pre-commit-config.yaml
├── AGENTS.md
├── CLAUDE.md
├── Directory_Structure.md
├── opencode.json
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── SCRIPT_GENERATION_PROMPT.md
└── SKILLS.md
```

---

## 3. 핵심 파일

| 파일명 | 발견 경로 |
| --- | --- |
| .env.example | .env.example |
| README.md | README.md, docs/README.md, docs/changelogs/README.md |
| package.json | 없음 |
| pyproject.toml | pyproject.toml |
| requirements.txt | requirements.txt |

---

## 4. 확장자 통계

| 확장자 | 파일 수 |
| --- | --- |
| .md | 66 |
| .py | 59 |
| (no extension) | 32 |
| .sh | 4 |
| .bat | 3 |
| .json | 2 |
| .ps1 | 2 |
| .pt | 2 |
| .txt | 2 |
| .yml | 2 |
| .example | 1 |
| .toml | 1 |
| .yaml | 1 |

---

## 5. 문서 파일

| 파일 | 크기(bytes) |
| --- | --- |
| AGENTS.md | 13958 |
| CLAUDE.md | 11302 |
| Directory_Structure.md | 9849 |
| README.md | 19064 |
| SCRIPT_GENERATION_PROMPT.md | 15727 |
| SKILLS.md | 8679 |
| requirements-dev.txt | 239 |
| requirements.txt | 395 |
| .agents/skills/camera-frame-capture/SKILL.md | 16513 |
| .agents/skills/camera-frame-capture/references/implementation_detail.md | 31675 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | 14456 |
| .agents/skills/llm-guidance-orchestrator/references/implementation_detail.md | 20038 |
| .agents/skills/rag-knowledge-builder/SKILL.md | 8974 |
| .agents/skills/rag-knowledge-builder/references/implementation_detail.md | 7993 |
| .agents/skills/rag-realtime-search/SKILL.md | 9705 |
| .agents/skills/rag-realtime-search/references/implementation_detail.md | 12116 |
| .agents/skills/tts-voice-streamer/SKILL.md | 12273 |
| .agents/skills/tts-voice-streamer/references/implementation_detail.md | 7833 |
| .agents/skills/websocket-gateway/SKILL.md | 19000 |
| .agents/skills/websocket-gateway/references/implementation_detail.md | 15521 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | 12762 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | 30243 |
| .claude/skills/camera-frame-capture/SKILL.md | 16513 |
| .claude/skills/camera-frame-capture/references/implementation_detail.md | 31675 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | 14456 |
| .claude/skills/llm-guidance-orchestrator/references/implementation_detail.md | 20038 |
| .claude/skills/rag-knowledge-builder/SKILL.md | 8974 |
| .claude/skills/rag-knowledge-builder/references/implementation_detail.md | 7993 |
| .claude/skills/rag-realtime-search/SKILL.md | 9705 |
| .claude/skills/rag-realtime-search/references/implementation_detail.md | 12116 |
| .claude/skills/tts-voice-streamer/SKILL.md | 12273 |
| .claude/skills/tts-voice-streamer/references/implementation_detail.md | 7833 |
| .claude/skills/websocket-gateway/SKILL.md | 19000 |
| .claude/skills/websocket-gateway/references/implementation_detail.md | 15521 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | 12762 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | 30243 |
| docs/AGENTS.md | 7636 |
| docs/README.md | 7942 |
| docs/antigravity_agent_prompt__4_5_final.md | 13777 |
| docs/api_specification.md | 10352 |
| docs/architecture.md | 34534 |
| docs/behavior_and_risk_insight.md | 9026 |
| docs/code_quality_guide.md | 20916 |
| docs/course_codebase_guide.md | 111433 |
| docs/deployment_guide.md | 13504 |
| docs/dual_gemma4_latency_analysis.md | 5824 |
| docs/environment_variables.md | 12101 |
| docs/gemini_fallback_feasibility.md | 5076 |
| docs/git_branching_strategy.md | 5820 |
| docs/latency_impact_analysis.md | 6378 |
| docs/minchodan_design_note.md | 18724 |
| docs/pipeline_stage_design.md | 8566 |
| docs/stage2_capture_design.md | 22326 |
| docs/stage3_detection_design.md | 28119 |
| docs/stage4_5_data_replacement_guide.md | 6694 |
| docs/stage4_5_directory_guide.md | 7031 |
| docs/stage4_5_implementation_log.md | 7400 |
| docs/stage4_5_rag_design.md | 16629 |
| docs/stage4_5_test_guide.md | 7291 |
| docs/stage6_orchestration_design.md | 24372 |
| docs/test_specification.md | 17846 |
| docs/changelogs/README.md | 2544 |
| docs/changelogs/TEMPLATE.md | 772 |
| docs/changelogs/dg.md | 2148 |
| docs/changelogs/jh.md | 172 |
| docs/changelogs/jy.md | 2304 |
| docs/changelogs/kb.md | 28576 |
| docs/changelogs/th.md | 822 |

---

## 6. Python 파일

| 파일 | 크기(bytes) |
| --- | --- |
| scripts/download_pretrained_weights.py | 1753 |
| scripts/integration_test_pipeline.py | 6668 |
| scripts/project_scan.py | 14242 |
| scripts/slack_publisher.py | 8200 |
| scripts/verify_pretrained_weights.py | 2495 |
| server/main.py | 2525 |
| server/api/monitor.py | 2480 |
| server/bus/__init__.py | 168 |
| server/bus/producer.py | 1982 |
| server/bus/redis_client.py | 2597 |
| server/capture/__init__.py | 266 |
| server/capture/frame_decoder.py | 3973 |
| server/capture/stream_splitter.py | 4364 |
| server/detection/__init__.py | 842 |
| server/detection/bytetrack_tracker.py | 2837 |
| server/detection/config.py | 2850 |
| server/detection/detection_pipeline.py | 4894 |
| server/detection/detector_interface.py | 963 |
| server/detection/mock_detector.py | 1809 |
| server/detection/schemas.py | 1201 |
| server/detection/yolo_detector.py | 2946 |
| server/detection/yolo_segmentor.py | 2900 |
| server/detection/gates/__init__.py | 167 |
| server/detection/gates/reflex_gate.py | 1239 |
| server/detection/gates/surface_gate.py | 932 |
| server/mcp/gpu_monitor.py | 3762 |
| server/mcp/manager.py | 5812 |
| server/orchestration/__init__.py | 243 |
| server/orchestration/graph.py | 3159 |
| server/orchestration/llm_client_factory.py | 8304 |
| server/orchestration/state.py | 1088 |
| server/orchestration/nodes/__init__.py | 421 |
| server/orchestration/nodes/fallback_node.py | 896 |
| server/orchestration/nodes/l1_classifier.py | 1711 |
| server/orchestration/nodes/l2_generator.py | 4334 |
| server/orchestration/nodes/l3_validator.py | 2417 |
| server/rag/embedding_engine_factory.py | 4914 |
| server/rag/fallback.py | 3167 |
| server/rag/retriever.py | 5665 |
| server/rag/vector_db_factory.py | 3989 |
| server/rag/build/db_builder.py | 9347 |
| server/rag/build/dedup_phash.py | 2950 |
| server/rag/build/frame_extractor.py | 3446 |
| server/rag/build/gemini_captioner.py | 4031 |
| server/rag/shared/labels.py | 723 |
| tests/test_db_builder.py | 2134 |
| tests/test_dedup_phash.py | 1768 |
| tests/test_detection.py | 11852 |
| tests/test_e2e_pipeline.py | 3604 |
| tests/test_embedding_engine_factory.py | 1737 |
| tests/test_fallback.py | 1288 |
| tests/test_frame_decode.py | 12789 |
| tests/test_frame_extractor.py | 1726 |
| tests/test_gemini_captioner.py | 2048 |
| tests/test_langgraph.py | 8030 |
| tests/test_mcp_gpu.py | 2556 |
| tests/test_mcp_integration.py | 2340 |
| tests/test_retriever.py | 3068 |
| tests/test_vector_db_factory.py | 1614 |

---

## 7. 키워드 기반 관련 파일

### yolo

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | yolo, detect | 66 |
| .gitignore | detect, train | 243 |
| AGENTS.md | yolo, ultralytics, detect, train | 184 |
| CLAUDE.md | yolo, ultralytics, detect, train | 170 |
| Directory_Structure.md | yolo, detect, predict, train | 149 |
| README.md | yolo, ultralytics, detect, train | 355 |
| SCRIPT_GENERATION_PROMPT.md | yolo, detect | 381 |
| SKILLS.md | yolo, detect, train | 158 |
| pyproject.toml | ultralytics, train | 158 |
| requirements.txt | ultralytics | 21 |
| docs/AGENTS.md | yolo, ultralytics, detect, train | 138 |
| docs/README.md | yolo, detect | 78 |
| docs/antigravity_agent_prompt__4_5_final.md | yolo, detect | 188 |
| docs/api_specification.md | detect, bbox, confidence | 283 |
| docs/architecture.md | yolo, ultralytics, detect, predict, train, bbox, confidence | 512 |
| docs/behavior_and_risk_insight.md | yolo, detect, bbox | 91 |
| docs/code_quality_guide.md | yolo, ultralytics, detect | 654 |
| docs/course_codebase_guide.md | yolo, ultralytics, detect, predict, train, bbox, class_id, confidence | 2986 |
| docs/deployment_guide.md | detect | 328 |
| docs/dual_gemma4_latency_analysis.md | yolo, predict | 86 |
| docs/environment_variables.md | yolo, detect | 176 |
| docs/git_branching_strategy.md | yolo, detect | 144 |
| docs/latency_impact_analysis.md | yolo, detect | 106 |
| docs/minchodan_design_note.md | yolo, ultralytics, detect, predict, bbox, confidence | 212 |
| docs/pipeline_stage_design.md | yolo, detect, predict | 176 |
| docs/stage2_capture_design.md | yolo, detect | 447 |
| docs/stage3_detection_design.md | yolo, ultralytics, detect, predict, bbox, confidence | 578 |
| docs/stage4_5_directory_guide.md | yolo | 60 |
| docs/stage4_5_implementation_log.md | yolo, detect | 93 |
| docs/stage4_5_rag_design.md | yolo, detect | 342 |
| docs/stage4_5_test_guide.md | yolo | 88 |
| docs/stage6_orchestration_design.md | yolo, detect, predict, bbox, confidence | 514 |
| docs/test_specification.md | yolo, detect | 330 |
| scripts/download_pretrained_weights.py | yolo, ultralytics, detect | 52 |
| scripts/integration_test_pipeline.py | yolo, detect, bbox, confidence | 151 |
| scripts/postwork.bat | detect | 338 |
| scripts/postwork.ps1 | detect | 285 |
| scripts/postwork.sh | detect | 301 |
| scripts/prework.bat | yolo, detect | 247 |
| scripts/prework.ps1 | yolo, detect | 209 |
| scripts/prework.sh | yolo, detect | 222 |
| scripts/project_scan.py | yolo, ultralytics, detect, predict, train, bbox, class_id, confidence | 468 |
| scripts/verify_pretrained_weights.py | yolo, detect, predict | 69 |
| tests/test_detection.py | yolo, detect, predict, bbox, confidence | 332 |
| tests/test_e2e_pipeline.py | yolo, detect, bbox, confidence | 98 |
| tests/test_langgraph.py | detect | 202 |
| tests/test_retriever.py | detect, confidence | 85 |
| docs/changelogs/README.md | detect | 69 |
| docs/changelogs/kb.md | yolo, detect, train, bbox, confidence | 267 |
| server/bus/producer.py | detect, bbox, confidence | 66 |
| server/detection/__init__.py | yolo, detect, bbox | 30 |
| server/detection/bytetrack_tracker.py | yolo, ultralytics, detect, bbox | 78 |
| server/detection/config.py | yolo, detect | 84 |
| server/detection/detection_pipeline.py | detect, predict | 149 |
| server/detection/detector_interface.py | detect, predict | 32 |
| server/detection/mock_detector.py | detect, predict, bbox, confidence | 61 |
| server/detection/schemas.py | detect, bbox, confidence | 56 |
| server/detection/yolo_detector.py | yolo, ultralytics, detect, predict, bbox, confidence | 86 |
| server/detection/yolo_segmentor.py | yolo, ultralytics, detect, predict | 86 |
| server/orchestration/llm_client_factory.py | predict | 207 |
| server/orchestration/state.py | detect | 35 |
| server/rag/fallback.py | yolo | 73 |
| server/rag/retriever.py | yolo, detect, bbox, confidence | 145 |
| .agents/skills/camera-frame-capture/SKILL.md | yolo, detect | 391 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | yolo, detect, predict | 359 |
| .agents/skills/rag-knowledge-builder/SKILL.md | yolo, detect | 241 |
| .agents/skills/rag-realtime-search/SKILL.md | yolo, detect | 257 |
| .agents/skills/websocket-gateway/SKILL.md | detect | 534 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | yolo, ultralytics, detect, predict, bbox, confidence | 332 |
| .claude/skills/camera-frame-capture/SKILL.md | yolo, detect | 391 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | yolo, detect, predict | 359 |
| .claude/skills/rag-knowledge-builder/SKILL.md | yolo, detect | 241 |
| .claude/skills/rag-realtime-search/SKILL.md | yolo, detect | 257 |
| .claude/skills/websocket-gateway/SKILL.md | detect | 534 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | yolo, ultralytics, detect, predict, bbox, confidence | 332 |
| server/detection/gates/__init__.py | detect | 5 |
| server/detection/gates/reflex_gate.py | detect, bbox | 44 |
| server/detection/gates/surface_gate.py | detect | 38 |
| server/orchestration/nodes/l1_classifier.py | detect | 45 |
| server/orchestration/nodes/l2_generator.py | detect | 113 |

### langchain

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | langchain, chain | 66 |
| .gitignore | langchain, langgraph, agent, chain | 243 |
| AGENTS.md | langchain, langgraph, agent, chain | 184 |
| CLAUDE.md | langchain, langgraph, agent, chain | 170 |
| Directory_Structure.md | langgraph | 149 |
| README.md | langchain, langgraph, agent, chain | 355 |
| SCRIPT_GENERATION_PROMPT.md | langgraph, agent, Runnable | 381 |
| SKILLS.md | langgraph, agent | 158 |
| pyproject.toml | langgraph, agent, tool | 158 |
| requirements.txt | langchain, langgraph, chain | 21 |
| docker/docker-compose.yml | tool | 79 |
| docs/AGENTS.md | langchain, langgraph, agent, chain | 138 |
| docs/README.md | langgraph, agent | 78 |
| docs/antigravity_agent_prompt__4_5_final.md | langchain, langgraph, chain | 188 |
| docs/api_specification.md | langgraph | 283 |
| docs/architecture.md | langchain, langgraph, chain | 512 |
| docs/behavior_and_risk_insight.md | langchain, langgraph, chain | 91 |
| docs/code_quality_guide.md | langchain, agent, tool, chain, ChatOpenAI | 654 |
| docs/course_codebase_guide.md | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 2986 |
| docs/deployment_guide.md | langchain, tool, chain | 328 |
| docs/dual_gemma4_latency_analysis.md | langgraph | 86 |
| docs/environment_variables.md | langchain, langgraph, chain | 176 |
| docs/git_branching_strategy.md | langchain, langgraph, chain | 144 |
| docs/latency_impact_analysis.md | langgraph | 106 |
| docs/minchodan_design_note.md | langchain, langgraph, chain | 212 |
| docs/pipeline_stage_design.md | langgraph | 176 |
| docs/stage2_capture_design.md | langgraph, agent | 447 |
| docs/stage3_detection_design.md | langgraph, agent | 578 |
| docs/stage4_5_implementation_log.md | langchain, chain | 93 |
| docs/stage4_5_rag_design.md | langchain, langgraph, agent, chain | 342 |
| docs/stage4_5_test_guide.md | langchain, chain | 88 |
| docs/stage6_orchestration_design.md | langchain, langgraph, agent, chain, ChatOpenAI | 514 |
| docs/test_specification.md | langgraph | 330 |
| scripts/postwork.bat | langgraph | 338 |
| scripts/postwork.ps1 | langgraph | 285 |
| scripts/postwork.sh | langgraph | 301 |
| scripts/prework.bat | langgraph, agent | 247 |
| scripts/prework.ps1 | langgraph, agent | 209 |
| scripts/prework.sh | langgraph, agent | 222 |
| scripts/project_scan.py | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 468 |
| scripts/slack_publisher.py | tool | 223 |
| tests/test_frame_decode.py | langgraph | 348 |
| tests/test_langgraph.py | langgraph | 202 |
| tests/test_retriever.py | langchain, chain | 85 |
| docs/changelogs/kb.md | langchain, langgraph, agent, chain | 267 |
| server/orchestration/graph.py | langgraph | 98 |
| server/orchestration/llm_client_factory.py | langchain, chain | 207 |
| server/orchestration/state.py | langgraph | 35 |
| server/rag/embedding_engine_factory.py | langchain, chain | 133 |
| server/rag/retriever.py | langchain, chain | 145 |
| server/rag/vector_db_factory.py | langchain, chain | 101 |
| .agents/skills/camera-frame-capture/SKILL.md | langgraph | 391 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | langchain, langgraph, chain, ChatOpenAI | 359 |
| .agents/skills/rag-knowledge-builder/SKILL.md | langchain, chain | 241 |
| .agents/skills/rag-realtime-search/SKILL.md | langchain, langgraph, chain | 257 |
| .agents/skills/tts-voice-streamer/SKILL.md | langgraph | 337 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | langgraph | 332 |
| .claude/skills/camera-frame-capture/SKILL.md | langgraph | 391 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | langchain, langgraph, chain, ChatOpenAI | 359 |
| .claude/skills/rag-knowledge-builder/SKILL.md | langchain, chain | 241 |
| .claude/skills/rag-realtime-search/SKILL.md | langchain, langgraph, chain | 257 |
| .claude/skills/tts-voice-streamer/SKILL.md | langgraph | 337 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | langgraph | 332 |
| server/orchestration/nodes/fallback_node.py | langgraph | 29 |
| server/orchestration/nodes/l1_classifier.py | langgraph | 45 |
| server/orchestration/nodes/l2_generator.py | langchain, langgraph, chain | 113 |
| server/orchestration/nodes/l3_validator.py | langgraph | 73 |
| server/rag/build/db_builder.py | langchain, chain | 221 |
| server/rag/build/gemini_captioner.py | langchain, chain | 102 |
| .agents/skills/llm-guidance-orchestrator/references/implementation_detail.md | langgraph | 561 |
| .agents/skills/rag-knowledge-builder/references/implementation_detail.md | langchain, chain | 216 |
| .agents/skills/rag-realtime-search/references/implementation_detail.md | langgraph, tool | 358 |
| .agents/skills/websocket-gateway/references/implementation_detail.md | agent | 449 |
| .claude/skills/llm-guidance-orchestrator/references/implementation_detail.md | langgraph | 561 |
| .claude/skills/rag-knowledge-builder/references/implementation_detail.md | langchain, chain | 216 |
| .claude/skills/rag-realtime-search/references/implementation_detail.md | langgraph, tool | 358 |
| .claude/skills/websocket-gateway/references/implementation_detail.md | agent | 449 |

### fastapi

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .gitignore | fastapi, uvicorn | 243 |
| AGENTS.md | fastapi, uvicorn | 184 |
| CLAUDE.md | fastapi, uvicorn | 170 |
| Directory_Structure.md | fastapi, APIRouter | 149 |
| README.md | fastapi, uvicorn | 355 |
| SCRIPT_GENERATION_PROMPT.md | fastapi | 381 |
| SKILLS.md | fastapi | 158 |
| pyproject.toml | fastapi | 158 |
| requirements.txt | fastapi, uvicorn | 21 |
| docker/Dockerfile | fastapi, uvicorn | 26 |
| docker/docker-compose.yml | fastapi | 79 |
| docker/linux_docker_start.sh | fastapi | 205 |
| docker/macos_docker_start.sh | fastapi | 214 |
| docker/windows_docker_start.bat | fastapi | 117 |
| docs/AGENTS.md | fastapi, uvicorn | 138 |
| docs/README.md | fastapi | 78 |
| docs/architecture.md | fastapi, APIRouter, uvicorn | 512 |
| docs/course_codebase_guide.md | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 2986 |
| docs/deployment_guide.md | fastapi, uvicorn | 328 |
| docs/minchodan_design_note.md | fastapi, APIRouter, uvicorn | 212 |
| docs/pipeline_stage_design.md | fastapi, APIRouter | 176 |
| docs/stage2_capture_design.md | fastapi | 447 |
| docs/stage3_detection_design.md | fastapi, BaseModel | 578 |
| docs/test_specification.md | fastapi | 330 |
| scripts/postwork.bat | fastapi | 338 |
| scripts/postwork.ps1 | fastapi | 285 |
| scripts/postwork.sh | fastapi | 301 |
| scripts/project_scan.py | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 468 |
| server/main.py | fastapi | 81 |
| tests/test_mcp_integration.py | fastapi | 64 |
| docs/changelogs/kb.md | fastapi, uvicorn | 267 |
| server/api/monitor.py | fastapi, APIRouter | 65 |
| server/detection/schemas.py | BaseModel | 56 |
| server/mcp/manager.py | fastapi | 144 |
| .agents/skills/camera-frame-capture/SKILL.md | fastapi | 391 |
| .agents/skills/tts-voice-streamer/SKILL.md | fastapi, uvicorn | 337 |
| .agents/skills/websocket-gateway/SKILL.md | fastapi, APIRouter, uvicorn, BaseModel | 534 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | BaseModel | 332 |
| .claude/skills/camera-frame-capture/SKILL.md | fastapi | 391 |
| .claude/skills/tts-voice-streamer/SKILL.md | fastapi, uvicorn | 337 |
| .claude/skills/websocket-gateway/SKILL.md | fastapi, APIRouter, uvicorn, BaseModel | 534 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | BaseModel | 332 |
| .agents/skills/camera-frame-capture/references/implementation_detail.md | fastapi | 785 |
| .agents/skills/llm-guidance-orchestrator/references/implementation_detail.md | fastapi, APIRouter | 561 |
| .agents/skills/rag-realtime-search/references/implementation_detail.md | fastapi | 358 |
| .agents/skills/websocket-gateway/references/implementation_detail.md | fastapi | 449 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | fastapi, BaseModel | 930 |
| .claude/skills/camera-frame-capture/references/implementation_detail.md | fastapi | 785 |
| .claude/skills/llm-guidance-orchestrator/references/implementation_detail.md | fastapi, APIRouter | 561 |
| .claude/skills/rag-realtime-search/references/implementation_detail.md | fastapi | 358 |
| .claude/skills/websocket-gateway/references/implementation_detail.md | fastapi | 449 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | fastapi, BaseModel | 930 |

### openai

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | OpenAI, OPENAI_API_KEY | 66 |
| .gitignore | OpenAI | 243 |
| README.md | OpenAI, OPENAI_API_KEY | 355 |
| docs/README.md | OpenAI | 78 |
| docs/architecture.md | OpenAI, OPENAI_API_KEY | 512 |
| docs/code_quality_guide.md | OpenAI, OPENAI_API_KEY | 654 |
| docs/course_codebase_guide.md | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 2986 |
| docs/environment_variables.md | OpenAI, OPENAI_API_KEY | 176 |
| docs/gemini_fallback_feasibility.md | OpenAI | 80 |
| docs/minchodan_design_note.md | OpenAI | 212 |
| docs/pipeline_stage_design.md | OpenAI | 176 |
| docs/stage4_5_data_replacement_guide.md | OpenAI | 92 |
| docs/stage4_5_rag_design.md | OpenAI | 342 |
| docs/stage6_orchestration_design.md | OpenAI, OPENAI_API_KEY | 514 |
| docs/test_specification.md | OpenAI | 330 |
| scripts/project_scan.py | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 468 |
| tests/test_mcp_gpu.py | OpenAI, OPENAI_API_KEY | 78 |
| docs/changelogs/kb.md | OpenAI | 267 |
| server/api/monitor.py | responses | 65 |
| server/bus/redis_client.py | responses | 88 |
| server/mcp/gpu_monitor.py | OpenAI | 92 |
| server/mcp/manager.py | responses | 144 |
| server/orchestration/llm_client_factory.py | OpenAI, OPENAI_API_KEY | 207 |
| server/rag/embedding_engine_factory.py | OpenAI | 133 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 359 |
| .agents/skills/tts-voice-streamer/SKILL.md | OpenAI | 337 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 359 |
| .claude/skills/tts-voice-streamer/SKILL.md | OpenAI | 337 |
| server/orchestration/nodes/l2_generator.py | OpenAI | 113 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |

### dataset

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | frame | 66 |
| .gitignore | dataset, images, json | 243 |
| AGENTS.md | labels, frame | 184 |
| CLAUDE.md | labels, frame | 170 |
| Directory_Structure.md | dataset, images, labels, json, frame | 149 |
| README.md | dataset, json, frame | 355 |
| SCRIPT_GENERATION_PROMPT.md | frame | 381 |
| SKILLS.md | labels, frame | 158 |
| opencode.json | json | 10 |
| pyproject.toml | annotation | 158 |
| docker/windows_docker_start.bat | images | 117 |
| docs/AGENTS.md | labels, frame | 138 |
| docs/antigravity_agent_prompt__4_5_final.md | labels, frame | 188 |
| docs/api_specification.md | json, frame | 283 |
| docs/architecture.md | json, frame | 512 |
| docs/behavior_and_risk_insight.md | frame | 91 |
| docs/code_quality_guide.md | json, frame | 654 |
| docs/course_codebase_guide.md | dataset, images, labels, json, frame | 2986 |
| docs/deployment_guide.md | json | 328 |
| docs/environment_variables.md | json, frame | 176 |
| docs/latency_impact_analysis.md | json | 106 |
| docs/minchodan_design_note.md | json, frame | 212 |
| docs/stage2_capture_design.md | json, frame | 447 |
| docs/stage3_detection_design.md | json, frame | 578 |
| docs/stage4_5_data_replacement_guide.md | frame | 92 |
| docs/stage4_5_directory_guide.md | labels, frame | 60 |
| docs/stage4_5_implementation_log.md | labels, frame | 93 |
| docs/stage4_5_rag_design.md | labels, frame | 342 |
| docs/stage4_5_test_guide.md | frame | 88 |
| docs/stage6_orchestration_design.md | json | 514 |
| docs/test_specification.md | json, frame | 330 |
| scripts/integration_test_pipeline.py | frame | 151 |
| scripts/postwork.bat | frame | 338 |
| scripts/postwork.ps1 | frame | 285 |
| scripts/postwork.sh | frame | 301 |
| scripts/prework.bat | frame | 247 |
| scripts/prework.ps1 | frame | 209 |
| scripts/prework.sh | frame | 222 |
| scripts/project_scan.py | dataset, data.yaml, images, labels, json, annotation, frame | 468 |
| scripts/slack_publisher.py | json | 223 |
| scripts/verify_pretrained_weights.py | frame | 69 |
| tests/test_db_builder.py | frame | 69 |
| tests/test_detection.py | frame | 332 |
| tests/test_e2e_pipeline.py | labels, frame | 98 |
| tests/test_fallback.py | labels | 41 |
| tests/test_frame_decode.py | frame | 348 |
| tests/test_frame_extractor.py | frame | 55 |
| tests/test_mcp_integration.py | json | 64 |
| tests/test_retriever.py | labels, json | 85 |
| docs/changelogs/dg.md | labels, frame | 20 |
| docs/changelogs/kb.md | json, frame | 267 |
| docs/changelogs/th.md | json | 16 |
| server/api/monitor.py | json | 65 |
| server/bus/producer.py | json, annotation | 66 |
| server/capture/__init__.py | frame | 10 |
| server/capture/frame_decoder.py | frame | 123 |
| server/capture/stream_splitter.py | frame | 114 |
| server/detection/bytetrack_tracker.py | json | 78 |
| server/detection/config.py | frame | 84 |
| server/detection/detection_pipeline.py | frame | 149 |
| server/detection/detector_interface.py | frame | 32 |
| server/detection/mock_detector.py | frame | 61 |
| server/detection/yolo_detector.py | frame | 86 |
| server/detection/yolo_segmentor.py | frame | 86 |
| server/mcp/manager.py | json | 144 |
| server/orchestration/llm_client_factory.py | json | 207 |
| server/rag/fallback.py | labels | 73 |
| server/rag/retriever.py | labels, json | 145 |
| .agents/skills/camera-frame-capture/SKILL.md | frame | 391 |
| .agents/skills/rag-knowledge-builder/SKILL.md | images, json, frame | 241 |
| .agents/skills/tts-voice-streamer/SKILL.md | json | 337 |
| .agents/skills/websocket-gateway/SKILL.md | json, frame | 534 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | json, frame | 332 |
| .claude/skills/camera-frame-capture/SKILL.md | frame | 391 |
| .claude/skills/rag-knowledge-builder/SKILL.md | images, json, frame | 241 |
| .claude/skills/tts-voice-streamer/SKILL.md | json | 337 |
| .claude/skills/websocket-gateway/SKILL.md | json, frame | 534 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | json, frame | 332 |
| server/detection/gates/reflex_gate.py | frame | 44 |
| server/detection/gates/surface_gate.py | frame | 38 |

---

## 8. 다음 작업 제안

| 순서 | 작업 |
| --- | --- |
| 1 | YOLO 관련 파일을 열어 실제 탐지/추론 구조와 모델 경로를 확인합니다. |
| 2 | LangChain/LangGraph 관련 파일을 열어 탐지 JSON이 연결될 입력 스키마를 확인합니다. |
| 3 | 데이터셋 원본 폴더를 별도 스캔하여 라벨 형식과 YOLO 변환 가능성을 판단합니다. |
| 4 | 확인된 라벨 형식 기준으로 class_mapping.json과 변환 계획을 작성합니다. |
