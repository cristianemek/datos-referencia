import csv
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = REPO / "build"
CACHE = BUILD / "cache" / "banderas"
PAISES = REPO / "direcciones" / "paises.csv"
SELECTION = CACHE / "seleccion.json"
META = CACHE / "commons_meta.json"
NAMES = CACHE / "nombres.json"
RAW = CACHE / "svg_originales"
RESULTS = CACHE / "resultados.json"
USER_AGENT = "datos-referencia/1.0 (+https://github.com/cristianemek/datos-referencia)"
RETRIES = 5
RETRY_STATUS = {429, 500, 502, 503, 504}


def http_get(url: str, params: dict | None = None, accept: str | None = None) -> bytes:
    full = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    headers = {"User-Agent": USER_AGENT, **({"Accept": accept} if accept else {})}
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(urllib.request.Request(full, headers=headers), timeout=180) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            last = error
            if error.code not in RETRY_STATUS:
                break
        except OSError as error:
            last = error
        time.sleep(10 * (attempt + 1))
    raise SystemExit(f"No se pudo descargar {url}: {last}")


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
    print(f"{path.relative_to(REPO)}: {len(rows)} filas, {path.stat().st_size} bytes")


def read_json(path: Path, step: str) -> dict:
    if not path.exists():
        raise SystemExit(f"Falta {path.relative_to(REPO)}: ejecuta antes {step} (o python3 scripts/banderas/banderas.py)")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def require_node() -> None:
    if not shutil.which("node"):
        raise SystemExit("No se encuentra node: instala Node.js para optimizar y renderizar los SVG")
    if not (HERE / "node_modules").is_dir():
        raise SystemExit("Faltan las dependencias de Node: ejecuta `npm ci` en scripts/banderas")


def fail_if(problems: list[str], title: str) -> None:
    if problems:
        detail = "\n  ".join(problems[:30])
        raise SystemExit(f"{title} ({len(problems)}):\n  {detail}")
