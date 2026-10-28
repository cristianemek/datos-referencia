import argparse
import csv
import io
import json
import re
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MUNICIPALITIES = REPO / "direcciones" / "municipios_es.csv"
ENTITIES_OUTPUT = REPO / "direcciones" / "entidades_poblacion_es.csv"
CAPITALS_OUTPUT = REPO / "build" / "municipios_capital_coords.csv"
PROVINCES_OUTPUT = REPO / "build" / "provincias_capital_coords.csv"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
NOMENCLATOR_URL = "https://www.ine.es/nomen_files/nacional/es/Nacional_{year}.zip"
NOMENCLATOR_MEMBER = "Nomdef{year}_sex.txt"
IGN_ITEMS_URL = "https://api-features.ign.es/collections/{collection}/items?f=json&limit={limit}&offset={offset}&skipGeometry=true"
IGN_PAGE_SIZE = 1000
ENTITIES_HEADER = ["code", "municipality_code", "type", "name", "population", "latitude", "longitude", "altitude"]
CAPITALS_HEADER = ["municipality_code", "latitude", "longitude", "altitude"]
PROVINCES_HEADER = ["province_code", "latitude", "longitude"]
DISSEMINATED_PREFIX = "*DISEMINADO* "
PROVINCIAL_CAPITAL_FLAG = 2
MUNICIPAL_CAPITAL_FLAG = 3
COORDINATE_DECIMALS = 6


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except OSError as error:
            if attempt == 4:
                raise RuntimeError(f"No se puede descargar {url}: {error}") from error

            time.sleep(2 ** attempt)

    raise RuntimeError(f"No se puede descargar {url}")


def unit_type(code: str) -> str:
    collective, singular, nucleus = code[5:7], code[7:9], code[9:11]

    if singular == "00" and nucleus == "00":
        return "municipio" if collective == "00" else "colectiva"

    if nucleus == "00":
        return "singular"

    return "diseminado" if nucleus == "99" else "nucleo"


def clean_name(raw: str, kind: str) -> str:
    name = re.sub(r"\s+", " ", raw.replace("\xa0", " ")).strip()

    if kind == "diseminado" and name.startswith(DISSEMINATED_PREFIX):
        name = name[len(DISSEMINATED_PREFIX):]

    if not name:
        raise ValueError(f"Nombre vacío en el nomenclátor: «{raw}»")

    return name


def read_nomenclator(year: int) -> list[dict]:
    archive = zipfile.ZipFile(io.BytesIO(fetch(NOMENCLATOR_URL.format(year=year))))
    text = archive.read(NOMENCLATOR_MEMBER.format(year=year)).decode("utf-8")
    units = []

    for line in text.splitlines():
        if not line.strip():
            continue

        code, raw_name, population = line[:11], line[11:83], line[83:90].strip()

        if not code.isdigit() or not population.isdigit():
            raise ValueError(f"Línea con formato inesperado: «{line}»")

        kind = unit_type(code)
        units.append({"code": code, "type": kind, "name": clean_name(raw_name, kind), "population": int(population)})

    return units


def check_hierarchy(units: list[dict]) -> None:
    by_code = {unit["code"]: unit for unit in units}

    if len(by_code) != len(units):
        raise ValueError("Hay códigos de unidad poblacional repetidos")

    totals = defaultdict(int)

    for unit in units:
        if unit["type"] == "singular":
            totals[unit["code"][:5] + "000000"] += unit["population"]

            if unit["code"][5:7] != "00":
                totals[unit["code"][:7] + "0000"] += unit["population"]
        elif unit["type"] in ("nucleo", "diseminado"):
            totals[unit["code"][:9] + "00"] += unit["population"]

    wrong = [code for code, total in totals.items() if code not in by_code or by_code[code]["population"] != total]

    if wrong:
        raise ValueError(f"La población no cuadra con la jerarquía en {len(wrong)} unidades, p. ej. {wrong[:5]}")


def fetch_ign(collection: str) -> list[dict]:
    features, offset, expected = [], 0, None

    while True:
        url = IGN_ITEMS_URL.format(collection=collection, limit=IGN_PAGE_SIZE, offset=offset)
        page = json.loads(fetch(url))
        expected = page.get("numberMatched", expected)
        features.extend(feature["properties"] for feature in page["features"])

        if len(page["features"]) < IGN_PAGE_SIZE:
            break

        offset += IGN_PAGE_SIZE

    if expected is not None and len(features) != expected:
        raise ValueError(f"IGN {collection}: {len(features)} elementos descargados de {expected}")

    return features


def point(feature: dict) -> dict:
    altitude = feature.get("altitud")

    return {
        "latitude": f"{feature['latitud']:.{COORDINATE_DECIMALS}f}",
        "longitude": f"{feature['longitud']:.{COORDINATE_DECIMALS}f}",
        "altitude": "" if altitude is None else str(round(altitude)),
    }


def nucleus_points(nuclei: list[dict]) -> dict:
    counts = Counter(feature["codine"] for feature in nuclei)
    repeated = [code for code, count in counts.items() if count > 1]

    if repeated:
        raise ValueError(f"Códigos INE repetidos en los núcleos del IGN: {repeated[:5]}")

    return {feature["codine"]: point(feature) for feature in nuclei if feature.get("latitud") is not None}


def capital_points(features: list[dict], municipalities: set) -> tuple[dict, dict]:
    candidates = defaultdict(list)

    for feature in features:
        flags = feature.get("capital") or ""

        if len(flags) > MUNICIPAL_CAPITAL_FLAG and flags[MUNICIPAL_CAPITAL_FLAG] == "1":
            candidates[feature["codine"][:5]].append(feature)

    unique = {code: point(items[0]) for code, items in candidates.items() if len(items) == 1 and code in municipalities}
    ambiguous = {code: items for code, items in candidates.items() if len(items) > 1}

    return unique, ambiguous


def provincial_capitals(features: list[dict], capitals: dict, municipalities: set) -> dict:
    found = defaultdict(list)

    for feature in features:
        flags = feature.get("capital") or ""

        if len(flags) > MUNICIPAL_CAPITAL_FLAG and flags[PROVINCIAL_CAPITAL_FLAG] == "1" and flags[MUNICIPAL_CAPITAL_FLAG] == "1":
            found[feature["codine"][:2]].append(feature)

    repeated = sorted(province for province, items in found.items() if len(items) > 1)

    if repeated:
        raise ValueError(f"Provincias con varias capitales en el IGN: {repeated}")

    result = {province: point(items[0]) for province, items in found.items()}
    per_province = Counter(code[:2] for code in municipalities)

    for province, count in per_province.items():
        only = next(code for code in municipalities if code[:2] == province) if count == 1 else None

        if province not in result and only in capitals:
            result[province] = capitals[only]

    missing = sorted(set(per_province) - set(result))

    if missing:
        raise ValueError(f"Provincias sin capital en el IGN: {missing}")

    return result


def read_municipalities(path: Path) -> set:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["municipality_code"] for row in csv.DictReader(handle)}


def write_csv(path: Path, header: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--municipalities", type=Path, default=MUNICIPALITIES)
    parser.add_argument("--output", type=Path, default=ENTITIES_OUTPUT)
    parser.add_argument("--capitals-output", type=Path, default=CAPITALS_OUTPUT)
    parser.add_argument("--provinces-output", type=Path, default=PROVINCES_OUTPUT)
    args = parser.parse_args()

    municipalities = read_municipalities(args.municipalities)
    units = read_nomenclator(args.year)
    check_hierarchy(units)
    nuclei = fetch_ign("nuc")
    others = fetch_ign("opob")
    points = nucleus_points(nuclei)
    empty = {"latitude": "", "longitude": "", "altitude": ""}
    rows = [
        {"code": unit["code"], "municipality_code": unit["code"][:5], "type": unit["type"], "name": unit["name"],
         "population": unit["population"], **points.get(unit["code"], empty)}
        for unit in sorted(units, key=lambda item: item["code"]) if unit["type"] != "municipio"
    ]
    unknown = sorted({row["municipality_code"] for row in rows} - municipalities)

    if unknown:
        raise ValueError(f"Municipios del nomenclátor que no están en {args.municipalities.name}: {unknown}")

    capitals, ambiguous = capital_points(nuclei + others, municipalities)
    capital_rows = [{"municipality_code": code, **capitals[code]} for code in sorted(capitals)]
    provinces = provincial_capitals(nuclei + others, capitals, municipalities)
    province_rows = [
        {"province_code": code, "latitude": provinces[code]["latitude"], "longitude": provinces[code]["longitude"]}
        for code in sorted(provinces)
    ]
    write_csv(args.output, ENTITIES_HEADER, rows)
    write_csv(args.capitals_output, CAPITALS_HEADER, capital_rows)
    write_csv(args.provinces_output, PROVINCES_HEADER, province_rows)

    located = sum(1 for row in rows if row["latitude"])
    print(f"Entidades: {len(rows)} ({dict(Counter(row['type'] for row in rows))}), {located} con coordenadas del IGN")
    print(f"Núcleos IGN sin unidad en el nomenclátor: {sorted(set(points) - {row['code'] for row in rows})}")
    print(f"Capitales: {len(capital_rows)} de {len(municipalities)} municipios; {len(province_rows)} capitales de provincia")
    print(f"Capitales ambiguas descartadas: {sorted(ambiguous)}")
    print(f"Municipios sin capital en el IGN: {sorted(municipalities - set(capitals) - set(ambiguous))}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        sys.exit(str(error))
