import csv
import html
import io
import re
import sys
import urllib.request
from pathlib import Path

import xlrd

REPO = Path(__file__).resolve().parents[2]
STRUCTURE_URL = "https://www.ine.es/daco/daco42/clasificaciones/cno11_estructura.xls"
CORRESPONDENCE_URL = "https://www.ine.es/daco/daco42/clasificaciones/corr_cno11_ciuo08.xls"
BOE_URL = "https://www.boe.es/buscar/act.php?id=BOE-A-2010-19389"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
HEADER = ["code", "level", "name", "parent_code", "isco_08"]
LEVEL_PATTERNS = [(1, r"\d"), (2, r"[A-Q]"), (3, r"\d{2}"), (4, r"\d{3}"), (5, r"\d{4}")]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def cell_text(cell) -> str:
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        return str(int(cell.value))

    return re.sub(r"\s+", " ", str(cell.value)).strip()


def level_of(code: str) -> int:
    for level, pattern in LEVEL_PATTERNS:
        if re.fullmatch(pattern, code):
            return level

    raise RuntimeError(f"Código CNO-11 con formato desconocido: {code!r}")


def read_structure() -> list:
    sheet = xlrd.open_workbook(file_contents=fetch(STRUCTURE_URL)).sheet_by_index(0)
    rows = [(cell_text(sheet.cell(r, 0)), cell_text(sheet.cell(r, 1))) for r in range(sheet.nrows)]

    return [(code, name) for code, name in rows if code]


def read_boe_annex() -> list:
    page = fetch(BOE_URL).decode("utf-8")
    annex = page[page.index('class="anexo"'):]
    entries = []

    for row in re.findall(r"<tr>(.*?)</tr>", annex, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cell))).strip()
                 for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]

        if len(cells) == 2:
            entries.append((cells[0], cells[1].removesuffix(".")))

    return entries


def build_hierarchy(structure: list) -> list:
    last = {}
    rows = []

    for code, name in structure:
        level = level_of(code)

        if level == 1:
            parent = ""
        elif level in (2, 3):
            parent = last.get(level - 1, "")
        else:
            parent = code[:-1]

        if level > 1 and last.get(level - 1) != parent:
            raise RuntimeError(f"{code}: el padre {parent!r} no es el epígrafe anterior de nivel {level - 1}")

        last = {**{k: v for k, v in last.items() if k < level}, level: code}
        rows.append({"code": code, "level": level, "name": name, "parent_code": parent})

    return rows


def validate(rows: list) -> None:
    by_code = {row["code"]: row for row in rows}

    if len(by_code) != len(rows):
        raise RuntimeError("Hay códigos CNO-11 duplicados")

    for row in rows:
        parent = by_code.get(row["parent_code"])

        if row["level"] > 1 and (parent is None or parent["level"] != row["level"] - 1):
            raise RuntimeError(f"{row['code']}: padre inexistente o de nivel incorrecto")

        if row["level"] == 3 and row["code"][0] != parent["parent_code"]:
            raise RuntimeError(f"{row['code']}: no pertenece al gran grupo de su grupo principal")


def read_correspondence(valid_codes: set) -> dict:
    sheet = xlrd.open_workbook(file_contents=fetch(CORRESPONDENCE_URL)).sheet_by_index(0)
    header = [cell_text(sheet.cell(2, c)) for c in range(sheet.ncols)]

    if header[:4] != ["CNO11", "TITULO11", "FREC11", "CIUO08"]:
        raise RuntimeError(f"Cabecera inesperada en la correspondencia: {header}")

    mapping = {}

    for r in range(3, sheet.nrows):
        cno, isco = cell_text(sheet.cell(r, 0)), cell_text(sheet.cell(r, 3))

        if not cno:
            continue

        if cno not in valid_codes or not re.fullmatch(r"\d{4}", isco):
            raise RuntimeError(f"Fila {r + 1} de la correspondencia no válida: {cno!r} -> {isco!r}")

        mapping = {**mapping, cno: sorted({*mapping.get(cno, []), isco})}

    missing = valid_codes - mapping.keys()

    if missing:
        raise RuntimeError(f"Grupos primarios sin correspondencia CIUO-08: {sorted(missing)}")

    return mapping


def main() -> None:
    output = (Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "catalogos") / "cno_11.csv"
    structure = read_structure()
    annex = read_boe_annex()

    if [code for code, _ in structure] != [code for code, _ in annex]:
        raise RuntimeError("La estructura del INE no coincide con el anexo del Real Decreto 1591/2010")

    renamed = sum(1 for (_, ine), (_, boe) in zip(structure, annex) if ine != boe)
    rows = build_hierarchy(annex)
    validate(rows)
    primary = {row["code"] for row in rows if row["level"] == 5}
    isco = read_correspondence(primary)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows([row["code"], row["level"], row["name"], row["parent_code"], "|".join(isco.get(row["code"], []))]
                     for row in rows)
    output.write_text(buffer.getvalue(), encoding="utf-8")
    levels = [sum(1 for row in rows if row["level"] == level) for level in range(1, 6)]
    print(f"CNO-11: {len(rows)} epígrafes {levels}, {renamed} nombres distintos del INE, en {output}")


if __name__ == "__main__":
    sys.exit(main())
