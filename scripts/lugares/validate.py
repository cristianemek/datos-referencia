import csv
import re
import sys

from common import OUT, in_spain_bbox, read_municipios, read_provincias
from geo import MunicipalityIndex

FILES = {
    "hospitales_es.csv": {"key": "hospital_code", "unique": ["regcess_code"], "coast_km": None},
    "centros_salud_es.csv": {"key": "center_code", "unique": [], "coast_km": None},
    "aeropuertos_es.csv": {"key": "aerodrome_code", "unique": ["icao", "iata"], "coast_km": 1.0},
    "puertos_es.csv": {"key": "port_code", "unique": [], "coast_km": 3.0},
    "unlocode_es.csv": {"key": "code", "unique": [], "coast_km": 5.0},
    "centros_educativos_es.csv": {"key": "center_code", "unique": [], "coast_km": None},
    "universidades_es.csv": {"key": "university_code", "unique": [], "coast_km": None},
}
PATTERNS = {
    "province_code": r"\d{2}", "municipality_code": r"\d{5}", "postal_code": r"\d{5}", "ccaa_code": r"\d{2}",
    "icao": r"[A-Z]{4}", "iata": r"[A-Z]{3}", "code": r"ES[A-Z0-9]{3}", "unlocode": r"ES[A-Z0-9]{3}",
    "hospital_code": r"\d{6}", "aerodrome_code": r"\d{12}", "regcess_code": r"\d{10}", "center_code": r"\d{8}|\d{10}",
    "university_code": r"\d{3}", "port_code": r"\d{12}", "phone": r"\d{9}(\|\d{9})*",
    "latitude": r"-?\d+\.\d+", "longitude": r"-?\d+\.\d+", "is_general_interest": r"[01]",
}


def check_format(path) -> list:
    raw = path.read_bytes()
    problems = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("BOM")
    if b"\r" in raw:
        problems.append("CR")
    if not raw.endswith(b"\n"):
        problems.append("sin salto final")
    if "�" in raw.decode("utf-8"):
        problems.append("U+FFFD")
    return problems


def check_coords(rows: list, key: str, coast_km: float, idx: MunicipalityIndex) -> tuple:
    inside, near, bad = 0, 0, []
    for r in rows:
        if not r.get("latitude"):
            continue
        lat, lon = float(r["latitude"]), float(r["longitude"])
        if not in_spain_bbox(lat, lon):
            bad.append(r[key])
        elif idx.locate(lon, lat):
            inside += 1
        elif idx.nearest(lon, lat, max_km=coast_km)[0] is not None:
            near += 1
        else:
            bad.append(r[key])
    return inside, near, bad


def validate(fname: str, spec: dict, municipios: dict, provincias: dict, idx) -> bool:
    path = OUT / fname
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames
        rows = list(reader)
    ok = True
    problems = check_format(path)
    bad_header = [h for h in header if not re.fullmatch(r"[a-z][a-z0-9_]*", h)]
    keys = [r[spec["key"]] for r in rows]
    dup = len(keys) - len(set(keys))
    empty_key = sum(1 for k in keys if not k)
    dup_extra = {}
    for col in spec["unique"]:
        vals = [r[col] for r in rows if r[col]]
        dup_extra[col] = len(vals) - len(set(vals))
    bad_pattern = {}
    for col in header:
        if col in PATTERNS:
            n = sum(1 for r in rows if r[col] and not re.fullmatch(PATTERNS[col], r[col]))
            if n:
                bad_pattern[col] = n
    bad_muni = sum(1 for r in rows if r.get("municipality_code") and r["municipality_code"] not in municipios)
    bad_prov = sum(1 for r in rows if r.get("province_code") and r["province_code"] not in provincias)
    incoherent = sum(1 for r in rows if r.get("municipality_code") and r.get("province_code") and r["municipality_code"][:2] != r["province_code"])
    with_muni = sum(1 for r in rows if r.get("municipality_code"))
    print(f"== {fname}: {len(rows)} filas, {len(header)} columnas")
    print(f"   formato {problems or 'OK'}, cabecera {'OK' if not bad_header else bad_header}")
    print(f"   clave {spec['key']}: duplicadas {dup}, vacías {empty_key}; otras únicas {dup_extra}")
    print(f"   patrones incorrectos {bad_pattern or 'ninguno'}")
    print(f"   municipio fuera del INE {bad_muni}, provincia fuera del INE {bad_prov}, municipio/provincia incoherentes {incoherent}")
    if "municipality_code" in header:
        print(f"   con municipio {with_muni} ({with_muni / len(rows):.2%})")
    ok = not (problems or bad_header or dup or empty_key or any(dup_extra.values()) or bad_pattern or bad_muni or bad_prov or incoherent)
    if spec["coast_km"] is not None:
        inside, near, bad = check_coords(rows, spec["key"], spec["coast_km"], idx)
        print(f"   coordenadas: dentro de un municipio {inside}, a menos de {spec['coast_km']} km de la costa {near}, fuera {len(bad)} {bad[:10]}")
        ok = ok and not bad
    return ok


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    idx = MunicipalityIndex()
    results = [validate(f, s, municipios, provincias, idx) for f, s in FILES.items()]
    print("RESULTADO", "OK" if all(results) else "CON ERRORES")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
