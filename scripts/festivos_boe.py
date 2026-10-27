import argparse
import csv
import datetime
import html
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "calendario" / "festivos_es.csv"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
SUMMARY_URL = "https://www.boe.es/datosabiertos/api/boe/sumario/{day:%Y%m%d}"
DOCUMENT_URL = "https://www.boe.es/diario_boe/xml.php?id={boe_id}"
HEADER = ["date", "ccaa_code", "island_code", "territory", "name", "type", "boe_id"]

EXPECTED_IN_TABLE = {"05": 11}
EXPECTED_DEFAULT = 12

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
MARKS = {"*": "national", "**": "national_not_substituted", "***": "regional"}

REGION_KEYWORDS = {
    "andalucia": "01", "aragon": "02", "asturias": "03", "balears": "04", "canarias": "05",
    "cantabria": "06", "castilla y leon": "07", "castilla-la mancha": "08", "castilla la mancha": "08",
    "cataluna": "09", "valenciana": "10", "extremadura": "11", "galicia": "12", "madrid": "13",
    "murcia": "14", "navarra": "15", "pais vasco": "16", "rioja": "17", "ceuta": "18", "melilla": "19",
}


def region_code(header: str, boe_id: str) -> str:
    codes = {code for keyword, code in REGION_KEYWORDS.items() if keyword in normalize(header)}

    if len(codes) != 1:
        raise ValueError(f"{boe_id}: no se reconoce la comunidad de la columna «{header}»")

    return codes.pop()


CANARY_ISLANDS = {
    "el hierro": "382", "fuerteventura": "351", "gran canaria": "352", "la gomera": "381",
    "la palma": "383", "lanzarote": "353", "lanzarote y la graciosa": "353", "tenerife": "384",
}
CANARY_NOTE = re.compile(r"en ([A-ZÁÉÍÓÚ][\w ]+?): el (\d{1,2}) de (\w+), (festividad de [^;»]+)")
ARAN_NOTE = re.compile(
    r"En el territorio de Arán, la fiesta del día (\d{1,2}) de (\w+) \([^)]*\) queda sustituida por la de "
    r"(\d{1,2}) de (\w+) \(([^)]+)\)"
)


def fetch(url: str, accept: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})

    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as error:
            last_error = error
            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"No se pudo descargar {url}: {last_error}")


def summary_items(node):
    if isinstance(node, dict):
        if "identificador" in node and "titulo" in node:
            yield node

        for value in node.values():
            yield from summary_items(value)
    elif isinstance(node, list):
        for value in node:
            yield from summary_items(value)


def find_resolution(year: int) -> str | None:
    pattern = re.compile(rf"relaci[oó]n de fiestas laborales para el a[nñ]o {year}", re.I)
    day = datetime.date(year - 1, 9, 1)
    last = min(datetime.date(year, 1, 31), datetime.date.today())

    while day <= last:
        try:
            summary = json.loads(fetch(SUMMARY_URL.format(day=day), "application/json"))
        except (RuntimeError, json.JSONDecodeError):
            summary = None

        for item in summary_items(summary or {}):
            if pattern.search(item["titulo"]):
                return item["identificador"]

        day += datetime.timedelta(days=1)
        time.sleep(0.2)

    return None


def normalize(text: str) -> str:
    text = re.sub(r"\(\d+\)", "", text).strip().lower()

    return text.translate(str.maketrans("áéíóúü", "aeiouu")).replace("ñ", "n")


def plain_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def iso_date(year: int, day: str, month: str) -> str:
    return datetime.date(year, MONTHS[normalize(month)], int(day)).isoformat()


def parse_table(table: str, year: int, boe_id: str) -> list[list[str]]:
    rows = [[plain_text(cell) for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
            for row in re.findall(r"<tr.*?</tr>", table, re.S)]
    header_index = next(index for index, row in enumerate(rows) if row and "andalucia" in normalize(row[0]))
    regions = [region_code(name, boe_id) for name in rows[header_index]]

    if sorted(regions) != sorted(set(REGION_KEYWORDS.values())):
        raise ValueError(f"Columnas de comunidades inesperadas en {boe_id}: {rows[header_index]}")

    output, month = [], None

    for row in rows[header_index + 1:]:
        if not row or not row[0]:
            continue

        if normalize(row[0]) in MONTHS:
            month = row[0]
            continue

        match = re.match(r"^(\d{1,2})\s+(.+?)\.?$", row[0])

        if not match or month is None:
            raise ValueError(f"Fila no reconocida en {boe_id}: {row}")

        for region, mark in zip(regions, row[1:]):
            if mark and mark not in MARKS:
                raise ValueError(f"Marca desconocida «{mark}» en {boe_id}, fila {row[0]}")

            if mark:
                output.append([iso_date(year, match.group(1), month), region, "", "", match.group(2).strip(), MARKS[mark], boe_id])

    return output


def apply_notes(rows: list[list[str]], notes: str, year: int, boe_id: str) -> list[list[str]]:
    output = list(rows)

    if "Canarias" in notes:
        islands = CANARY_NOTE.findall(notes.split("Canarias", 1)[1])

        if not islands:
            raise ValueError(f"{boe_id}: hay nota de Canarias pero no se reconoce su formato")

        for island, day, month, name in islands:
            code = CANARY_ISLANDS.get(island.strip().lower())

            if not code:
                raise ValueError(f"{boe_id}: isla desconocida en la nota de Canarias: {island}")

            output.append([iso_date(year, day, month), "05", code, island.strip(), upper_first(re.sub(r"^festividad de\s+", "", name.strip())), "island", boe_id])

    aran = ARAN_NOTE.search(notes)

    if "Arán" in notes and not aran:
        raise ValueError(f"{boe_id}: hay nota de Arán pero no se reconoce su formato")

    if aran:
        replaced = iso_date(year, aran.group(1), aran.group(2))

        for row in output:
            if row[0] == replaced and row[1] == "09" and not row[3]:
                row[3] = "Cataluña excepto Arán"

        output.append([iso_date(year, aran.group(3), aran.group(4)), "09", "", "Arán", aran.group(5).strip(), "regional", boe_id])

    return output


def validate(rows: list[list[str]], boe_id: str) -> None:
    in_table = {}

    for row in rows:
        if row[5] != "island" and row[3] != "Arán":
            in_table[row[1]] = in_table.get(row[1], 0) + 1

    wrong = {region: count for region, count in in_table.items() if count != EXPECTED_IN_TABLE.get(region, EXPECTED_DEFAULT)}

    if len(in_table) != 19 or wrong:
        raise ValueError(f"{boe_id}: número de fiestas por comunidad inesperado: {wrong or len(in_table)}")


def merge(new_rows: list[list[str]], year: int) -> int:
    existing = []

    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8", newline="") as file:
            existing = list(csv.reader(file))[1:]

    kept = [row for row in existing if not row[0].startswith(f"{year}-")]
    rows = sorted(kept + new_rows, key=lambda row: (row[0], row[1], row[2], row[3]))
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(buffer.getvalue(), encoding="utf-8")

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza calendario/festivos_es.csv con las fiestas laborales del BOE.")
    parser.add_argument("year", nargs="?", type=int, default=datetime.date.today().year + 1)
    parser.add_argument("--boe-id", help="identificador BOE-A-… de la resolución (evita buscar en los sumarios)")
    args = parser.parse_args()

    boe_id = args.boe_id or find_resolution(args.year)

    if not boe_id:
        print(f"La relación de fiestas laborales de {args.year} todavía no está publicada en el BOE.")
        sys.exit(2)

    xml = fetch(DOCUMENT_URL.format(boe_id=boe_id), "application/xml").decode("utf-8")
    tables = re.findall(r"<table.*?</table>", xml, re.S)

    if len(tables) != 1:
        raise ValueError(f"Se esperaba una tabla en {boe_id} y hay {len(tables)}")

    notes = plain_text(xml[xml.rfind("</table>"):])
    rows = parse_table(tables[0], args.year, boe_id)
    validate(rows, boe_id)
    rows = apply_notes(rows, notes, args.year, boe_id)
    total = merge(rows, args.year)
    print(f"{args.year}: {len(rows)} filas de {boe_id} ({total} en total en {OUTPUT.relative_to(REPO)})")


if __name__ == "__main__":
    main()
