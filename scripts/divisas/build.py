import argparse
import csv
import re
import sys
from decimal import Decimal
from pathlib import Path

import report
import sources

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "build" / "cache" / "divisas"
DIVISAS = REPO / "catalogos" / "divisas.csv"
PAISES = REPO / "direcciones" / "paises.csv"
OUT_HISTORIC = REPO / "catalogos" / "divisas_historicas.csv"
OUT_COLUMNS = REPO / "build" / "divisas_columnas.csv"
OUT_COUNTRIES = REPO / "build" / "paises_divisa.csv"
SEP = "|"
COLUMN_FIELDS = ("code", "symbol_narrow", "name_plural", "countries", "cash_minor_units", "cash_rounding")
COUNTRY_FIELDS = ("code", "currency_code", "other_currency_codes")
HISTORIC_FIELDS = ("code", "numeric", "name", "name_lang", "country", "withdrawn")


def symbol_narrow(code, es, und):
    value = sources.resolve((es, und), code, ("symbol-alt-narrow", "symbol"))
    return "" if value in (None, code) else value


def plural_name(code, es):
    entry = es.get(code, {})
    return entry.get("displayName-count-other") or entry.get("displayName") or ""


def current_by_region(regions, allowed):
    return {
        region: tuple(dict.fromkeys(c for c, a in regions.get(region, ()) if sources.is_current_tender(a)))
        for region in allowed
    }


def with_parent_entities(current, six_entries):
    overrides = {
        region: sources.entity_currencies(six_entries, entity)
        for region, entity in sources.PARENT_ENTITY.items()
        if region in current
    }
    return {**current, **overrides}


def countries_by_currency(current):
    pairs = sorted((code, region) for region, codes in current.items() for code in codes)
    result = {}
    for code, region in pairs:
        result = {**result, code: result.get(code, ()) + (region,)}
    return result


def fraction_values(code, fractions):
    default = fractions["DEFAULT"]
    entry = fractions.get(code, default)
    digits = int(entry.get("_digits", default["_digits"]))
    rounding = int(entry.get("_rounding", default["_rounding"]))
    return digits, rounding, int(entry.get("_cashDigits", digits)), int(entry.get("_cashRounding", rounding))


def cash_fields(code, minor_units, fractions):
    if minor_units == "":
        return "", ""
    _, _, cash_digits, cash_rounding = fraction_values(code, fractions)
    minor = "" if cash_digits == int(minor_units) else str(cash_digits)
    if cash_rounding <= 1:
        return minor, ""
    return minor, format(Decimal(cash_rounding).scaleb(-cash_digits), f".{cash_digits}f")


def build_columns(divisas, es, und, fractions, by_currency):
    rows = []
    for row in divisas:
        code = row["code"]
        cash_minor, cash_rounding = cash_fields(code, row["minor_units"], fractions)
        rows.append({
            "code": code,
            "symbol_narrow": symbol_narrow(code, es, und),
            "name_plural": plural_name(code, es),
            "countries": SEP.join(by_currency.get(code, ())),
            "cash_minor_units": cash_minor,
            "cash_rounding": cash_rounding,
        })
    return tuple(rows)


def build_countries(paises, current):
    return tuple(
        {
            "code": p["code"],
            "currency_code": current[p["code"]][0] if current[p["code"]] else "",
            "other_currency_codes": SEP.join(current[p["code"]][1:]),
        }
        for p in paises
    )


def historic_row(entry, es):
    cldr_name = es.get(entry["code"], {}).get("displayName")
    has_es = bool(cldr_name) and cldr_name != entry["code"]
    return {
        "code": entry["code"],
        "numeric": entry["numeric"],
        "name": cldr_name if has_es else entry["six_name"],
        "name_lang": "es" if has_es else "en",
        "country": entry["entity"],
        "withdrawn": entry["withdrawn"],
    }


def build_historic(entries, es):
    rows = {(r["code"], r["country"], r["withdrawn"]): r for r in (historic_row(e, es) for e in entries)}
    if len(rows) != len(entries):
        raise ValueError("Entradas repetidas (código, entidad, fecha) en list-three")
    return tuple(rows[k] for k in sorted(rows))


def validate_inputs(divisas, paises, fractions):
    if any(fraction_values(c, fractions)[1] != 0 for c in fractions):
        raise ValueError("CLDR define _rounding no nulo: hace falta una columna rounding")
    if len({r["code"] for r in divisas}) != len(divisas) or len({p["code"] for p in paises}) != len(paises):
        raise ValueError("Códigos repetidos en divisas.csv o paises.csv")


def validate_outputs(columns, countries, historic, divisas):
    known = {r["code"] for r in divisas}
    used = {c for r in countries for c in [r["currency_code"], *r["other_currency_codes"].split(SEP)] if c}
    if used - known:
        raise ValueError(f"Divisas de paises_divisa ausentes en divisas.csv: {sorted(used - known)}")
    if [r["code"] for r in columns] != [r["code"] for r in divisas]:
        raise ValueError("divisas_columnas no sigue el orden de divisas.csv")
    for row in historic:
        if not re.fullmatch(r"[A-Z]{3}", row["code"]) or not re.fullmatch(r"(\d{3})?", row["numeric"]):
            raise ValueError(f"Formato inesperado en histórica: {row}")
        if not row["name"] or not row["country"] or not row["withdrawn"]:
            raise ValueError(f"Campo vacío en histórica: {row}")


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.relative_to(REPO)}: {len(rows)} filas")


def load_all():
    return {
        "divisas": sources.read_csv(DIVISAS),
        "paises": sources.read_csv(PAISES),
        "six_one": sources.six_current(CACHE / "list-one.xml"),
        "six_three": sources.six_historic(CACHE / "list-three.xml"),
        "es": sources.cldr_currencies(CACHE / "cldr-numbers-full_main_es_currencies.json", "es"),
        "und": sources.cldr_currencies(CACHE / "cldr-numbers-full_main_und_currencies.json", "und"),
        "currency_data": sources.cldr_currency_data(CACHE / "cldr-core_supplemental_currencyData.json"),
        "iso_index": sources.iso3166_index(CACHE / "iso-codes_iso_3166-1.json"),
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Genera las divisas históricas y las columnas de divisas y países.")
    parser.add_argument("--descargar", action="store_true", help="vuelve a descargar las fuentes aunque estén en caché")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    sources.fetch_all(CACHE, args.descargar)
    data = load_all()
    _, fractions, regions = data["currency_data"]
    validate_inputs(data["divisas"], data["paises"], fractions)
    current = current_by_region(regions, [p["code"] for p in data["paises"]])
    columns = build_columns(data["divisas"], data["es"], data["und"], fractions, countries_by_currency(current))
    countries = build_countries(data["paises"], with_parent_entities(current, data["six_one"][1]))
    historic = build_historic(data["six_three"][1], data["es"])
    validate_outputs(columns, countries, historic, data["divisas"])
    write_csv(OUT_HISTORIC, HISTORIC_FIELDS, historic)
    write_csv(OUT_COLUMNS, COLUMN_FIELDS, columns)
    write_csv(OUT_COUNTRIES, COUNTRY_FIELDS, countries)
    report.print_report(data, current, columns, countries, historic)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
