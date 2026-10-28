import csv
import html
import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "comercio_exterior"
BUILD = REPO / "build"
BOE_ID = "BOE-A-2022-1361"
BOE_URL = f"https://www.boe.es/diario_boe/xml.php?id={BOE_ID}"
EU_URL = "http://publications.europa.eu/resource/celex/02020R1197-20260305"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
BOE_REF = f"Res. DAIE-AEAT 24/01/2022 ({BOE_ID})"
EU_REF = "Reglamento de Ejecución (UE) 2020/1197, anexo I, parte C"
ONLY_EU = {"6"}
ONLY_BOE = {("8", "0")}
DELIVERY_FIXES = [("a costado del buque", "al costado del buque"), ("una vez descargas", "una vez descargadas")]


def fetch(url: str, headers: dict = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def text_of(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def strip_dot(text: str) -> str:
    return text.strip().rstrip(".").strip()


def boe_annexes(document: bytes) -> dict:
    root = ET.fromstring(document)

    if root.findtext("metadatos/estatus_derogacion") != "N":
        raise RuntimeError(f"{BOE_ID} figura como derogada en el BOE")

    annexes, current = {}, None

    for element in root.find("texto"):
        if element.tag == "p" and element.get("class") == "anexo_num":
            current = " ".join("".join(element.itertext()).split())
        elif element.tag == "table" and current and current not in annexes:
            annexes[current] = [
                [" ".join("".join(cell.itertext()).split()) for cell in row if cell.tag in ("td", "th")]
                for row in element.iter("tr")
            ][1:]

    return annexes


def eu_rows(page: str, number: str) -> list:
    start = page.index(f"Cuadro {number}. Desglose por")
    return re.findall(r"<tr.*?</tr>", page[start:page.index("</table>", start)], re.S)


def eu_tables(document: bytes) -> dict:
    page = document.decode("utf-8")
    natures_table = [[text_of(cell) for cell in re.findall(r"<td.*?</td>", row, re.S)] for row in eu_rows(page, "1")]
    modes_list = [text_of(p) for p in re.findall(r"<p[^>]*>.*?</p>", eu_rows(page, "2")[1], re.S)]
    return {"1": natures_table, "2": modes_list}


def natures(rows: list) -> tuple:
    groups, details, group = {}, {}, None

    for cells in rows:
        cells = [strip_dot(cell) for cell in cells]

        if len(cells) == 4:
            group = cells[0]
            groups[group] = cells[1]
            cells = cells[2:]

        if len(cells) == 2 and cells[0] and group:
            details[(group, cells[0])] = cells[1]
        elif cells and cells[0] and cells[0] != "A":
            raise RuntimeError(f"Fila inesperada en la naturaleza de la transacción: {cells}")

    return groups, details


def transaction_rows(eu: list, boe: list) -> list:
    eu_groups, eu_details = natures(eu)
    boe_groups, boe_details = natures(boe)

    if set(eu_groups) - set(boe_groups) != ONLY_EU or set(boe_groups) - set(eu_groups):
        raise RuntimeError("Los grupos de la columna A no coinciden entre el reglamento y la resolución")

    if set(boe_details) - set(eu_details) != ONLY_BOE or set(eu_details) - set(boe_details):
        raise RuntimeError("Las subdivisiones de la columna B no coinciden entre el reglamento y la resolución")

    for key, name in list(boe_groups.items()) + [(k, v) for k, v in boe_details.items() if k not in ONLY_BOE]:
        official = eu_groups.get(key) if isinstance(key, str) else eu_details.get(key)

        if official != name:
            raise RuntimeError(f"Texto distinto para {key}: {official!r} / {name!r}")

    rows = []

    for group in sorted(eu_groups):
        sources = [f"{EU_REF}, cuadro 1, columna A"] + ([] if group in ONLY_EU else [f"{BOE_REF}, anexo IV"])
        rows.append([group, eu_groups[group], "", "; ".join(sources)])

        for (parent, detail) in sorted(k for k in boe_details if k[0] == group):
            if (parent, detail) in ONLY_BOE:
                rows.append([parent + detail, eu_groups[group], parent, f"{BOE_REF}, anexo IV"])
            else:
                sources = [f"{EU_REF}, cuadro 1, columna B", f"{BOE_REF}, anexo IV"]
                rows.append([parent + detail, eu_details[(parent, detail)], parent, "; ".join(sources)])

    return rows


def transport_rows(eu: list, boe: list) -> list:
    modes = [[cells[0], strip_dot(cells[1])] for cells in boe]

    if [code for code, _ in modes] != ["1", "2", "3", "4", "5", "7", "8", "9"] or len(eu) != len(modes):
        raise RuntimeError("Los modos de transporte no coinciden con los esperados")

    return [[code, name, f"{BOE_REF}, anexo V; {EU_REF}, cuadro 2"] for code, name in modes]


def delivery_rows(boe: list) -> list:
    rows = []

    for code, name, responsibility in boe:
        for wrong, right in DELIVERY_FIXES:
            responsibility = responsibility.replace(wrong, right)

        rows.append([code, strip_dot(name), responsibility, f"{BOE_REF}, anexo III"])

    if len(rows) != 11 or any(not re.fullmatch(r"[A-Z]{3}", row[0]) for row in rows):
        raise RuntimeError("Los códigos de condiciones de entrega no tienen el formato esperado")

    return rows


def write(path: Path, header: list, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"{len(rows)} filas en {path.relative_to(REPO)}")


def main() -> None:
    annexes = boe_annexes(fetch(BOE_URL))
    eu = eu_tables(fetch(EU_URL, {"Accept": "application/xhtml+xml, text/html", "Accept-Language": "spa"}))
    write(OUTPUT / "intrastat_naturaleza_transaccion.csv", ["code", "name", "parent_code", "regulation"],
          transaction_rows(eu["1"], annexes["ANEXO IV"]))
    write(OUTPUT / "intrastat_modos_transporte.csv", ["code", "name", "regulation"], transport_rows(eu["2"], annexes["ANEXO V"]))
    write(BUILD / "intrastat_condiciones_entrega.csv", ["code", "name", "seller_responsibility", "regulation"],
          delivery_rows(annexes["ANEXO III"]))


if __name__ == "__main__":
    sys.exit(main())
