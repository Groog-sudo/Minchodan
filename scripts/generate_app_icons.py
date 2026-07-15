import json
import os
import sys

if sys.stdout.encoding != "utf-8":
    import contextlib

    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "client", "assets")
SOURCE_LOGO = os.path.join(ASSETS_DIR, "gildang-logo.jpeg")
IOS_APPICON_DIR = os.path.join(
    PROJECT_ROOT, "client", "ios", "Minchodan", "Images.xcassets", "AppIcon.appiconset"
)
IOS_SPLASH_DIR = os.path.join(
    PROJECT_ROOT, "client", "ios", "Minchodan", "Images.xcassets", "SplashScreen.imageset"
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

ANDROID_SPLASH_SIZES = {
    "mdpi": 288,
    "hdpi": 432,
    "xhdpi": 576,
    "xxhdpi": 864,
    "xxxhdpi": 1152,
}

SOURCE_BG_COLOR = (231, 231, 233)
ICON_BG_COLOR = (255, 255, 255)
SPLASH_BG_COLOR = (10, 13, 16)
SPLASH_YELLOW = (249, 183, 0)
CHROMA_THRESHOLD = 18


def white_disc_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """원본 JPEG의 회색 배경 위 흰 원형 로고 영역 바운딩 박스."""
    rgb = img.convert("RGB")
    pixels = rgb.load()
    w, h = rgb.size
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            dist = (
                (r - SOURCE_BG_COLOR[0]) ** 2
                + (g - SOURCE_BG_COLOR[1]) ** 2
                + (b - SOURCE_BG_COLOR[2]) ** 2
            ) ** 0.5
            if r > 245 and g > 245 and b > 245 and dist >= 10:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def content_bbox_on_icon(img: Image.Image) -> tuple[int, int, int, int]:
    """흰 배경 위 실제 로고(강아지+텍스트) 바운딩 박스."""
    rgb = img.convert("RGB")
    pixels = rgb.load()
    w, h = rgb.size
    minx, miny, maxx, maxy = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            dist_white = (
                (r - ICON_BG_COLOR[0]) ** 2
                + (g - ICON_BG_COLOR[1]) ** 2
                + (b - ICON_BG_COLOR[2]) ** 2
            ) ** 0.5
            if dist_white >= 25:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    return minx, miny, maxx, maxy


def scale_content_to_fill(img: Image.Image, fill_ratio: float = 0.88) -> Image.Image:
    """흰 배경 위 로고 내용을 아이콘 세이프존에 맞게 확대한다."""
    minx, miny, maxx, maxy = content_bbox_on_icon(img)
    if maxx <= minx or maxy <= miny:
        return img
    content = img.crop((minx, miny, maxx, maxy))
    cw, ch = content.size
    target_side = int(img.width * fill_ratio)
    scale = target_side / max(cw, ch)
    new_w, new_h = max(1, int(cw * scale)), max(1, int(ch * scale))
    scaled = content.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", img.size, ICON_BG_COLOR)
    ox = (img.width - new_w) // 2
    oy = (img.height - new_h) // 2
    canvas.paste(scaled, (ox, oy))
    return canvas


def flatten_source_bg(img: Image.Image) -> Image.Image:
    """원본 JPEG 회색 배경(원형 바깥 모서리)을 아이콘 흰 배경으로 치환한다."""
    rgb = img.convert("RGB")
    pixels = rgb.load()
    w, h = rgb.size
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            dist = (
                (r - SOURCE_BG_COLOR[0]) ** 2
                + (g - SOURCE_BG_COLOR[1]) ** 2
                + (b - SOURCE_BG_COLOR[2]) ** 2
            ) ** 0.5
            if dist < CHROMA_THRESHOLD:
                pixels[x, y] = ICON_BG_COLOR
    return rgb


def make_square_master(img: Image.Image) -> Image.Image:
    """흰 원형 로고를 정사각형으로 크롭해 iOS 아이콘 모서리까지 흰 배경이 채워지게 한다."""
    minx, miny, maxx, maxy = white_disc_bbox(img)
    disc = img.crop((minx, miny, maxx, maxy))
    side = max(disc.width, disc.height)
    canvas = Image.new("RGB", (side, side), ICON_BG_COLOR)
    offset_x = (side - disc.width) // 2
    offset_y = (side - disc.height) // 2
    canvas.paste(disc, (offset_x, offset_y))
    return flatten_source_bg(canvas)


def chroma_key_transparent(img: Image.Image) -> Image.Image:
    """흰 배경·원본 회색 배경을 투명 처리해 강아지+GILDANG만 남긴다."""
    rgba = img.convert("RGBA")
    pixels = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            dist_source = (
                (r - SOURCE_BG_COLOR[0]) ** 2
                + (g - SOURCE_BG_COLOR[1]) ** 2
                + (b - SOURCE_BG_COLOR[2]) ** 2
            ) ** 0.5
            dist_white = (
                (r - ICON_BG_COLOR[0]) ** 2
                + (g - ICON_BG_COLOR[1]) ** 2
                + (b - ICON_BG_COLOR[2]) ** 2
            ) ** 0.5
            if dist_source < CHROMA_THRESHOLD or dist_white < CHROMA_THRESHOLD:
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


def load_bold_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def circular_logo_from_jpeg(source: Image.Image, size: int) -> Image.Image:
    """React LoadingScreen(Image cover + borderRadius)과 동일하게 원형 클립한다."""
    src_w, src_h = source.size
    scale = size / min(src_w, src_h)
    new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
    resized = source.resize((new_w, new_h), Image.LANCZOS).convert("RGBA")
    left = (new_w - size) // 2
    top = (new_h - size) // 2
    square = resized.crop((left, top, left + size, top + size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    square.putalpha(mask)
    return square


def render_brand_status_screen(
    source: Image.Image, status_text: str, width: int, height: int
) -> Image.Image:
    """React BrandStatusScreen(140px 로고 + 상태 텍스트)과 동일 레이아웃의 정적 스플래시."""
    scale = width / 393.0
    logo_size = max(96, int(140 * scale))
    border = max(2, int(2 * scale))
    font_size = max(14, int(20 * scale))
    text_gap = int(20 * scale)
    letter_spacing = max(1, int(2 * scale))

    canvas = Image.new("RGB", (width, height), SPLASH_BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    logo = circular_logo_from_jpeg(source, logo_size)

    font = load_bold_font(font_size)
    text = status_text.upper()
    text_height = font_size + 4
    for ch in text:
        ch_box = draw.textbbox((0, 0), ch, font=font)
        text_height = max(text_height, ch_box[3] - ch_box[1])

    group_height = logo_size + text_gap + text_height
    logo_x = (width - logo_size) // 2
    logo_y = (height - group_height) // 2

    draw.ellipse(
        (
            logo_x - border,
            logo_y - border,
            logo_x + logo_size + border,
            logo_y + logo_size + border,
        ),
        outline=SPLASH_YELLOW,
        width=border,
    )
    canvas.paste(logo, (logo_x, logo_y), logo)

    text_y = logo_y + logo_size + text_gap
    total_w = 0
    char_widths: list[int] = []
    for ch in text:
        ch_box = draw.textbbox((0, 0), ch, font=font)
        ch_w = ch_box[2] - ch_box[0]
        char_widths.append(ch_w)
        total_w += ch_w
    total_w += letter_spacing * max(0, len(text) - 1)
    text_x = (width - total_w) // 2
    for i, ch in enumerate(text):
        draw.text((text_x, text_y), ch, fill=SPLASH_YELLOW, font=font)
        text_x += char_widths[i] + letter_spacing

    return canvas


def write_ios_splash_asset(source: Image.Image, status_text: str) -> None:
    os.makedirs(IOS_SPLASH_DIR, exist_ok=True)
    splash = render_brand_status_screen(source, status_text, 1179, 2556)
    splash.save(os.path.join(IOS_SPLASH_DIR, "SplashScreen.png"))
    contents = {
        "images": [
            {
                "filename": "SplashScreen.png",
                "idiom": "universal",
                "scale": "1x",
            }
        ],
        "info": {"version": 1, "author": "expo"},
    }
    with open(os.path.join(IOS_SPLASH_DIR, "Contents.json"), "w", encoding="utf-8") as fp:
        json.dump(contents, fp, indent=2)
        fp.write("\n")


def write_android_splash_assets(source: Image.Image, status_text: str) -> None:
    for density, width in ANDROID_SPLASH_SIZES.items():
        out_dir = os.path.join(ANDROID_RES_DIR, f"drawable-{density}")
        if not os.path.isdir(out_dir):
            continue
        height = int(width * (2556 / 1179))
        splash = render_brand_status_screen(source, status_text, width, height)
        splash.save(os.path.join(out_dir, "splashscreen_logo.png"))


def write_native_splash_assets(source: Image.Image) -> None:
    splash_loading = render_brand_status_screen(source, "Loading", 1179, 2556)
    splash_loading.save(os.path.join(ASSETS_DIR, "splash-loading.png"))

    if os.path.isdir(ANDROID_RES_DIR):
        write_android_splash_assets(source, "Loading")
        print(f"안드로이드 splashscreen_logo 갱신: {ANDROID_RES_DIR}")

    if os.path.isdir(os.path.dirname(IOS_SPLASH_DIR)):
        write_ios_splash_asset(source, "Loading")
        print(f"iOS SplashScreen.imageset 갱신: {IOS_SPLASH_DIR}")


def main() -> None:
    if not os.path.exists(SOURCE_LOGO):
        print(f"Error: 원본 로고를 찾을 수 없습니다: {SOURCE_LOGO}")
        sys.exit(1)

    source = Image.open(SOURCE_LOGO)
    square_master = scale_content_to_fill(make_square_master(source))

    # iOS/웹 아이콘 (알파 없는 불투명 정사각형)
    icon_1024 = square_master.resize((1024, 1024), Image.LANCZOS)
    icon_1024.save(os.path.join(ASSETS_DIR, "icon.png"))
    icon_1024.save(os.path.join(ASSETS_DIR, "splash-icon.png"))

    favicon = square_master.resize((48, 48), Image.LANCZOS)
    favicon.save(os.path.join(ASSETS_DIR, "favicon.png"))

    # 안드로이드 어댑티브 아이콘 (전경: 투명 배경 위 로고, 배경: 단색)
    transparent_logo = chroma_key_transparent(square_master)

    foreground_512 = fit_on_transparent_canvas(transparent_logo, 512, safe_zone_ratio=0.82)
    foreground_512.save(os.path.join(ASSETS_DIR, "android-icon-foreground.png"))

    background_512 = Image.new("RGB", (512, 512), (255, 255, 255))
    background_512.save(os.path.join(ASSETS_DIR, "android-icon-background.png"))

    monochrome_432 = to_monochrome(
        fit_on_transparent_canvas(transparent_logo, 432, safe_zone_ratio=0.82)
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

            fg = fit_on_transparent_canvas(transparent_logo, adaptive_size, safe_zone_ratio=0.82)
            fg.save(os.path.join(mipmap_dir, "ic_launcher_foreground.webp"), lossless=True)

            bg = Image.new("RGBA", (adaptive_size, adaptive_size), (255, 255, 255, 255))
            bg.save(os.path.join(mipmap_dir, "ic_launcher_background.webp"), lossless=True)

            mono = to_monochrome(
                fit_on_transparent_canvas(transparent_logo, adaptive_size, safe_zone_ratio=0.82)
            )
            mono.save(os.path.join(mipmap_dir, "ic_launcher_monochrome.webp"), lossless=True)

        print(f"안드로이드 mipmap 리소스 갱신: {ANDROID_RES_DIR}")

    write_native_splash_assets(source)

    print(
        "아이콘 생성 완료: icon.png, splash-icon.png, splash-loading.png, favicon.png, "
        "android-icon-foreground.png, android-icon-background.png, android-icon-monochrome.png"
    )


if __name__ == "__main__":
    main()
