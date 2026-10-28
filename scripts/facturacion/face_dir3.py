import argparse
import csv
import io
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
RELATIONS_URL = "https://proveedores.face.gob.es/api/v1/relations.csv"
SOURCE_HEADER = [
    "oficinaContableNombre", "oficinaContableCodigoDir3",
    "organoGestorNombre", "organoGestorCodigoDir3",
    "unidadTramitadoraNombre", "unidadTramitadoraCodigoDir3",
    "activo",
]
HEADER = [
    "accounting_office_code", "accounting_office_name",
    "managing_body_code", "managing_body_name",
    "processing_unit_code", "processing_unit_name",
]
DIR3_PATTERN = re.compile(r"[A-Z0-9]{9}")
MUNICIPAL_PATTERN = re.compile(r"L01(\d{5})(\d)")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def clean(text: str) -> str:
    return " ".join(text.split())


def relations(raw: bytes) -> list:
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")), delimiter=";")

    if next(reader) != SOURCE_HEADER:
        raise RuntimeError("La cabecera de relations.csv de FACe ha cambiado")

    source = list(reader)
    malformed = [row for row in source if len(row) != len(SOURCE_HEADER) or row[6].strip() not in {"0", "1"}]

    if malformed:
        raise RuntimeError(f"Filas con formato inesperado en relations.csv: {malformed[:5]}")

    rows = {
        (row[1].strip(), clean(row[0]), row[3].strip(), clean(row[2]), row[5].strip(), clean(row[4]))
        for row in source
        if row[6].strip() == "1"
    }
    invalid = [row for row in rows if not all(DIR3_PATTERN.fullmatch(row[index]) for index in (0, 2, 4))]

    if invalid:
        raise RuntimeError(f"Códigos DIR3 con formato inesperado: {invalid[:5]}")

    return sorted(rows, key=lambda row: (row[0], row[2], row[4]))


def unit_names(rows: list) -> dict:
    names = {}

    for row in rows:
        for code, name in ((row[0], row[1]), (row[2], row[3]), (row[4], row[5])):
            if names.setdefault(code, name) != name:
                raise RuntimeError(f"El código DIR3 {code} tiene varios nombres en FACe")

    return names


def municipal_codes(path: Path, names: dict) -> tuple:
    with path.open(encoding="utf-8") as handle:
        municipalities = list(csv.DictReader(handle))

    rows = [(item["municipality_code"], f"L01{item['municipality_code']}{item['check_digit']}") for item in municipalities]
    malformed = [dir3 for _, dir3 in rows if not MUNICIPAL_PATTERN.fullmatch(dir3)]

    if malformed:
        raise RuntimeError(f"Códigos de municipio o dígitos de control con formato inesperado: {malformed[:5]}")

    computed = dict(rows)
    published = {}

    for code in sorted(names):
        match = MUNICIPAL_PATTERN.fullmatch(code)

        if match:
            published[match.group(1)] = published.get(match.group(1), []) + [code]

    mismatched = sorted(code for ine, codes in published.items() if ine in computed for code in codes if code != computed[ine])

    if mismatched:
        raise RuntimeError(f"El dígito de control no coincide con FACe: {mismatched}")

    stats = {
        "confirmed": sum(1 for ine in computed if ine in published),
        "absent": sorted(ine for ine in computed if ine not in published),
        "obsolete": sorted(f"{code} {names[code]}" for ine, codes in published.items() if ine not in computed for code in codes),
    }
    return sorted(rows), stats


def write_csv(path: Path, header: list, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Relaciones DIR3 de FACe y código DIR3 de cada ayuntamiento")
    parser.add_argument("--output-dir", type=Path, default=REPO / "facturacion")
    parser.add_argument("--build-dir", type=Path, default=REPO / "build")
    parser.add_argument("--municipalities", type=Path, default=REPO / "direcciones" / "municipios_es.csv")
    arguments = parser.parse_args()

    rows = relations(fetch(RELATIONS_URL))
    names = unit_names(rows)
    municipal, stats = municipal_codes(arguments.municipalities, names)
    write_csv(arguments.output_dir / "face_unidades.csv", HEADER, rows)
    write_csv(arguments.build_dir / "municipios_dir3.csv", ["municipality_code", "dir3_code"], municipal)
    print(f"FACe: {len(rows)} relaciones y {len(names)} unidades DIR3")
    print(f"Ayuntamientos: {len(municipal)} códigos, {stats['confirmed']} confirmados en FACe, {len(stats['absent'])} sin código L01 en FACe")
    print(f"Códigos L01 de FACe sin municipio vigente: {stats['obsolete']}")


if __name__ == "__main__":
    sys.exit(main())
