import collections
import html
import json
import re

from common import OUT, RAW, name_key, name_variants, read_csv, read_municipios, report, write_csv
from geo import MunicipalityIndex, assign, haversine_km
from places import similarity

HEADER = [
    "port_code", "name", "unlocode", "is_general_interest", "status", "province_code", "municipality_code",
    "latitude", "longitude",
]
STATUS = {"functional": "operativo", "disused": "en_desuso", "underConstruction": "en_construccion"}
CLUSTER_KM = 10.0
COAST_KM = 3.0
LOCODE_KM = 15.0
TOWN_LIKENESS = 0.75
PORT_WORDS = ("puerto", "port", "porto", "portu", "portua")
GENERIC_LOCODE = {"port", "puerto", "porto", "moll", "muelle", "el port"}
SUFFIX = r"\s+su\s+(ria|bahia)$|\s+ria\s+\w+$"


def load_nodes() -> list:
    data = json.loads((RAW / "portnode.json").read_text(encoding="utf-8"))
    nodes = []
    for feat in data["features"]:
        p = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"][:2]
        code = str(p["id_puerto"]).zfill(12)
        nodes.append({
            "code": code, "embedded": code[:5], "name": (p.get("nombre") or "").strip(),
            "status": STATUS.get((p.get("estadofis") or "").rsplit("/", 1)[-1], ""), "lat": lat, "lon": lon,
        })
    return nodes


def clusters(nodes: list) -> list:
    by_name = collections.defaultdict(list)
    for n in nodes:
        by_name[n["name"]].append(n)
    groups = []
    for same in by_name.values():
        pending = sorted(same, key=lambda n: n["code"])
        while pending:
            group = [pending.pop(0)]
            frontier = list(group)
            while frontier:
                current = frontier.pop()
                close = [n for n in pending if haversine_km(current["lat"], current["lon"], n["lat"], n["lon"]) <= CLUSTER_KM]
                for n in close:
                    pending.remove(n)
                group.extend(close)
                frontier.extend(close)
            groups.append(sorted(group, key=lambda n: n["code"]))
    return groups


def representative(group: list) -> dict:
    lat = sum(n["lat"] for n in group) / len(group)
    lon = sum(n["lon"] for n in group) / len(group)
    return min(group, key=lambda n: (haversine_km(lat, lon, n["lat"], n["lon"]), n["code"]))


def general_interest_names() -> list:
    text = (RAW / "boe_trlpemm.html").read_text(encoding="utf-8")
    start = text.find('id="ani"')
    end = text.find('id="anii"', start)
    if start < 0 or end < 0:
        raise RuntimeError("No se encuentra el anexo I en el texto del BOE")
    block = html.unescape(re.sub(r"<[^>]+>", " ", text[start:end]))
    items = re.findall(r"\d+\.\s+(.*?)(?:\s+en\s+(?:el|la|las|los)?\s*[A-ZÁÉÍÓÚ][^,.]*)?\.(?=\s+\d+\.|\s+Redactado|\s*$)", block, flags=re.S)
    names = []
    for item in items:
        for inner in re.findall(r"\(que incluye\s+([^)]*)\)", item):
            names.extend(re.split(r",\s*|\s+y\s+", inner))
        item = re.sub(r"\([^)]*\)", "", item)
        names.extend(re.split(r",\s*|\s+y\s+(?!su\b|ría\b|ria\b)", item))
    cleaned = []
    for n in names:
        n = re.sub(r"^(el|la|los|las)\s+(de\s+)?|^el de\s+", "", n.strip(), flags=re.I)
        n = re.sub(r"^(puerto|dársena)\s+de\s+", "", n, flags=re.I).strip(" .")
        if n:
            cleaned.append(n)
    if len(cleaned) < 40:
        raise RuntimeError(f"El anexo I del BOE solo da {len(cleaned)} puertos")
    return cleaned


def gi_keys(names: list) -> dict:
    keys = {}
    for n in names:
        key = name_key(n)
        keys[key] = n
        keys.setdefault(re.sub(SUFFIX, "", key), n)
    return keys


def port_core(name: str) -> str:
    key = name_key(name)
    for w in PORT_WORDS:
        if key.startswith(w + " "):
            return key[len(w) + 1:]
    return ""


def phrases(text: str) -> set:
    found = set(name_variants(text))
    for part in re.split(r"-", text or ""):
        found |= name_variants(part)
    return {k for k in found if k and k not in GENERIC_LOCODE and len(k) >= 3}


def load_locodes(municipios: dict) -> list:
    rows = []
    for r in read_csv(OUT / "unlocode_es.csv"):
        if "puerto" not in r["functions"].split(";"):
            continue
        names = phrases(r["name"])
        town = phrases(municipios[r["municipality_code"]]["municipality"]) if r["municipality_code"] else set()
        if not any(similarity(a, b) >= TOWN_LIKENESS for a in names for b in town):
            town = set()
        if names or town:
            rows.append({**r, "names": names, "town": town})
    return rows


def contains(port_key: str, phrase: str) -> bool:
    return f" {phrase} " in f" {port_key} "


def score(port: dict, loc: dict) -> tuple:
    key, core = port["key"], port["core"]
    same = bool(port["muni"]) and loc["municipality_code"] == port["muni"]
    by_name = max((len(p) for p in loc["names"] if contains(key, p)), default=0)
    if not by_name and same and len(core) >= 5 and any(set(core.split()) <= set(p.split()) for p in loc["names"]):
        by_name = len(core)
    by_town = max((len(p) for p in loc["town"] if contains(key, p)), default=0) if same else 0
    resemblance = max((similarity(core or key, n) for n in loc["names"]), default=0.0)
    return (by_name, by_town, round(resemblance, 3)) if by_name or by_town else ()


def near_enough(port: dict, loc: dict, idx, units_by_ine) -> bool:
    if port["muni"] and loc["municipality_code"] == port["muni"]:
        return True
    if loc["province_code"] and port["prov"] and loc["province_code"] != port["prov"]:
        return False
    if loc["latitude"] and haversine_km(port["lat"], port["lon"], float(loc["latitude"]), float(loc["longitude"])) <= LOCODE_KM:
        return True
    unit = units_by_ine.get(loc["municipality_code"])
    return bool(unit) and idx.unit_distance_km(port["lon"], port["lat"], unit) <= LOCODE_KM


def match_locodes(ports: list, locodes: list, idx, units_by_ine) -> None:
    for port in ports:
        best = None
        for loc in locodes:
            s = score(port, loc)
            if s and near_enough(port, loc, idx, units_by_ine) and (best is None or s > best[0]):
                best = (s, loc["code"])
        port["unlocode"] = best[1] if best else ""
    for loc in locodes:
        if loc["municipality_code"] or loc["latitude"] or loc["code"] in {p["unlocode"] for p in ports}:
            continue
        hits = [p for p in ports if not p["unlocode"] and any(len(n) >= 6 and contains(p["key"], n) for n in loc["names"])]
        if len(hits) == 1:
            hits[0]["unlocode"] = loc["code"]
            hits[0]["unlocode_by_name"] = True


def main() -> None:
    municipios = read_municipios()
    idx = MunicipalityIndex()
    units_by_ine = idx.by_ine()
    locodes = load_locodes(municipios)
    gi = gi_keys(general_interest_names())
    gi_found = collections.defaultdict(list)
    stats, issues, ports = collections.Counter(), [], []
    nodes = load_nodes()
    stats["nodos"] = len(nodes)
    for group in clusters(nodes):
        rep = representative(group)
        prov, muni, method = assign(idx, municipios, rep["lon"], rep["lat"], coast_km=COAST_KM)
        if method == "costa" and rep["embedded"] not in municipios:
            method = "fuera"
        stats["municipio_" + method] += 1
        if method == "fuera":
            issues.append(f"fuera\t{rep['code']}\t{rep['name']}")
            continue
        if muni != rep["embedded"]:
            stats["municipio_distinto_del_codigo_ign"] += 1
            issues.append(f"municipio_distinto\t{rep['code']}\t{rep['name']}\tcoordenadas {muni}\tcodigo {rep['embedded']}")
        stats["nodos_agrupados"] += len(group) - 1
        bare = re.sub(r"\s*\(.*?\)", "", rep["name"])
        variants = {port_core(rep["name"]), port_core(bare), name_key(rep["name"])}
        gi_name = next((gi[v] for v in variants if v in gi), None)
        if gi_name:
            gi_found[gi_name].append(rep["name"])
        ports.append({
            **rep, "prov": prov, "muni": muni, "gi": gi_name, "key": name_key(rep["name"]),
            "core": port_core(bare), "status": rep["status"] or group[0]["status"],
        })
    match_locodes(ports, locodes, idx, units_by_ine)
    rows = [{
        "port_code": p["code"], "name": p["name"], "unlocode": p["unlocode"], "is_general_interest": "1" if p["gi"] else "0",
        "status": p["status"], "province_code": p["prov"], "municipality_code": p["muni"],
        "latitude": f"{p['lat']:.6f}", "longitude": f"{p['lon']:.6f}",
    } for p in sorted(ports, key=lambda p: p["code"])]
    write_csv(OUT / "puertos_es.csv", HEADER, rows)
    stats["con_unlocode"] = sum(1 for r in rows if r["unlocode"])
    stats["unlocode_solo_por_nombre"] = sum(1 for p in ports if p.get("unlocode_by_name"))
    stats["interes_general"] = sum(1 for r in rows if r["is_general_interest"] == "1")
    stats["interes_general_con_unlocode"] = sum(1 for r in rows if r["is_general_interest"] == "1" and r["unlocode"])
    used = {r["unlocode"] for r in rows if r["unlocode"]}
    stats["unlocode_puerto_sin_cruce"] = sum(1 for r in locodes if r["code"] not in used)
    missing = sorted(set(gi.values()) - set(gi_found))
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())]
    lines += [f"interes_general_sin_cruce\t{m}" for m in missing]
    lines += [f"interes_general\t{k}\t{' | '.join(sorted(set(v)))}" for k, v in sorted(gi_found.items())]
    report("puertos.tsv", lines + issues)


if __name__ == "__main__":
    main()
