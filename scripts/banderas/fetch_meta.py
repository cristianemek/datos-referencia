import html
import json
import re
import time

from comun import META, SELECTION, fail_if, http_get, read_json, write_json

API = "https://commons.wikimedia.org/w/api.php"
BATCH = 50
PAUSE = 2


def strip_html(text: str | None) -> str:
    text = re.sub(r"<(\w+)[^>]*display:\s*none[^>]*>.*?</\1>", "", text or "", flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def clean_url(url: str) -> str:
    return re.sub(r"[?&]utm_[^&]*", "", url).rstrip("?&")


def fetch_batch(batch: list[str]) -> dict:
    params = {
        "action": "query", "format": "json", "formatversion": "2", "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist",
        "titles": "|".join("File:" + name for name in batch),
    }
    data = json.loads(http_get(API, params))["query"]
    normalized = {n["to"]: n["from"] for n in data.get("normalized", [])}
    meta = {}
    for page in data["pages"]:
        original = normalized.get(page["title"], page["title"])[len("File:"):]
        if "imageinfo" not in page:
            continue
        info = page["imageinfo"][0]
        ext = info.get("extmetadata", {})
        meta[original] = {
            "title": page["title"], "url": clean_url(info["url"]), "page_url": clean_url(info["descriptionurl"]),
            "width": info.get("width"), "height": info.get("height"), "size": info.get("size"), "mime": info.get("mime"),
            "license": strip_html(ext.get("LicenseShortName", {}).get("value")),
            "author": strip_html(ext.get("Artist", {}).get("value")),
        }
    return meta


def main() -> None:
    selection = read_json(SELECTION, "select_flags.py")
    files = sorted({s["file"] for s in selection.values() if s["file"]})
    cached = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    if not all(name in cached for name in files):
        cached = {}
        for start in range(0, len(files), BATCH):
            cached.update(fetch_batch(files[start:start + BATCH]))
            time.sleep(PAUSE)
        write_json(META, cached)
    fail_if([name for name in files if name not in cached], "Ficheros sin metadatos en Commons")
    fail_if([f"{name}: {cached[name]['mime']}" for name in files if cached[name]["mime"] != "image/svg+xml"],
            "Banderas que no son SVG")
    print(f"Commons: metadatos de {len(files)} ficheros SVG")


if __name__ == "__main__":
    main()
