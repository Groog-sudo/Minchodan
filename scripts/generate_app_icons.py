import os
import sys

if sys.stdout.encoding != "utf-8":
    import contextlib

    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "client", "assets")
SOURCE_LOGO = os.path.join(ASSETS_DIR, "gildang-logo.jpeg")
IOS_APPICON_DIR = os.path.join(
    PROJECT_ROOT, "client", "ios", "Minchodan", "Images.xcassets", "AppIcon.appiconset"
)
ANDROID_RES_DIR = os.path.join(PROJECT_ROOT, "client", "android", "app", "src", "main", "res")

# density -> (레거시 ic_launcher 표시 크기, 어댑티브 108dp 캔버스 크기)
ANDROID_DENSITIES = {
    "mdpi": (48, 108),
    "hdpi": (72, 162),
    "xhdpi": (96, 216),
    "xxhdpi": (144, 324),
    "xxxhdpi": (192, 432),
}

BG_COLOR = (231, 231, 233)
CHROMA_THRESHOLD = 18


def content_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """배경색과 다른 픽셀(로고 실제 내용)의 바운딩 박스를 찾는다."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            dist = ((r - BG_COLOR[0]) ** 2 + (g - BG_COLOR[1]) ** 2 + (b - BG_COLOR[2]) ** 2) ** 0.5
            if dist >= CHROMA_THRESHOLD:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def make_square_master(img: Image.Image, margin_ratio: float = 0.06) -> Image.Image:
    """로고 내용(강아지+GILDANG 텍스트) 바운딩 박스를 기준으로 여백을 최소화한 정사각형을 만든다.
    아이콘에 로고가 꽉 차 보이도록 레터박싱 대신 내용 중심 크롭을 사용한다."""
    minx, miny, maxx, maxy = content_bbox(img)
    content_w, content_h = maxx - minx, maxy - miny
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    side = max(content_w, content_h) * (1 + margin_ratio)

    canvas = Image.new("RGB", (int(side), int(side)), BG_COLOR)
    crop_box = (int(cx - side / 2), int(cy - side / 2), int(cx + side / 2), int(cy + side / 2))
    # 원본 범위를 벗어나는 부분은 배경색 캔버스가 그대로 채워지도록 교집합만 크롭한다.
    src_w, src_h = img.size
    isect = (
        max(0, crop_box[0]),
        max(0, crop_box[1]),
        min(src_w, crop_box[2]),
        min(src_h, crop_box[3]),
    )
    cropped = img.crop(isect)
    paste_x = isect[0] - crop_box[0]
    paste_y = isect[1] - crop_box[1]
    canvas.paste(cropped, (paste_x, paste_y))
    return canvas


def chroma_key_transparent(img: Image.Image) -> Image.Image:
    """배경색과 가까운 픽셀을 투명 처리해 로고(강아지+GILDANG)만 남긴다."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            dist = ((r - BG_COLOR[0]) ** 2 + (g - BG_COLOR[1]) ** 2 + (b - BG_COLOR[2]) ** 2) ** 0.5
            if dist < CHROMA_THRESHOLD:
                pixels[x, y] = (r, g, b, 0)
    return rgba


def fit_on_transparent_canvas(
    img: Image.Image, canvas_size: int, safe_zone_ratio: float
) -> Image.Image:
    """투명 배경 정사각 캔버스 중앙에 세이프존 비율만큼 축소 배치(안드로이드 어댑티브 아이콘용)."""
    content_size = int(canvas_size * safe_zone_ratio)
    fitted = img.copy()
    fitted.thumbnail((content_size, content_size), Image.LANCZOS)
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset = ((canvas_size - fitted.width) // 2, (canvas_size - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)
    return canvas


def to_monochrome(img: Image.Image) -> Image.Image:
    """알파 형태는 유지하되 RGB를 흰색으로 채운 실루엣(안드로이드 monochrome 아이콘 규격)."""
    alpha = img.split()[-1]
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    white.putalpha(alpha)
    return white


def main() -> None:
    if not os.path.exists(SOURCE_LOGO):
        print(f"Error: 원본 로고를 찾을 수 없습니다: {SOURCE_LOGO}")
        sys.exit(1)

    source = Image.open(SOURCE_LOGO)
    square_master = make_square_master(source)

    # iOS/웹 아이콘 (알파 없는 불투명 정사각형)
    icon_1024 = square_master.resize((1024, 1024), Image.LANCZOS)
    icon_1024.save(os.path.join(ASSETS_DIR, "icon.png"))
    icon_1024.save(os.path.join(ASSETS_DIR, "splash-icon.png"))

    favicon = square_master.resize((48, 48), Image.LANCZOS)
    favicon.save(os.path.join(ASSETS_DIR, "favicon.png"))

    # 안드로이드 어댑티브 아이콘 (전경: 투명 배경 위 로고, 배경: 단색)
    transparent_logo = chroma_key_transparent(square_master)

    foreground_512 = fit_on_transparent_canvas(transparent_logo, 512, safe_zone_ratio=0.72)
    foreground_512.save(os.path.join(ASSETS_DIR, "android-icon-foreground.png"))

    background_512 = Image.new("RGB", (512, 512), (255, 255, 255))
    background_512.save(os.path.join(ASSETS_DIR, "android-icon-background.png"))

    monochrome_432 = to_monochrome(
        fit_on_transparent_canvas(transparent_logo, 432, safe_zone_ratio=0.72)
    )
    monochrome_432.save(os.path.join(ASSETS_DIR, "android-icon-monochrome.png"))

    # iOS 네이티브 asset catalog (프로젝트가 bare workflow라 expo prebuild로 재생성하지 않고 직접 갱신)
    if os.path.isdir(IOS_APPICON_DIR):
        icon_1024.save(os.path.join(IOS_APPICON_DIR, "App-Icon-1024x1024@1x.png"))
        print(f"iOS AppIcon.appiconset 갱신: {IOS_APPICON_DIR}")

    # 안드로이드 네이티브 mipmap 밀도별 리소스 직접 갱신(webp)
    if os.path.isdir(ANDROID_RES_DIR):
        legacy_source = square_master  # 레거시 아이콘은 불투명 정사각형 그대로 축소
        for density, (legacy_size, adaptive_size) in ANDROID_DENSITIES.items():
            mipmap_dir = os.path.join(ANDROID_RES_DIR, f"mipmap-{density}")
            if not os.path.isdir(mipmap_dir):
                continue

            legacy_icon = legacy_source.resize((legacy_size, legacy_size), Image.LANCZOS).convert(
                "RGBA"
            )
            legacy_icon.save(os.path.join(mipmap_dir, "ic_launcher.webp"), lossless=True)
            legacy_icon.save(os.path.join(mipmap_dir, "ic_launcher_round.webp"), lossless=True)

            fg = fit_on_transparent_canvas(transparent_logo, adaptive_size, safe_zone_ratio=0.72)
            fg.save(os.path.join(mipmap_dir, "ic_launcher_foreground.webp"), lossless=True)

            bg = Image.new("RGBA", (adaptive_size, adaptive_size), (255, 255, 255, 255))
            bg.save(os.path.join(mipmap_dir, "ic_launcher_background.webp"), lossless=True)

            mono = to_monochrome(
                fit_on_transparent_canvas(transparent_logo, adaptive_size, safe_zone_ratio=0.72)
            )
            mono.save(os.path.join(mipmap_dir, "ic_launcher_monochrome.webp"), lossless=True)

        print(f"안드로이드 mipmap 리소스 갱신: {ANDROID_RES_DIR}")

    print(
        "아이콘 생성 완료: icon.png, splash-icon.png, favicon.png, android-icon-foreground.png, "
        "android-icon-background.png, android-icon-monochrome.png"
    )


if __name__ == "__main__":
    main()
