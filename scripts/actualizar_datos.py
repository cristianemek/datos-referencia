import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 3600
OUTPUT_LINES = 15
DATA_FOLDERS = [
    "bancos", "catalogos", "comercio_exterior", "direcciones", "facturacion", "lugares", "pagos", "telecomunicaciones",
]
NEW_BANKS = REPO / "build" / "bancos_nuevos.csv"

STEPS = [
    ("Redsys", ["scripts/redsys_codigos.py"]),
    ("Registro del Banco de España", ["scripts/bancos/bancos_bde.py"]),
    ("Municipios (Eurostat y partidos judiciales)", ["scripts/territorio/municipios_columnas.py"]),
    ("Países", ["scripts/territorio/paises_columnas.py"]),
    ("Zonas horarias y cambios de hora", ["scripts/territorio/zonas_horarias.py"]),
    ("Entidades de población y capitales", ["scripts/poblacion/entidades_poblacion_es.py"]),
    ("Secciones censales", ["scripts/poblacion/secciones_censales_es.py"]),
    ("Divisas", ["scripts/divisas/build.py", "--descargar"]),
    ("CNO-11", ["scripts/rrhh/cno_11.py"]),
    ("CNED-2014", ["scripts/rrhh/cned_2014.py"]),
    ("Tipos de documento de identidad", ["scripts/rrhh/tipos_documento_identidad.py"]),
    ("Idiomas", ["scripts/rrhh/idiomas.py"]),
    ("Formas jurídicas y letras del NIF", ["scripts/empresa/formas_juridicas_es.py"]),
    ("Incoterms", ["scripts/empresa/incoterms.py"]),
    ("Unidades de medida", ["scripts/empresa/unidades_medida.py"]),
    ("Nomenclatura Combinada", ["scripts/comercio_exterior/nomenclatura_combinada.py"]),
    ("Intrastat", ["scripts/comercio_exterior/intrastat_listas.py"]),
    ("VeriFactu", ["scripts/facturacion/verifactu.py"]),
    ("Facturae", ["scripts/facturacion/facturae_codigos.py"]),
    ("ISO 20022", ["scripts/facturacion/iso20022_codigos.py"]),
    ("Norma 43", ["scripts/facturacion/norma43_conceptos.py"]),
    ("FACe y DIR3", ["scripts/facturacion/face_dir3.py"]),
    ("Numeración y operadores de la CNMC", ["scripts/telecomunicaciones/cnmc_numeracion.py"]),
    ("Sanidad, transporte y educación", ["scripts/lugares/build_all.py"]),
    ("Banderas de países", ["scripts/banderas/banderas.py"]),
    ("Unión de columnas", ["scripts/unir_columnas.py"]),
]


def run(command: list[str]) -> tuple[int, str, float]:
    start = time.monotonic()
    try:
        result = subprocess.run([sys.executable, *command], cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124, f"Sin respuesta tras {TIMEOUT} s", time.monotonic() - start
    return result.returncode, (result.stdout + result.stderr).strip(), time.monotonic() - start


def tail(text: str, lines: int) -> str:
    rows = text.splitlines()
    return "\n".join(rows[-lines:]) if len(rows) > lines else text


def restore_unmerged(output: str) -> list[str]:
    targets = [line.split(":", 1)[0].removeprefix("Error en ").strip() for line in output.splitlines() if line.startswith("Error en ")]
    for target in targets:
        subprocess.run(["git", "checkout", "--", target], cwd=REPO, check=True)
    return targets


def changed_files() -> str:
    tracked = subprocess.run(["git", "diff", "--stat", "--", *DATA_FOLDERS], cwd=REPO, capture_output=True, text=True).stdout
    new = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", *DATA_FOLDERS],
                         cwd=REPO, capture_output=True, text=True).stdout
    return "\n".join(part.strip() for part in (tracked, new and f"Ficheros nuevos:\n{new}") if part.strip())


def new_banks() -> list[str]:
    if not NEW_BANKS.exists():
        return []
    with NEW_BANKS.open(encoding="utf-8", newline="") as handle:
        return [f"{row['bank_code']} {row['name']}" for row in csv.DictReader(handle)]


def report(results: list[tuple[str, int, str, float]]) -> str:
    failed = [item for item in results if item[1] != 0]
    lines = [
        "Actualización de los datos desde sus fuentes oficiales. Revisa el diff antes de fusionar.",
        "",
        "| Paso | Resultado | Tiempo |",
        "|---|---|---|",
        *[f"| {name} | {'correcto' if status == 0 else f'falla ({status})'} | {seconds:.0f} s |"
          for name, status, _, seconds in results],
    ]
    banks = new_banks()
    if banks:
        lines += ["", "## Entidades nuevas en el registro del Banco de España",
                  "", "No están en `bancos_es.csv`; hay que añadirlas a mano con su BIC y su logo:", "",
                  *[f"- {bank}" for bank in banks]]
    for name, status, output, _ in failed:
        lines += ["", f"## Falla: {name}", "", f"```\n{tail(output, OUTPUT_LINES)}\n```"]
    changes = changed_files()
    lines += ["", "## Ficheros cambiados", "", f"```\n{changes}\n```" if changes else "Ninguno."]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenera todos los datos desde sus fuentes y resume los cambios.")
    parser.add_argument("--informe", type=Path, help="fichero Markdown donde escribir el informe")
    args = parser.parse_args()
    results = []

    for name, command in STEPS:
        status, output, seconds = run(command)
        if command[0] == "scripts/unir_columnas.py" and status != 0:
            restored = restore_unmerged(output)
            output += f"\n\nRestaurados sin cambios por no poder unir sus columnas: {', '.join(restored) or 'ninguno'}"
        results.append((name, status, output, seconds))
        print(f"{name}: {'correcto' if status == 0 else f'falla ({status})'} en {seconds:.0f} s", flush=True)

    text = report(results)
    if args.informe:
        args.informe.write_text(text, encoding="utf-8")
    else:
        print(f"\n{text}")
    sys.exit(1 if any(status != 0 for _, status, _, _ in results) else 0)


if __name__ == "__main__":
    main()
