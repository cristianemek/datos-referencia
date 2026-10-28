from collections import Counter
from datetime import date, timedelta

import sources

EURO = "EUR"


def section(title, lines):
    print(f"\n== {title}")
    for line in lines:
        print(f"  {line}")


def source_lines(data):
    cldr_version, _, _ = data["currency_data"]
    return [
        f"SIX list-one publicada {data['six_one'][0]} ({len(data['six_one'][1])} entradas)",
        f"SIX list-three publicada {data['six_three'][0]} ({len(data['six_three'][1])} entradas)",
        f"CLDR currencyData versión {cldr_version}",
    ]


def consistency_lines(data):
    es, und = data["es"], data["und"]
    bad_names = [r["code"] for r in data["divisas"] if (es.get(r["code"], {}).get("displayName") or "") != r["name"]]
    bad_symbols = []
    for r in data["divisas"]:
        symbol = sources.resolve((es, und), r["code"], ("symbol",))
        if ("" if symbol in (None, r["code"]) else symbol) != r["symbol"]:
            bad_symbols.append(r["code"])
    return [f"nombres distintos de CLDR es: {bad_names}", f"símbolos distintos de CLDR: {bad_symbols}"]


def digits_lines(data):
    _, fractions, _ = data["currency_data"]
    default = fractions["DEFAULT"]["_digits"]
    differ = {
        r["code"]: (r["minor_units"], fractions.get(r["code"], {}).get("_digits", default))
        for r in data["divisas"]
        if r["minor_units"] and r["minor_units"] != fractions.get(r["code"], {}).get("_digits", default)
    }
    return [f"ISO minor_units vs CLDR _digits ({len(differ)}): {differ}"]


def column_lines(columns, es):
    narrow = {r["code"]: r["symbol_narrow"] for r in columns if r["symbol_narrow"]}
    fallback_plural = [r["code"] for r in columns
                       if "displayName-count-other" not in es.get(r["code"], {}) and r["name_plural"]]
    cash = {r["code"]: (r["cash_minor_units"], r["cash_rounding"]) for r in columns
            if r["cash_minor_units"] or r["cash_rounding"]}
    return [
        f"filas: {len(columns)}",
        f"con symbol_narrow ({len(narrow)}): {narrow}",
        f"name_plural sin displayName-count-other (se usa displayName): {fallback_plural}",
        f"sin datos CLDR es (name_plural vacío): {[r['code'] for r in columns if not r['name_plural']]}",
        f"sin countries: {[r['code'] for r in columns if not r['countries']]}",
        f"cash_minor_units/cash_rounding ({len(cash)}): {cash}",
    ]


def country_lines(countries):
    multi = {r["code"]: (r["currency_code"], r["other_currency_codes"]) for r in countries if r["other_currency_codes"]}
    by_code = {r["code"]: r["currency_code"] for r in countries}
    parents = {region: f"{entity} -> {by_code.get(region)}" for region, entity in sources.PARENT_ENTITY.items()}
    return [
        f"filas: {len(countries)}",
        f"tomadas de la entidad SIX que las contiene: {parents}",
        f"sin divisa: {[r['code'] for r in countries if not r['currency_code']]}",
        f"con varias ({len(multi)}): {multi}",
    ]


def cldr_reason(code, region, regions):
    attrs = [a for c, a in regions.get(region, ()) if c == code]
    if not attrs:
        return "CLDR no la asocia"
    if any(a.get("_tender") == sources.NOT_TENDER and "_to" not in a for a in attrs):
        return "CLDR _tender=false"
    ends = sorted(a["_to"] for a in attrs if "_to" in a)
    return f"CLDR _to={ends[-1]}" if ends else "CLDR otra causa"


def six_mapping(data, allowed):
    mapped, supranational, no_currency = set(), set(), set()
    for entry in data["six_one"][1]:
        alpha2 = sources.entity_alpha2(entry["entity"], data["iso_index"])
        if not entry["code"]:
            no_currency.add(f"{entry['entity']}={alpha2}")
        elif alpha2 is None:
            supranational.add(f"{entry['entity']}:{entry['code']}")
        elif alpha2 in allowed:
            mapped.add((entry["code"], alpha2))
    return mapped, supranational, no_currency


def comparison_lines(data, current):
    _, _, regions = data["currency_data"]
    allowed = {p["code"] for p in data["paises"]}
    six_pairs, supranational, no_currency = six_mapping(data, allowed)
    six_codes = {e["code"] for e in data["six_one"][1] if e["code"]}
    cldr_pairs = {(code, region) for region, codes in current.items() for code in codes}
    six_regions = {region for _, region in six_pairs} | {e.split("=")[1] for e in no_currency}
    only_six = [f"{c}@{r} ({cldr_reason(c, r, regions)})" for c, r in sorted(six_pairs - cldr_pairs)]
    only_cldr = [f"{c}@{r}" for c, r in sorted(cldr_pairs - six_pairs)]
    return [
        f"pares divisa@país SIX={len(six_pairs)} CLDR={len(cldr_pairs)} comunes={len(six_pairs & cldr_pairs)}",
        f"solo SIX ({len(only_six)}): {only_six}",
        f"solo CLDR ({len(only_cldr)}): {only_cldr}",
        f"SIX sin moneda universal: {sorted(no_currency)}",
        f"SIX entidades no territoriales ({len(supranational)}): {sorted(supranational)}",
        f"paises.csv sin entidad SIX: {sorted(allowed - six_regions)}",
        f"CLDR con divisa vigente fuera de paises.csv: {outside_lines(regions, allowed)}",
        f"vigentes en CLDR y ausentes en list-one: {sorted(cldr_current_codes(regions) - six_codes)}",
    ]


def cldr_current_codes(regions):
    return {c for items in regions.values() for c, a in items if sources.is_current_tender(a)}


def outside_lines(regions, allowed):
    return {
        region: [c for c, a in items if sources.is_current_tender(a)]
        for region, items in sorted(regions.items())
        if region not in allowed and any(sources.is_current_tender(a) for _, a in items)
    }


def historic_lines(data, historic):
    entries = data["six_three"][1]
    current_codes = {e["code"] for e in data["six_one"][1] if e["code"]}
    per_code = Counter(r["code"] for r in historic)
    same_entity = Counter((r["code"], r["country"]) for r in historic)
    english = sorted({r["code"] for r in historic if r["name_lang"] == "en"})
    return [
        f"filas: {len(historic)}, códigos distintos: {len(per_code)}",
        f"códigos en varias filas: {dict(sorted((c, n) for c, n in per_code.items() if n > 1))}",
        f"misma divisa y entidad repetida: {[k for k, n in same_entity.items() if n > 1]}",
        f"códigos aún vigentes en list-one: {sorted(set(per_code) & current_codes)}",
        f"nombre inglés SIX ({len(english)}): {english}",
        f"withdrawn no AAAA-MM: {sorted({r['withdrawn'] for r in historic if not sources.WITHDRAWN_MONTH.fullmatch(r['withdrawn'])})}",
        f"sin numérico: {[r['code'] for r in historic if not r['numeric']]}",
        f"IsFund: {[(e['code'], e['is_fund_attr']) for e in entries if e['is_fund_attr']]}",
        f"espacios normalizados en entidad: {sorted({e['entity_raw'] for e in entries if e['entity_raw'] != e['entity']})}",
    ]


def euro_start(items):
    start = next(a["_from"] for c, a in items if c == EURO and sources.is_current_tender(a))
    return (date.fromisoformat(start) - timedelta(days=1)).isoformat()


def euro_lines(data, current):
    _, _, regions = data["currency_data"]
    historic_codes = {e["code"] for e in data["six_three"][1]}
    previous = {
        code
        for region, codes in current.items() if EURO in codes
        for code, attrs in regions.get(region, ())
        if attrs.get("_to", "") >= euro_start(regions[region]) and attrs.get("_tender") != sources.NOT_TENDER
    }
    return [
        f"divisas sustituidas por el euro según CLDR: {sorted(previous)}",
        f"ausentes en list-three: {sorted(previous - historic_codes)}",
    ]


def print_report(data, current, columns, countries, historic):
    section("Fuentes", source_lines(data))
    section("Coherencia con divisas.csv", consistency_lines(data))
    section("divisas_columnas.csv", column_lines(columns, data["es"]))
    section("paises_divisa.csv", country_lines(countries))
    section("SIX list-one vs CLDR currencyData", comparison_lines(data, current) + digits_lines(data))
    section("divisas_historicas.csv", historic_lines(data, historic))
    section("Monedas previas al euro", euro_lines(data, current))
