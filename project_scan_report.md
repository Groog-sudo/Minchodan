# 프로젝트 스캔 보고서

> **작성일**: 2026-07-06
> **버전**: v0.1.0
> **대상 루트**: `C:\dev_task\workspace\Project\finally_project\AI_GilDang\Minchodan`

---

## 1. 요약

| 항목 | 값 |
| --- | --- |
| 전체 파일 수 | 84016 |
| 문서 파일 수 | 41926 |
| Python 파일 수 | 101 |

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
│       ├── xcode-build-management/
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
│   ├── android/
│   │   ├── app/
│   │   ├── gradle/
│   │   ├── .gitignore
│   │   ├── build.gradle
│   │   ├── gradle.properties
│   │   ├── gradlew
│   │   ├── gradlew.bat
│   │   └── settings.gradle
│   ├── assets/
│   │   └── models/
│   ├── ios/
│   │   ├── Minchodan/
│   │   ├── Minchodan.xcodeproj/
│   │   ├── Minchodan.xcworkspace/
│   │   ├── segmentation.mlpackage/
│   │   ├── .gitignore
│   │   ├── .xcode.env
│   │   ├── CoreMLInferenceBridge.mm
│   │   ├── CoreMLInferenceBridge.swift
│   │   ├── Podfile
│   │   ├── Podfile.lock
│   │   └── Podfile.properties.json
│   ├── src/
│   │   ├── components/
│   │   ├── config/
│   │   ├── hooks/
│   │   ├── inference/
│   │   ├── services/
│   │   └── types/
│   ├── .gitignore
│   ├── app.json
│   ├── App.tsx
│   ├── index.ts
│   ├── metro.config.js
│   ├── package-lock.json
│   ├── package.json
│   └── tsconfig.json
├── data/
│   └── raw/
│       └── aihub_walk_sample/
├── docker/
│   ├── .dockerignore
│   ├── docker-compose.macos.yml
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
│   ├── design/
│   │   ├── api_specification.md
│   │   ├── architecture.md
│   │   ├── backend_db_architecture.md
│   │   ├── behavior_and_risk_insight.md
│   │   ├── minchodan_design_note.md
│   │   ├── pipeline_stage_design.md
│   │   └── reflex_audio_specification.md
│   ├── dev-guides/
│   │   ├── antigravity_agent_prompt__4_5_final.md
│   │   ├── course_codebase_guide.md
│   │   ├── llm_collaboration_workflow.md
│   │   └── 신규_설계서_예시_2.md
│   ├── mobile/
│   │   ├── mobile_android_implementation_plan.md
│   │   ├── mobile_app_implementation_plan.md
│   │   ├── mobile_ios_implementation_plan.md
│   │   └── ondevice_inference_engine_isolation_plan.md
│   ├── ops/
│   │   ├── ai_model_hardware_setup.md
│   │   ├── code_quality_guide.md
│   │   ├── deployment_guide.md
│   │   ├── environment_variables.md
│   │   ├── git_branching_strategy.md
│   │   ├── mobile_build_troubleshooting.md
│   │   ├── ondevice_coreml_benchmark.md
│   │   ├── redis_streams_schema.md
│   │   ├── test_specification.md
│   │   └── wireless_test_guide.md
│   ├── research/
│   │   ├── dual_gemma4_latency_analysis.md
│   │   ├── gemini_fallback_feasibility.md
│   │   ├── latency_impact_analysis.md
│   │   ├── post_mvp_hybrid_roadmap.md
│   │   ├── post_mvp_ondevice_feasibility.md
│   │   └── yolo_tts_mvp_next_steps.md
│   ├── stage-guides/
│   │   ├── stage1_websocket_design.md
│   │   ├── stage2_capture_design.md
│   │   ├── stage3_detection_design.md
│   │   ├── stage4_5_data_replacement_guide.md
│   │   ├── stage4_5_directory_guide.md
│   │   ├── stage4_5_implementation_log.md
│   │   ├── stage4_5_rag_design.md
│   │   ├── stage4_5_test_guide.md
│   │   ├── stage6_orchestration_design.md
│   │   └── stage7_tts_design.md
│   ├── AGENTS.md
│   └── README.md
├── scripts/
│   ├── bench_ondevice.py
│   ├── convert_aihub_seg_to_yolo.py
│   ├── convert_yolo_to_coreml.py
│   ├── download_pretrained_weights.py
│   ├── export_mobile.py
│   ├── export_tflite.py
│   ├── inspect_aihub_bbox_xml.py
│   ├── integration_test_pipeline.py
│   ├── postwork.bat
│   ├── postwork.ps1
│   ├── postwork.sh
│   ├── prepare_aihub_yolo_detection.py
│   ├── prework.bat
│   ├── prework.ps1
│   ├── prework.sh
│   ├── project_scan.py
│   ├── resolve_conflicts.py
│   ├── run_desktop_full_training.py
│   ├── run_yolo_tts_demo.py
│   ├── scan_aihub_walk_dataset.py
│   ├── slack_publisher.py
│   ├── verify_gpu.py
│   └── verify_pretrained_weights.py
├── server/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── admin_router.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── heartbeat.py
│   │   ├── monitor.py
│   │   ├── schemas.py
│   │   ├── session_manager.py
│   │   ├── user_router.py
│   │   └── ws_router.py
│   ├── bus/
│   │   ├── __init__.py
│   │   ├── producer.py
│   │   └── redis_client.py
│   ├── capture/
│   │   ├── __init__.py
│   │   ├── frame_decoder.py
│   │   └── stream_splitter.py
│   ├── db/
│   │   ├── base.py
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── repositories.py
│   │   ├── schema.sql
│   │   ├── schemas.py
│   │   └── security.py
│   ├── detection/
│   │   ├── gates/
│   │   ├── __init__.py
│   │   ├── bytetrack_tracker.py
│   │   ├── config.py
│   │   ├── consumer.py
│   │   ├── detection_pipeline.py
│   │   ├── detector_interface.py
│   │   ├── direction.py
│   │   ├── mock_detector.py
│   │   ├── risk_rules.py
│   │   ├── schemas.py
│   │   ├── yolo_code_review.md
│   │   ├── yolo_detector.py
│   │   └── yolo_segmentor.py
│   ├── mcp/
│   │   ├── gpu_monitor.py
│   │   └── manager.py
│   ├── models/
│   │   ├── piper/
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
│   ├── services/
│   │   ├── admin_service.py
│   │   └── user_service.py
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── realtime_tts.py
│   │   ├── reflex_clip_sender.py
│   │   ├── suppressor.py
│   │   └── tts_service.py
│   └── main.py
├── tests/
│   ├── test_api_ws.py
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
│   ├── test_vector_db_factory.py
│   └── test_ws_echo.py
├── training/
│   ├── configs/
│   │   ├── aihub_yolo_detection.yaml
│   │   └── aihub_yolo_segmentation.yaml
│   ├── datasets/
│   │   ├── detection/
│   │   └── segmentation/
│   ├── train_common.py
│   ├── train_detection.py
│   └── train_segmentation.py
├── .env
├── .env.example
├── .gitignore
├── .jscpd.json
├── .pre-commit-config.yaml
├── AGENTS.md
├── ai_prompt_context.md
├── CLAUDE.md
├── Directory_Structure.md
├── ios_env_setup.zip
├── Minchodan DB.session.sql
├── opencode.json
├── project_scan_verification.md
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── SCRIPT_GENERATION_PROMPT.md
├── SKILLS.md
├── yolo26n.pt
└── yolov8n-seg.pt
```

---

## 3. 핵심 파일

| 파일명 | 발견 경로 |
| --- | --- |
| .env.example | .env.example |
| README.md | README.md, docs/README.md, docs/changelogs/README.md |
| package.json | client/package.json |
| pyproject.toml | pyproject.toml |
| requirements.txt | requirements.txt |

---

## 4. 확장자 통계

| 확장자 | 파일 수 |
| --- | --- |
| .txt | 41837 |
| .jpg | 38587 |
| .png | 3251 |
| .py | 101 |
| .md | 89 |
| .webp | 25 |
| .ts | 19 |
| .json | 14 |
| .xml | 10 |
| (no extension) | 9 |
| .cache | 6 |
| .bat | 4 |
| .pt | 4 |
| .sh | 4 |
| .tflite | 4 |
| .tsx | 4 |
| .bin | 3 |
| .gradle | 3 |
| .mlmodel | 3 |
| .swift | 3 |
| .yaml | 3 |
| .yml | 3 |
| .kt | 2 |
| .mm | 2 |
| .onnx | 2 |
| .plist | 2 |
| .properties | 2 |
| .ps1 | 2 |
| .sql | 2 |
| .entitlements | 1 |

---

## 5. 문서 파일

| 파일 | 크기(bytes) |
| --- | --- |
| AGENTS.md | 14741 |
| CLAUDE.md | 11326 |
| Directory_Structure.md | 9849 |
| README.md | 19527 |
| SCRIPT_GENERATION_PROMPT.md | 15727 |
| SKILLS.md | 10141 |
| ai_prompt_context.md | 0 |
| project_scan_verification.md | 1710 |
| requirements-dev.txt | 239 |
| requirements.txt | 3042 |
| .agents/skills/camera-frame-capture/SKILL.md | 18234 |
| .agents/skills/camera-frame-capture/references/implementation_detail.md | 31675 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | 14456 |
| .agents/skills/llm-guidance-orchestrator/references/implementation_detail.md | 20038 |
| .agents/skills/rag-knowledge-builder/SKILL.md | 8974 |
| .agents/skills/rag-knowledge-builder/references/implementation_detail.md | 7993 |
| .agents/skills/rag-realtime-search/SKILL.md | 9705 |
| .agents/skills/rag-realtime-search/references/implementation_detail.md | 12116 |
| .agents/skills/tts-voice-streamer/SKILL.md | 12596 |
| .agents/skills/tts-voice-streamer/references/implementation_detail.md | 7833 |
| .agents/skills/websocket-gateway/SKILL.md | 19000 |
| .agents/skills/websocket-gateway/references/implementation_detail.md | 15521 |
| .agents/skills/xcode-build-management/SKILL.md | 6874 |
| .agents/skills/xcode-build-management/references/implementation_detail.md | 7112 |
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
| .claude/skills/tts-voice-streamer/SKILL.md | 12249 |
| .claude/skills/tts-voice-streamer/references/implementation_detail.md | 7833 |
| .claude/skills/websocket-gateway/SKILL.md | 19000 |
| .claude/skills/websocket-gateway/references/implementation_detail.md | 15521 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | 12762 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | 30243 |
| docs/AGENTS.md | 7656 |
| docs/README.md | 18361 |
| docs/changelogs/README.md | 2516 |
| docs/changelogs/TEMPLATE.md | 772 |
| docs/changelogs/dg.md | 2148 |
| docs/changelogs/jh.md | 16320 |
| docs/changelogs/jy.md | 4641 |
| docs/changelogs/kb.md | 92436 |
| docs/changelogs/th.md | 17813 |
| docs/design/api_specification.md | 12775 |
| docs/design/architecture.md | 36670 |
| docs/design/backend_db_architecture.md | 4438 |
| docs/design/behavior_and_risk_insight.md | 9033 |
| docs/design/minchodan_design_note.md | 19342 |
| docs/design/pipeline_stage_design.md | 8566 |
| docs/design/reflex_audio_specification.md | 9888 |
| docs/dev-guides/antigravity_agent_prompt__4_5_final.md | 13777 |
| docs/dev-guides/course_codebase_guide.md | 111433 |
| docs/dev-guides/llm_collaboration_workflow.md | 10334 |
| docs/dev-guides/신규_설계서_예시_2.md | 14250 |
| docs/mobile/mobile_android_implementation_plan.md | 26858 |
| docs/mobile/mobile_app_implementation_plan.md | 28160 |
| docs/mobile/mobile_ios_implementation_plan.md | 33151 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | 38301 |
| docs/ops/ai_model_hardware_setup.md | 3491 |
| docs/ops/code_quality_guide.md | 20916 |
| docs/ops/deployment_guide.md | 13504 |
| docs/ops/environment_variables.md | 13074 |
| docs/ops/git_branching_strategy.md | 5799 |
| docs/ops/mobile_build_troubleshooting.md | 17030 |
| docs/ops/ondevice_coreml_benchmark.md | 10082 |
| docs/ops/redis_streams_schema.md | 3342 |
| docs/ops/test_specification.md | 18354 |
| docs/ops/wireless_test_guide.md | 12281 |
| docs/research/dual_gemma4_latency_analysis.md | 5824 |
| docs/research/gemini_fallback_feasibility.md | 5076 |
| docs/research/latency_impact_analysis.md | 6378 |
| docs/research/post_mvp_hybrid_roadmap.md | 23118 |
| docs/research/post_mvp_ondevice_feasibility.md | 6080 |
| docs/research/yolo_tts_mvp_next_steps.md | 6203 |
| docs/stage-guides/stage1_websocket_design.md | 4356 |
| docs/stage-guides/stage2_capture_design.md | 22326 |
| docs/stage-guides/stage3_detection_design.md | 28119 |
| docs/stage-guides/stage4_5_data_replacement_guide.md | 6692 |
| docs/stage-guides/stage4_5_directory_guide.md | 7031 |
| docs/stage-guides/stage4_5_implementation_log.md | 7399 |
| docs/stage-guides/stage4_5_rag_design.md | 16497 |
| docs/stage-guides/stage4_5_test_guide.md | 7291 |
| docs/stage-guides/stage6_orchestration_design.md | 24372 |
| docs/stage-guides/stage7_tts_design.md | 10615 |
| server/detection/yolo_code_review.md | 10625 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026951.txt | 230 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026953.txt | 233 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026954.txt | 153 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026955.txt | 153 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026956.txt | 543 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026957.txt | 192 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026958.txt | 542 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026959.txt | 229 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026963.txt | 502 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026964.txt | 344 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026965.txt | 116 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026966.txt | 422 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026968.txt | 344 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026969.txt | 195 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026970.txt | 537 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026971.txt | 153 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026972.txt | 304 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026973.txt | 231 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026974.txt | 232 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026975.txt | 769 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026976.txt | 422 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026977.txt | 424 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026979.txt | 386 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026980.txt | 307 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026981.txt | 231 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026983.txt | 347 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026984.txt | 268 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026986.txt | 539 |
| training/datasets/detection/aihub_0820_26/labels/train/MP_SEL_B026987.txt | 272 |

---

## 6. Python 파일

| 파일 | 크기(bytes) |
| --- | --- |
| scripts/bench_ondevice.py | 7190 |
| scripts/convert_aihub_seg_to_yolo.py | 6995 |
| scripts/convert_yolo_to_coreml.py | 7426 |
| scripts/download_pretrained_weights.py | 1753 |
| scripts/export_mobile.py | 5413 |
| scripts/export_tflite.py | 1593 |
| scripts/inspect_aihub_bbox_xml.py | 11792 |
| scripts/integration_test_pipeline.py | 6668 |
| scripts/prepare_aihub_yolo_detection.py | 12688 |
| scripts/project_scan.py | 15033 |
| scripts/resolve_conflicts.py | 1933 |
| scripts/run_desktop_full_training.py | 6020 |
| scripts/run_yolo_tts_demo.py | 6859 |
| scripts/scan_aihub_walk_dataset.py | 13033 |
| scripts/slack_publisher.py | 8200 |
| scripts/verify_gpu.py | 1651 |
| scripts/verify_pretrained_weights.py | 2495 |
| server/main.py | 5093 |
| server/api/__init__.py | 39 |
| server/api/admin_router.py | 3267 |
| server/api/auth.py | 1177 |
| server/api/config.py | 1251 |
| server/api/heartbeat.py | 2337 |
| server/api/monitor.py | 2480 |
| server/api/schemas.py | 1987 |
| server/api/session_manager.py | 1733 |
| server/api/user_router.py | 2817 |
| server/api/ws_router.py | 7222 |
| server/bus/__init__.py | 168 |
| server/bus/producer.py | 1982 |
| server/bus/redis_client.py | 2597 |
| server/capture/__init__.py | 266 |
| server/capture/frame_decoder.py | 3973 |
| server/capture/stream_splitter.py | 4364 |
| server/db/base.py | 1352 |
| server/db/connection.py | 2533 |
| server/db/models.py | 11224 |
| server/db/repositories.py | 4168 |
| server/db/schemas.py | 4055 |
| server/db/security.py | 1340 |
| server/detection/__init__.py | 2048 |
| server/detection/bytetrack_tracker.py | 2837 |
| server/detection/config.py | 3082 |
| server/detection/consumer.py | 9417 |
| server/detection/detection_pipeline.py | 5078 |
| server/detection/detector_interface.py | 963 |
| server/detection/direction.py | 2227 |
| server/detection/mock_detector.py | 623 |
| server/detection/risk_rules.py | 5839 |
| server/detection/schemas.py | 1323 |
| server/detection/yolo_detector.py | 6415 |
| server/detection/yolo_segmentor.py | 4405 |
| server/detection/gates/__init__.py | 167 |
| server/detection/gates/reflex_gate.py | 4709 |
| server/detection/gates/surface_gate.py | 1268 |
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
| server/services/admin_service.py | 5056 |
| server/services/user_service.py | 3736 |
| server/tts/__init__.py | 635 |
| server/tts/realtime_tts.py | 2725 |
| server/tts/reflex_clip_sender.py | 6200 |
| server/tts/suppressor.py | 2877 |
| server/tts/tts_service.py | 9806 |
| tests/test_api_ws.py | 2203 |
| tests/test_db_builder.py | 2134 |
| tests/test_dedup_phash.py | 1768 |
| tests/test_detection.py | 12703 |
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
| tests/test_vector_db_factory.py | 1730 |
| tests/test_ws_echo.py | 5896 |
| training/train_common.py | 3664 |
| training/train_detection.py | 2146 |
| training/train_segmentation.py | 2039 |

---

## 7. 키워드 기반 관련 파일

### yolo

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | yolo, detect, train | 81 |
| .gitignore | yolo, detect, train | 276 |
| AGENTS.md | yolo, ultralytics, detect, train | 189 |
| CLAUDE.md | yolo, ultralytics, detect, train | 170 |
| Directory_Structure.md | yolo, detect, predict, train | 149 |
| README.md | yolo, ultralytics, detect, train | 359 |
| SCRIPT_GENERATION_PROMPT.md | yolo, detect | 381 |
| SKILLS.md | yolo, detect, train, bbox | 175 |
| pyproject.toml | ultralytics, train | 158 |
| requirements.txt | ultralytics | 152 |
| client/app.json | predict | 46 |
| client/package-lock.json | detect | 6730 |
| docs/AGENTS.md | yolo, ultralytics, detect, train | 138 |
| docs/README.md | yolo, detect | 204 |
| scripts/bench_ondevice.py | yolo, ultralytics, detect, predict | 224 |
| scripts/convert_aihub_seg_to_yolo.py | yolo, ultralytics, train, class_id | 204 |
| scripts/convert_yolo_to_coreml.py | yolo, ultralytics, detect, predict, confidence | 182 |
| scripts/download_pretrained_weights.py | yolo, ultralytics, detect | 52 |
| scripts/export_mobile.py | yolo, ultralytics, detect | 162 |
| scripts/export_tflite.py | yolo, ultralytics | 50 |
| scripts/inspect_aihub_bbox_xml.py | yolo, bbox | 360 |
| scripts/integration_test_pipeline.py | yolo, detect, bbox, confidence | 151 |
| scripts/postwork.bat | detect | 338 |
| scripts/postwork.ps1 | detect | 285 |
| scripts/postwork.sh | detect | 301 |
| scripts/prepare_aihub_yolo_detection.py | yolo, ultralytics, detect, train, class_id | 371 |
| scripts/prework.bat | yolo, detect | 247 |
| scripts/prework.ps1 | yolo, detect | 209 |
| scripts/prework.sh | yolo, detect | 222 |
| scripts/project_scan.py | yolo, ultralytics, detect, predict, train, bbox, class_id, confidence | 471 |
| scripts/run_desktop_full_training.py | yolo, detect, train, bbox | 170 |
| scripts/run_yolo_tts_demo.py | yolo, detect, predict, bbox, confidence | 208 |
| scripts/scan_aihub_walk_dataset.py | yolo | 361 |
| scripts/verify_pretrained_weights.py | yolo, detect, predict | 69 |
| server/main.py | detect | 136 |
| tests/test_api_ws.py | detect | 64 |
| tests/test_detection.py | yolo, detect, predict, bbox, confidence | 359 |
| tests/test_e2e_pipeline.py | yolo, detect, bbox, confidence | 98 |
| tests/test_langgraph.py | detect | 202 |
| tests/test_retriever.py | detect, confidence | 85 |
| tests/test_ws_echo.py | detect | 184 |
| training/train_common.py | yolo, ultralytics, train | 105 |
| training/train_detection.py | yolo, ultralytics, detect, train | 61 |
| training/train_segmentation.py | yolo, ultralytics, train | 59 |
| docs/changelogs/jh.md | detect | 189 |
| docs/changelogs/kb.md | yolo, ultralytics, detect, train, bbox, confidence | 818 |
| docs/changelogs/th.md | yolo, detect, predict, train, bbox | 209 |
| docs/design/api_specification.md | yolo, detect, bbox, confidence | 373 |
| docs/design/architecture.md | yolo, ultralytics, detect, predict, train, bbox, confidence | 544 |
| docs/design/behavior_and_risk_insight.md | yolo, detect, bbox | 91 |
| docs/design/minchodan_design_note.md | yolo, ultralytics, detect, predict, bbox, confidence | 215 |
| docs/design/pipeline_stage_design.md | yolo, detect, predict | 176 |
| docs/dev-guides/antigravity_agent_prompt__4_5_final.md | yolo, detect | 188 |
| docs/dev-guides/course_codebase_guide.md | yolo, ultralytics, detect, predict, train, bbox, class_id, confidence | 2986 |
| docs/dev-guides/llm_collaboration_workflow.md | yolo, detect, bbox, confidence | 168 |
| docs/dev-guides/신규_설계서_예시_2.md | yolo, detect, bbox | 235 |
| docs/mobile/mobile_android_implementation_plan.md | detect | 488 |
| docs/mobile/mobile_app_implementation_plan.md | yolo, detect | 583 |
| docs/mobile/mobile_ios_implementation_plan.md | yolo, detect, bbox | 598 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | yolo, ultralytics, detect, train, bbox, confidence | 573 |
| docs/ops/code_quality_guide.md | yolo, ultralytics, detect | 654 |
| docs/ops/deployment_guide.md | detect | 328 |
| docs/ops/environment_variables.md | yolo, detect | 183 |
| docs/ops/git_branching_strategy.md | yolo, detect | 144 |
| docs/ops/mobile_build_troubleshooting.md | detect, confidence | 223 |
| docs/ops/ondevice_coreml_benchmark.md | yolo, detect | 240 |
| docs/ops/redis_streams_schema.md | detect | 56 |
| docs/ops/test_specification.md | yolo, detect | 336 |
| docs/ops/wireless_test_guide.md | yolo, ultralytics, detect | 167 |
| docs/research/dual_gemma4_latency_analysis.md | yolo, predict | 86 |
| docs/research/latency_impact_analysis.md | yolo, detect | 106 |
| docs/research/post_mvp_hybrid_roadmap.md | yolo, ultralytics, detect, predict, bbox, confidence | 389 |
| docs/research/post_mvp_ondevice_feasibility.md | yolo, detect | 78 |
| docs/research/yolo_tts_mvp_next_steps.md | yolo, detect, train, bbox, confidence | 144 |
| docs/stage-guides/stage1_websocket_design.md | detect | 93 |
| docs/stage-guides/stage2_capture_design.md | yolo, detect | 447 |
| docs/stage-guides/stage3_detection_design.md | yolo, ultralytics, detect, predict, bbox, confidence | 578 |
| docs/stage-guides/stage4_5_directory_guide.md | yolo | 60 |
| docs/stage-guides/stage4_5_implementation_log.md | yolo, detect | 93 |
| docs/stage-guides/stage4_5_rag_design.md | yolo, detect | 342 |

### langchain

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | langchain, chain | 81 |
| .gitignore | langchain, langgraph, agent, chain | 276 |
| AGENTS.md | langchain, langgraph, agent, chain | 189 |
| CLAUDE.md | langchain, langgraph, agent, chain | 170 |
| Directory_Structure.md | langgraph | 149 |
| README.md | langchain, langgraph, agent, chain | 359 |
| SCRIPT_GENERATION_PROMPT.md | langgraph, agent, Runnable | 381 |
| SKILLS.md | langgraph, agent | 175 |
| pyproject.toml | langgraph, agent, tool | 158 |
| requirements.txt | langchain, langgraph, tool, chain | 152 |
| client/package-lock.json | agent, tool, chain | 6730 |
| docker/docker-compose.yml | tool | 79 |
| docs/AGENTS.md | langchain, langgraph, agent, chain | 138 |
| docs/README.md | langgraph, agent | 204 |
| scripts/convert_yolo_to_coreml.py | tool | 182 |
| scripts/export_tflite.py | agent | 50 |
| scripts/postwork.bat | langgraph | 338 |
| scripts/postwork.ps1 | langgraph | 285 |
| scripts/postwork.sh | langgraph | 301 |
| scripts/prework.bat | langgraph, agent | 247 |
| scripts/prework.ps1 | langgraph, agent | 209 |
| scripts/prework.sh | langgraph, agent | 222 |
| scripts/project_scan.py | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 471 |
| scripts/slack_publisher.py | tool | 223 |
| tests/test_frame_decode.py | langgraph | 348 |
| tests/test_langgraph.py | langgraph | 202 |
| tests/test_retriever.py | langchain, chain | 85 |
| docs/changelogs/kb.md | langchain, langgraph, agent, chain | 818 |
| docs/changelogs/th.md | agent | 209 |
| docs/design/api_specification.md | langgraph | 373 |
| docs/design/architecture.md | langchain, langgraph, chain | 544 |
| docs/design/behavior_and_risk_insight.md | langchain, langgraph, chain | 91 |
| docs/design/minchodan_design_note.md | langchain, langgraph, chain | 215 |
| docs/design/pipeline_stage_design.md | langgraph | 176 |
| docs/dev-guides/antigravity_agent_prompt__4_5_final.md | langchain, langgraph, chain | 188 |
| docs/dev-guides/course_codebase_guide.md | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 2986 |
| docs/dev-guides/llm_collaboration_workflow.md | agent | 168 |
| docs/mobile/mobile_android_implementation_plan.md | langgraph, agent | 488 |
| docs/mobile/mobile_app_implementation_plan.md | langgraph, agent | 583 |
| docs/mobile/mobile_ios_implementation_plan.md | langgraph, agent | 598 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | agent, tool | 573 |
| docs/ops/ai_model_hardware_setup.md | langgraph | 64 |
| docs/ops/code_quality_guide.md | langchain, agent, tool, chain, ChatOpenAI | 654 |
| docs/ops/deployment_guide.md | langchain, tool, chain | 328 |
| docs/ops/environment_variables.md | langchain, langgraph, chain | 183 |
| docs/ops/git_branching_strategy.md | langchain, langgraph, chain | 144 |
| docs/ops/mobile_build_troubleshooting.md | chain | 223 |
| docs/ops/redis_streams_schema.md | langgraph | 56 |
| docs/ops/test_specification.md | langgraph | 336 |
| docs/ops/wireless_test_guide.md | agent, tool, chain | 167 |
| docs/research/dual_gemma4_latency_analysis.md | langgraph | 86 |
| docs/research/latency_impact_analysis.md | langgraph | 106 |
| docs/research/post_mvp_hybrid_roadmap.md | langgraph, agent | 389 |
| docs/research/post_mvp_ondevice_feasibility.md | tool, chain | 78 |
| docs/research/yolo_tts_mvp_next_steps.md | langgraph, agent | 144 |
| docs/stage-guides/stage2_capture_design.md | langgraph, agent | 447 |
| docs/stage-guides/stage3_detection_design.md | langgraph, agent | 578 |
| docs/stage-guides/stage4_5_implementation_log.md | langchain, chain | 93 |
| docs/stage-guides/stage4_5_rag_design.md | langchain, langgraph, agent, chain | 342 |
| docs/stage-guides/stage4_5_test_guide.md | langchain, chain | 88 |
| docs/stage-guides/stage6_orchestration_design.md | langchain, langgraph, agent, chain, ChatOpenAI | 514 |
| docs/stage-guides/stage7_tts_design.md | langgraph, agent, tool | 232 |
| server/detection/yolo_code_review.md | langgraph, agent | 242 |
| server/orchestration/graph.py | langgraph | 98 |
| server/orchestration/llm_client_factory.py | langchain, chain | 207 |
| server/orchestration/state.py | langgraph | 35 |
| server/rag/embedding_engine_factory.py | langchain, chain | 133 |
| server/rag/retriever.py | langchain, chain | 145 |
| server/rag/vector_db_factory.py | langchain, chain | 101 |
| .agents/skills/camera-frame-capture/SKILL.md | langgraph | 409 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | langchain, langgraph, chain, ChatOpenAI | 359 |
| .agents/skills/rag-knowledge-builder/SKILL.md | langchain, chain | 241 |
| .agents/skills/rag-realtime-search/SKILL.md | langchain, langgraph, chain | 257 |
| .agents/skills/tts-voice-streamer/SKILL.md | langgraph | 338 |
| .agents/skills/xcode-build-management/SKILL.md | tool, chain | 155 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | langgraph | 332 |
| .claude/skills/camera-frame-capture/SKILL.md | langgraph | 391 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | langchain, langgraph, chain, ChatOpenAI | 359 |
| .claude/skills/rag-knowledge-builder/SKILL.md | langchain, chain | 241 |
| .claude/skills/rag-realtime-search/SKILL.md | langchain, langgraph, chain | 257 |

### fastapi

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .gitignore | fastapi, uvicorn | 276 |
| AGENTS.md | fastapi, uvicorn | 189 |
| CLAUDE.md | fastapi, uvicorn | 170 |
| Directory_Structure.md | fastapi, APIRouter | 149 |
| README.md | fastapi, uvicorn | 359 |
| SCRIPT_GENERATION_PROMPT.md | fastapi | 381 |
| SKILLS.md | fastapi | 175 |
| pyproject.toml | fastapi | 158 |
| requirements.txt | fastapi, uvicorn | 152 |
| docker/Dockerfile | fastapi, uvicorn | 26 |
| docker/docker-compose.macos.yml | fastapi | 63 |
| docker/docker-compose.yml | fastapi | 79 |
| docker/linux_docker_start.sh | fastapi | 205 |
| docker/macos_docker_start.sh | fastapi | 214 |
| docker/windows_docker_start.bat | fastapi | 133 |
| docs/AGENTS.md | fastapi, uvicorn | 138 |
| docs/README.md | fastapi | 204 |
| scripts/postwork.bat | fastapi | 338 |
| scripts/postwork.ps1 | fastapi | 285 |
| scripts/postwork.sh | fastapi | 301 |
| scripts/project_scan.py | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 471 |
| server/main.py | fastapi | 136 |
| tests/test_api_ws.py | fastapi | 64 |
| tests/test_mcp_integration.py | fastapi | 64 |
| docs/changelogs/kb.md | fastapi, uvicorn | 818 |
| docs/changelogs/th.md | fastapi | 209 |
| docs/design/api_specification.md | fastapi | 373 |
| docs/design/architecture.md | fastapi, APIRouter, uvicorn | 544 |
| docs/design/backend_db_architecture.md | fastapi, HTTPException | 60 |
| docs/design/minchodan_design_note.md | fastapi, APIRouter, uvicorn | 215 |
| docs/design/pipeline_stage_design.md | fastapi, APIRouter | 176 |
| docs/dev-guides/course_codebase_guide.md | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 2986 |
| docs/dev-guides/신규_설계서_예시_2.md | fastapi, uvicorn | 235 |
| docs/mobile/mobile_android_implementation_plan.md | fastapi, uvicorn | 488 |
| docs/mobile/mobile_app_implementation_plan.md | fastapi, uvicorn | 583 |
| docs/mobile/mobile_ios_implementation_plan.md | fastapi, uvicorn | 598 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | fastapi, uvicorn | 573 |
| docs/ops/deployment_guide.md | fastapi, uvicorn | 328 |
| docs/ops/ondevice_coreml_benchmark.md | fastapi | 240 |
| docs/ops/redis_streams_schema.md | fastapi | 56 |
| docs/ops/test_specification.md | fastapi, uvicorn | 336 |
| docs/ops/wireless_test_guide.md | fastapi | 167 |
| docs/stage-guides/stage1_websocket_design.md | fastapi | 93 |
| docs/stage-guides/stage2_capture_design.md | fastapi | 447 |
| docs/stage-guides/stage3_detection_design.md | fastapi, BaseModel | 578 |
| server/api/admin_router.py | fastapi, APIRouter | 61 |
| server/api/heartbeat.py | fastapi | 77 |
| server/api/monitor.py | fastapi, APIRouter | 65 |
| server/api/schemas.py | BaseModel | 85 |
| server/api/session_manager.py | fastapi | 54 |
| server/api/user_router.py | fastapi, APIRouter, BaseModel | 61 |
| server/api/ws_router.py | fastapi, APIRouter | 195 |
| server/db/connection.py | fastapi | 59 |
| server/db/schemas.py | BaseModel | 130 |
| server/detection/schemas.py | BaseModel | 60 |
| server/detection/yolo_code_review.md | fastapi | 242 |
| server/mcp/manager.py | fastapi | 144 |
| server/services/admin_service.py | fastapi, HTTPException | 96 |
| server/services/user_service.py | fastapi, HTTPException | 79 |
| .agents/skills/camera-frame-capture/SKILL.md | fastapi | 409 |
| .agents/skills/tts-voice-streamer/SKILL.md | fastapi, uvicorn | 338 |
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
| .env.example | OpenAI, OPENAI_API_KEY | 81 |
| .gitignore | OpenAI | 276 |
| README.md | OpenAI, OPENAI_API_KEY | 359 |
| docs/README.md | OpenAI | 204 |
| scripts/project_scan.py | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 471 |
| tests/test_mcp_gpu.py | OpenAI, OPENAI_API_KEY | 78 |
| docs/changelogs/kb.md | OpenAI | 818 |
| docs/design/architecture.md | OpenAI, OPENAI_API_KEY | 544 |
| docs/design/minchodan_design_note.md | OpenAI | 215 |
| docs/design/pipeline_stage_design.md | OpenAI | 176 |
| docs/dev-guides/course_codebase_guide.md | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 2986 |
| docs/dev-guides/신규_설계서_예시_2.md | OpenAI | 235 |
| docs/ops/code_quality_guide.md | OpenAI, OPENAI_API_KEY | 654 |
| docs/ops/environment_variables.md | OpenAI, OPENAI_API_KEY | 183 |
| docs/ops/test_specification.md | OpenAI | 336 |
| docs/research/gemini_fallback_feasibility.md | OpenAI | 80 |
| docs/stage-guides/stage4_5_data_replacement_guide.md | OpenAI | 92 |
| docs/stage-guides/stage4_5_rag_design.md | OpenAI | 342 |
| docs/stage-guides/stage6_orchestration_design.md | OpenAI, OPENAI_API_KEY | 514 |
| docs/stage-guides/stage7_tts_design.md | OpenAI | 232 |
| server/api/monitor.py | responses | 65 |
| server/bus/redis_client.py | responses | 88 |
| server/mcp/gpu_monitor.py | OpenAI | 92 |
| server/mcp/manager.py | responses | 144 |
| server/orchestration/llm_client_factory.py | OpenAI, OPENAI_API_KEY | 207 |
| server/rag/embedding_engine_factory.py | OpenAI | 133 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 359 |
| .agents/skills/tts-voice-streamer/SKILL.md | OpenAI | 338 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 359 |
| .claude/skills/tts-voice-streamer/SKILL.md | OpenAI | 337 |
| server/orchestration/nodes/l2_generator.py | OpenAI | 113 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |

### dataset

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | dataset, frame | 81 |
| .gitignore | dataset, images, json | 276 |
| AGENTS.md | labels, frame | 189 |
| CLAUDE.md | labels, frame | 170 |
| Directory_Structure.md | dataset, images, labels, json, frame | 149 |
| README.md | dataset, json, frame | 359 |
| SCRIPT_GENERATION_PROMPT.md | frame | 381 |
| SKILLS.md | labels, json, frame | 175 |
| opencode.json | json | 10 |
| project_scan_verification.md | json | 61 |
| pyproject.toml | annotation | 158 |
| requirements.txt | json | 152 |
| client/package-lock.json | json, annotation, frame | 6730 |
| docker/windows_docker_start.bat | images | 133 |
| docs/AGENTS.md | labels, frame | 138 |
| scripts/bench_ondevice.py | frame | 224 |
| scripts/convert_aihub_seg_to_yolo.py | dataset, images, labels, json, annotation | 204 |
| scripts/inspect_aihub_bbox_xml.py | dataset, images, labels, json | 360 |
| scripts/integration_test_pipeline.py | frame | 151 |
| scripts/postwork.bat | frame | 338 |
| scripts/postwork.ps1 | frame | 285 |
| scripts/postwork.sh | frame | 301 |
| scripts/prepare_aihub_yolo_detection.py | dataset, images, labels, json, annotation | 371 |
| scripts/prework.bat | frame | 247 |
| scripts/prework.ps1 | frame | 209 |
| scripts/prework.sh | frame | 222 |
| scripts/project_scan.py | dataset, data.yaml, images, labels, json, annotation, frame | 471 |
| scripts/resolve_conflicts.py | json | 68 |
| scripts/run_desktop_full_training.py | dataset, images, annotation | 170 |
| scripts/run_yolo_tts_demo.py | images, json, frame | 208 |
| scripts/scan_aihub_walk_dataset.py | dataset, json | 361 |
| scripts/slack_publisher.py | json | 223 |
| scripts/verify_pretrained_weights.py | frame | 69 |
| tests/test_api_ws.py | json | 64 |
| tests/test_db_builder.py | frame | 69 |
| tests/test_detection.py | frame | 359 |
| tests/test_e2e_pipeline.py | labels, frame | 98 |
| tests/test_fallback.py | labels | 41 |
| tests/test_frame_decode.py | frame | 348 |
| tests/test_frame_extractor.py | frame | 55 |
| tests/test_mcp_integration.py | json | 64 |
| tests/test_retriever.py | labels, json | 85 |
| tests/test_ws_echo.py | json, frame | 184 |
| training/train_common.py | dataset, annotation | 105 |
| training/train_detection.py | dataset, annotation | 61 |
| training/train_segmentation.py | dataset, annotation | 59 |
| docs/changelogs/dg.md | labels, frame | 20 |
| docs/changelogs/jh.md | json | 189 |
| docs/changelogs/kb.md | json, frame | 818 |
| docs/changelogs/th.md | dataset, json, frame | 209 |
| docs/design/api_specification.md | json, frame | 373 |
| docs/design/architecture.md | json, frame | 544 |
| docs/design/behavior_and_risk_insight.md | frame | 91 |
| docs/design/minchodan_design_note.md | json, frame | 215 |
| docs/dev-guides/antigravity_agent_prompt__4_5_final.md | labels, frame | 188 |
| docs/dev-guides/course_codebase_guide.md | dataset, images, labels, json, frame | 2986 |
| docs/dev-guides/llm_collaboration_workflow.md | json | 168 |
| docs/dev-guides/신규_설계서_예시_2.md | json, frame | 235 |
| docs/mobile/mobile_android_implementation_plan.md | json, frame | 488 |
| docs/mobile/mobile_app_implementation_plan.md | json, frame | 583 |
| docs/mobile/mobile_ios_implementation_plan.md | json, frame | 598 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | json, frame | 573 |
| docs/ops/code_quality_guide.md | json, frame | 654 |
| docs/ops/deployment_guide.md | json | 328 |
| docs/ops/environment_variables.md | json, frame | 183 |
| docs/ops/ondevice_coreml_benchmark.md | json | 240 |
| docs/ops/redis_streams_schema.md | json, frame | 56 |
| docs/ops/test_specification.md | json, frame | 336 |
| docs/ops/wireless_test_guide.md | json, frame | 167 |
| docs/research/latency_impact_analysis.md | json | 106 |
| docs/research/post_mvp_hybrid_roadmap.md | frame | 389 |
| docs/research/yolo_tts_mvp_next_steps.md | dataset, json, frame | 144 |
| docs/stage-guides/stage1_websocket_design.md | json, frame | 93 |
| docs/stage-guides/stage2_capture_design.md | json, frame | 447 |
| docs/stage-guides/stage3_detection_design.md | json, frame | 578 |
| docs/stage-guides/stage4_5_data_replacement_guide.md | frame | 92 |
| docs/stage-guides/stage4_5_directory_guide.md | labels, frame | 60 |
| docs/stage-guides/stage4_5_implementation_log.md | labels, frame | 93 |
| docs/stage-guides/stage4_5_rag_design.md | labels, frame | 342 |
| docs/stage-guides/stage4_5_test_guide.md | frame | 88 |

---

## 8. 다음 작업 제안

| 순서 | 작업 |
| --- | --- |
| 1 | YOLO 관련 파일을 열어 실제 탐지/추론 구조와 모델 경로를 확인합니다. |
| 2 | LangChain/LangGraph 관련 파일을 열어 탐지 JSON이 연결될 입력 스키마를 확인합니다. |
| 3 | 데이터셋 원본 폴더를 별도 스캔하여 라벨 형식과 YOLO 변환 가능성을 판단합니다. |
| 4 | 확인된 라벨 형식 기준으로 class_mapping.json과 변환 계획을 작성합니다. |
