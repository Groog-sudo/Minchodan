# -*- coding: utf-8 -*-
"""길댕 브랜드 자산의 플랫폼별 규격과 설정 연결을 검증합니다."""

import json
import struct
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_info(relative_path: str) -> tuple[int, int, int]:
    data = (PROJECT_ROOT / relative_path).read_bytes()[:26]
    assert data[:8] == PNG_SIGNATURE
    width, height = struct.unpack(">II", data[16:24])
    color_type = data[25]
    return width, height, color_type


def test_canonical_brand_sources_are_preserved() -> None:
    expected = {
        "gildang-mascot.jpg",
        "gildang-symbol.jpg",
        "gildang-wordmark.jpg",
        "gildang-symbol-voice.jpg",
        "gildang-touch-icon.jpg",
        "gildang-favicon-16.jpg",
        "gildang-favicon-32.jpg",
        "gildang-favicon.ico",
    }
    brand_dir = PROJECT_ROOT / "assets" / "brand"
    assert expected.issubset({path.name for path in brand_dir.iterdir()})


def test_client_icon_and_splash_match_native_contracts() -> None:
    assert _png_info("client/assets/icon.png") == (1024, 1024, 2)
    assert _png_info("client/assets/splash-loading.png")[:2] == (1179, 2556)
    assert _png_info(
        "client/ios/Minchodan/Images.xcassets/AppIcon.appiconset/"
        "App-Icon-1024x1024@1x.png"
    ) == (1024, 1024, 2)
    assert _png_info(
        "client/ios/Minchodan/Images.xcassets/SplashScreen.imageset/SplashScreen.png"
    )[:2] == (1179, 2556)

    app_config = json.loads((PROJECT_ROOT / "client" / "app.json").read_text(encoding="utf-8"))
    expo = app_config["expo"]
    assert expo["icon"] == "./assets/icon.png"
    assert expo["splash"]["image"] == "./assets/splash-loading.png"
    assert expo["splash"]["backgroundColor"] == "#FFFFFF"


def test_android_launcher_and_splash_density_sizes() -> None:
    expected = {
        "mdpi": ((48, 48), (108, 108), (288, 624)),
        "hdpi": ((72, 72), (162, 162), (432, 936)),
        "xhdpi": ((96, 96), (216, 216), (576, 1248)),
        "xxhdpi": ((144, 144), (324, 324), (864, 1873)),
        "xxxhdpi": ((192, 192), (432, 432), (1152, 2497)),
    }
    for density, (legacy_size, adaptive_size, splash_size) in expected.items():
        mipmap_dir = f"client/android/app/src/main/res/mipmap-{density}"
        drawable_dir = f"client/android/app/src/main/res/drawable-{density}"
        assert _png_info(f"{mipmap_dir}/ic_launcher.webp")[:2] == legacy_size
        assert _png_info(f"{mipmap_dir}/ic_launcher_round.webp")[:2] == legacy_size
        assert _png_info(f"{mipmap_dir}/ic_launcher_foreground.webp")[:2] == adaptive_size
        assert _png_info(f"{mipmap_dir}/ic_launcher_monochrome.webp")[:2] == adaptive_size
        assert _png_info(f"{drawable_dir}/splashscreen_logo.png")[:2] == splash_size


def test_web_and_server_favicons_use_supplied_sizes() -> None:
    assert _png_info("console/public/favicon-16x16.png")[:2] == (16, 16)
    assert _png_info("console/public/favicon-32x32.png")[:2] == (32, 32)
    assert _png_info("console/public/apple-touch-icon.png")[:2] == (180, 180)

    ico_header = (PROJECT_ROOT / "console" / "public" / "favicon.ico").read_bytes()[:6]
    reserved, icon_type, image_count = struct.unpack("<HHH", ico_header)
    assert (reserved, icon_type, image_count) == (0, 1, 6)

    assert (PROJECT_ROOT / "server" / "static" / "brand" / "favicon.ico").is_file()
    server_main = (PROJECT_ROOT / "server" / "main.py").read_text(encoding="utf-8")
    assert 'methods=["GET", "HEAD"]' in server_main
    navigation_html = (PROJECT_ROOT / "server" / "navigation" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "/brand/gildang-wordmark.png" in navigation_html
    assert "/favicon.ico" in navigation_html
