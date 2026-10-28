import collections
import html
import json
import re

from common import (
    OUT, RAW, DIRECCIONES, clean, name_variants, norm, read_codigos_postales, read_csv, read_municipios,
    read_provincias, report, write_csv,
)
from places import PlaceIndex

FOLDER = RAW / "ruct"
HEADER = [
    "university_code", "name", "acronym", "type", "ccaa_code", "oversight", "tax_id", "erasmus_code",
    "address", "postal_code", "province_code", "municipality_code", "website",
]
PSEUDO = re.compile(r"^(otros\s+)?centros\b", re.I)
FIELDS = {
    "codigoUniversidad": "code", "acronimo": "acronym", "tipo_univ": "type", "cif": "tax_id",
    "cod_erasmus": "erasmus", "descResponsable": "authority", "domicilio": "address", "post_id": "cp",
    "dloc": "locality", "dmunic": "municipality", "dprov": "province", "dccaa": "ccaa", "url": "url",
}
TYPES = {"publica": "publica", "privada": "privada"}


def parse(path) -> dict:
    text = path.read_bytes().decode("latin-1")
    title = re.search(r'<form id="universidad"[^>]*>\s*<h2><strong>(.*?)</strong></h2>', text, re.S)
    data = {"name": clean(html.unescape(title.group(1))) if title else ""}
    for field, key in FIELDS.items():
        m = re.search(rf'<label for="{field}"[^>]*>.*?<span class="label">.*?</span>\s*<span>(.*?)</span>', text, re.S)
        data[key] = clean(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else ""
    return data


def ccaa_lookup() -> dict:
    index = {}
    for r in read_csv(DIRECCIONES / "comunidades_es.csv"):
        for key in name_variants(r["ccaa"]):
            index[key] = r["ccaa_code"]
    return index


def ccaa_code(text: str, index: dict) -> str:
    key = re.sub(r"^(comunidad autonoma|comunidad foral|comunidad|ciudad autonoma|ciudad|region|principado)\s+(de\s+)?", "", norm(text))
    key = re.sub(r"^(las|la|el|les|l)\s+", "", key)
    for k in (key, *name_variants(key)):
        if k in index:
            return index[k]
    for k, code in index.items():
        if key and (key in k or k in key):
            return code
    return ""


def province_lookup(provincias: dict) -> dict:
    index = {}
    for code, r in provincias.items():
        for key in name_variants(r["province"]):
            index[key] = code
    return index


def website(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        return ""
    return url if re.match(r"^https?://", url, re.I) else f"https://{url}"


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    cps = read_codigos_postales()
    places = PlaceIndex(municipios, cps)
    postal = collections.defaultdict(set)
    for r in cps:
        postal[r["postal_code"]].add(r["municipality_code"])
    ccaa_index, prov_index = ccaa_lookup(), province_lookup(provincias)
    listing = json.loads((FOLDER / "lista.json").read_text(encoding="utf-8"))
    stats, issues, rows = collections.Counter(), [], []
    for code, listed_name in sorted(listing.items()):
        if PSEUDO.match(listed_name):
            stats["pseudoentrada_excluida"] += 1
            issues.append(f"pseudoentrada\t{code}\t{listed_name}")
            continue
        d = parse(FOLDER / f"universidad_{code}.html")
        if d["code"] != code:
            raise RuntimeError(f"La ficha {code} no corresponde a la universidad esperada")
        prov = next((prov_index[k] for k in name_variants(d["province"]) if k in prov_index), "")
        cp = d["cp"] if re.fullmatch(r"\d{5}", d["cp"]) else ""
        muni = ""
        if prov:
            found, _ = places.match([d["municipality"]], {prov})
            if len(found) != 1:
                found, _ = places.match([d["locality"]], {prov})
            muni = next(iter(found)) if len(found) == 1 else ""
        by_cp = postal.get(cp, set())
        if cp and by_cp and muni not in by_cp:
            stats["municipio_corregido_por_cp" if len(by_cp) == 1 else "municipio_distinto_del_cp"] += 1
            issues.append(f"municipio_cp\t{code}\t{d['municipality']}\t{cp}\t{sorted(by_cp)}")
            if len(by_cp) == 1:
                muni = next(iter(by_cp))
        if not muni:
            stats["sin_municipio"] += 1
            issues.append(f"sin_municipio\t{code}\t{d['municipality']}\t{d['province']}")
        if cp and prov and cp[:2] != prov:
            stats["cp_otra_provincia"] += 1
            issues.append(f"cp_otra_provincia\t{code}\t{cp}\t{prov}")
        ccaa = ccaa_code(d["ccaa"], ccaa_index)
        if prov and ccaa and provincias[prov]["ccaa_code"] != ccaa:
            stats["ccaa_incoherente"] += 1
            issues.append(f"ccaa_incoherente\t{code}\t{d['ccaa']}\t{prov}")
        utype = next((v for k, v in TYPES.items() if norm(d["type"]).startswith(k)), "")
        if not utype:
            stats["tipo_desconocido"] += 1
            issues.append(f"tipo_desconocido\t{code}\t{d['type']}")
        rows.append({
            "university_code": code, "name": d["name"] or listed_name, "acronym": d["acronym"], "type": utype,
            "ccaa_code": ccaa, "oversight": "estatal" if norm(d["authority"]) == "estado" else "autonomica",
            "tax_id": d["tax_id"].upper().replace("-", "").replace(" ", ""), "erasmus_code": d["erasmus"],
            "address": d["address"], "postal_code": cp, "province_code": prov, "municipality_code": muni,
            "website": website(d["url"]),
        })
    write_csv(OUT / "universidades_es.csv", HEADER, rows)
    stats["publicas"] = sum(1 for r in rows if r["type"] == "publica")
    stats["privadas"] = sum(1 for r in rows if r["type"] == "privada")
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("universidades.tsv", lines)


if __name__ == "__main__":
    main()
