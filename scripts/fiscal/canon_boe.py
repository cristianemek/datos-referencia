import argparse
import csv
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "build" / "cache" / "fiscal_canon"
OUT_DIR = REPO / "fiscal"
API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}/texto"
DIARIO = "https://www.boe.es/diario_boe/xml.php?id={boe_id}"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"


def options(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--refrescar", action="store_true",
                        help="vuelve a descargar las fuentes aunque estén en la caché")
    return parser.parse_args()


def fetch(url, name, refresh=False, accept="*/*"):
    path = CACHE / name
    if path.exists() and not refresh:
        return path
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
    except OSError as error:
        raise SystemExit(f"No se pudo descargar {url}: {error}") from error
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(data)
    partial.replace(path)
    return path


def consolidated(boe_id, refresh=False):
    path = fetch(API.format(boe_id=boe_id), f"{boe_id}_texto.xml", refresh, "application/xml")
    root = ET.parse(path).getroot()
    if root.findtext("status/code") != "200":
        raise SystemExit(f"El BOE no devuelve el texto consolidado de {boe_id}")
    return root


def official(boe_id, refresh=False):
    path = fetch(DIARIO.format(boe_id=boe_id), f"{boe_id}_diario.xml", refresh, "application/xml")
    root = ET.parse(path).getroot()
    if root.find("texto") is None:
        raise SystemExit(f"El BOE no devuelve el texto original de {boe_id}")
    return root


def pdf_text(url, name, refresh=False):
    if shutil.which("pdftotext") is None:
        raise SystemExit("Falta pdftotext (paquete poppler-utils) para comprobar los PDF del BOE")
    path = fetch(url, name, refresh, "application/pdf")
    result = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"pdftotext no pudo leer {path.name}: {result.stderr.strip()}")
    return result.stdout


def text_of(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def block(root, title):
    for candidate in root.iter("bloque"):
        if re.sub(r"\s+", " ", candidate.get("titulo") or "").strip() == title:
            return candidate
    raise SystemExit(f"No se encuentra el bloque «{title}» en el texto del BOE")


def last_version_text(root, title):
    versions = block(root, title).findall("version")
    return text_of(versions[-1])


def require(text, fragment, where):
    if fragment not in text:
        raise SystemExit(f"{where}: no aparece «{fragment}»; hay que revisar la norma")


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)
    print(f"{path.relative_to(REPO)}: {len(rows)} filas", file=sys.stderr)
