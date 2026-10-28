import argparse
import csv
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "build"

MERGES = {
    "bancos/bancos_es.csv": {
        "key": "bank_code",
        "sources": [
            {"file": "bancos_enriquecimiento.csv", "columns": ["nif", "lei", "entity_type", "active", "deregistered_on", "successor_code"]},
        ],
        "order": [
            "country_code", "bank_code", "bic", "bank_name", "nif", "lei", "entity_type", "active",
            "deregistered_on", "successor_code", "logo",
        ],
    },
    "direcciones/municipios_es.csv": {
        "key": "municipality_code",
        "sources": [
            {"file": "municipios_dir3.csv", "columns": ["dir3_code"]},
            {"file": "municipios_columnas.csv", "columns": [
                "judicial_district_code", "area_km2", "degurba", "coastal", "city_code", "city_name", "fua_code", "fua_name",
            ]},
            {"file": "municipios_capital_coords.csv", "columns": ["latitude", "longitude"], "keep_missing": True},
            {"file": "municipios_capital_coords.csv", "columns": ["altitude"]},
        ],
        "order": [
            "municipality_code", "check_digit", "dir3_code", "province_code", "municipality", "island_code", "island", "nuts3",
            "judicial_district_code", "population", "area_km2", "degurba", "coastal", "city_code", "city_name", "fua_code",
            "fua_name", "latitude", "longitude", "altitude",
        ],
    },
    "direcciones/paises.csv": {
        "key": "code",
        "sources": [
            {"file": "paises_columnas.csv", "columns": [
                "official_name", "capital", "demonym", "numeric", "region_code", "region", "subregion_code", "subregion",
                "ine_code", "vat_prefix",
            ]},
            {"file": "paises_divisa.csv", "columns": ["currency_code", "other_currency_codes"]},
            {"file": "paises_banderas.csv", "columns": ["flag_url", "flag_page_url", "flag_license", "flag_author", "flag_svg"]},
        ],
        "order": [
            "code", "alpha3", "numeric", "name", "official_name", "capital", "demonym", "phone_prefix", "vat_prefix",
            "currency_code", "other_currency_codes", "is_eu", "region_code", "region", "subregion_code", "subregion",
            "ine_code", "latitude", "longitude", "flag_url", "flag_page_url", "flag_license", "flag_author", "flag_svg",
        ],
    },
    "direcciones/comunidades_es.csv": {
        "key": "ccaa_code",
        "sources": [{"file": "comunidades_timezone.csv", "columns": ["timezone"]}],
        "order": [
            "ccaa_code", "ccaa", "iso_code", "nuts1", "nuts2", "timezone", "latitude", "longitude", "flag_svg",
            "coat_of_arms_svg",
        ],
    },
    "direcciones/provincias_es.csv": {
        "key": "province_code",
        "sources": [{"file": "provincias_timezone.csv", "columns": ["timezone"]}],
        "order": [
            "province_code", "province", "ccaa_code", "iso_code", "plate_code", "plate_code_old", "phone_prefixes",
            "timezone", "latitude", "longitude",
        ],
    },
    "catalogos/divisas.csv": {
        "key": "code",
        "sources": [
            {"file": "divisas_columnas.csv", "columns": ["symbol_narrow", "name_plural", "countries", "cash_minor_units", "cash_rounding"]},
        ],
        "order": [
            "code", "numeric", "minor_units", "name", "name_plural", "symbol", "symbol_narrow", "is_fund_or_special",
            "cash_minor_units", "cash_rounding", "countries",
        ],
    },
    "comercio_exterior/incoterms.csv": {
        "key": "code",
        "sources": [
            {"file": "intrastat_condiciones_entrega.csv", "columns": ["name", "seller_responsibility", "regulation"],
             "rename": {"name": "intrastat_name", "regulation": "intrastat_regulation"}},
        ],
        "order": [
            "code", "name", "intrastat_name", "transport_mode", "place", "seller_responsibility", "regulation",
            "intrastat_regulation",
        ],
    },
}


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def source_values(source: dict, key: str) -> dict | None:
    path = BUILD / source["file"]

    if not path.exists():
        return None

    header, rows = read_csv(path)
    missing = [column for column in [key, *source["columns"]] if column not in header]

    if missing:
        raise ValueError(f"{source['file']}: faltan las columnas {missing}")

    rename = source.get("rename", {})
    values = {}

    for row in rows:
        if row[key] in values:
            raise ValueError(f"{source['file']}: clave repetida {row[key]}")

        values[row[key]] = {rename.get(column, column): row[column] for column in source["columns"]}

    return values


def apply_source(rows: list[dict], key: str, source: dict, values: dict, target: str) -> list[dict]:
    unknown = set(values) - {row[key] for row in rows}

    if unknown:
        raise ValueError(f"{source['file']}: claves que no están en {target}: {sorted(unknown)[:10]}")

    columns = [source.get("rename", {}).get(column, column) for column in source["columns"]]
    keep = source.get("keep_missing", False)
    merged = []

    for row in rows:
        new = values.get(row[key])

        if new is None:
            new = {column: row.get(column, "") for column in columns} if keep else dict.fromkeys(columns, "")

        merged.append({**row, **new})

    return merged


def merge_target(target: str, spec: dict) -> str:
    path = REPO / target
    header, rows = read_csv(path)
    present = set(header)
    used = []

    for source in spec["sources"]:
        values = source_values(source, spec["key"])

        if values is None:
            continue

        rows = apply_source(rows, spec["key"], source, values, target)
        present |= {source.get("rename", {}).get(column, column) for column in source["columns"]}
        used.append(source["file"])

    order = [column for column in spec["order"] if column in present]
    leftover = present - set(order)

    if leftover:
        raise ValueError(f"{target}: columnas sin posición en el orden: {sorted(leftover)}")

    write_csv(path, order, [{column: row.get(column, "") for column in order} for row in rows])

    return f"{target}: {len(rows)} filas, {len(order)} columnas ({', '.join(dict.fromkeys(used)) or 'sin fuentes en build/'})"


def main() -> None:
    parser = argparse.ArgumentParser(description="Une a los CSV del repo las columnas que generan los scripts en build/.")
    parser.add_argument("targets", nargs="*", metavar="fichero", help=f"por defecto, todos: {', '.join(MERGES)}")
    args = parser.parse_args()
    unknown = [target for target in args.targets if target not in MERGES]

    if unknown:
        parser.error(f"ficheros desconocidos: {', '.join(unknown)}")

    csv.field_size_limit(sys.maxsize)

    for target in args.targets or MERGES:
        print(merge_target(target, MERGES[target]))


if __name__ == "__main__":
    main()
