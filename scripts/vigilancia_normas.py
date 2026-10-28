import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TIMEOUT = 1800
OUTPUT_LINES = 20
DIFF_LINES = 60

CHECKS = [
    ("Tipos de IVA, IGIC e IPSI", ["scripts/fiscal/tipos_impositivos.py", "--sin-boletines"], ["fiscal/tipos_impositivos_es.csv"]),
    ("Canon digital", ["scripts/fiscal/canon_digital.py", "--refrescar"], ["fiscal/canon_digital_es.csv"]),
    ("Reglas del canon digital", ["scripts/fiscal/canon_digital_reglas.py"], ["fiscal/canon_digital_reglas_es.csv"]),
    ("Impuesto sobre los envases de plástico", ["scripts/fiscal/canon_gravamenes_producto.py", "--refrescar"],
     ["fiscal/gravamenes_producto_es.csv"]),
    ("Menciones obligatorias de factura", ["scripts/facturacion/menciones_verificar.py", "--descargar"], []),
    ("Formas jurídicas y letras del NIF", ["scripts/empresa/formas_juridicas_es.py"],
     ["catalogos/formas_juridicas_es.csv", "catalogos/letras_nif_es.csv"]),
    ("Tipos de documento de identidad", ["scripts/rrhh/tipos_documento_identidad.py"], ["catalogos/tipos_documento_identidad.csv"]),
    ("Idiomas cooficiales", ["scripts/rrhh/idiomas.py"], ["catalogos/idiomas.csv"]),
]


def run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [sys.executable, *command], cwd=REPO, capture_output=True, text=True, timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 124, f"Sin respuesta tras {TIMEOUT} s"
    return result.returncode, (result.stdout + result.stderr).strip()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def changes(files: list[str]) -> str:
    if not files:
        return ""
    untracked = git("ls-files", "--others", "--exclude-standard", "--", *files).strip()
    diff = git("diff", "--unified=0", "--", *files).strip()
    return "\n".join(part for part in (untracked and f"Ficheros nuevos:\n{untracked}", diff) if part)


def tail(text: str, lines: int) -> str:
    rows = text.splitlines()
    return "\n".join(rows[-lines:]) if len(rows) > lines else text


def check(name: str, command: list[str], files: list[str]) -> tuple[str, str]:
    status, output = run(command)
    if status != 0:
        return "falla", f"`python3 {' '.join(command)}` terminó con el código {status}:\n\n```\n{tail(output, OUTPUT_LINES)}\n```"
    diff = changes(files)
    if diff:
        return "datos cambiados", f"La fuente ha cambiado los datos:\n\n```diff\n{tail(diff, DIFF_LINES)}\n```"
    return "sin cambios", ""


def report(results: list[tuple[str, str, str]]) -> str:
    lines = [
        "La comprobación semanal de las normas vigiladas ha encontrado cambios que hay que revisar a mano.",
        "",
        "| Comprobación | Resultado |",
        "|---|---|",
        *[f"| {name} | {state} |" for name, state, _ in results],
    ]
    for name, state, detail in results:
        if detail:
            lines += ["", f"## {name}", "", detail]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba que los datos tomados de normas siguen coincidiendo con el BOE y las fuentes oficiales.")
    parser.add_argument("--informe", type=Path, help="fichero Markdown donde escribir el informe si hay algo que revisar")
    args = parser.parse_args()
    results = []

    for name, command, files in CHECKS:
        state, detail = check(name, command, files)
        results.append((name, state, detail))
        print(f"{name}: {state}")

    if all(state == "sin cambios" for _, state, _ in results):
        print("Todo coincide con las fuentes.")
        return

    text = report(results)
    if args.informe:
        args.informe.write_text(text, encoding="utf-8")
    else:
        print(f"\n{text}")
    sys.exit(1)


if __name__ == "__main__":
    main()
