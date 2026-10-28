import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from comun import CACHE, HERE, NAMES, RAW, RESULTS, fail_if, read_json, require_node, write_json

try:
    from PIL import Image, ImageChops
except ImportError as error:
    raise SystemExit("Falta Pillow: instálalo con `pip install Pillow`") from error

WORK = CACHE / "variantes"
WIDTHS = (1000, 2000)
VARIANTS = ("minimal", "lossless", "lossless-paths")
DEDUPE_MINIMUM = "10"
TOLERANCE = 32


def run(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0, (result.stderr or result.stdout).strip()


def render(svg: Path, png: Path, width: int) -> None:
    ok, message = run(["node", str(HERE / "render.js"), str(svg), str(png), str(width), "transparent"])
    if not ok:
        raise RuntimeError(message)


def compare(reference: Path, candidate: Path) -> tuple[bool, int]:
    a, b = Image.open(reference).convert("RGBA"), Image.open(candidate).convert("RGBA")
    if a.size != b.size:
        return False, 255
    bands = ImageChops.difference(a, b).split()
    return all(band.getbbox() is None for band in bands), max(band.getextrema()[1] for band in bands)


def build_variants(stem: str, folder: Path, keep_dims: bool) -> tuple[dict, dict]:
    script = HERE / ("optimize-keepdims.js" if keep_dims else "optimize-symbol.js")
    suffix = "-dims" if keep_dims else ""
    produced, errors = {}, {}
    for variant in VARIANTS:
        target = folder / f"{variant}{suffix}.svg"
        ok, message = run(["node", str(script), str(RAW / f"{stem}.svg"), str(target), variant])
        if ok:
            produced[variant + suffix] = target
        else:
            errors[variant + suffix] = message
    base = produced.get("lossless-paths" + suffix)
    if base:
        target = folder / f"dedupe{suffix}.svg"
        ok, message = run([sys.executable, str(HERE / "dedupe_paths.py"), str(base), str(target), DEDUPE_MINIMUM])
        if ok and target.exists() and target.stat().st_size < base.stat().st_size:
            produced["dedupe" + suffix] = target
        else:
            errors["dedupe" + suffix] = message or "sin ganancia"
    return produced, errors


def evaluate(folder: Path, produced: dict) -> dict:
    results = {}
    for variant, svg in produced.items():
        entry = {"size": svg.stat().st_size, "identical": True, "max_diff": 0}
        try:
            for width in WIDTHS:
                png = folder / f"{variant}-{width}.png"
                render(svg, png, width)
                identical, max_diff = compare(folder / f"original-{width}.png", png)
                entry["identical"] = entry["identical"] and identical
                entry["max_diff"] = max(entry["max_diff"], max_diff)
                png.unlink()
        except RuntimeError as error:
            entry.update(identical=False, max_diff=255, error=str(error))
        results[variant] = entry
    return results


def process(stem: str) -> dict:
    folder = WORK / stem
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("*"):
        stale.unlink()
    for width in WIDTHS:
        render(RAW / f"{stem}.svg", folder / f"original-{width}.png", width)
    produced, errors = build_variants(stem, folder, keep_dims=False)
    variants = evaluate(folder, produced)
    if not any(entry["identical"] for entry in variants.values()):
        produced_dims, errors_dims = build_variants(stem, folder, keep_dims=True)
        variants.update(evaluate(folder, produced_dims))
        errors.update(errors_dims)
        produced.update(produced_dims)
    for png in folder.glob("*.png"):
        png.unlink()
    identical = {v: e for v, e in variants.items() if e["identical"]}
    tolerated = {v: e for v, e in variants.items() if e["max_diff"] <= TOLERANCE}
    pool = identical or tolerated
    chosen = min(pool, key=lambda v: pool[v]["size"]) if pool else None
    return {
        "stem": stem, "raw_size": (RAW / f"{stem}.svg").stat().st_size, "variants": variants, "errors": errors,
        "chosen": chosen, "path": str(produced[chosen].relative_to(CACHE)) if chosen else None,
        "mode": "identical" if identical else ("tolerance" if tolerated else "none"),
    }


def main() -> None:
    require_node()
    names = read_json(NAMES, "download.py")
    stems = sorted(Path(name).stem for name in names.values())
    with ThreadPoolExecutor(max_workers=min(10, os.cpu_count() or 1)) as executor:
        reports = list(executor.map(process, stems))
    results = {report["stem"]: report for report in reports}
    write_json(RESULTS, results)
    fail_if([f"{r['stem']}: {r['variants']}" for r in reports if r["mode"] == "none"],
            f"Banderas sin variante idéntica ni con diferencia ≤ {TOLERANCE}/255")
    identical = sum(r["mode"] == "identical" for r in reports)
    with_dims = [r["stem"] for r in reports if r["chosen"].endswith("-dims")]
    print(f"Verificación a {' y '.join(map(str, WIDTHS))} px: {identical} idénticas píxel a píxel, "
          f"{len(with_dims)} de ellas conservando width/height")
    for report in reports:
        if report["mode"] == "tolerance":
            print(f"  con tolerancia {report['stem']}: {report['chosen']}, "
                  f"diferencia máxima {report['variants'][report['chosen']]['max_diff']}/255")


if __name__ == "__main__":
    main()
