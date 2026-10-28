import csv
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
DUA_ID = "BOE-A-2014-7683"
ANNEX_BLOCK = "av-5"
BOE_API = f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{DUA_ID}/texto/bloque/{ANNEX_BLOCK}"
DUA_REF = f"Res. DAIE-AEAT 11/07/2014 ({DUA_ID}), anexo V"
SECTIONS = {
    "todos los modos de transporte": "all",
    "transporte marítimo y por vías navegables interiores": "sea_inland_waterways",
}
WITHOUT_MODE = {"XXX"}
ACCENTS = {"fabrica": "fábrica"}
EXPECTED = {"EXW", "FCA", "CPT", "CIP", "DPU", "DAP", "DDP", "DAT", "FAS", "FOB", "CFR", "CIF", "XXX"}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/xml"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except OSError as error:
        raise RuntimeError(f"No se pudo descargar {url}: {error}") from error


def text(element: ET.Element) -> str:
    return re.sub(r"\s+", " ", html.unescape("".join(element.itertext()))).strip()


def sentence_case(value: str) -> str:
    words = [
        word if word.startswith("(") else ACCENTS.get(word.lower(), word.lower())
        for word in value.rstrip(".").split(" ")
    ]
    joined = " ".join(words)
    return joined[0].upper() + joined[1:]


def section_mode(label: str) -> str:
    for key, mode in SECTIONS.items():
        if key in label.lower():
            return mode
    raise RuntimeError(f"Sección desconocida en el anexo V: {label}")


def current_version() -> ET.Element:
    versions = list(ET.fromstring(fetch(BOE_API)).iter("version"))
    if not versions:
        raise RuntimeError(f"El bloque {ANNEX_BLOCK} de {DUA_ID} no tiene texto")
    return versions[-1]


def incoterms() -> list[dict]:
    version = current_version()
    modifier = version.get("id_norma")
    regulation = DUA_REF + (f"; mod. {modifier}" if modifier != DUA_ID else "")
    rows, mode = [], ""
    for tr in version.iter("tr"):
        cells = [text(td) for td in tr.findall("td")]
        if len(cells) == 1:
            mode = section_mode(cells[0])
        elif len(cells) == 3 and re.fullmatch(r"[A-Z]{3}", cells[0]):
            code, name, place = cells
            rows.append({
                "code": code,
                "name": sentence_case(name),
                "transport_mode": "" if code in WITHOUT_MODE else mode,
                "place": place.rstrip("."),
                "regulation": regulation,
            })
    found = {row["code"] for row in rows}
    if found != EXPECTED:
        raise RuntimeError(f"Códigos inesperados en el anexo V: faltan {sorted(EXPECTED - found)}, sobran {sorted(found - EXPECTED)}")
    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} filas")


def main() -> None:
    write_csv(REPO / "comercio_exterior" / "incoterms.csv", ["code", "name", "transport_mode", "place", "regulation"], incoterms())


if __name__ == "__main__":
    main()
