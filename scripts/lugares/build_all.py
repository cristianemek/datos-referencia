import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PKL = REPO / "build" / "cache" / "lugares" / "ign" / "municipios_ign.pkl"
STEPS = [
    "download.py", "build_hospitales.py", "build_centros_salud.py", "build_aeropuertos.py",
    "build_unlocode.py", "build_puertos.py", "build_centros_educativos.py", "build_universidades.py",
    "validate.py",
]


def main() -> None:
    steps = (["ign_download.py"] if not PKL.exists() else []) + STEPS
    for step in steps:
        print(f"### {step}", flush=True)
        result = subprocess.run([sys.executable, str(HERE / step)], cwd=REPO)
        if result.returncode != 0:
            sys.exit(f"Falló {step}")


if __name__ == "__main__":
    main()
