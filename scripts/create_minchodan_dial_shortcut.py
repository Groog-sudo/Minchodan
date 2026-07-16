#!/usr/bin/env python3
"""MinchodanDial 단축어(.shortcut) plist 생성 및 서명."""

from __future__ import annotations

import plistlib
import subprocess  # nosec B404
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "client" / "assets" / "shortcuts"
RAW_NAME = "MinchodanDial.shortcut"
SIGNED_NAME = "MinchodanDial_signed.shortcut"


def build_shortcut_plist() -> dict:
    return {
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.call",
                "WFWorkflowActionParameters": {
                    "WFCallType": "Custom",
                    "WFCallCustomPhoneNumber": {
                        "Value": {
                            "attachmentsByRange": {
                                "{0, 1}": {
                                    "Type": "ExtensionInput",
                                }
                            },
                            "string": "\ufffc",
                        },
                        "WFSerializationType": "WFTextTokenString",
                    },
                    "IntentAppDefinition": {
                        "BundleIdentifier": "com.apple.ShortcutsUI",
                        "Name": "Shortcuts",
                    },
                },
            }
        ],
        "WFWorkflowClientVersion": "2700.0.4",
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowIcon": {
            "WFWorkflowIconGlyphNumber": 59511,
            "WFWorkflowIconStartColor": 4282601983,
        },
        "WFWorkflowImportQuestions": [],
        "WFWorkflowInputContentItemClasses": [
            "WFStringContentItem",
            "WFPhoneNumberContentItem",
        ],
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowName": "MinchodanDial",
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowTypes": [],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUT_DIR / RAW_NAME
    signed_path = OUT_DIR / SIGNED_NAME

    with raw_path.open("wb") as fp:
        plistlib.dump(build_shortcut_plist(), fp)

    sign_cmd = [
        "shortcuts",
        "sign",
        "--mode",
        "anyone",
        "--input",
        str(raw_path),
        "--output",
        str(signed_path),
    ]
    result = subprocess.run(sign_cmd, capture_output=True, text=True)  # nosec B603 B607
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        return result.returncode

    print(f"created: {raw_path}")
    print(f"signed: {signed_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
