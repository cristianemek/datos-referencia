import collections
import re

import openpyxl

from common import (
    OUT, RAW, DIRECCIONES, clean, norm, phone_list, read_codigos_postales, read_csv, read_municipios,
    read_provincias, report, write_csv,
)
from person_names import load_given_names, looks_like_person

TYPES = {"C231": "Centro de salud", "C232": "Consultorio de atención primaria"}
EXTRA_VIA = {"GV": "GRAN VIA"}
HEADER = [
    "center_code", "regional_code", "name", "type_code", "type", "address", "postal_code",
    "province_code", "municipality_code", "phone", "dependency_code", "dependency",
]
COLUMNS = {
    "Tipo centro": "type", "Código de Centro Normalizado REGCESS (CCN)": "ccn",
    "Código Autonómico del Centro": "regional", "Nombre Centro": "name", "Código Provincia": "prov",
    "Código Municipio": "muni6", "Código Tipo Vía": "via", "Nombre de la vía": "street", "Número Vía": "number",
    "Código Postal": "cp", "Teléfono": "phone", "Código Dependencia Funcional": "dep_code",
    "Dependencia Funcional": "dep", "Grupo de dependencia Funcional": "group",
}


def load() -> list:
    wb = openpyxl.load_workbook(RAW / "regcess_C2.xlsx", read_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True)
    head = [clean(h) for h in next(it)]
    missing = set(COLUMNS) - set(head)
    if missing:
        raise RuntimeError(f"Columnas ausentes en el REGCESS: {sorted(missing)}")
    pos = {COLUMNS[h]: i for i, h in enumerate(head) if h in COLUMNS}
    rows = []
    for r in it:
        if r[pos["type"]] and str(r[pos["type"]])[:4] in TYPES:
            rows.append({k: clean(r[i]) for k, i in pos.items()})
    return rows


def build_address(src: dict, vias: dict) -> str:
    via = vias.get(src["via"], EXTRA_VIA.get(src["via"], src["via"]))
    number = "" if src["number"] in ("0", "00", "000") else src["number"]
    return clean(" ".join(p for p in (via, src["street"], number) if p))


def place_tokens(municipios: dict, cps: list) -> dict:
    tokens = collections.defaultdict(set)
    for code, row in municipios.items():
        tokens[code].update(norm(row["municipality"]).split())
    for row in cps:
        tokens[row["municipality_code"]].update(norm(row["locality"]).split())
    return tokens


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    vias = {r["code"]: r["name"] for r in read_csv(DIRECCIONES / "tipos_via.csv")}
    places = place_tokens(municipios, read_codigos_postales())
    given = load_given_names()
    stats, issues, rows, seen = collections.Counter(), [], [], set()
    for src in load():
        stats["origen_" + src["type"][:4]] += 1
        ccn = src["ccn"].zfill(10)
        muni6 = src["muni6"].zfill(6)
        muni = muni6[:5]
        if ccn in seen:
            stats["duplicado"] += 1
            issues.append(f"duplicado\t{ccn}")
            continue
        seen.add(ccn)
        person = looks_like_person(src["name"], given, places.get(muni, set()))
        private = src["group"] != "Publicos"
        if person and private:
            stats["excluido_nombre_persona_privado"] += 1
            issues.append(f"excluido_nombre_persona\t{ccn}\t{src['type'][:4]}")
            continue
        if person:
            stats["nombre_persona_publico_conservado"] += 1
            issues.append(f"nombre_persona_publico\t{ccn}\t{src['name']}")
        if muni not in municipios:
            stats["municipio_inexistente"] += 1
            issues.append(f"municipio_inexistente\t{ccn}\t{muni6}")
            muni = ""
        elif municipios[muni]["check_digit"] != muni6[5]:
            stats["digito_control_distinto"] += 1
            issues.append(f"digito_control\t{ccn}\t{muni6}")
        prov = src["prov"].zfill(2)
        if prov not in provincias or (muni and muni[:2] != prov):
            stats["provincia_incoherente"] += 1
            issues.append(f"provincia\t{ccn}\t{prov}\t{muni6}")
        cp = src["cp"].zfill(5) if re.fullmatch(r"\d{4,5}", src["cp"]) and int(src["cp"]) > 0 else ""
        if cp and cp[:2] != prov:
            stats["cp_otra_provincia"] += 1
            issues.append(f"cp_otra_provincia\t{ccn}\t{cp}\t{prov}")
        if private:
            stats["dependencia_privada"] += 1
        code = src["type"][:4]
        rows.append({
            "center_code": ccn, "regional_code": src["regional"], "name": src["name"],
            "type_code": code, "type": TYPES[code], "address": build_address(src, vias), "postal_code": cp,
            "province_code": prov, "municipality_code": muni, "phone": phone_list(src["phone"]),
            "dependency_code": src["dep_code"].zfill(2), "dependency": src["dep"],
        })
    rows.sort(key=lambda r: r["center_code"])
    write_csv(OUT / "centros_salud_es.csv", HEADER, rows)
    stats["sin_telefono"] = sum(1 for r in rows if not r["phone"])
    stats["sin_cp"] = sum(1 for r in rows if not r["postal_code"])
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("centros_salud.tsv", lines)


if __name__ == "__main__":
    main()
