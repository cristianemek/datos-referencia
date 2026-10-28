import argparse
import csv
import datetime
import io
import sys
from collections import Counter, defaultdict
from pathlib import Path

from adaptadores_ine import cataluna, euskadi, galicia, madrid, murcia
from adaptadores_mixtos import aragon, castilla_leon
from adaptadores_nombre import andalucia, asturias, baleares, extremadura, navarra
from comun import HEADER, OUTPUT, REPO, FormatChanged, Holiday, fold
from referencia import Context, Reference

ADAPTERS = [
    ("01", "Andalucía", andalucia),
    ("02", "Aragón", aragon),
    ("03", "Asturias", asturias),
    ("04", "Illes Balears", baleares),
    ("07", "Castilla y León", castilla_leon),
    ("09", "Cataluña", cataluna),
    ("11", "Extremadura", extremadura),
    ("12", "Galicia", galicia),
    ("13", "Comunidad de Madrid", madrid),
    ("14", "Región de Murcia", murcia),
    ("15", "Navarra", navarra),
    ("16", "País Vasco", euskadi),
]


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"Argumentos no válidos: {message}", file=sys.stderr)
        sys.exit(1)


def validate(rows: list[Holiday], context: Context) -> list[Holiday]:
    reference, kept, problems = context.reference, {}, Counter()

    if not reference.has_regional(context.year, context.ccaa):
        context.note(f"festivos_es.csv no tiene {context.year}: no se comprueba la coincidencia con festivos autonómicos")

    for row in rows:
        if row.municipality_code not in reference.municipalities:
            problem = "código INE inexistente"
        elif reference.ccaa(row.municipality_code) != context.ccaa:
            problem = "municipio de otra comunidad"
        elif not row.date.startswith(f"{context.year}-"):
            problem = "fecha de otro año"
        elif row.date in reference.regional_dates(context.year, context.ccaa, row.municipality_code):
            problem = "coincide con un festivo nacional o autonómico"
        else:
            kept.setdefault((row.date, row.municipality_code, fold(row.locality)), row)
            continue

        problems[problem] += 1
        context.note(f"{problem}: {row.date} {row.municipality_code} {row.locality}".rstrip())

    groups = defaultdict(list)

    for row in kept.values():
        groups[(row.municipality_code, fold(row.locality))].append(row)

    valid = []

    for (code, _), group in groups.items():
        if len(group) > 2:
            problems["más de dos fiestas en el mismo municipio o localidad"] += len(group)
            context.note(f"más de dos fiestas: {code} {group[0].locality} {[row.date for row in group]}")
            continue

        valid.extend(group)

    if problems:
        context.note(f"filas descartadas en la validación: {dict(problems)}")

    return sorted(valid, key=sort_key)


def sort_key(row: Holiday) -> tuple:
    return row.date, row.municipality_code, row.locality, row.name


def write(results: dict[tuple[int, str], list[Holiday]]) -> int:
    replaced = {(str(year), ccaa) for year, ccaa in results}
    existing = []

    if OUTPUT.exists():
        with OUTPUT.open(encoding="utf-8", newline="") as file:
            existing = [Holiday(*row) for row in list(csv.reader(file))[1:] if row]

    kept = [row for row in existing if (row.date[:4], row.ccaa_code) not in replaced]
    rows = sorted(kept + [row for group in results.values() for row in group], key=sort_key)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(row.row() for row in rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(buffer.getvalue(), encoding="utf-8")

    return len(rows)


def coverage(rows: list[Holiday], reference: Reference, ccaa: str) -> str:
    total = sum(1 for code in reference.municipalities if reference.ccaa(code) == ccaa)
    general = Counter(row.municipality_code for row in rows if not row.locality)
    with_data = {row.municipality_code for row in rows}
    localities = {(row.municipality_code, row.locality) for row in rows if row.locality}

    return (f"{len(rows)} filas, {len(with_data)}/{total} municipios con datos, "
            f"{sum(1 for count in general.values() if count == 2)} con 2 fiestas generales, {len(localities)} localidades")


def report(year: int, label: str, rows: list[Holiday], context: Context, detail: bool) -> None:
    print(f"{year} {context.ccaa} {label}: {coverage(rows, context.reference, context.ccaa)}")

    if context.matches:
        print(f"    cruce por nombre: {dict(context.matches)}")

    shown = context.notes if detail else context.notes[:5]

    for note in shown:
        print(f"    · {note}")

    if len(context.notes) > len(shown):
        print(f"    · … y {len(context.notes) - len(shown)} avisos más (usa --detalle)")


def write_report(path: Path, results: dict, errors: list[str], missing: list[int]) -> None:
    lines = [
        "El script `scripts/festivos_locales/festivos_locales.py` ha descargado las fiestas locales de los portales de datos abiertos autonómicos y ha actualizado `calendario/festivos_locales_es.csv`.",
        "",
        "Revisa el diff y el registro de la acción (cruces por nombre y filas descartadas) antes de fusionar.",
        "",
        "| Año | Comunidad | Filas |",
        "|---|---|---|",
        *[f"| {year} | {ccaa} | {len(rows)} |" for (year, ccaa), rows in sorted(results.items())],
    ]
    if errors:
        lines += ["", "## Fuentes que no han respondido", "", "Se conservan sus filas anteriores:", "", *[f"- {error}" for error in errors]]
    if missing:
        lines += ["", f"Todavía sin publicar en ninguna fuente: {', '.join(map(str, missing))}."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_arguments() -> tuple[list[int], set[str], bool, Path | None]:
    today = datetime.date.today()
    parser = Parser(description="Actualiza calendario/festivos_locales_es.csv con las fiestas locales de los portales de datos abiertos autonómicos.")
    parser.add_argument("years", nargs="*", type=int, help="años (por defecto, el actual y el siguiente)")
    parser.add_argument("--ccaa", help="códigos de comunidad separados por comas (por defecto, todas las que tienen adaptador)")
    parser.add_argument("--excluir", help="códigos de comunidad separados por comas que no se actualizan")
    parser.add_argument("--detalle", action="store_true", help="muestra todos los avisos de cruce y validación")
    parser.add_argument("--informe", type=Path, help="fichero Markdown donde resumir lo actualizado y las fuentes que fallan")
    args = parser.parse_args()

    available = {code for code, _, _ in ADAPTERS}
    excluded = set(args.excluir.split(",")) if args.excluir else set()
    wanted = (set(args.ccaa.split(",")) if args.ccaa else available) - excluded
    unknown = (wanted | excluded) - available

    if unknown:
        parser.error(f"no hay adaptador para las comunidades {sorted(unknown)}")

    return args.years or [today.year, today.year + 1], wanted, args.detalle, args.informe


def main() -> None:
    years, wanted, detail, report_path = parse_arguments()
    reference = Reference()
    results, errors = {}, []

    for year in years:
        for ccaa, label, adapter in ADAPTERS:
            if ccaa not in wanted:
                continue

            context = Context(reference, year, ccaa)

            try:
                rows = adapter(context)
            except (FormatChanged, RuntimeError, ValueError, KeyError) as error:
                errors.append(f"{label} {year}: {error}")
                continue

            if rows is None:
                print(f"{year} {ccaa} {label}: todavía no publicado" + (f" ({context.notes[0]})" if context.notes else ""))
                continue

            results[(year, ccaa)] = validate(rows, context)
            report(year, label, results[(year, ccaa)], context, detail)

    if results:
        total = write(results)
        print(f"\n{sum(len(rows) for rows in results.values())} filas actualizadas ({total} en total en {OUTPUT.relative_to(REPO)})")

    missing = [year for year in years if not any(key[0] == year for key in results)]

    if report_path:
        write_report(report_path, results, errors, missing)

    if errors:
        print("\nAlgunas fuentes han fallado; se conservan sus filas anteriores:", file=sys.stderr)

        for error in errors:
            print(f"  - {error}", file=sys.stderr)

        sys.exit(3)

    if missing:
        print(f"Las fiestas locales de {', '.join(map(str, missing))} todavía no están publicadas en ninguna fuente.")
        sys.exit(2)


if __name__ == "__main__":
    main()
