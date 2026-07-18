# 프로젝트 스캔 보고서

> **작성일**: 2026-07-18
> **버전**: v0.1.0
> **대상 루트**: `/Users/kwanbum/Documents/korea_IT/lanhchain_ai_vision/Minchodan`

---

## 1. 요약

| 항목 | 값 |
| --- | --- |
| 전체 파일 수 | 48193 |
| 문서 파일 수 | 180 |
| Python 파일 수 | 215 |

---

## 2. 폴더 트리

```text
Minchodan/
├── .agents/
│   └── skills/
│       ├── auto-publish-work/
│       ├── camera-frame-capture/
│       ├── llm-guidance-orchestrator/
│       ├── rag-knowledge-builder/
│       ├── rag-realtime-search/
│       ├── react-doctor/
│       ├── tts-voice-streamer/
│       ├── websocket-gateway/
│       ├── xcode-build-management/
│       └── yolo-obstacle-detection/
├── .antigravity/
│   └── rules.md
├── .claude/
│   ├── skills/
│   │   ├── auto-publish-work/
│   │   ├── camera-frame-capture/
│   │   ├── llm-guidance-orchestrator/
│   │   ├── rag-knowledge-builder/
│   │   ├── rag-realtime-search/
│   │   ├── react-doctor/
│   │   ├── tts-voice-streamer/
│   │   ├── websocket-gateway/
│   │   ├── xcode-build-management/
│   │   └── yolo-obstacle-detection/
│   ├── worktrees/
│   └── settings.local.json
├── .cursor/
│   └── rules/
│       ├── 00-core-guidelines.mdc
│       ├── 01-reflex-path-guard.mdc
│       ├── 02-stage1-websocket-gateway.mdc
│       ├── 03-stage2-camera-frame-capture.mdc
│       ├── 04-stage3-yolo-obstacle-detection.mdc
│       ├── 05-stage4-rag-knowledge-builder.mdc
│       ├── 06-stage5-rag-realtime-search.mdc
│       ├── 07-stage6-llm-guidance-orchestrator.mdc
│       ├── 08-stage7-tts-voice-streamer.mdc
│       ├── 09-xcode-build-management.mdc
│       ├── 10-react-doctor.mdc
│       └── 11-auto-publish-work.mdc
├── .github/
│   └── workflows/
│       └── lint.yml
├── .vscode/
│   └── settings.json
├── .xcodebuildmcp/
│   ├── config.yaml
│   └── Copy_config.yaml
├── .zcode/
│   └── plans/
│       ├── plan-sess_2dbd0ff5-fe6e-450a-bd34-71718823db8d.md
│       ├── plan-sess_86a22c13-a4c7-4ae8-b69d-297eb1cca7c1.md
│       ├── plan-sess_a88e625c-d9d4-47c0-9ded-126be54ac215.md
│       └── plan-sess_e737ed00-13c4-409b-8f47-a38bb4be49e2.md
├── client/
│   ├── .expo/
│   │   ├── dev/
│   │   ├── prebuild/
│   │   ├── web/
│   │   ├── devices.json
│   │   ├── README.md
│   │   ├── settings.json
│   │   ├── xcodebuild-error.log
│   │   └── xcodebuild.log
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
│   │   ├── models/
│   │   ├── samples/
│   │   ├── shortcuts/
│   │   ├── sounds/
│   │   ├── android-icon-background.png
│   │   ├── android-icon-foreground.png
│   │   ├── android-icon-monochrome.png
│   │   ├── favicon.png
│   │   ├── gildang-logo.jpeg
│   │   ├── icon.png
│   │   ├── splash-icon.png
│   │   └── splash-loading.png
│   ├── dist/
│   │   ├── _expo/
│   │   ├── assets/
│   │   └── metadata.json
│   ├── ios/
│   │   ├── build/
│   │   ├── Minchodan/
│   │   ├── Minchodan.xcodeproj/
│   │   ├── Minchodan.xcworkspace/
│   │   ├── Pods/
│   │   ├── segmentation.mlpackage/
│   │   ├── .DS_Store
│   │   ├── .gitignore
│   │   ├── .xcode.env
│   │   ├── .xcode.env.local
│   │   ├── AudioSessionBridge.mm
│   │   ├── AudioSessionBridge.swift
│   │   ├── CoreMLInferenceBridge.mm
│   │   ├── CoreMLInferenceBridge.swift
│   │   ├── DepthProbeBridge.mm
│   │   ├── DepthProbeBridge.swift
│   │   ├── MinchodanDialIntent.swift
│   │   ├── MinchodanSiriDialer.swift
│   │   ├── PhoneDialBridge.mm
│   │   ├── PhoneDialBridge.swift
│   │   ├── Podfile
│   │   ├── Podfile.lock
│   │   ├── Podfile.properties.json
│   │   ├── ReflexFrameProcessorPlugin.m
│   │   └── ReflexFrameProcessorPlugin.swift
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── config/
│   │   ├── hooks/
│   │   ├── inference/
│   │   ├── services/
│   │   └── types/
│   ├── .env
│   ├── .env.example
│   ├── .gitignore
│   ├── app.json
│   ├── App.tsx
│   ├── babel.config.js
│   ├── doctor.config.json
│   ├── eas.json
│   ├── index.ts
│   ├── metro.config.js
│   ├── package-lock.json
│   ├── package.json
│   ├── reverse.bat
│   ├── tsconfig.json
│   └── tunnel.bat
├── console/
│   ├── dist/
│   │   ├── assets/
│   │   ├── apple-touch-icon.png
│   │   ├── favicon-16x16.png
│   │   ├── favicon-32x32.png
│   │   ├── favicon.ico
│   │   ├── favicon.svg
│   │   ├── gildang-logo.jpeg
│   │   └── index.html
│   ├── public/
│   │   ├── apple-touch-icon.png
│   │   ├── favicon-16x16.png
│   │   ├── favicon-32x32.png
│   │   ├── favicon.ico
│   │   ├── favicon.svg
│   │   └── gildang-logo.jpeg
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── config/
│   │   ├── pages/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── vite-env.d.ts
│   ├── .env
│   ├── .env.example
│   ├── doctor.config.json
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── README.md
│   ├── tsconfig.json
│   └── vite.config.ts
├── data/
│   ├── captions/
│   │   └── .gitkeep
│   ├── chroma_db/
│   │   ├── 0571151f-fa3f-499d-9ec7-ce3c1c4bf180/
│   │   ├── convenience_guidelines/
│   │   ├── .gitkeep
│   │   └── chroma.sqlite3
│   ├── chroma_db_contacts/
│   │   └── chroma.sqlite3
│   ├── deduped/
│   │   └── .gitkeep
│   ├── event_frames/
│   │   ├── 20260711/
│   │   ├── 20260712/
│   │   ├── 20260713/
│   │   ├── 20260714/
│   │   ├── 20260715/
│   │   ├── 20260716/
│   │   └── 20260717/
│   ├── frames/
│   │   └── .gitkeep
│   ├── guide_clips/
│   │   ├── .gitkeep
│   │   ├── 10시_기둥_far_caution.wav
│   │   ├── 10시_기둥_medium_caution.wav
│   │   ├── 10시_기둥_near_caution.wav
│   │   ├── 10시_바리케이드_far_caution.wav
│   │   ├── 10시_바리케이드_medium_caution.wav
│   │   ├── 10시_바리케이드_near_caution.wav
│   │   ├── 10시_버스_far_caution.wav
│   │   ├── 10시_버스_medium_caution.wav
│   │   ├── 10시_버스_near_caution.wav
│   │   ├── 10시_볼라드_far_caution.wav
│   │   ├── 10시_볼라드_medium_caution.wav
│   │   ├── 10시_볼라드_near_caution.wav
│   │   ├── 10시_사람_far_caution.wav
│   │   ├── 10시_사람_medium_caution.wav
│   │   ├── 10시_사람_near_caution.wav
│   │   ├── 10시_오토바이_far_caution.wav
│   │   ├── 10시_오토바이_medium_caution.wav
│   │   ├── 10시_오토바이_near_caution.wav
│   │   ├── 10시_자전거_far_caution.wav
│   │   ├── 10시_자전거_medium_caution.wav
│   │   ├── 10시_자전거_near_caution.wav
│   │   ├── 10시_전동_킥보드_far_caution.wav
│   │   ├── 10시_전동_킥보드_medium_caution.wav
│   │   ├── 10시_전동_킥보드_near_caution.wav
│   │   ├── 10시_차량_far_caution.wav
│   │   ├── 10시_차량_medium_caution.wav
│   │   ├── 10시_차량_near_caution.wav
│   │   ├── 10시_트럭_far_caution.wav
│   │   ├── 10시_트럭_medium_caution.wav
│   │   ├── 10시_트럭_near_caution.wav
│   │   ├── 11시_기둥_far_caution.wav
│   │   ├── 11시_기둥_medium_caution.wav
│   │   ├── 11시_기둥_near_caution.wav
│   │   ├── 11시_바리케이드_far_caution.wav
│   │   ├── 11시_바리케이드_medium_caution.wav
│   │   ├── 11시_바리케이드_near_caution.wav
│   │   ├── 11시_버스_far_caution.wav
│   │   ├── 11시_버스_medium_caution.wav
│   │   ├── 11시_버스_near_caution.wav
│   │   ├── 11시_볼라드_far_caution.wav
│   │   ├── 11시_볼라드_medium_caution.wav
│   │   ├── 11시_볼라드_near_caution.wav
│   │   ├── 11시_사람_far_caution.wav
│   │   ├── 11시_사람_medium_caution.wav
│   │   ├── 11시_사람_near_caution.wav
│   │   ├── 11시_오토바이_far_caution.wav
│   │   ├── 11시_오토바이_medium_caution.wav
│   │   ├── 11시_오토바이_near_caution.wav
│   │   ├── 11시_자전거_far_caution.wav
│   │   ├── 11시_자전거_medium_caution.wav
│   │   ├── 11시_자전거_near_caution.wav
│   │   ├── 11시_전동_킥보드_far_caution.wav
│   │   ├── 11시_전동_킥보드_medium_caution.wav
│   │   ├── 11시_전동_킥보드_near_caution.wav
│   │   ├── 11시_차량_far_caution.wav
│   │   ├── 11시_차량_medium_caution.wav
│   │   ├── 11시_차량_near_caution.wav
│   │   ├── 11시_트럭_far_caution.wav
│   │   ├── 11시_트럭_medium_caution.wav
│   │   ├── 11시_트럭_near_caution.wav
│   │   ├── 12시_기둥_far_caution.wav
│   │   ├── 12시_기둥_medium_caution.wav
│   │   ├── 12시_기둥_near_caution.wav
│   │   ├── 12시_바리케이드_far_caution.wav
│   │   ├── 12시_바리케이드_medium_caution.wav
│   │   ├── 12시_바리케이드_near_caution.wav
│   │   ├── 12시_버스_far_caution.wav
│   │   ├── 12시_버스_medium_caution.wav
│   │   ├── 12시_버스_near_caution.wav
│   │   ├── 12시_볼라드_far_caution.wav
│   │   ├── 12시_볼라드_medium_caution.wav
│   │   ├── 12시_볼라드_near_caution.wav
│   │   ├── 12시_사람_far_caution.wav
│   │   ├── 12시_사람_medium_caution.wav
│   │   ├── 12시_사람_near_caution.wav
│   │   ├── 12시_오토바이_far_caution.wav
│   │   ├── 12시_오토바이_medium_caution.wav
│   │   ├── 12시_오토바이_near_caution.wav
│   │   ├── 12시_자전거_far_caution.wav
│   │   ├── 12시_자전거_medium_caution.wav
│   │   ├── 12시_자전거_near_caution.wav
│   │   ├── 12시_전동_킥보드_far_caution.wav
│   │   ├── 12시_전동_킥보드_medium_caution.wav
│   │   ├── 12시_전동_킥보드_near_caution.wav
│   │   ├── 12시_차량_far_caution.wav
│   │   ├── 12시_차량_medium_caution.wav
│   │   ├── 12시_차량_near_caution.wav
│   │   ├── 12시_트럭_far_caution.wav
│   │   ├── 12시_트럭_medium_caution.wav
│   │   ├── 12시_트럭_near_caution.wav
│   │   ├── 1시_기둥_far_caution.wav
│   │   ├── 1시_기둥_medium_caution.wav
│   │   ├── 1시_기둥_near_caution.wav
│   │   ├── 1시_바리케이드_far_caution.wav
│   │   ├── 1시_바리케이드_medium_caution.wav
│   │   ├── 1시_바리케이드_near_caution.wav
│   │   ├── 1시_버스_far_caution.wav
│   │   ├── 1시_버스_medium_caution.wav
│   │   ├── 1시_버스_near_caution.wav
│   │   ├── 1시_볼라드_far_caution.wav
│   │   ├── 1시_볼라드_medium_caution.wav
│   │   ├── 1시_볼라드_near_caution.wav
│   │   ├── 1시_사람_far_caution.wav
│   │   ├── 1시_사람_medium_caution.wav
│   │   ├── 1시_사람_near_caution.wav
│   │   ├── 1시_오토바이_far_caution.wav
│   │   ├── 1시_오토바이_medium_caution.wav
│   │   ├── 1시_오토바이_near_caution.wav
│   │   ├── 1시_자전거_far_caution.wav
│   │   ├── 1시_자전거_medium_caution.wav
│   │   ├── 1시_자전거_near_caution.wav
│   │   ├── 1시_전동_킥보드_far_caution.wav
│   │   ├── 1시_전동_킥보드_medium_caution.wav
│   │   ├── 1시_전동_킥보드_near_caution.wav
│   │   ├── 1시_차량_far_caution.wav
│   │   ├── 1시_차량_medium_caution.wav
│   │   ├── 1시_차량_near_caution.wav
│   │   ├── 1시_트럭_far_caution.wav
│   │   └── 1시_트럭_medium_caution.wav
│   │   └── ... (91개 생략)
│   ├── raw/
│   │   └── .gitkeep
│   ├── stt_debug/
│   │   ├── dev-001-1783742315254.543.wav
│   │   ├── dev-001-1783742321847.099.wav
│   │   ├── dev-001-1783742326007.211.wav
│   │   ├── dev-001-1783742340226.1301.wav
│   │   ├── dev-001-1783742350107.254.wav
│   │   ├── dev-001-1783742356951.8982.wav
│   │   ├── dev-001-1783742364306.9202.wav
│   │   ├── dev-001-1783742467062.9849.wav
│   │   ├── dev-001-1783742478045.26.wav
│   │   ├── dev-001-1783742485268.7021.wav
│   │   ├── dev-001-1783742495755.025.wav
│   │   ├── dev-001-1783742549680.65.wav
│   │   ├── dev-001-1783742559827.364.wav
│   │   ├── dev-001-1783742944168.388.wav
│   │   ├── dev-001-1783743561615.1519.wav
│   │   ├── dev-001-1783743580997.579.wav
│   │   ├── dev-001-1783743595518.922.wav
│   │   ├── dev-001-1783743613846.505.wav
│   │   ├── dev-001-1783743775570.547.wav
│   │   ├── dev-001-1783743779922.533.wav
│   │   ├── dev-001-1783743784441.3062.wav
│   │   ├── dev-001-1783743786999.218.wav
│   │   ├── dev-001-1783743793152.094.wav
│   │   ├── dev-001-1783743795362.4238.wav
│   │   ├── dev-001-1783743804359.53.wav
│   │   ├── dev-001-1783743812613.563.wav
│   │   ├── dev-001-1783743832223.419.wav
│   │   ├── dev-001-1783743847262.944.wav
│   │   ├── dev-001-1783743859814.905.wav
│   │   ├── dev-001-1783743872182.3271.wav
│   │   ├── dev-001-1783743884867.862.wav
│   │   ├── dev-001-1783743901709.1191.wav
│   │   ├── dev-001-1783743910667.262.wav
│   │   ├── dev-001-1783743916500.88.wav
│   │   ├── dev-001-1783743935289.9949.wav
│   │   ├── dev-001-1783746273170.395.wav
│   │   ├── dev-001-1783746332296.9512.wav
│   │   ├── dev-001-1783746334534.6912.wav
│   │   ├── dev-001-1783746338774.002.wav
│   │   ├── dev-001-1783746344695.533.wav
│   │   ├── dev-001-1783746349074.669.wav
│   │   ├── dev-001-1783746356575.096.wav
│   │   ├── dev-001-1783746371144.123.wav
│   │   ├── dev-001-1783746389066.624.wav
│   │   ├── dev-001-1783746399515.417.wav
│   │   ├── dev-001-1783746411274.561.wav
│   │   ├── dev-001-1783746423567.8909.wav
│   │   ├── dev-001-1783746431063.4028.wav
│   │   ├── dev-001-1783746444540.804.wav
│   │   ├── dev-001-1783746455031.796.wav
│   │   ├── dev-001-1783746469449.614.wav
│   │   ├── dev-001-1783746492776.531.wav
│   │   ├── dev-001-1783746515670.459.wav
│   │   ├── dev-001-1783750770481.77.wav
│   │   ├── dev-001-1783750776152.8252.wav
│   │   ├── dev-001-1783750786014.7158.wav
│   │   ├── dev-001-1783750805192.6602.wav
│   │   ├── dev-001-1783750837675.691.wav
│   │   ├── dev-001-1783755182189.568.wav
│   │   ├── dev-001-1783755192079.967.wav
│   │   ├── dev-001-1783755206888.356.wav
│   │   ├── dev-001-1783755224165.128.wav
│   │   ├── dev-001-1783755263803.438.wav
│   │   ├── dev-001-1783755272590.6738.wav
│   │   ├── dev-001-1783755284431.766.wav
│   │   ├── dev-001-1783755301537.729.wav
│   │   ├── dev-001-1783756014352.0862.wav
│   │   ├── dev-001-1783756017198.504.wav
│   │   ├── dev-001-1783757265576.367.wav
│   │   ├── dev-001-1783757278609.762.wav
│   │   └── dev-001-1783757295801.645.wav
│   ├── validation_samples/
│   │   ├── raw/
│   │   └── results/
│   ├── convenience_guidelines.json
│   ├── reflex_guidelines.json
│   └── safety_guidelines.json
├── docker/
│   ├── scripts/
│   │   └── db_tailscale_proxy.sh
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
│   │   ├── dg2.md
│   │   ├── jh.md
│   │   ├── jy.md
│   │   ├── kb.md
│   │   ├── model_run_verification.md
│   │   ├── README.md
│   │   ├── stage_safety_reflex.md
│   │   ├── TEMPLATE.md
│   │   ├── th.md
│   │   └── th_2026_07_12_share.md
│   ├── db_tailscale_guide/
│   │   └── README.md
│   ├── design/
│   │   ├── api_specification.md
│   │   ├── architecture.md
│   │   ├── backend_db_architecture.md
│   │   ├── behavior_and_risk_insight.md
│   │   ├── indoor_fp_mitigation_design.md
│   │   ├── minchodan_design_note.md
│   │   ├── pipeline_stage_design.md
│   │   ├── reflex_audio_specification.md
│   │   ├── risk_ssot_contract.md
│   │   └── scene_classifier_gate_guide.md
│   ├── dev-guides/
│   │   ├── integration/
│   │   ├── prompts/
│   │   ├── templates/
│   │   ├── course_codebase_guide.md
│   │   ├── llm_collaboration_workflow.md
│   │   └── multi_agent_setup.md
│   ├── handoff/
│   │   └── 2026-07-15_reflex_ood_handoff.md
│   ├── macOS_xcode_build/
│   │   ├── ios_device_build_iteration_guide.md
│   │   └── xcode_mcp_setup_guide.md
│   ├── mobile/
│   │   ├── android_aspect_ratio_calibration_report.md
│   │   ├── android_bbox_missing_fix_plan.md
│   │   ├── android_ondevice_tflite_build_plan.md
│   │   ├── android_platform_patch_results.md
│   │   ├── ios_android_bifurcation_contract.md
│   │   ├── mobile_android_implementation_plan.md
│   │   ├── mobile_app_implementation_plan.md
│   │   ├── mobile_ios_implementation_plan.md
│   │   └── ondevice_inference_engine_isolation_plan.md
│   ├── ops/
│   │   ├── ai_model_hardware_setup.md
│   │   ├── android_build_and_wireless_test_guide.md
│   │   ├── android_device_integration_guide.md
│   │   ├── android_eas_development_build_wireless_guide.md
│   │   ├── android_ondevice_tflite_completion_report.md
│   │   ├── android_ondevice_tflite_run_guide.md
│   │   ├── android_stt_recognition_issue_report.md
│   │   ├── android_wifi_usb_transport.md
│   │   ├── android_wireless_test_guide_v2.md
│   │   ├── code_quality_guide.md
│   │   ├── deployment_guide.md
│   │   ├── dev_8b2f606_improvement_plan.md
│   │   ├── environment_variables.md
│   │   ├── event_frame_image_loss_investigation.md
│   │   ├── git_branching_strategy.md
│   │   ├── integration_scenario_test.md
│   │   ├── ios_android_bifurcation_contract.md
│   │   ├── local_private_config_guide.md
│   │   ├── minchodan_optimization_checklist.md
│   │   ├── minchodan_optimization_final_report.md
│   │   ├── minchodan_optimization_plan.md
│   │   ├── mobile_build_troubleshooting.md
│   │   ├── model_class_validation_report.md
│   │   ├── navigation_and_reflex_guide.md
│   │   ├── network_latency_benchmark.md
│   │   ├── ondevice_coreml_benchmark.md
│   │   ├── redis_streams_schema.md
│   │   ├── tailscale_connection_guide.md
│   │   ├── team_share_summary.md
│   │   ├── test_specification.md
│   │   ├── tts_pyttsx3_replacement_report.md
│   │   └── wireless_test_guide.md
│   ├── research/
│   │   ├── cpu_and_mobile_performance_optimization_report.md
│   │   ├── dual_gemma4_latency_analysis.md
│   │   ├── field_test_improvement_plan.md
│   │   ├── gemini_fallback_feasibility.md
│   │   ├── latency_impact_analysis.md
│   │   ├── mitos_improvement_roadmap.md
│   │   ├── outdoor_guidance_refinement_roadmap.md
│   │   ├── post_mvp_hybrid_roadmap.md
│   │   ├── post_mvp_ondevice_feasibility.md
│   │   ├── sensevoice_stt_feasibility.md
│   │   └── yolo_tts_mvp_next_steps.md
│   ├── stage-guides/
│   │   ├── stage1_websocket_design.md
│   │   ├── stage2_capture_design.md
│   │   ├── stage3_detection_code_review.md
│   │   ├── stage3_detection_design.md
│   │   ├── stage4_5_data_replacement_guide.md
│   │   ├── stage4_5_directory_guide.md
│   │   ├── stage4_5_implementation_log.md
│   │   ├── stage4_5_rag_design.md
│   │   ├── stage4_5_test_guide.md
│   │   ├── stage6_orchestration_design.md
│   │   ├── stage7_tts_design.md
│   │   └── stage_stt_integration_guide.md
│   ├── .DS_Store
│   ├── AGENTS.md
│   ├── dg.md
│   ├── Directory_Structure.md
│   ├── finetune_weight_analysis.md
│   ├── README.md
│   └── yolo26n_custom_dataset_sources.md
├── logs/
│   └── dev-session/
│       ├── .pids/
│       ├── 20260717_110000/
│       ├── 20260717_110619/
│       ├── 20260717_120849/
│       ├── 20260717_144553/
│       ├── 20260717_181358/
│       ├── latest/
│       └── .gitkeep
├── reports/
│   └── jscpd/
│       └── jscpd-report.html
├── scripts/
│   ├── agent_tasks/
│   │   ├── shared/
│   │   ├── agent_dg_bbox_training.md
│   │   ├── agent_jy_env_e2e.md
│   │   └── agent_kb_polygon_inference.md
│   ├── obstacle_data_miner/
│   │   ├── docs/
│   │   ├── labelers/
│   │   ├── miners/
│   │   ├── utils/
│   │   ├── .env.example
│   │   ├── __init__.py
│   │   ├── class_specs.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── seg_config.py
│   │   └── train_classifier.py
│   ├── analyze_lidar_validation.py
│   ├── auto_publish_work.py
│   ├── bench_ondevice.py
│   ├── benchmark_ws_network.py
│   ├── build_convenience_db.py
│   ├── build_guide_clips.py
│   ├── build_safety_db.py
│   ├── convert_aihub_seg_to_yolo.py
│   ├── convert_yolo_to_coreml.py
│   ├── create_minchodan_dial_shortcut.py
│   ├── dev_ios_lab.sh
│   ├── dev_redis_stub.py
│   ├── download_pretrained_weights.py
│   ├── eval_hitrate.py
│   ├── eval_segmentation_stairs.py
│   ├── export_mobile.py
│   ├── export_tflite.py
│   ├── fix_android_usb_ws.ps1
│   ├── generate_app_icons.py
│   ├── inspect_aihub_bbox_xml.py
│   ├── install_minchodan_dial_shortcut_ios.sh
│   ├── integration_test_pipeline.py
│   ├── launch_agents.sh
│   ├── merge_external_dataset.py
│   ├── postwork.bat
│   ├── postwork.ps1
│   ├── postwork.sh
│   ├── prepare_aihub_yolo_detection.py
│   ├── prework.bat
│   ├── prework.ps1
│   ├── prework.sh
│   ├── project_scan.py
│   ├── project_scan_verification.md
│   ├── resolve_conflicts.py
│   ├── run_desktop_full_training.py
│   ├── run_test_100_samples.py
│   ├── run_test_per_class.py
│   ├── run_yolo_tts_demo.py
│   ├── scan_aihub_walk_dataset.py
│   ├── SCRIPT_GENERATION_PROMPT.md
│   ├── slack_publisher.py
│   ├── train_segmentation_5class.py
│   ├── validate_agent_rules.py
│   ├── validate_class_samples.py
│   ├── verify_gpu.py
│   ├── verify_ios_integration.py
│   └── verify_pretrained_weights.py
├── server/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── admin_member_router.py
│   │   ├── admin_router.py
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── detection_log_router.py
│   │   ├── heartbeat.py
│   │   ├── monitor.py
│   │   ├── schemas.py
│   │   ├── session_manager.py
│   │   ├── stt_router.py
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
│   │   ├── migrations/
│   │   ├── base.py
│   │   ├── connection.py
│   │   ├── init_db.py
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
│   │   ├── path_risk.py
│   │   ├── risk_rules.py
│   │   ├── schemas.py
│   │   ├── surface_departure.py
│   │   ├── yolo_detector.py
│   │   └── yolo_segmentor.py
│   ├── mcp/
│   │   ├── accessibility_simulator.py
│   │   ├── audio_validator.py
│   │   ├── cache_monitor.py
│   │   ├── gpu_monitor.py
│   │   ├── langsmith_tracer.py
│   │   ├── manager.py
│   │   └── slack_notifier.py
│   ├── models/
│   │   ├── piper/
│   │   └── yolo26n/
│   ├── navigation/
│   │   ├── __init__.py
│   │   ├── index.html
│   │   ├── manager.py
│   │   ├── navigation_filter.py
│   │   ├── server.py
│   │   └── tts_engine.py
│   ├── orchestration/
│   │   ├── nodes/
│   │   ├── __init__.py
│   │   ├── avoidance.py
│   │   ├── graph.py
│   │   ├── llm_client_factory.py
│   │   └── state.py
│   ├── rag/
│   │   ├── build/
│   │   ├── shared/
│   │   ├── convenience_dial_resolver.py
│   │   ├── convenience_rag.py
│   │   ├── embedding_engine_factory.py
│   │   ├── fallback.py
│   │   ├── retriever.py
│   │   └── vector_db_factory.py
│   ├── services/
│   │   ├── admin_service.py
│   │   ├── detection_guidance_log_service.py
│   │   ├── device_registry_service.py
│   │   ├── event_frame_store.py
│   │   ├── lidar_validation_service.py
│   │   ├── pipeline_debug_builder.py
│   │   ├── remote_storage_client.py
│   │   └── user_service.py
│   ├── stt/
│   │   ├── __init__.py
│   │   ├── dial_resolver.py
│   │   ├── phone_utils.py
│   │   ├── stt_config.py
│   │   ├── stt_runtime.py
│   │   ├── stt_schema.py
│   │   ├── stt_service.py
│   │   └── stt_to_llm_bridge.py
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── korean_g2p.py
│   │   ├── realtime_tts.py
│   │   ├── reflex_clip_sender.py
│   │   ├── suppressor.py
│   │   └── tts_service.py
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_29_classes_inference.py
│   ├── test_admin_service_login.py
│   ├── test_api_ws.py
│   ├── test_clock_direction.py
│   ├── test_cognitive_fields.py
│   ├── test_convenience_dial_resolver.py
│   ├── test_db_builder.py
│   ├── test_dedup_phash.py
│   ├── test_departure_hysteresis.py
│   ├── test_detection.py
│   ├── test_dial_resolver.py
│   ├── test_e2e_pipeline.py
│   ├── test_embedding_engine_factory.py
│   ├── test_event_frame_store.py
│   ├── test_fallback.py
│   ├── test_false_positive.py
│   ├── test_fast_lane.py
│   ├── test_frame_decode.py
│   ├── test_frame_extractor.py
│   ├── test_gemini_captioner.py
│   ├── test_langgraph.py
│   ├── test_mcp_gpu.py
│   ├── test_mcp_integration.py
│   ├── test_mcp_new.py
│   ├── test_path_risk.py
│   ├── test_phone_utils.py
│   ├── test_pipeline_debug.py
│   ├── test_reflex_and_nav.py
│   ├── test_retriever.py
│   ├── test_risk_event_broadcast.py
│   ├── test_risk_ssot.py
│   ├── test_session_manager.py
│   ├── test_stt_config_policy.py
│   ├── test_stt_faster_whisper_mode_template.py
│   ├── test_stt_router_nonblocking.py
│   ├── test_stt_service_template.py
│   ├── test_stt_to_llm_bridge_template.py
│   ├── test_stt_wait_notice.py
│   ├── test_suppressor_rearm.py
│   ├── test_surface_departure.py
│   ├── test_tts_prewarm.py
│   ├── test_user_service.py
│   ├── test_vector_db_factory.py
│   ├── test_ws_echo.py
│   └── test_ws_router_stt.py
├── training/
│   ├── configs/
│   │   ├── aihub_merged_detection.yaml
│   │   └── aihub_yolo_segmentation.yaml
│   ├── train_common.py
│   ├── train_detection.py
│   ├── train_finetune.py
│   └── train_segmentation.py
├── Z:\non_existent_drive_folder\chromadb_test/
│   └── chroma.sqlite3
├── .dockerignore
├── .DS_Store
├── .env
├── .env.example
├── .gitignore
├── .jscpd.json
├── .mcp.json
├── .pre-commit-config.yaml
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── opencode.json
├── package-lock.json
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
└── SKILLS.md
```

---

## 3. 핵심 파일

| 파일명 | 발견 경로 |
| --- | --- |
| .env.example | .env.example, client/.env.example, console/.env.example, scripts/obstacle_data_miner/.env.example |
| README.md | README.md, client/.expo/README.md, client/ios/Pods/RCT-Folly/README.md, client/ios/Pods/SDWebImage/README.md, client/ios/Pods/SDWebImageWebPCoder/README.md, client/ios/Pods/SocketRocket/README.md, client/ios/Pods/boost/README.md, client/ios/Pods/fast_float/README.md, client/ios/Pods/fmt/README.md, client/ios/Pods/libwebp/README.md, console/README.md, docs/README.md, docs/changelogs/README.md, docs/db_tailscale_guide/README.md, scripts/obstacle_data_miner/README.md, server/db/migrations/README.md |
| package.json | client/package.json, console/package.json |
| pyproject.toml | pyproject.toml |
| requirements.txt | requirements.txt, scripts/obstacle_data_miner/requirements.txt |

---

## 4. 확장자 통계

| 확장자 | 파일 수 |
| --- | --- |
| .pcm | 12356 |
| .h | 4895 |
| .hpp | 4081 |
| .jpg | 2030 |
| .dia | 1920 |
| .d | 1900 |
| .o | 1580 |
| .scan | 1140 |
| (no extension) | 988 |
| .hmap | 582 |
| .timestamp | 534 |
| .wav | 308 |
| .json | 270 |
| .py | 215 |
| .xcconfig | 212 |
| .resp | 204 |
| .m | 189 |
| .modulemap | 172 |
| .md | 169 |
| .swiftmodule | 148 |
| .c | 124 |
| .plist | 119 |
| .xcscheme | 118 |
| .dependencymetadatafilelist | 106 |
| .dependencystaticmetadatafilelist | 106 |
| .dat | 95 |
| .linkfilelist | 95 |
| .pch | 95 |
| .a | 94 |
| .pch-6v44bm6vrzxd | 93 |

---

## 5. 문서 파일

| 파일 | 크기(bytes) |
| --- | --- |
| AGENTS.md | 21911 |
| CLAUDE.md | 779 |
| GEMINI.md | 21911 |
| README.md | 22251 |
| SKILLS.md | 10498 |
| requirements-dev.txt | 239 |
| requirements.txt | 3802 |
| .agents/skills/auto-publish-work/SKILL.md | 6028 |
| .agents/skills/camera-frame-capture/SKILL.md | 22554 |
| .agents/skills/camera-frame-capture/references/implementation_detail.md | 31664 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | 15395 |
| .agents/skills/llm-guidance-orchestrator/references/implementation_detail.md | 19478 |
| .agents/skills/rag-knowledge-builder/SKILL.md | 10261 |
| .agents/skills/rag-knowledge-builder/references/implementation_detail.md | 7610 |
| .agents/skills/rag-realtime-search/SKILL.md | 10254 |
| .agents/skills/rag-realtime-search/references/implementation_detail.md | 11759 |
| .agents/skills/react-doctor/SKILL.md | 3553 |
| .agents/skills/tts-voice-streamer/SKILL.md | 16547 |
| .agents/skills/tts-voice-streamer/references/implementation_detail.md | 7560 |
| .agents/skills/websocket-gateway/SKILL.md | 20273 |
| .agents/skills/websocket-gateway/references/implementation_detail.md | 15073 |
| .agents/skills/xcode-build-management/SKILL.md | 6460 |
| .agents/skills/xcode-build-management/references/implementation_detail.md | 6926 |
| .agents/skills/yolo-obstacle-detection/SKILL.md | 17253 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | 29314 |
| .antigravity/rules.md | 8608 |
| .claude/skills/auto-publish-work/SKILL.md | 6028 |
| .claude/skills/camera-frame-capture/SKILL.md | 22554 |
| .claude/skills/camera-frame-capture/references/implementation_detail.md | 31664 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | 15395 |
| .claude/skills/llm-guidance-orchestrator/references/implementation_detail.md | 19478 |
| .claude/skills/rag-knowledge-builder/SKILL.md | 10261 |
| .claude/skills/rag-knowledge-builder/references/implementation_detail.md | 7610 |
| .claude/skills/rag-realtime-search/SKILL.md | 10254 |
| .claude/skills/rag-realtime-search/references/implementation_detail.md | 11759 |
| .claude/skills/react-doctor/SKILL.md | 3553 |
| .claude/skills/tts-voice-streamer/SKILL.md | 16547 |
| .claude/skills/tts-voice-streamer/references/implementation_detail.md | 7560 |
| .claude/skills/websocket-gateway/SKILL.md | 20273 |
| .claude/skills/websocket-gateway/references/implementation_detail.md | 15073 |
| .claude/skills/xcode-build-management/SKILL.md | 6460 |
| .claude/skills/xcode-build-management/references/implementation_detail.md | 6926 |
| .claude/skills/yolo-obstacle-detection/SKILL.md | 17253 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | 29314 |
| .zcode/plans/plan-sess_2dbd0ff5-fe6e-450a-bd34-71718823db8d.md | 6084 |
| .zcode/plans/plan-sess_86a22c13-a4c7-4ae8-b69d-297eb1cca7c1.md | 8498 |
| .zcode/plans/plan-sess_a88e625c-d9d4-47c0-9ded-126be54ac215.md | 10768 |
| .zcode/plans/plan-sess_e737ed00-13c4-409b-8f47-a38bb4be49e2.md | 4475 |
| client/.expo/README.md | 889 |
| client/assets/models/yolo26n/EXPORT_SOURCE_260714.txt | 224 |
| client/ios/Pods/RCT-Folly/README.md | 11206 |
| client/ios/Pods/SDWebImage/README.md | 26796 |
| client/ios/Pods/SDWebImageWebPCoder/README.md | 10726 |
| client/ios/Pods/SocketRocket/README.md | 6721 |
| client/ios/Pods/boost/LICENSE_1_0.txt | 1361 |
| client/ios/Pods/boost/README.md | 1066 |
| client/ios/Pods/fast_float/README.md | 19746 |
| client/ios/Pods/fmt/README.md | 19681 |
| client/ios/Pods/libwebp/README.md | 1662 |
| client/ios/build/Build/Intermediates.noindex/Minchodan.build/Release-iphoneos/Minchodan.build/DerivedSources/Pods-Minchodan-checkManifestLockResult.txt | 8 |
| client/ios/build/Build/Intermediates.noindex/XCBuildData/1fac7d1fb4efe52d763d65281295f824.xcbuilddata/target-graph.txt | 94 |
| client/ios/build/Build/Intermediates.noindex/XCBuildData/510b3305c31c283e5f904cfec08d7218.xcbuilddata/target-graph.txt | 98526 |
| console/README.md | 4463 |
| docs/AGENTS.md | 400 |
| docs/Directory_Structure.md | 10714 |
| docs/README.md | 26176 |
| docs/dg.md | 9955 |
| docs/finetune_weight_analysis.md | 7621 |
| docs/yolo26n_custom_dataset_sources.md | 1982 |
| docs/changelogs/README.md | 2448 |
| docs/changelogs/TEMPLATE.md | 756 |
| docs/changelogs/dg.md | 74433 |
| docs/changelogs/dg2.md | 1775 |
| docs/changelogs/jh.md | 67096 |
| docs/changelogs/jy.md | 59954 |
| docs/changelogs/kb.md | 475582 |
| docs/changelogs/model_run_verification.md | 2017 |
| docs/changelogs/stage_safety_reflex.md | 16607 |
| docs/changelogs/th.md | 69374 |
| docs/changelogs/th_2026_07_12_share.md | 2932 |
| docs/db_tailscale_guide/README.md | 12948 |
| docs/design/api_specification.md | 62013 |
| docs/design/architecture.md | 55735 |
| docs/design/backend_db_architecture.md | 4377 |
| docs/design/behavior_and_risk_insight.md | 10633 |
| docs/design/indoor_fp_mitigation_design.md | 23799 |
| docs/design/minchodan_design_note.md | 19747 |
| docs/design/pipeline_stage_design.md | 10971 |
| docs/design/reflex_audio_specification.md | 15071 |
| docs/design/risk_ssot_contract.md | 6576 |
| docs/design/scene_classifier_gate_guide.md | 15874 |
| docs/dev-guides/course_codebase_guide.md | 108448 |
| docs/dev-guides/llm_collaboration_workflow.md | 10166 |
| docs/dev-guides/multi_agent_setup.md | 8373 |
| docs/dev-guides/integration/관제_UI_및_시나리오_연동_지침서.md | 6216 |
| docs/dev-guides/integration/서버_및_시스템_통합_기술_지침서.md | 5359 |
| docs/dev-guides/prompts/antigravity_agent_prompt__4_5_final.md | 13590 |
| docs/dev-guides/templates/신규_설계서_예시_2.md | 14016 |
| docs/handoff/2026-07-15_reflex_ood_handoff.md | 7672 |
| docs/macOS_xcode_build/ios_device_build_iteration_guide.md | 18578 |
| docs/macOS_xcode_build/xcode_mcp_setup_guide.md | 6539 |
| docs/mobile/android_aspect_ratio_calibration_report.md | 4033 |
| docs/mobile/android_bbox_missing_fix_plan.md | 4458 |
| docs/mobile/android_ondevice_tflite_build_plan.md | 2380 |
| docs/mobile/android_platform_patch_results.md | 7128 |
| docs/mobile/ios_android_bifurcation_contract.md | 26472 |
| docs/mobile/mobile_android_implementation_plan.md | 27155 |
| docs/mobile/mobile_app_implementation_plan.md | 27714 |
| docs/mobile/mobile_ios_implementation_plan.md | 34778 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | 37729 |
| docs/ops/ai_model_hardware_setup.md | 5067 |
| docs/ops/android_build_and_wireless_test_guide.md | 4859 |
| docs/ops/android_device_integration_guide.md | 20858 |
| docs/ops/android_eas_development_build_wireless_guide.md | 2843 |
| docs/ops/android_ondevice_tflite_completion_report.md | 1318 |
| docs/ops/android_ondevice_tflite_run_guide.md | 6283 |
| docs/ops/android_stt_recognition_issue_report.md | 10281 |
| docs/ops/android_wifi_usb_transport.md | 7354 |
| docs/ops/android_wireless_test_guide_v2.md | 15034 |
| docs/ops/code_quality_guide.md | 22081 |

---

## 6. Python 파일

| 파일 | 크기(bytes) |
| --- | --- |
| scripts/analyze_lidar_validation.py | 3153 |
| scripts/auto_publish_work.py | 18175 |
| scripts/bench_ondevice.py | 6967 |
| scripts/benchmark_ws_network.py | 12452 |
| scripts/build_convenience_db.py | 2691 |
| scripts/build_guide_clips.py | 3385 |
| scripts/build_safety_db.py | 3724 |
| scripts/convert_aihub_seg_to_yolo.py | 6792 |
| scripts/convert_yolo_to_coreml.py | 9259 |
| scripts/create_minchodan_dial_shortcut.py | 2843 |
| scripts/dev_redis_stub.py | 8224 |
| scripts/download_pretrained_weights.py | 1702 |
| scripts/eval_hitrate.py | 10062 |
| scripts/eval_segmentation_stairs.py | 5689 |
| scripts/export_mobile.py | 5634 |
| scripts/export_tflite.py | 3427 |
| scripts/generate_app_icons.py | 14480 |
| scripts/inspect_aihub_bbox_xml.py | 11433 |
| scripts/integration_test_pipeline.py | 6518 |
| scripts/merge_external_dataset.py | 4359 |
| scripts/prepare_aihub_yolo_detection.py | 12314 |
| scripts/project_scan.py | 14584 |
| scripts/resolve_conflicts.py | 1866 |
| scripts/run_desktop_full_training.py | 5851 |
| scripts/run_test_100_samples.py | 1857 |
| scripts/run_test_per_class.py | 3767 |
| scripts/run_yolo_tts_demo.py | 6652 |
| scripts/scan_aihub_walk_dataset.py | 12673 |
| scripts/slack_publisher.py | 7978 |
| scripts/train_segmentation_5class.py | 5186 |
| scripts/validate_agent_rules.py | 10805 |
| scripts/validate_class_samples.py | 4791 |
| scripts/verify_gpu.py | 1604 |
| scripts/verify_ios_integration.py | 7764 |
| scripts/verify_pretrained_weights.py | 2427 |
| scripts/obstacle_data_miner/__init__.py | 80 |
| scripts/obstacle_data_miner/class_specs.py | 11049 |
| scripts/obstacle_data_miner/config.py | 3926 |
| scripts/obstacle_data_miner/main.py | 7450 |
| scripts/obstacle_data_miner/seg_config.py | 1043 |
| scripts/obstacle_data_miner/train_classifier.py | 1267 |
| scripts/obstacle_data_miner/labelers/__init__.py | 29 |
| scripts/obstacle_data_miner/labelers/auto_labeler.py | 4780 |
| scripts/obstacle_data_miner/miners/__init__.py | 30 |
| scripts/obstacle_data_miner/miners/aihub_objdet_miner.py | 8493 |
| scripts/obstacle_data_miner/miners/aihub_seg_miner.py | 6489 |
| scripts/obstacle_data_miner/miners/api_dataset_collector.py | 4399 |
| scripts/obstacle_data_miner/miners/fiftyone_miner.py | 6358 |
| scripts/obstacle_data_miner/miners/kaggle_miner.py | 2341 |
| scripts/obstacle_data_miner/miners/web_scraper.py | 8168 |
| scripts/obstacle_data_miner/utils/__init__.py | 23 |
| scripts/obstacle_data_miner/utils/analyze_yolo_results.py | 5194 |
| scripts/obstacle_data_miner/utils/collection_plan.py | 1676 |
| scripts/obstacle_data_miner/utils/format_converter.py | 6682 |
| scripts/obstacle_data_miner/utils/import_scooterdet.py | 4286 |
| scripts/obstacle_data_miner/utils/inference_with_filter.py | 2948 |
| scripts/obstacle_data_miner/utils/prepare_cls_dataset.py | 2317 |
| scripts/obstacle_data_miner/utils/preview_jsons.py | 877 |
| scripts/obstacle_data_miner/utils/preview_xmls.py | 399 |
| scripts/obstacle_data_miner/utils/quarantine_suspect_images.py | 2915 |
| scripts/obstacle_data_miner/utils/visualize_samples.py | 4512 |
| server/__init__.py | 68 |
| server/main.py | 11876 |
| server/api/__init__.py | 38 |
| server/api/admin_member_router.py | 2263 |
| server/api/admin_router.py | 3207 |
| server/api/auth.py | 4573 |
| server/api/config.py | 2392 |
| server/api/dependencies.py | 2562 |
| server/api/detection_log_router.py | 5191 |
| server/api/heartbeat.py | 2689 |
| server/api/monitor.py | 4656 |
| server/api/schemas.py | 2512 |
| server/api/session_manager.py | 9359 |
| server/api/stt_router.py | 10233 |
| server/api/user_router.py | 2731 |
| server/api/ws_router.py | 50490 |
| server/bus/__init__.py | 164 |
| server/bus/producer.py | 2560 |
| server/bus/redis_client.py | 2510 |
| server/capture/__init__.py | 305 |
| server/capture/frame_decoder.py | 6754 |
| server/capture/stream_splitter.py | 4858 |
| server/db/base.py | 1311 |
| server/db/connection.py | 1814 |
| server/db/init_db.py | 2826 |
| server/db/models.py | 21196 |
| server/db/repositories.py | 14452 |
| server/db/schemas.py | 9471 |
| server/db/security.py | 2498 |
| server/detection/__init__.py | 1980 |
| server/detection/bytetrack_tracker.py | 6481 |
| server/detection/config.py | 4418 |
| server/detection/consumer.py | 57020 |
| server/detection/detection_pipeline.py | 15130 |
| server/detection/detector_interface.py | 932 |
| server/detection/direction.py | 4074 |
| server/detection/mock_detector.py | 959 |
| server/detection/path_risk.py | 3722 |
| server/detection/risk_rules.py | 9623 |
| server/detection/schemas.py | 4435 |
| server/detection/surface_departure.py | 6674 |
| server/detection/yolo_detector.py | 8695 |
| server/detection/yolo_segmentor.py | 5302 |
| server/detection/gates/__init__.py | 163 |
| server/detection/gates/head_level_gate.py | 4363 |
| server/detection/gates/reflex_gate.py | 7834 |
| server/detection/gates/surface_gate.py | 3622 |
| server/mcp/accessibility_simulator.py | 4247 |
| server/mcp/audio_validator.py | 5016 |
| server/mcp/cache_monitor.py | 4234 |
| server/mcp/gpu_monitor.py | 3671 |
| server/mcp/langsmith_tracer.py | 3310 |
| server/mcp/manager.py | 8231 |
| server/mcp/slack_notifier.py | 4761 |
| server/navigation/__init__.py | 96 |
| server/navigation/manager.py | 11814 |
| server/navigation/navigation_filter.py | 9429 |
| server/navigation/server.py | 17143 |
| server/navigation/tts_engine.py | 3473 |

---

## 7. 키워드 기반 관련 파일

### yolo

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | yolo, detect | 190 |
| .gitignore | yolo, detect, train, bbox | 351 |
| AGENTS.md | yolo, ultralytics, detect, train | 236 |
| GEMINI.md | yolo, ultralytics, detect, train | 236 |
| README.md | yolo, ultralytics, detect, train | 376 |
| SKILLS.md | yolo, detect, train, bbox | 177 |
| pyproject.toml | ultralytics, train | 161 |
| requirements.txt | ultralytics | 169 |
| .antigravity/rules.md | yolo, detect | 172 |
| .claude/settings.local.json | yolo, detect, train | 544 |
| client/app.json | predict | 83 |
| client/package-lock.json | detect | 6976 |
| console/README.md | detect, bbox | 108 |
| docker/docker-compose.macos.yml | yolo | 104 |
| docker/windows_docker_start.bat | detect | 153 |
| docs/Directory_Structure.md | yolo, detect, predict, train | 154 |
| docs/README.md | yolo, detect, confidence | 248 |
| docs/dg.md | detect, bbox | 78 |
| docs/finetune_weight_analysis.md | yolo, detect | 77 |
| docs/yolo26n_custom_dataset_sources.md | yolo, detect, bbox | 40 |
| scripts/SCRIPT_GENERATION_PROMPT.md | yolo, detect | 381 |
| scripts/auto_publish_work.py | detect | 486 |
| scripts/bench_ondevice.py | yolo, ultralytics, detect, predict | 224 |
| scripts/benchmark_ws_network.py | detect | 338 |
| scripts/build_guide_clips.py | detect | 101 |
| scripts/convert_aihub_seg_to_yolo.py | yolo, ultralytics, train, class_id | 204 |
| scripts/convert_yolo_to_coreml.py | yolo, ultralytics, detect, predict, confidence | 219 |
| scripts/dev_ios_lab.sh | detect | 396 |
| scripts/download_pretrained_weights.py | yolo, ultralytics, detect | 52 |
| scripts/eval_hitrate.py | predict | 285 |
| scripts/eval_segmentation_stairs.py | yolo, ultralytics, predict, class_id | 148 |
| scripts/export_mobile.py | yolo, ultralytics, detect | 171 |
| scripts/export_tflite.py | yolo, ultralytics, detect | 103 |
| scripts/fix_android_usb_ws.ps1 | detect | 24 |
| scripts/generate_app_icons.py | bbox | 380 |
| scripts/inspect_aihub_bbox_xml.py | yolo, bbox | 360 |
| scripts/integration_test_pipeline.py | yolo, detect, bbox, confidence | 151 |
| scripts/launch_agents.sh | yolo, ultralytics, detect, train, bbox | 218 |
| scripts/merge_external_dataset.py | yolo, detect, train | 113 |
| scripts/postwork.bat | detect | 338 |
| scripts/postwork.ps1 | detect | 285 |
| scripts/postwork.sh | detect | 301 |
| scripts/prepare_aihub_yolo_detection.py | yolo, ultralytics, detect, train, class_id | 371 |
| scripts/prework.bat | yolo, detect | 247 |
| scripts/prework.ps1 | yolo, detect | 209 |
| scripts/prework.sh | yolo, detect | 222 |
| scripts/project_scan.py | yolo, ultralytics, detect, predict, train, bbox, class_id, confidence | 469 |
| scripts/run_desktop_full_training.py | yolo, detect, train, bbox | 170 |
| scripts/run_test_100_samples.py | yolo, ultralytics, detect, predict, train | 61 |
| scripts/run_test_per_class.py | yolo, ultralytics, detect, predict, train | 120 |
| scripts/run_yolo_tts_demo.py | yolo, detect, predict, bbox, confidence | 208 |
| scripts/scan_aihub_walk_dataset.py | yolo | 361 |
| scripts/train_segmentation_5class.py | yolo, ultralytics, train | 139 |
| scripts/validate_class_samples.py | yolo, ultralytics, detect, predict, train | 149 |
| scripts/verify_ios_integration.py | yolo, detect | 193 |
| scripts/verify_pretrained_weights.py | yolo, detect, predict | 69 |
| server/main.py | detect | 285 |
| tests/test_29_classes_inference.py | yolo, ultralytics, predict | 83 |
| tests/test_api_ws.py | detect | 125 |
| tests/test_clock_direction.py | detect, bbox | 134 |
| tests/test_cognitive_fields.py | detect, bbox | 77 |
| tests/test_departure_hysteresis.py | detect | 145 |
| tests/test_detection.py | yolo, detect, predict, bbox, confidence | 946 |
| tests/test_e2e_pipeline.py | yolo, detect, bbox, confidence | 98 |
| tests/test_false_positive.py | detect | 122 |
| tests/test_fast_lane.py | detect | 146 |
| tests/test_frame_decode.py | detect | 545 |
| tests/test_langgraph.py | detect, bbox, confidence | 386 |
| tests/test_path_risk.py | detect | 95 |
| tests/test_pipeline_debug.py | detect, bbox, confidence | 140 |
| tests/test_retriever.py | detect, confidence | 88 |
| tests/test_risk_event_broadcast.py | detect, confidence | 53 |
| tests/test_risk_ssot.py | detect, confidence | 107 |
| tests/test_stt_to_llm_bridge_template.py | detect | 371 |
| tests/test_stt_wait_notice.py | detect | 74 |
| tests/test_surface_departure.py | detect | 161 |
| tests/test_tts_prewarm.py | detect | 142 |
| tests/test_ws_echo.py | detect | 184 |
| tests/test_ws_router_stt.py | detect | 281 |
| training/train_common.py | yolo, ultralytics, train | 106 |

### langchain

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | langchain, chain | 190 |
| .gitignore | langchain, langgraph, agent, tool, chain | 351 |
| AGENTS.md | langchain, langgraph, agent, chain | 236 |
| CLAUDE.md | agent | 17 |
| GEMINI.md | langchain, langgraph, agent, chain | 236 |
| README.md | langgraph, agent | 376 |
| SKILLS.md | langgraph, agent | 177 |
| pyproject.toml | langgraph, agent, tool | 161 |
| requirements.txt | langchain, langgraph, tool, chain | 169 |
| .antigravity/rules.md | langchain, langgraph, agent, chain | 172 |
| .claude/settings.local.json | langgraph, agent, chain | 544 |
| .vscode/settings.json | tool | 14 |
| .xcodebuildmcp/Copy_config.yaml | chain | 11 |
| client/package-lock.json | agent, tool, chain | 6976 |
| client/package.json | chain | 45 |
| client/tunnel.bat | tool | 6 |
| docker/docker-compose.yml | tool | 93 |
| docs/AGENTS.md | agent | 5 |
| docs/Directory_Structure.md | langgraph | 154 |
| docs/README.md | langgraph, agent | 248 |
| scripts/SCRIPT_GENERATION_PROMPT.md | langgraph, agent, Runnable | 381 |
| scripts/auto_publish_work.py | langgraph | 486 |
| scripts/build_safety_db.py | langchain, chain | 104 |
| scripts/convert_yolo_to_coreml.py | tool | 219 |
| scripts/eval_hitrate.py | langchain, chain | 285 |
| scripts/launch_agents.sh | langgraph, agent, tool | 218 |
| scripts/postwork.bat | langgraph | 338 |
| scripts/postwork.ps1 | langgraph | 285 |
| scripts/postwork.sh | langgraph | 301 |
| scripts/prework.bat | langgraph, agent | 247 |
| scripts/prework.ps1 | langgraph, agent | 209 |
| scripts/prework.sh | langgraph, agent | 222 |
| scripts/project_scan.py | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 469 |
| scripts/slack_publisher.py | tool | 223 |
| scripts/validate_agent_rules.py | agent | 281 |
| scripts/verify_ios_integration.py | langgraph | 193 |
| tests/test_departure_hysteresis.py | langgraph | 145 |
| tests/test_fast_lane.py | langgraph | 146 |
| tests/test_frame_decode.py | langgraph | 545 |
| tests/test_langgraph.py | langgraph | 386 |
| tests/test_mcp_new.py | langchain, chain | 131 |
| tests/test_retriever.py | langchain, chain | 88 |
| .zcode/plans/plan-sess_86a22c13-a4c7-4ae8-b69d-297eb1cca7c1.md | agent | 164 |
| .zcode/plans/plan-sess_a88e625c-d9d4-47c0-9ded-126be54ac215.md | agent | 141 |
| docs/changelogs/dg.md | langchain, langgraph, agent, tool, chain | 584 |
| docs/changelogs/jh.md | langgraph, agent | 872 |
| docs/changelogs/jy.md | agent | 548 |
| docs/changelogs/kb.md | langchain, langgraph, agent, chain, ChatOpenAI | 2890 |
| docs/changelogs/th.md | langchain, langgraph, agent, tool, chain | 828 |
| docs/design/api_specification.md | langgraph | 925 |
| docs/design/architecture.md | langchain, langgraph, chain | 694 |
| docs/design/behavior_and_risk_insight.md | langgraph | 95 |
| docs/design/minchodan_design_note.md | langchain, langgraph, chain | 215 |
| docs/design/pipeline_stage_design.md | langchain, langgraph, chain | 180 |
| docs/dev-guides/course_codebase_guide.md | langchain, langgraph, agent, tool, chain, Runnable, ChatOpenAI | 2986 |
| docs/dev-guides/llm_collaboration_workflow.md | agent | 168 |
| docs/dev-guides/multi_agent_setup.md | agent | 179 |
| docs/handoff/2026-07-15_reflex_ood_handoff.md | langchain, chain | 54 |
| docs/macOS_xcode_build/ios_device_build_iteration_guide.md | tool | 436 |
| docs/macOS_xcode_build/xcode_mcp_setup_guide.md | tool | 154 |
| docs/mobile/android_bbox_missing_fix_plan.md | langchain, chain | 57 |
| docs/mobile/android_ondevice_tflite_build_plan.md | langchain, chain | 44 |
| docs/mobile/ios_android_bifurcation_contract.md | agent | 255 |
| docs/mobile/mobile_android_implementation_plan.md | langgraph, agent | 492 |
| docs/mobile/mobile_app_implementation_plan.md | langgraph, agent | 584 |
| docs/mobile/mobile_ios_implementation_plan.md | langgraph, agent | 615 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | agent, tool | 573 |
| docs/ops/ai_model_hardware_setup.md | langgraph | 75 |
| docs/ops/android_build_and_wireless_test_guide.md | langchain, chain | 97 |
| docs/ops/android_device_integration_guide.md | langchain, chain | 470 |
| docs/ops/android_ondevice_tflite_completion_report.md | langchain, chain | 22 |
| docs/ops/android_ondevice_tflite_run_guide.md | langchain, chain | 127 |
| docs/ops/code_quality_guide.md | langchain, agent, tool, chain, ChatOpenAI | 661 |
| docs/ops/deployment_guide.md | langchain, tool, chain | 361 |
| docs/ops/dev_8b2f606_improvement_plan.md | langgraph, agent | 108 |
| docs/ops/environment_variables.md | langchain, langgraph, chain | 305 |
| docs/ops/git_branching_strategy.md | langchain, langgraph, chain | 144 |
| docs/ops/integration_scenario_test.md | langgraph | 127 |
| docs/ops/ios_android_bifurcation_contract.md | agent | 234 |
| docs/ops/minchodan_optimization_checklist.md | langchain, chain | 25 |

### fastapi

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | fastapi | 190 |
| .gitignore | fastapi, uvicorn | 351 |
| AGENTS.md | fastapi, uvicorn | 236 |
| GEMINI.md | fastapi, uvicorn | 236 |
| README.md | fastapi, uvicorn | 376 |
| SKILLS.md | fastapi | 177 |
| pyproject.toml | fastapi | 161 |
| requirements.txt | fastapi, uvicorn | 169 |
| .antigravity/rules.md | fastapi, uvicorn | 172 |
| .claude/settings.local.json | fastapi, uvicorn | 544 |
| docker/Dockerfile | fastapi, uvicorn | 45 |
| docker/docker-compose.macos.yml | fastapi | 104 |
| docker/docker-compose.yml | fastapi | 93 |
| docker/linux_docker_start.sh | fastapi | 340 |
| docker/macos_docker_start.sh | fastapi | 245 |
| docker/windows_docker_start.bat | fastapi | 153 |
| docs/Directory_Structure.md | fastapi, APIRouter | 154 |
| docs/README.md | fastapi | 248 |
| scripts/SCRIPT_GENERATION_PROMPT.md | fastapi | 381 |
| scripts/dev_ios_lab.sh | fastapi | 396 |
| scripts/postwork.bat | fastapi | 338 |
| scripts/postwork.ps1 | fastapi | 285 |
| scripts/postwork.sh | fastapi | 301 |
| scripts/project_scan.py | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 469 |
| scripts/verify_ios_integration.py | fastapi, uvicorn | 193 |
| server/main.py | fastapi | 285 |
| tests/test_admin_service_login.py | fastapi, HTTPException | 124 |
| tests/test_api_ws.py | fastapi | 125 |
| tests/test_false_positive.py | fastapi | 122 |
| tests/test_mcp_integration.py | fastapi | 78 |
| tests/test_session_manager.py | fastapi | 49 |
| tests/test_stt_router_nonblocking.py | fastapi | 105 |
| tests/test_user_service.py | fastapi, HTTPException | 170 |
| .zcode/plans/plan-sess_2dbd0ff5-fe6e-450a-bd34-71718823db8d.md | BaseModel | 141 |
| .zcode/plans/plan-sess_a88e625c-d9d4-47c0-9ded-126be54ac215.md | fastapi | 141 |
| docs/changelogs/dg.md | fastapi, uvicorn | 584 |
| docs/changelogs/jy.md | fastapi | 548 |
| docs/changelogs/kb.md | fastapi, uvicorn | 2890 |
| docs/changelogs/model_run_verification.md | fastapi | 32 |
| docs/changelogs/th.md | fastapi, uvicorn | 828 |
| docs/changelogs/th_2026_07_12_share.md | fastapi | 71 |
| docs/db_tailscale_guide/README.md | fastapi | 316 |
| docs/design/api_specification.md | fastapi | 925 |
| docs/design/architecture.md | fastapi, APIRouter, uvicorn | 694 |
| docs/design/backend_db_architecture.md | fastapi, HTTPException | 60 |
| docs/design/minchodan_design_note.md | fastapi, APIRouter, uvicorn | 215 |
| docs/design/pipeline_stage_design.md | fastapi, APIRouter | 180 |
| docs/dev-guides/course_codebase_guide.md | fastapi, APIRouter, uvicorn, BaseModel, HTTPException | 2986 |
| docs/mobile/android_aspect_ratio_calibration_report.md | fastapi | 39 |
| docs/mobile/mobile_android_implementation_plan.md | fastapi, uvicorn | 492 |
| docs/mobile/mobile_app_implementation_plan.md | fastapi, uvicorn | 584 |
| docs/mobile/mobile_ios_implementation_plan.md | fastapi, uvicorn | 615 |
| docs/mobile/ondevice_inference_engine_isolation_plan.md | fastapi, uvicorn | 573 |
| docs/ops/ai_model_hardware_setup.md | fastapi | 75 |
| docs/ops/android_build_and_wireless_test_guide.md | uvicorn | 97 |
| docs/ops/android_device_integration_guide.md | fastapi | 470 |
| docs/ops/android_ondevice_tflite_run_guide.md | fastapi | 127 |
| docs/ops/android_stt_recognition_issue_report.md | fastapi | 233 |
| docs/ops/android_wifi_usb_transport.md | fastapi | 140 |
| docs/ops/android_wireless_test_guide_v2.md | fastapi | 393 |
| docs/ops/deployment_guide.md | fastapi, uvicorn | 361 |
| docs/ops/environment_variables.md | fastapi | 305 |
| docs/ops/event_frame_image_loss_investigation.md | fastapi | 270 |
| docs/ops/integration_scenario_test.md | fastapi | 127 |
| docs/ops/minchodan_optimization_checklist.md | fastapi | 25 |
| docs/ops/minchodan_optimization_final_report.md | fastapi | 63 |
| docs/ops/minchodan_optimization_plan.md | fastapi | 148 |
| docs/ops/network_latency_benchmark.md | fastapi | 114 |
| docs/ops/redis_streams_schema.md | fastapi | 74 |
| docs/ops/tailscale_connection_guide.md | fastapi | 113 |
| docs/ops/test_specification.md | fastapi, uvicorn | 370 |
| docs/ops/wireless_test_guide.md | fastapi | 169 |
| docs/research/mitos_improvement_roadmap.md | fastapi | 153 |
| docs/research/sensevoice_stt_feasibility.md | fastapi | 122 |
| docs/stage-guides/stage1_websocket_design.md | fastapi | 117 |
| docs/stage-guides/stage2_capture_design.md | fastapi | 490 |
| docs/stage-guides/stage3_detection_code_review.md | fastapi | 242 |
| docs/stage-guides/stage3_detection_design.md | fastapi, BaseModel | 614 |
| server/api/admin_member_router.py | fastapi, APIRouter | 54 |
| server/api/admin_router.py | fastapi, APIRouter | 61 |

### openai

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | OpenAI, OPENAI_API_KEY | 190 |
| .gitignore | OpenAI | 351 |
| AGENTS.md | OpenAI | 236 |
| GEMINI.md | OpenAI | 236 |
| README.md | OpenAI, OPENAI_API_KEY | 376 |
| .antigravity/rules.md | OpenAI | 172 |
| docs/README.md | OpenAI | 248 |
| scripts/project_scan.py | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 469 |
| tests/test_mcp_gpu.py | OpenAI, OPENAI_API_KEY | 78 |
| docs/changelogs/kb.md | OpenAI | 2890 |
| docs/design/architecture.md | OpenAI, OPENAI_API_KEY | 694 |
| docs/design/minchodan_design_note.md | OpenAI | 215 |
| docs/design/pipeline_stage_design.md | OpenAI | 180 |
| docs/dev-guides/course_codebase_guide.md | OpenAI, AsyncOpenAI, OPENAI_API_KEY, chat.completions, responses | 2986 |
| docs/dev-guides/multi_agent_setup.md | OpenAI | 179 |
| docs/ops/code_quality_guide.md | OpenAI, OPENAI_API_KEY | 661 |
| docs/ops/environment_variables.md | OpenAI, OPENAI_API_KEY | 305 |
| docs/ops/integration_scenario_test.md | OpenAI | 127 |
| docs/ops/test_specification.md | OpenAI | 370 |
| docs/research/gemini_fallback_feasibility.md | OpenAI | 80 |
| docs/research/outdoor_guidance_refinement_roadmap.md | OpenAI | 492 |
| docs/stage-guides/stage4_5_data_replacement_guide.md | OpenAI | 96 |
| docs/stage-guides/stage4_5_rag_design.md | OpenAI | 342 |
| docs/stage-guides/stage6_orchestration_design.md | OpenAI, OPENAI_API_KEY | 523 |
| docs/stage-guides/stage7_tts_design.md | OpenAI | 244 |
| server/api/detection_log_router.py | responses | 115 |
| server/api/monitor.py | responses | 109 |
| server/bus/redis_client.py | responses | 88 |
| server/mcp/gpu_monitor.py | OpenAI | 92 |
| server/mcp/manager.py | responses | 197 |
| server/navigation/server.py | responses | 424 |
| server/orchestration/llm_client_factory.py | OpenAI, OPENAI_API_KEY | 337 |
| server/rag/embedding_engine_factory.py | OpenAI | 139 |
| .agents/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 370 |
| .agents/skills/tts-voice-streamer/SKILL.md | OpenAI | 347 |
| .claude/skills/llm-guidance-orchestrator/SKILL.md | OpenAI, OPENAI_API_KEY | 370 |
| .claude/skills/tts-voice-streamer/SKILL.md | OpenAI | 347 |
| docs/dev-guides/templates/신규_설계서_예시_2.md | OpenAI | 235 |
| server/orchestration/nodes/l2_generator.py | OpenAI | 176 |
| .agents/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |
| .claude/skills/yolo-obstacle-detection/references/implementation_detail.md | responses | 930 |
| client/ios/build/Build/Intermediates.noindex/Pods.build/Release-iphoneos/Expo.build/Objects-normal/arm64/Expo-OutputFileMap.json | responses | 96 |

### dataset

| 파일 | 매칭 키워드 | 라인 수 |
| --- | --- | --- |
| .env.example | dataset, json, frame | 190 |
| .gitignore | dataset, images, json, frame | 351 |
| AGENTS.md | labels, json, frame | 236 |
| GEMINI.md | labels, json, frame | 236 |
| README.md | dataset, json, frame | 376 |
| SKILLS.md | labels, json, frame | 177 |
| opencode.json | json | 9 |
| pyproject.toml | annotation | 161 |
| requirements.txt | json | 169 |
| .antigravity/rules.md | frame | 172 |
| .claude/settings.local.json | dataset, json, frame | 544 |
| client/app.json | frame | 83 |
| client/babel.config.js | frame | 10 |
| client/package-lock.json | json, annotation, frame | 6976 |
| console/package-lock.json | json, frame | 1809 |
| console/tsconfig.json | json | 22 |
| data/convenience_guidelines.json | dataset | 607 |
| docker/windows_docker_start.bat | images | 153 |
| docs/Directory_Structure.md | dataset, images, labels, json, frame | 154 |
| docs/README.md | frame | 248 |
| docs/dg.md | frame | 78 |
| docs/yolo26n_custom_dataset_sources.md | dataset, images | 40 |
| scripts/SCRIPT_GENERATION_PROMPT.md | frame | 381 |
| scripts/auto_publish_work.py | frame | 486 |
| scripts/bench_ondevice.py | frame | 224 |
| scripts/benchmark_ws_network.py | json | 338 |
| scripts/build_convenience_db.py | json | 86 |
| scripts/build_guide_clips.py | annotation | 101 |
| scripts/build_safety_db.py | json | 104 |
| scripts/convert_aihub_seg_to_yolo.py | dataset, images, labels, json, annotation | 204 |
| scripts/create_minchodan_dial_shortcut.py | annotation | 94 |
| scripts/dev_ios_lab.sh | json | 396 |
| scripts/eval_hitrate.py | labels, json | 285 |
| scripts/eval_segmentation_stairs.py | dataset, images, labels | 148 |
| scripts/generate_app_icons.py | images, json | 380 |
| scripts/inspect_aihub_bbox_xml.py | dataset, images, labels, json | 360 |
| scripts/integration_test_pipeline.py | frame | 151 |
| scripts/launch_agents.sh | json | 218 |
| scripts/merge_external_dataset.py | dataset, images, labels | 113 |
| scripts/postwork.bat | frame | 338 |
| scripts/postwork.ps1 | frame | 285 |
| scripts/postwork.sh | frame | 301 |
| scripts/prepare_aihub_yolo_detection.py | dataset, images, labels, json, annotation | 371 |
| scripts/prework.bat | frame | 247 |
| scripts/prework.ps1 | frame | 209 |
| scripts/prework.sh | frame | 222 |
| scripts/project_scan.py | dataset, data.yaml, images, labels, json, annotation, frame | 469 |
| scripts/project_scan_verification.md | json | 61 |
| scripts/resolve_conflicts.py | json | 68 |
| scripts/run_desktop_full_training.py | dataset, images, annotation | 170 |
| scripts/run_test_100_samples.py | dataset, images | 61 |
| scripts/run_test_per_class.py | dataset, images, labels | 120 |
| scripts/run_yolo_tts_demo.py | images, json, frame | 208 |
| scripts/scan_aihub_walk_dataset.py | dataset, json | 361 |
| scripts/slack_publisher.py | json | 223 |
| scripts/train_segmentation_5class.py | dataset, data.yaml, images, labels | 139 |
| scripts/validate_agent_rules.py | annotation | 281 |
| scripts/validate_class_samples.py | images, labels | 149 |
| scripts/verify_ios_integration.py | json, frame | 193 |
| scripts/verify_pretrained_weights.py | frame | 69 |
| server/main.py | frame | 285 |
| tests/test_29_classes_inference.py | frame | 83 |
| tests/test_api_ws.py | json, frame | 125 |
| tests/test_clock_direction.py | frame | 134 |
| tests/test_db_builder.py | frame | 69 |
| tests/test_departure_hysteresis.py | frame | 145 |
| tests/test_detection.py | json, frame | 946 |
| tests/test_e2e_pipeline.py | labels, frame | 98 |
| tests/test_event_frame_store.py | frame | 139 |
| tests/test_fallback.py | labels | 42 |
| tests/test_false_positive.py | json, frame | 122 |
| tests/test_fast_lane.py | frame | 146 |
| tests/test_frame_decode.py | json, frame | 545 |
| tests/test_frame_extractor.py | frame | 55 |
| tests/test_mcp_integration.py | json | 78 |
| tests/test_path_risk.py | frame | 95 |
| tests/test_reflex_and_nav.py | json | 63 |
| tests/test_retriever.py | labels, json | 88 |
| tests/test_session_manager.py | json | 49 |
| tests/test_surface_departure.py | frame | 161 |

---

## 8. 다음 작업 제안

| 순서 | 작업 |
| --- | --- |
| 1 | YOLO 관련 파일을 열어 실제 탐지/추론 구조와 모델 경로를 확인합니다. |
| 2 | LangChain/LangGraph 관련 파일을 열어 탐지 JSON이 연결될 입력 스키마를 확인합니다. |
| 3 | 데이터셋 원본 폴더를 별도 스캔하여 라벨 형식과 YOLO 변환 가능성을 판단합니다. |
| 4 | 확인된 라벨 형식 기준으로 class_mapping.json과 변환 계획을 작성합니다. |
