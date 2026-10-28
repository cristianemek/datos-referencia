import collections
import re

import xlrd

from common import (
    OUT, RAW, clean, name_variants, phone_list, read_codigos_postales, read_municipios, read_provincias,
    report, write_csv,
)
from places import PlaceIndex

HEADER = [
    "center_code", "name", "center_type", "ownership", "address", "postal_code", "locality",
    "province_code", "municipality_code", "phone",
]
OWNERSHIP = {"Centro público": "publico", "Centro concertado": "concertado", "Centro privado": "privado"}
COLUMNS = {
    "LOCALIDAD": "locality", "DENOMINACIÓN GENÉRICA": "center_type", "DENOMINACIÓN ESPECÍFICA": "name",
    "CÓDIGO": "code", "NATURALEZA": "ownership", "DOMICILIO": "address", "CÓD POSTAL": "cp", "TELÉFONO": "phone",
    "PROVINCIA": "province",
}
FUZZY = 0.85
MARGIN = 0.08


def load() -> list:
    sheet = xlrd.open_workbook(RAW / "centros_educativos.xls").sheet_by_index(0)
    head = [clean(h) for h in sheet.row_values(0)]
    missing = set(COLUMNS) - set(head)
    if missing:
        raise RuntimeError(f"Columnas ausentes en la exportación: {sorted(missing)}")
    pos = {COLUMNS[h]: i for i, h in enumerate(head) if h in COLUMNS}
    rows = []
    for i in range(1, sheet.nrows):
        values = sheet.row_values(i)
        row = {k: clean(values[j]) for k, j in pos.items()}
        if re.fullmatch(r"\d{8}", row["code"]):
            rows.append(row)
    return rows


class PostalIndex:
    def __init__(self, cps: list) -> None:
        self.munis = collections.defaultdict(set)
        self.localities = collections.defaultdict(lambda: collections.defaultdict(set))
        for r in cps:
            self.munis[r["postal_code"]].add(r["municipality_code"])
            for key in name_variants(r["locality"]):
                self.localities[r["postal_code"]][key].add(r["municipality_code"])


def locate(row: dict, prov: str, postal: PostalIndex, places: PlaceIndex) -> tuple:
    cp, names = row["cp"], [row["locality"]]
    keys = set().union(*(name_variants(n) for n in names))
    candidates = {c for c in postal.munis.get(cp, set()) if c[:2] == prov}
    if candidates:
        by_locality = set()
        for k in keys:
            by_locality |= postal.localities[cp].get(k, set())
        by_locality &= candidates
        if len(by_locality) == 1:
            return by_locality.pop(), "cp_localidad"
        by_name, how = places.match(names, {prov})
        both = by_name & candidates
        if len(both) == 1:
            return both.pop(), f"cp_{how}"
        if len(candidates) == 1:
            return next(iter(candidates)), "cp_unico"
        muni, _ = places.fuzzy(names, sorted(candidates), FUZZY, MARGIN)
        if muni:
            return muni, "cp_aproximado"
    by_name, how = places.match(names, {prov})
    if len(by_name) == 1:
        return by_name.pop(), f"provincia_{how}"
    return "", "sin_asignar"


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    cps = read_codigos_postales()
    postal = PostalIndex(cps)
    places = PlaceIndex(municipios, cps)
    stats, issues, rows, seen = collections.Counter(), [], [], set()
    for src in load():
        code = src["code"]
        if code in seen:
            stats["duplicado"] += 1
            continue
        seen.add(code)
        prov = code[:2]
        if prov not in provincias:
            stats["provincia_no_valida"] += 1
            issues.append(f"provincia_no_valida\t{code}")
            continue
        cp = src["cp"].zfill(5) if re.fullmatch(r"\d{4,5}", src["cp"]) and int(src["cp"]) > 0 else ""
        if cp and cp[:2] != prov:
            stats["cp_otra_provincia"] += 1
            issues.append(f"cp_otra_provincia\t{code}\t{cp}")
        src = {**src, "cp": cp}
        muni, how = locate(src, prov, postal, places)
        stats["municipio_" + how] += 1
        if not muni:
            issues.append(f"sin_municipio\t{code}\t{cp}\t{src['locality']}")
        ownership = OWNERSHIP.get(src["ownership"], "")
        if not ownership:
            stats["naturaleza_desconocida"] += 1
        rows.append({
            "center_code": code, "name": src["name"], "center_type": src["center_type"], "ownership": ownership,
            "address": src["address"], "postal_code": cp, "locality": src["locality"], "province_code": prov,
            "municipality_code": muni, "phone": phone_list(src["phone"]),
        })
    rows.sort(key=lambda r: r["center_code"])
    write_csv(OUT / "centros_educativos_es.csv", HEADER, rows)
    total = len(rows)
    assigned = sum(1 for r in rows if r["municipality_code"])
    stats["con_municipio"] = assigned
    stats["sin_cp"] = sum(1 for r in rows if not r["postal_code"])
    stats["sin_tipo"] = sum(1 for r in rows if not r["center_type"])
    stats["sin_telefono"] = sum(1 for r in rows if not r["phone"])
    lines = [f"filas\t{total}", f"tasa_cruce_municipio\t{assigned / total:.4f}"]
    lines += [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("centros_educativos.tsv", lines)


if __name__ == "__main__":
    main()
