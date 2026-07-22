"""Crash-resistant image scraper with pHash de-duplication."""

from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from config import SETTINGS, WEB_EXCLUDE_TERMS
from utils.format_converter import HashIndex, safe_image_open


class WebScraper:
    """Scrape web images for rare local obstacle classes."""

    def __init__(self, output_root: Path | None = None, headless: bool = True) -> None:
        self.output_root = output_root or SETTINGS.raw_root / "web"
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.hash_index = HashIndex(SETTINGS.hash_index_path)

    def scrape_google_images(self, keyword: str, max_images: int = 100) -> list[Path]:
        """Collect image URLs from Google Images and download unique images.

        This is intentionally conservative and exception-safe because public image
        pages change frequently and may return broken or temporary URLs.
        """

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
        except ImportError as exc:
            raise RuntimeError("Install selenium first: pip install selenium") from exc

        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        urls: set[str] = set()
        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(SETTINGS.request_timeout_seconds)
            driver.get(f"https://www.google.com/search?tbm=isch&q={keyword}")
            for _ in range(6):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.0)
                for image in driver.find_elements(By.CSS_SELECTOR, "img"):
                    src = image.get_attribute("src") or image.get_attribute("data-src")
                    if src and src.startswith("http"):
                        urls.add(src)
                    if len(urls) >= max_images * 3:
                        break
                if len(urls) >= max_images * 3:
                    break
        finally:
            driver.quit()

        target_dir = self.output_root / self._slug(keyword)
        target_dir.mkdir(parents=True, exist_ok=True)
        return self.download_urls(sorted(urls), target_dir, max_images=max_images)

    def scrape_page_images(self, page_url: str, max_images: int = 100) -> list[Path]:
        """Fallback scraper for ordinary HTML pages using requests + BeautifulSoup."""

        try:
            response = requests.get(page_url, timeout=SETTINGS.request_timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WARN] Cannot fetch page {page_url}: {exc}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        urls = [img.get("src") for img in soup.find_all("img") if img.get("src")]
        target_dir = self.output_root / self._slug(urlparse(page_url).netloc)
        target_dir.mkdir(parents=True, exist_ok=True)
        return self.download_urls(urls, target_dir, max_images=max_images)

    def download_urls(self, urls: list[str], target_dir: Path, max_images: int) -> list[Path]:
        saved: list[Path] = []
        for url in urls:
            if len(saved) >= max_images:
                break
            try:
                response = requests.get(url, timeout=SETTINGS.request_timeout_seconds, stream=True)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0]
                extension = mimetypes.guess_extension(content_type) or ".jpg"
                candidate = target_dir / f"web_{len(saved):06d}{extension}"
                candidate.write_bytes(response.content)

                with safe_image_open(candidate) as image:
                    if (
                        image is None
                        or self._reject_image_shape(candidate)
                        or self.hash_index.is_duplicate(image)
                    ):
                        candidate.unlink(missing_ok=True)
                        continue
                    self.hash_index.add(image, str(candidate))
                saved.append(candidate)
            except Exception as exc:
                print(f"[WARN] Skipping broken image URL {url[:80]}: {exc}")

        self.hash_index.save()
        print(f"Saved {len(saved)} unique images to {target_dir}")
        return saved

    def scrape_bing_images(self, keyword: str, max_images: int = 100) -> list[Path]:
        """Collect original image URLs from Bing Images metadata.

        Bing exposes source URLs in the JSON stored on `a.iusc` elements. This
        tends to be more reliable than reading thumbnail `img.src` values.
        """

        strict_query = self._strict_photo_query(keyword)
        search_url = (
            "https://www.bing.com/images/search?"
            f"q={quote_plus(strict_query)}&form=HDRSC2&first=1&qft=+filterui:photo-photo"
        )
        try:
            response = requests.get(
                search_url,
                timeout=SETTINGS.request_timeout_seconds,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[WARN] Cannot fetch Bing Images page for {keyword!r}: {exc}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        urls: list[str] = []
        for anchor in soup.select("a.iusc"):
            raw = anchor.get("m")
            if not raw:
                continue
            try:
                metadata = json.loads(raw)
            except json.JSONDecodeError:
                continue
            url = metadata.get("murl")
            title = str(metadata.get("t", ""))
            if (
                isinstance(url, str)
                and url.startswith("http")
                and not self._looks_non_photo(url, title)
            ):
                urls.append(url)

        target_dir = self.output_root / self._slug(keyword)
        target_dir.mkdir(parents=True, exist_ok=True)
        return self.download_urls(urls, target_dir, max_images=max_images)

    @staticmethod
    def _slug(text: str) -> str:
        return "".join(char if char.isalnum() else "_" for char in text.lower()).strip("_")[:80]

    @staticmethod
    def _strict_photo_query(keyword: str) -> str:
        excludes = " ".join(f"-{term}" for term in WEB_EXCLUDE_TERMS[:18])
        return f"{keyword} real photo street sidewalk {excludes}"

    @staticmethod
    def _looks_non_photo(url: str, title: str = "") -> bool:
        haystack = f"{url} {title}".lower()
        return any(term in haystack for term in WEB_EXCLUDE_TERMS)

    @staticmethod
    def _reject_image_shape(path: Path) -> bool:
        try:
            from PIL import Image

            with Image.open(path) as image:
                width, height = image.size
                if width < 320 or height < 240:
                    return True
                aspect = max(width / height, height / width)
                if aspect > 3.5:
                    return True
                if image.mode in {"RGBA", "LA", "P"}:
                    rgba = image.convert("RGBA")
                    alpha = rgba.getchannel("A")
                    transparent = sum(1 for value in alpha.getdata() if value < 250)
                    if transparent / max(width * height, 1) > 0.05:
                        return True
        except Exception:
            return True
        return False
