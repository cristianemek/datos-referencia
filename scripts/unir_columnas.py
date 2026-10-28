import argparse
import csv
import io
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIELD_SIZE_LIMIT = 2**31 - 1
BUILD = REPO / "build"

MERGES = {
    "bancos/bancos_es.csv": {
        "key": "bank_code",
        "sources": [
            {"file": "bancos_enriquecimiento.csv", "columns": ["nif", "lei", "entity_type", "active", "deregistered_on", "successor_code"]},
        ],
        "order": [
            "country_code", "bank_code", "bic", "bank_name", "nif", "lei", "entity_type", "active",
            "deregistered_on", "successor_code", "logo_on_dark", "logo",
        ],
    },
    "direcciones/municipios_es.csv": {
        "key": "municipality_code",
        "sources": [
            {"file": "municipios_dir3.csv", "columns": ["dir3_code"]},
            {"file": "municipios_columnas.csv", "columns": [
                "judicial_district_code", "area_km2", "degurba", "coastal", "city_code", "city_name", "fua_code", "fua_name",
            ]},
            {"file": "municipios_capital_coords.csv", "columns": ["latitude", "longitude"], "keep_missing": True, "min_coverage": 0.99},
            {"file": "municipios_capital_coords.csv", "columns": ["altitude"], "min_coverage": 0.99},
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
        "sources": [
            {"file": "provincias_timezone.csv", "columns": ["timezone"]},
            {"file": "provincias_capital_coords.csv", "columns": ["latitude", "longitude"]},
        ],
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
             "rename": {"name": "intrastat_name", "regulation": "intrastat_regulation"}, "min_coverage": 0.8},
        ],
        "order": [
            "code", "name", "intrastat_name", "transport_mode", "place", "seller_responsibility", "regulation",
            "intrastat_regulation",
        ],
    },
}


class MergeError(Exception):
    pass


def output_columns(source: dict) -> list[str]:
    rename = source.get("rename", {})

    return [rename.get(column, column) for column in source["columns"]]


def read_csv(path: Path, key: str) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    if len(header) != len(set(header)):
        raise MergeError(f"{path.relative_to(REPO)}: columnas repetidas en la cabecera")

    if key not in header:
        raise MergeError(f"{path.relative_to(REPO)}: falta la columna clave {key}")

    malformed = [index for index, row in enumerate(rows, 2) if None in row or None in row.values()]

    if malformed:
        raise MergeError(f"{path.relative_to(REPO)}: filas con un número de campos distinto de la cabecera: {malformed[:10]}")

    counts = Counter(row[key] for row in rows)
    repeated = [value for value, count in counts.items() if count > 1 or not value]

    if repeated:
        raise MergeError(f"{path.relative_to(REPO)}: claves vacías o repetidas: {repeated[:10]}")

    return header, rows


def write_csv(path: Path, header: list[str], rows: list[dict]) -> None:
    if any("\r" in value for row in rows for value in row.values()):
        raise MergeError(f"{path.relative_to(REPO)}: hay celdas con retornos de carro")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    os.replace(temporary, path)


def check_spec(target: str, spec: dict) -> None:
    columns = [column for source in spec["sources"] for column in output_columns(source)]
    repeated = sorted({column for column in columns if columns.count(column) > 1})

    if spec["key"] in columns or repeated:
        raise MergeError(f"{target}: varias fuentes escriben las mismas columnas: {repeated or [spec['key']]}")


def source_values(source: dict, key: str) -> dict:
    path = BUILD / source["file"]
    header, rows = read_csv(path, key)
    missing = [column for column in source["columns"] if column not in header]

    if missing:
        raise MergeError(f"{source['file']}: faltan las columnas {missing}")

    if not rows:
        raise MergeError(f"{source['file']}: no tiene filas")

    columns = output_columns(source)

    return {row[key]: dict(zip(columns, (row[column] for column in source["columns"]))) for row in rows}


def apply_source(rows: list[dict], key: str, source: dict, values: dict, target: str) -> list[dict]:
    keys = {row[key] for row in rows}
    unknown = set(values) - keys

    if unknown:
        raise MergeError(f"{source['file']}: claves que no están en {target}: {sorted(unknown)[:10]}")

    coverage = len(values) / len(keys) if keys else 1
    minimum = source.get("min_coverage", 1)

    if coverage < minimum:
        raise MergeError(f"{source['file']}: solo cubre {len(values)} de {len(keys)} filas de {target} (mínimo {minimum:.0%})")

    columns = output_columns(source)
    keep = source.get("keep_missing", False)

    return [
        {**row, **values.get(row[key], {column: row.get(column, "") if keep else "" for column in columns})}
        for row in rows
    ]


def merge_target(target: str, spec: dict) -> str:
    check_spec(target, spec)
    path = REPO / target
    header, rows = read_csv(path, spec["key"])
    present = set(header)
    used, skipped = [], []

    for source in spec["sources"]:
        if not (BUILD / source["file"]).exists():
            lost = [column for column in output_columns(source) if column not in present]

            if lost:
                raise MergeError(f"{target}: falta build/{source['file']} y sin él se perderían las columnas {lost}")

            skipped.append(source["file"])
            continue

        rows = apply_source(rows, spec["key"], source, source_values(source, spec["key"]), target)
        present |= set(output_columns(source))
        used.append(source["file"])

    order = [column for column in spec["order"] if column in present]
    leftover = present - set(order)

    if leftover:
        raise MergeError(f"{target}: columnas sin posición en el orden: {sorted(leftover)}")

    write_csv(path, order, [{column: row.get(column, "") for column in order} for row in rows])
    message = f"{target}: {len(rows)} filas, {len(order)} columnas"

    if used:
        message += f"; unidas: {', '.join(dict.fromkeys(used))}"

    if skipped:
        message += f"; sin cambios (no está en build/): {', '.join(dict.fromkeys(skipped))}"

    return message


def main() -> None:
    parser = argparse.ArgumentParser(description="Une a los CSV del repo las columnas que generan los scripts en build/.")
    parser.add_argument("targets", nargs="*", metavar="fichero", help=f"por defecto, todos: {', '.join(MERGES)}")
    args = parser.parse_args()
    targets = [Path(target).as_posix().removeprefix("./") for target in args.targets]
    unknown = [target for target in targets if target not in MERGES]

    if unknown:
        parser.error(f"ficheros desconocidos: {', '.join(unknown)}")

    csv.field_size_limit(FIELD_SIZE_LIMIT)

    try:
        for target in targets or MERGES:
            print(merge_target(target, MERGES[target]))
    except MergeError as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()
