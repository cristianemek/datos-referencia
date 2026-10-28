import io
import json
import re
import zipfile
from collections import defaultdict

import openpyxl

from anexo_a5 import parse_annex
from comun import BUILD, REPO, fail_if, fetch, fold, read_csv, write_csv

A5_URL = "https://style-guide.europa.eu/o/opportal-service/isg?resource=es/annex-a5-list-countries-territories-currencies.html"
CLDR = "https://raw.githubusercontent.com/unicode-org/cldr-json/49.0.0/cldr-json"
CODE_MAPPINGS_URL = f"{CLDR}/cldr-core/supplemental/codeMappings.json"
CONTAINMENT_URL = f"{CLDR}/cldr-core/supplemental/territoryContainment.json"
TERRITORIES_URL = f"{CLDR}/cldr-localenames-full/main/es/territories.json"
INE_URL = "https://www.ine.es/ftp/microdatos/censopv/cen21/dr_CensoPersonas_2021.zip"
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-status"
PAISES = REPO / "direcciones" / "paises.csv"
OUTPUT = BUILD / "paises_columnas.csv"

HEADER = [
    "code", "official_name", "capital", "demonym", "numeric", "region_code", "region",
    "subregion_code", "subregion", "ine_code", "vat_prefix",
]
EU_TO_ISO = {"EL": "GR", "UK": "GB"}
CONTINENTS = {"002", "009", "019", "142", "150"}
USER_ASSIGNED_NUMERIC = 900
INE_WITHOUT_COUNTRY = {"199", "299", "399", "499", "555", "599", "966", "999"}
INE_ALIASES = {
    "138": "BY", "156": "MK", "205": "BW", "209": "KM", "212": "DJ", "219": "GW", "222": "LS",
    "226": "MW", "244": "SZ", "252": "ZW", "403": "BH", "404": "BD", "405": "MM", "412": "IQ",
    "430": "KR", "443": "KZ", "445": "TJ", "448": "BT", "449": "PS", "502": "FJ",
}


def load_json(url: str, name: str) -> dict:
    return json.loads(fetch(url, name).read_text(encoding="utf-8"))


def annex() -> dict:
    entries = parse_annex(fetch(A5_URL, "isg_a5_es.html").read_text(encoding="utf-8"))
    by_code = {}
    for entry in entries:
        code = EU_TO_ISO.get(entry["code"], entry["code"])
        fail_if([code] if code in by_code else [], "Código repetido en el anexo A5")
        by_code[code] = entry
    return by_code


def cldr() -> tuple[dict, dict, dict]:
    mappings = load_json(CODE_MAPPINGS_URL, "cldr49_codeMappings.json")["supplemental"]["codeMappings"]
    containment = load_json(CONTAINMENT_URL, "cldr49_territoryContainment.json")["supplemental"]["territoryContainment"]
    names = load_json(TERRITORIES_URL, "cldr49_es_territories.json")["main"]["es"]["localeDisplayNames"]["territories"]
    parents = {}
    for parent, data in containment.items():
        if "-" in parent or data.get("_grouping") == "true":
            continue
        for child in data["_contains"]:
            fail_if([child] if child in parents else [], "Territorio con dos contenedores en CLDR")
            parents[child] = parent
    numeric = {code: data["_numeric"] for code, data in mappings.items()
               if "_numeric" in data and int(data["_numeric"]) < USER_ASSIGNED_NUMERIC}
    return numeric, parents, names


def m49(code: str, parents: dict, names: dict) -> dict:
    subregion = parents.get(code, "")
    region = parents.get(subregion, "")
    if not (subregion.isdigit() and region in CONTINENTS and parents.get(region) == "001"):
        return {"region_code": "", "region": "", "subregion_code": "", "subregion": ""}
    return {"region_code": region, "region": names[region], "subregion_code": subregion, "subregion": names[subregion]}


def ine_countries() -> list[tuple[str, str]]:
    archive = zipfile.ZipFile(fetch(INE_URL, "dr_CensoPersonas_2021.zip"))
    book = openpyxl.load_workbook(io.BytesIO(archive.read("dr_CensoPersonas_2021.xlsx")), read_only=True)
    rows = list(book["Tablas2"].iter_rows(values_only=True))
    start = next(i for i, row in enumerate(rows) if row[0] == "T_PAIS")
    countries = []
    for row in rows[start + 2:]:
        if row[0] is None and row[1] is None:
            break
        if row[0] is not None:
            countries.append((str(row[0]).strip(), str(row[1]).strip()))
    return countries


def ine_codes(paises: list[dict], a5: dict) -> dict:
    index = defaultdict(set)
    for p in paises:
        index[fold(p["name"])].add(p["code"])
    for code, entry in a5.items():
        index[fold(entry["name"])].add(code)
        index[fold(entry["official_name"])].add(code)
    result, problems = {}, []
    for ine, name in ine_countries():
        if ine in INE_WITHOUT_COUNTRY:
            continue
        matches = index.get(fold(name), set())
        iso = INE_ALIASES.get(ine) or (next(iter(matches)) if len(matches) == 1 else None)
        if iso is None:
            problems.append(f"{ine} {name}: {sorted(matches)}")
        elif iso in result:
            problems.append(f"{ine} {name}: {iso} ya asignado a {result[iso]}")
        else:
            result[iso] = ine
    fail_if(problems, "Países del INE sin cruce inequívoco")
    return result


def vat_prefixes(paises: list[dict]) -> dict:
    status = load_json(VIES_URL, "vies_check_status.json")
    prefixes = {EU_TO_ISO.get(c["countryCode"], c["countryCode"]): c["countryCode"] for c in status["countries"]}
    eu = {p["code"] for p in paises if p["is_eu"] == "1"}
    fail_if(sorted(eu ^ (set(prefixes) - {"XI"})), "Estados de la UE distintos entre VIES y paises.csv")
    fail_if([] if "XI" in prefixes else ["XI"], "VIES no incluye Irlanda del Norte")
    return prefixes


def main() -> None:
    paises = read_csv(PAISES)
    a5 = annex()
    numeric, parents, names = cldr()
    ine = ine_codes(paises, a5)
    vat = vat_prefixes(paises)
    codes = {p["code"] for p in paises}
    rows = []
    for p in paises:
        code = p["code"]
        entry = a5.get(code, {})
        rows.append({
            "code": code,
            "official_name": entry.get("official_name", ""),
            "capital": entry.get("capital", ""),
            "demonym": entry.get("demonym", ""),
            "numeric": numeric.get(code, ""),
            **m49(code, parents, names),
            "ine_code": ine.get(code, ""),
            "vat_prefix": vat.get(code, ""),
        })
    fail_if([r["numeric"] for r in rows if r["numeric"] and not re.fullmatch(r"\d{3}", r["numeric"])], "Numérico ISO mal formado")
    fail_if(sorted(set(ine) - codes), "Códigos INE asignados a países que no están en paises.csv")
    write_csv(OUTPUT, HEADER, rows)
    print(f"  anexo A5 sin fila en paises.csv: {sorted(set(a5) - codes)}")
    for column in HEADER[1:]:
        empty = [r["code"] for r in rows if not r[column]]
        detail = "" if column == "vat_prefix" else f": {' '.join(empty)}"
        print(f"  {column}: {len(rows) - len(empty)} con dato, {len(empty)} vacíos{detail}")


if __name__ == "__main__":
    main()
