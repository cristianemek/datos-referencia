import csv
import io
import json
import urllib.parse
from collections import defaultdict

from comun import CACHE, PAISES, SELECTION, fail_if, http_get, read_csv, write_json

SPARQL_URL = "https://query.wikidata.org/sparql"
FLAGS_QUERY = """SELECT ?item ?itemLabel ?code ?codeRank ?flag ?flagRank ?start ?end ?endItem WHERE {
  ?item p:P297 ?cs .
  ?cs ps:P297 ?code ; wikibase:rank ?codeRank .
  OPTIONAL {
    ?item p:P41 ?fs .
    ?fs ps:P41 ?flag ; wikibase:rank ?flagRank .
    OPTIONAL { ?fs pq:P580 ?start }
    OPTIONAL { ?fs pq:P582 ?end }
  }
  OPTIONAL { ?item wdt:P576 ?endItem }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""
QUALIFIERS_QUERY = """SELECT ?item ?code ?pq ?val WHERE {
  ?item p:P297 ?cs . ?cs ps:P297 ?code .
  ?cs ?pqp ?val . ?pq wikibase:qualifier ?pqp .
}"""
MANUAL = {
    "GP": ("Flag of France.svg", "dos banderas preferentes (Francia y «local»); se toma la bandera estatal oficial (Francia)"),
    "BQ": ("Flag of the Netherlands.svg", "municipios especiales de los Países Bajos: se toma la bandera de los Países Bajos"),
    "XI": ("Flag of the United Kingdom (3-5).svg", "sin bandera oficial propia desde 1972: se toma la del Reino Unido, la misma que GB"),
    "EH": ("Flag of the Sahrawi Arab Democratic Republic.svg",
           "territorio en disputa sin bandera reconocida por la ONU: se toma la de la RASD, la convención de los conjuntos de banderas por código ISO"),
}
FIELDS = ["item", "itemLabel", "codeRank", "flag", "flagRank", "start", "end", "endItem"]


def sparql(query: str, name: str, accept: str) -> str:
    target = CACHE / name
    if not target.exists() or target.stat().st_size == 0:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(http_get(SPARQL_URL, {"query": query}, accept))
    return target.read_text(encoding="utf-8")


def value(binding: dict, key: str) -> str | None:
    cell = binding.get(key)
    if not cell:
        return None
    text = cell["value"]
    if key in ("codeRank", "flagRank"):
        return text.split("#")[-1].replace("Rank", "")
    if key == "item":
        return text.rsplit("/", 1)[-1]
    if key == "flag":
        return urllib.parse.unquote(text.rsplit("/", 1)[-1])
    return text


def load_flags() -> dict:
    bindings = json.loads(sparql(FLAGS_QUERY, "wikidata_p297_p41.json", "application/sparql-results+json"))
    by_code = defaultdict(list)
    for binding in bindings["results"]["bindings"]:
        by_code[value(binding, "code")].append({key: value(binding, key) for key in FIELDS})
    return by_code


def load_code_ends() -> dict:
    rows = csv.DictReader(io.StringIO(sparql(QUALIFIERS_QUERY, "wikidata_p297_cualificadores.csv", "text/csv")))
    ends = defaultdict(set)
    for row in rows:
        if row["pq"].endswith("/P582"):
            ends[row["code"]].add(row["item"].rsplit("/", 1)[-1])
    return ends


def current_flags(rows: list[dict], item: str) -> set:
    return {(r["flag"], r["flagRank"]) for r in rows
            if r["item"] == item and r["flag"] and r["flagRank"] != "Deprecated" and not r["end"]}


def candidates_for(code: str, rows: list[dict], ends: set, notes: list[str]) -> tuple[list[str], dict]:
    entities = {}
    for row in rows:
        entities.setdefault(row["item"], row)
    candidates = sorted(e for e, r in entities.items() if r["codeRank"] != "Deprecated" and not r["endItem"] and e not in ends)
    discarded = sorted(set(entities) - set(candidates))
    if discarded:
        names = ", ".join(f"{e} {entities[e]['itemLabel']}" for e in discarded)
        notes.append(f"descartadas (P297 obsoleto o caducado, o entidad disuelta): {names}")
    if len(candidates) > 1:
        names = ", ".join(f"{e} {entities[e]['itemLabel']}" for e in candidates)
        notes.append(f"varias entidades vigentes: {names}; se toma la que tiene P41")
        candidates = [e for e in candidates if current_flags(rows, e)] or candidates
    return candidates, entities


def choose_flag(code: str, flags: set, notes: list[str]) -> str | None:
    preferred = sorted(f for f, rank in flags if rank == "Preferred")
    normal = sorted(f for f, rank in flags if rank == "Normal")
    if code in MANUAL:
        notes.append(MANUAL[code][1])
        return MANUAL[code][0]
    if len(preferred) == 1:
        return preferred[0]
    if len(preferred) > 1:
        notes.append("SIN RESOLVER: varias banderas preferentes: " + "; ".join(preferred))
    elif len(normal) == 1:
        return normal[0]
    elif len(normal) > 1:
        notes.append("SIN RESOLVER: varias banderas normales sin preferente: " + "; ".join(normal))
    else:
        notes.append("la entidad no tiene P41 vigente (no obsoleto y sin fecha de fin)")
    return None


def select(code: str, rows: list[dict], ends: set) -> dict:
    notes = []
    candidates, entities = candidates_for(code, rows, ends, notes)
    if not candidates:
        if code in MANUAL:
            return {"item": None, "label": None, "file": MANUAL[code][0], "notes": notes + [MANUAL[code][1]]}
        return {"item": None, "label": None, "file": None, "notes": notes + ["sin entidad con P297 vigente"]}
    if len(candidates) > 1:
        notes.append("SIN RESOLVER: varias entidades vigentes con P41")
    item = candidates[0]
    chosen = choose_flag(code, current_flags(rows, item), notes)
    return {"item": item, "label": entities[item]["itemLabel"], "file": chosen, "notes": notes}


def main() -> None:
    by_code = load_flags()
    ends = load_code_ends()
    codes = [row["code"] for row in read_csv(PAISES)]
    selection = {code: select(code, by_code.get(code, []), ends[code]) for code in codes}
    fail_if([f"{code}: {' / '.join(s['notes'])}" for code, s in selection.items() if any("SIN RESOLVER" in n for n in s["notes"])],
            "Banderas que necesitan una decisión manual (añádelas a MANUAL)")
    write_json(SELECTION, selection)
    files = [s["file"] for s in selection.values() if s["file"]]
    print(f"Wikidata: {len(selection)} códigos, {len(files)} con bandera ({len(set(files))} ficheros distintos)")
    for code, entry in selection.items():
        if not entry["file"]:
            print(f"  sin bandera {code}: {' / '.join(entry['notes'])}")


if __name__ == "__main__":
    main()
