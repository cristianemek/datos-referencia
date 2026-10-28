import argparse
import csv
import io
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
DOCUMENT_URL = "https://www.cajamar.es/storage/documents/1733/cuaderno-43.pdf"
EXPECTED = [f"{number:02d}" for number in range(1, 18)] + ["98", "99"]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def pdf_text(document: bytes) -> str:
    result = subprocess.run(["pdftotext", "-layout", "-", "-"], input=document, capture_output=True, check=True)
    return result.stdout.decode("utf-8")


def concepts(text: str) -> list:
    match = re.search(r"ANEXO 2\s+1\.\s+CONCEPTOS COMUNES(.*?)2\.\s+TABLAS DE DIVISAS", text, re.S)

    if not match:
        raise RuntimeError("No se encuentra la tabla de conceptos comunes del anexo 2")

    rows = []

    for line in (raw.strip() for raw in match.group(1).splitlines()):
        row = re.fullmatch(r"(\d{2})[ \t]{2,}(\S.*)", line)

        if row:
            rows.append((row.group(1), " ".join(row.group(2).split())))
        elif line and not re.fullmatch(r"\d{1,3}", line):
            raise RuntimeError(f"Línea inesperada en los conceptos comunes del cuaderno 43: {line}")

    if [code for code, _ in rows] != EXPECTED:
        raise RuntimeError(f"Conceptos inesperados en el cuaderno 43: {[code for code, _ in rows]}")

    return rows


def write_csv(path: Path, header: list, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Conceptos comunes del cuaderno 43 (Norma 43)")
    parser.add_argument("--output-dir", type=Path, default=REPO / "pagos")
    output = parser.parse_args().output_dir

    text = pdf_text(fetch(DOCUMENT_URL))
    edition = re.search(r"Nº\s+43\s+(\w+\s+\d{4})", text)
    rows = concepts(text)
    write_csv(output / "norma43_conceptos.csv", ["code", "description"], rows)
    print(f"Cuaderno 43 ({edition.group(1) if edition else 'edición desconocida'}): {len(rows)} conceptos comunes")


if __name__ == "__main__":
    sys.exit(main())
