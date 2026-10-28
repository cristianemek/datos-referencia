import collections
import csv
import json
import re

from common import OUT, RAW, name_key, read_municipios, report, write_csv
from geo import MunicipalityIndex, assign, haversine_km

HEADER = [
    "aerodrome_code", "icao", "iata", "name", "type", "category", "status", "province_code", "municipality_code",
    "altitude", "latitude", "longitude",
]
TYPES = {
    "aerodromeOnly": "aerodromo", "heliportOnly": "helipuerto",
    "aerodromeHeliport": "aerodromo_helipuerto", "landingSite": "pista_aterrizaje",
}
CATEGORIES = {"international": "internacional", "domesticNational": "nacional"}
STATUS = {"functional": "operativo", "disused": "en_desuso"}
FEET = 0.3048
MATCH_KM = 5.0
ALT_TOLERANCE_M = 100.0
GENERIC = {
    "aeropuerto", "aerodromo", "helipuerto", "heliport", "airport", "airfield", "airstrip", "aerodrom", "base",
    "hospital", "helipad", "c", "ci", "military", "municipal", "forestal", "de", "del",
}


def tail(uri) -> str:
    return (uri or "").rsplit("/", 1)[-1]


def load_ign() -> list:
    data = json.loads((RAW / "aerodromenode.json").read_text(encoding="utf-8"))
    nodes = []
    for feat in data["features"]:
        p = feat["properties"]
        icaos = [c for c in re.split(r"[/;, ]+", p.get("cod_icao") or "") if c]
        iata = (p.get("cod_iata") or "").strip()
        if not icaos and not iata:
            continue
        lon, lat, *z = feat["geometry"]["coordinates"]
        alt = p.get("altitude")
        if alt is not None and p.get("altitude_uom") == "Pies":
            alt = alt * FEET
        nodes.append({
            "code": str(p["id_aerodro"]).zfill(12), "icao": icaos[0] if icaos else "", "iata": iata,
            "name": (p.get("nombre") or "").strip(), "type": TYPES.get(tail(p.get("aerodrometype")), ""),
            "category": CATEGORIES.get(tail(p.get("aerodromecategory")), ""),
            "status": STATUS.get(tail(p.get("currentstatus")), ""),
            "lat": lat, "lon": lon, "alt": alt, "z": z[0] if z else None,
        })
    return nodes


def load_ourairports() -> dict:
    index = collections.defaultdict(list)
    with (RAW / "ourairports_airports.csv").open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            for rank, key in enumerate(("ident", "icao_code", "gps_code")):
                code = r[key]
                if re.fullmatch(r"[A-Z]{4}", code or "") and all(x["id"] != r["id"] for _, x in index[code]):
                    index[code].append((rank, r))
    return dict(index)


def consistent_altitude(node: dict) -> bool:
    return node["alt"] is not None and bool(node["z"]) and abs(node["alt"] - node["z"]) <= ALT_TOLERANCE_M


def altitude(node: dict, stats: collections.Counter) -> str:
    alt, z = node["alt"], node["z"]
    if alt is not None and z and abs(alt - z) > ALT_TOLERANCE_M:
        stats["altitud_sustituida_por_cota_del_nodo"] += 1
        alt = z
    elif alt is None and z:
        stats["altitud_de_cota_del_nodo"] += 1
        alt = z
    return str(round(alt)) if alt is not None else ""


def resolve_duplicates(nodes: list, stats: collections.Counter, issues: list) -> None:
    groups = collections.defaultdict(list)
    for n in nodes:
        if n["icao"]:
            groups[n["icao"]].append(n)
    for icao, group in sorted(groups.items()):
        if len(group) == 1:
            continue
        chosen, how = None, ""
        working = [n for n in group if n["status"] == "operativo"]
        if len(working) == 1:
            chosen, how = working[0], "nodo_en_servicio"
        else:
            pool = working or group
            fitting = [n for n in pool if consistent_altitude(n)]
            if len(fitting) == 1:
                chosen, how = fitting[0], "altitud_coherente"
        for n in group:
            if n is chosen:
                continue
            n["icao"] = ""
            issues.append(f"oaci_duplicado_sin_codigo\t{icao}\t{n['code']}\t{n['name']}")
        if chosen:
            stats[f"oaci_duplicado_resuelto_{how}"] += 1
            issues.append(f"oaci_duplicado_conservado\t{icao}\t{chosen['code']}\t{chosen['name']}\t{how}")
        else:
            stats["oaci_duplicado_sin_resolver"] += 1


def same_place_name(a: str, b: str) -> bool:
    ta = {w for w in name_key(a).split() if w not in GENERIC and len(w) >= 4}
    tb = {w for w in name_key(b).split() if w not in GENERIC and len(w) >= 4}
    return bool(ta & tb)


def check_with_ourairports(nodes: list, oa: dict, stats: collections.Counter, issues: list) -> None:
    for n in nodes:
        n["oa"] = None
        if not n["icao"]:
            continue
        records = oa.get(n["icao"], [])
        dists = [(haversine_km(n["lat"], n["lon"], float(r["latitude_deg"]), float(r["longitude_deg"])), rank, r) for rank, r in records]
        near = sorted((d for d in dists if d[0] <= MATCH_KM), key=lambda d: (d[1], d[0]))
        if near:
            n["oa"] = near[0][2]
            stats["oa_confirma_oaci"] += 1
            continue
        strong = [d for d in dists if d[1] < 2]
        if not strong:
            stats["oa_sin_contraste"] += 1
            continue
        km, _, r = min(strong, key=lambda d: d[0])
        if same_place_name(n["name"], r["name"]):
            stats["oa_mismo_nombre_otra_posicion"] += 1
            issues.append(f"oa_otra_posicion\t{n['icao']}\t{n['code']}\t{n['name']}\t{km:.1f} km")
            continue
        stats["oaci_vaciado_por_error"] += 1
        issues.append(f"oaci_vaciado\t{n['icao']}\t{n['code']}\t{n['name']}\tOurAirports: {r['name']} a {km:.0f} km")
        n["icao"] = ""
    for n in nodes:
        oa_iata = (n["oa"] or {}).get("iata_code", "")
        if n["iata"] and oa_iata and n["iata"] != oa_iata:
            stats["iata_vaciado_por_error"] += 1
            issues.append(f"iata_vaciado\t{n['icao']}\t{n['code']}\t{n['name']}\tIGN {n['iata']}, OurAirports {oa_iata}")
            n["iata"] = ""


def missing_in_ign(oa: dict, present: set, stats: collections.Counter, issues: list) -> None:
    seen = set()
    for icao, recs in sorted(oa.items()):
        for _, r in recs:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            relevant = r["type"] in ("large_airport", "medium_airport") or r["iata_code"] or r["scheduled_service"] == "yes"
            aliases = set(r["keywords"].replace(",", " ").split())
            if r["iso_country"] == "ES" and relevant and r["type"] != "closed" and icao not in present and not aliases & present:
                stats["oa_aeropuerto_ausente_en_ign"] += 1
                issues.append(f"oa_ausente_en_ign\t{icao}\t{r['iata_code']}\t{r['name']}\t{r['type']}")


def main() -> None:
    municipios = read_municipios()
    idx = MunicipalityIndex()
    oa = load_ourairports()
    stats, issues, nodes = collections.Counter(), [], []
    for n in load_ign():
        prov, muni, method = assign(idx, municipios, n["lon"], n["lat"], coast_km=1.0)
        if method == "fuera":
            stats["fuera_de_espana"] += 1
            issues.append(f"fuera_de_espana\t{n['icao']}\t{n['code']}\t{n['name']}")
            continue
        stats["municipio_" + method] += 1
        nodes.append({**n, "prov": prov, "muni": muni})
    stats["nodos_con_codigo_en_espana"] = len(nodes)
    resolve_duplicates(nodes, stats, issues)
    check_with_ourairports(nodes, oa, stats, issues)
    rows = []
    for n in sorted(nodes, key=lambda n: n["code"]):
        if not n["icao"] and not n["iata"]:
            stats["sin_ningun_codigo"] += 1
            issues.append(f"sin_codigo\t{n['code']}\t{n['name']}")
        rows.append({
            "aerodrome_code": n["code"], "icao": n["icao"], "iata": n["iata"], "name": n["name"], "type": n["type"],
            "category": n["category"], "status": n["status"], "province_code": n["prov"], "municipality_code": n["muni"],
            "altitude": altitude(n, stats), "latitude": f"{n['lat']:.6f}", "longitude": f"{n['lon']:.6f}",
        })
    write_csv(OUT / "aeropuertos_es.csv", HEADER, rows)
    missing_in_ign(oa, {r["icao"] for r in rows if r["icao"]}, stats, issues)
    stats["con_oaci"] = sum(1 for r in rows if r["icao"])
    stats["con_iata"] = sum(1 for r in rows if r["iata"])
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("aeropuertos.tsv", lines)


if __name__ == "__main__":
    main()
