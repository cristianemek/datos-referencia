import collections
import csv
import io
import re
import zipfile

from common import OUT, RAW, DIRECCIONES, in_spain_bbox, read_csv, read_municipios, read_provincias, report, write_csv
from geo import MunicipalityIndex
from places import PlaceIndex

ZIP = RAW / "unlocode-latest.zip"
HEADER = [
    "code", "name", "subdivision", "functions", "status", "iata", "province_code", "municipality_code",
    "latitude", "longitude",
]
FUNCTIONS = ["puerto", "ferrocarril", "carretera", "aeropuerto", "oficina_postal", "multimodal", "instalacion_fija", "paso_fronterizo"]
SINGLE_PROVINCE_CCAA = {"AS": "33", "CB": "39", "MD": "28", "MC": "30", "NC": "31", "RI": "26", "IB": "07", "CE": "51", "ML": "52"}
NEAR_SPAIN_KM = 5.0
MATCH_KM = 10.0
DEEP_KM = 3.0
FAR_KM = 30.0
COLUMNS = ["change", "country", "location", "name", "name_ascii", "subdivision", "function", "status", "date", "iata", "coordinates", "remarks"]


def load() -> list:
    rows = []
    with zipfile.ZipFile(ZIP) as zf:
        parts = sorted(n for n in zf.namelist() if re.search(r"CodeListPart\d+\.csv$", n))
        if not parts:
            raise RuntimeError("El ZIP de UN/LOCODE no contiene los CSV esperados")
        for name in parts:
            with zf.open(name) as fh:
                for r in csv.reader(io.TextIOWrapper(fh, encoding="utf-8")):
                    if len(r) >= 12 and r[1] == "ES" and r[2]:
                        rows.append(dict(zip(COLUMNS, (x.strip() for x in r))))
    return rows


def parse_coords(text: str):
    m = re.fullmatch(r"(\d{2})(\d{2})([NS])\s+(\d{3})(\d{2})([EW])", text or "")
    if not m:
        return None
    lat = int(m.group(1)) + int(m.group(2)) / 60
    lon = int(m.group(4)) + int(m.group(5)) / 60
    return (-lat if m.group(3) == "S" else lat, -lon if m.group(6) == "W" else lon)


def functions(code: str) -> str:
    return ";".join(FUNCTIONS[i] for i, ch in enumerate(code[:8]) if ch not in "-0 " and i < len(FUNCTIONS))


def subdivision_info(sub: str, prov_by_iso: dict, ccaa_provs: dict) -> tuple:
    iso = f"ES-{sub}" if sub else ""
    if iso in prov_by_iso:
        return iso, {prov_by_iso[iso]}, prov_by_iso[iso]
    if sub in SINGLE_PROVINCE_CCAA:
        p = SINGLE_PROVINCE_CCAA[sub]
        return iso, {p}, p
    if iso in ccaa_provs:
        return iso, ccaa_provs[iso], ""
    return "", None, ""


def nearby(idx: MunicipalityIndex, point, km: float) -> list:
    return idx.near(point[1], point[0], km) if point else []


def distance(idx, units_by_ine, point, code) -> float:
    unit = units_by_ine.get(code)
    return idx.unit_distance_km(point[1], point[0], unit) if unit else float("inf")


def by_name(rec, scope, point, idx, places, units_by_ine) -> tuple:
    cands, how = places.match([rec["name"], rec["name_ascii"]], scope)
    single = scope is not None and len(scope) == 1
    if not cands:
        return "", "", point
    if not point:
        return (next(iter(cands)), f"nombre_{how}", None) if len(cands) == 1 else ("", "ambiguo", None)
    dist = {c: distance(idx, units_by_ine, point, c) for c in cands}
    close = [c for c in cands if dist[c] <= MATCH_KM]
    if len(close) == 1:
        return close[0], f"nombre_{how}", point
    if len(close) > 1:
        inside = [c for c in close if dist[c] == 0]
        return (inside[0], f"nombre_{how}", point) if len(inside) == 1 else ("", "ambiguo", point)
    if len(cands) == 1 and single and how == "municipio":
        only = next(iter(cands))
        if dist[only] <= FAR_KM:
            return only, "nombre_municipio_coordenadas_desplazadas", point
        return only, "nombre_municipio_coordenadas_descartadas", None
    return "", "conflicto_nombre_coordenadas", point


def by_coordinates(point, scope, idx, municipios) -> str:
    near = nearby(idx, point, DEEP_KM)
    if len(near) == 1 and near[0][1] == 0 and near[0][0]["ine"] in municipios:
        if scope is None or near[0][0]["ine"][:2] in scope:
            return near[0][0]["ine"]
    return ""


def resolve(rec, scope, point, idx, places, units_by_ine, municipios) -> tuple:
    if point and scope is not None:
        provs = {u["natcode"][4:6] for u, _ in nearby(idx, point, MATCH_KM)}
        if not provs & scope:
            muni, how, kept = by_name(rec, None, point, idx, places, units_by_ine)
            if muni and kept and "desplazadas" not in how:
                return muni, how, kept, "subdivision_incoherente"
            muni, how, _ = by_name(rec, scope, None, idx, places, units_by_ine)
            return muni, how or "sin_asignar", None, "coordenadas_otra_subdivision"
    muni, how, kept = by_name(rec, scope, point, idx, places, units_by_ine)
    if muni or how:
        return muni, how, kept, ""
    if point:
        muni = by_coordinates(point, scope, idx, municipios)
        if muni:
            return muni, "coordenadas", point, ""
    return "", "sin_asignar", point, ""


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    prov_by_iso = {r["iso_code"]: code for code, r in provincias.items()}
    ccaa_iso = {r["ccaa_code"]: r["iso_code"] for r in read_csv(DIRECCIONES / "comunidades_es.csv")}
    ccaa_provs = collections.defaultdict(set)
    for code, r in provincias.items():
        ccaa_provs[ccaa_iso[r["ccaa_code"]]].add(code)
    idx = MunicipalityIndex()
    units_by_ine = idx.by_ine()
    places = PlaceIndex(municipios)
    stats, issues, rows, seen = collections.Counter(), [], [], {}
    for rec in sorted(load(), key=lambda r: r["date"], reverse=True):
        code = "ES" + rec["location"]
        if rec["change"] == "X" or rec["status"] in ("XX", "RR") or rec["name"].lower() == "rejected":
            stats["excluido_baja"] += 1
            continue
        if code in seen:
            stats["codigo_duplicado"] += 1
            issues.append(f"codigo_duplicado\t{code}\t{rec['name']}\t{seen[code]}")
            continue
        seen[code] = rec["name"]
        iso, scope, sub_prov = subdivision_info(rec["subdivision"], prov_by_iso, dict(ccaa_provs))
        if rec["subdivision"] and not iso:
            stats["subdivision_no_valida"] += 1
            issues.append(f"subdivision_no_valida\t{code}\t{rec['subdivision']}")
        point = parse_coords(rec["coordinates"])
        if rec["coordinates"] and not point:
            stats["coordenadas_ilegibles"] += 1
        if point:
            near = nearby(idx, point, NEAR_SPAIN_KM) if in_spain_bbox(*point) else []
            if not near:
                stats["coordenadas_fuera_de_espana"] += 1
                issues.append(f"coordenadas_fuera\t{code}\t{rec['name']}\t{rec['coordinates']}")
                point = None
        muni, how, point, flag = resolve(rec, scope, point, idx, places, units_by_ine, municipios)
        stats["municipio_" + how] += 1
        if flag:
            stats[flag] += 1
            issues.append(f"{flag}\t{code}\t{rec['name']}\t{rec['subdivision']}\t{rec['coordinates']}\t{muni}")
        if how in ("conflicto_nombre_coordenadas", "ambiguo") or "coordenadas_" in how:
            issues.append(f"municipio_{how}\t{code}\t{rec['name']}\t{rec['subdivision']}\t{rec['coordinates']}\t{muni}")
        prov = muni[:2] if muni else sub_prov
        if not prov and point:
            provs = {u["natcode"][4:6] for u, _ in nearby(idx, point, DEEP_KM)}
            prov = provs.pop() if len(provs) == 1 and (scope is None or provs <= scope) else ""
        if muni and sub_prov and muni[:2] != sub_prov:
            stats["provincia_distinta_de_subdivision"] += 1
            issues.append(f"provincia_distinta\t{code}\t{rec['name']}\t{rec['subdivision']}\t{prov}")
        rows.append({
            "code": code, "name": rec["name"], "subdivision": iso, "functions": functions(rec["function"]),
            "status": rec["status"], "iata": rec["iata"], "province_code": prov, "municipality_code": muni,
            "latitude": f"{point[0]:.4f}" if point else "", "longitude": f"{point[1]:.4f}" if point else "",
        })
    rows.sort(key=lambda r: r["code"])
    write_csv(OUT / "unlocode_es.csv", HEADER, rows)
    stats["con_municipio"] = sum(1 for r in rows if r["municipality_code"])
    stats["con_provincia"] = sum(1 for r in rows if r["province_code"])
    stats["con_coordenadas"] = sum(1 for r in rows if r["latitude"])
    stats["con_funcion_puerto"] = sum(1 for r in rows if "puerto" in r["functions"].split(";"))
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("unlocode.tsv", lines)


if __name__ == "__main__":
    main()
