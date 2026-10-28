import csv
import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "comercio_exterior" / "nomenclatura_combinada_2026.csv"
CELLAR = "https://op.europa.eu/o/opportal-service/euvoc-download-handler?cellarURI=http%3A%2F%2Fpublications.europa.eu%2Fresource%2Fcellar%2F"
CN_URL = CELLAR + "79c210b8-c4a3-11f0-8da2-01aa75ed71a1.0001.02%2FDOC_1&fileName=ESTAT-CN2026.rdf"
SU_URL = CELLAR + "cc0423dc-082c-11ed-b11c-01aa75ed71a1.0001.02%2FDOC_1&fileName=ESTAT-Supplementary-units.rdf"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
BASE = "http://data.europa.eu/xsp/cn2026/"
SCHEME = BASE + "cn2026"
LEVELS = {"sections": 1, "chapters": 2, "headings": 3, "hs_subheadings": 4, "cn_subheadings": 5}
DIGITS = {2: 2, 3: 4, 4: 6, 5: 8}
NO_UNIT = "NO_SU"
TEXT_FIXES = [
    ("??", ""), (" m?", " m²"), ("p?ara", "para"), ("Î¼m", "μm"),
    ("DÃ £ o", "Dão"), ("Penedés © s", "Penedés"), ("Valdepeñas ± as", "Valdepeñas"),
]
DAMAGED = re.compile(r"[?ÃÎ©±]")

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
SKOS = "{http://www.w3.org/2004/02/skos/core#}"
DCT = "{http://purl.org/dc/terms/}"
ELI = "{http://data.europa.eu/eli/ontology#}"
M8G = "{http://data.europa.eu/m8g/}"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def open_source(location: str):
    if location.startswith("http"):
        request = urllib.request.Request(location, headers={"User-Agent": USER_AGENT})
        return urllib.request.urlopen(request, timeout=600)

    return open(location, "rb")


def fix_text(text: str) -> str:
    for wrong, right in TEXT_FIXES:
        text = text.replace(wrong, right)

    return clean(text)


def clean(text: str) -> str:
    return " ".join((text or "").replace("\xa0", " ").split())


def spanish(element: ET.Element, tag: str) -> str:
    return next((child.text for child in element if child.tag == tag and child.get(LANG) == "es"), "")


def resource(element: ET.Element, tag: str) -> str:
    return next((child.get(RDF + "resource") for child in element if child.tag == tag), "")


def read_units(location: str) -> dict:
    units = {}

    with open_source(location) as source:
        for _, element in ET.iterparse(source):
            if element.tag != RDF + "Description":
                continue

            for child in element:
                if child.tag == SKOS + "notation" and child.get(RDF + "datatype", "").endswith("/su/cn"):
                    units[element.get(RDF + "about").rsplit("/", 1)[1]] = clean(child.text)

            element.clear()

    return units


def read_classification(location: str) -> tuple:
    concepts, levels, scheme = {}, {}, {}

    with open_source(location) as source:
        for _, element in ET.iterparse(source):
            if element.tag != RDF + "Description":
                continue

            about = element.get(RDF + "about") or ""
            types = {child.get(RDF + "resource", "").rsplit("#", 1)[-1] for child in element if child.tag == RDF + "type"}
            key = about[len(BASE):] if about.startswith(BASE) else ""

            if about == SCHEME:
                scheme = {
                    "issued": next((c.text for c in element if c.tag == DCT + "issued"), ""),
                    "version_date": next((c.text for c in element if c.tag == ELI + "version_date"), ""),
                    "based_on": resource(element, ELI + "based_on"),
                }
            elif key in LEVELS:
                for child in element:
                    if child.tag == SKOS + "member":
                        levels.setdefault(child.get(RDF + "resource")[len(BASE):], set()).add(LEVELS[key])
            elif key and "Concept" in types:
                concepts[key] = {
                    "notation": next((c.text for c in element if c.tag == SKOS + "notation"), ""),
                    "label": clean(spanish(element, SKOS + "altLabel")),
                    "note": clean(spanish(element, SKOS + "scopeNote")),
                    "broader": resource(element, SKOS + "broader")[len(BASE):],
                    "unit": resource(element, M8G + "statUnitMeasure").rsplit("/", 1)[-1],
                }

            element.clear()

    return concepts, levels, scheme


def name_for(concept: dict, level: int) -> str:
    label = concept["label"]

    if level in (1, 2):
        title = re.sub(r"^(SECCIÓN [IVXL]+|CAPÍTULO \d+) - ", "", label)
        return title[0] + title[1:].lower()

    return re.sub(r"^-+\s*", "", label)


def code_for(concept: dict, level: int) -> str:
    if level == 1:
        return concept["notation"]

    digits = concept["notation"].replace(" ", "")

    if not digits.isdigit() or len(digits) < DIGITS[level] or set(digits[DIGITS[level]:]) - {"0"}:
        raise RuntimeError(f"Notación inesperada {concept['notation']!r} para el nivel {level}")

    return digits[:DIGITS[level]]


def leveled_ancestor(key: str, concepts: dict, levels: dict) -> str:
    parent = concepts[key]["broader"]

    while parent and parent not in levels:
        parent = concepts[parent]["broader"]

    return parent


def build_rows(concepts: dict, levels: dict, units: dict) -> list:
    rows = []

    for key in sorted(levels):
        concept = concepts[key]
        ancestor = leveled_ancestor(key, concepts, levels)
        first = max(levels[ancestor]) + 1 if ancestor else 1

        for level in range(first, max(levels[key]) + 1):
            code = code_for(concept, level)

            if level == 1:
                parent = ""
            elif level == 2:
                parent = concepts[leveled_ancestor(key, concepts, levels)]["notation"]
            else:
                parent = code[:DIGITS[level - 1]]

            unit = ""

            if level == 5:
                if concept["unit"] not in units:
                    raise RuntimeError(f"Unidad suplementaria desconocida {concept['unit']!r} en {code}")

                unit = "" if concept["unit"] == NO_UNIT else units[concept["unit"]]

            note = fix_text(concept["note"]) if level >= 3 else ""
            rows.append({"key": key, "code": code, "level": level, "name": name_for(concept, level),
                         "parent_code": parent, "supplementary_unit": unit, "self_explanatory_text": note})

    return rows


def validate(rows: list, concepts: dict, levels: dict) -> dict:
    by_code = {row["code"]: row for row in rows}

    if len(by_code) != len(rows):
        raise RuntimeError("Hay códigos repetidos")

    for row in rows:
        if row["level"] == 1:
            continue

        parent = by_code.get(row["parent_code"])

        if not parent or parent["level"] != row["level"] - 1:
            raise RuntimeError(f"{row['code']}: el padre {row['parent_code']!r} no existe o no es del nivel anterior")

        if parent["key"] != row["key"]:
            ancestor = leveled_ancestor(row["key"], concepts, levels)

            if ancestor != parent["key"]:
                raise RuntimeError(f"{row['code']}: la jerarquía del RDF lleva a {ancestor}, no a {parent['code']}")

    with_children = {row["parent_code"] for row in rows}
    empty_chapters = [row["code"] for row in rows if row["level"] == 2 and row["code"] not in with_children]

    for row in rows:
        if row["level"] != 2 and (row["level"] == 5) == (row["code"] in with_children):
            raise RuntimeError(f"{row['code']}: solo las subpartidas de 8 dígitos pueden ser hojas")

        if not row["name"]:
            raise RuntimeError(f"{row['code']}: sin nombre en español")

        if row["level"] == 5 and not row["self_explanatory_text"]:
            raise RuntimeError(f"{row['code']}: sin texto autoexplicativo en español")

        if DAMAGED.search(row["name"] + row["self_explanatory_text"]):
            raise RuntimeError(f"{row['code']}: texto con caracteres dañados")

    published = {(row["key"], row["level"]) for row in rows}
    missing = [key for key, own in levels.items() for level in own if (key, level) not in published]

    if missing:
        raise RuntimeError(f"Faltan conceptos del RDF: {missing[:5]}")

    added = [row for row in rows if row["level"] not in levels[row["key"]]]

    if any(row["level"] != 3 for row in added):
        raise RuntimeError("Solo se esperan partidas de 4 dígitos sin concepto propio en el RDF")

    return {"added": len(added), "empty_chapters": empty_chapters}


def main() -> None:
    cn_source = sys.argv[1] if len(sys.argv) > 1 else CN_URL
    su_source = sys.argv[2] if len(sys.argv) > 2 else SU_URL
    units = read_units(su_source)
    concepts, levels, scheme = read_classification(cn_source)
    rows = build_rows(concepts, levels, units)
    checks = validate(rows, concepts, levels)
    columns = ["code", "level", "name", "parent_code", "supplementary_unit", "self_explanatory_text"]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows([row[column] for column in columns] for row in rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(buffer.getvalue(), encoding="utf-8")
    counts = ", ".join(f"nivel {level}: {sum(1 for r in rows if r['level'] == level)}" for level in sorted(set(LEVELS.values())))
    print(f"NC 2026 ({scheme.get('based_on')}, versión {scheme.get('version_date')}, publicada {scheme.get('issued')})")
    print(f"{len(rows)} filas ({counts}) en {OUTPUT.relative_to(REPO)}, {OUTPUT.stat().st_size} bytes")
    print(f"{checks['added']} partidas de 4 dígitos comparten concepto con su subpartida en el RDF")
    print(f"Capítulos sin partidas en la fuente: {', '.join(checks['empty_chapters']) or 'ninguno'}")


if __name__ == "__main__":
    sys.exit(main())
