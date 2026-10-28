import csv
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build"
CACHE = BUILD / "cache" / "territorio"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"


def fetch(url: str, name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if target.exists() and target.stat().st_size > 0:
        return target
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
    except OSError as error:
        raise SystemExit(f"No se pudo descargar {url}: {error}") from error
    if not data:
        raise SystemExit(f"Descarga vacía: {url}")
    target.write_bytes(data)
    return target


def read_csv(path: Path) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} filas")


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    plain = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def fail_if(problems: list[str], title: str) -> None:
    if problems:
        detail = "\n  ".join(problems[:30])
        raise SystemExit(f"{title} ({len(problems)}):\n  {detail}")
