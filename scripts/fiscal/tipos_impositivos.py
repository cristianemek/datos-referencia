import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

import tipos_boe
import tipos_ipsi
from tipos_igic import IGIC_ROWS
from tipos_ipsi import IPSI_ROWS
from tipos_iva import IVA_ROWS

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "fiscal" / "tipos_impositivos_es.csv"
COLUMNS = ["tax", "territory", "rate_type", "rate", "surcharge_rate",
           "valid_from", "valid_to", "applies_to", "regulation"]
TAX_ORDER = {"IVA": 0, "IGIC": 1, "IPSI": 2}
TYPE_ORDER = {t: i for i, t in enumerate(
    ["minimo", "maximo", "general", "reducido", "superreducido", "cero", "especifico",
     "incrementado", "especial", "sectorial", "temporal"])}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TEXTS: dict[str, str] = {}
_LATEST: dict[tuple, tuple[dict, str]] = {}


def norm(text: str) -> str:
    text = text.replace("\xa0", " ").replace("­", "")
    return " ".join(text.split())


def bulletin(name: str) -> str:
    if name not in _TEXTS:
        _TEXTS[name] = norm(tipos_ipsi.bulletin_text(name))
    return _TEXTS[name]


def boe_texts(boe_id: str, block_id: str, version_id: str | None) -> list[str]:
    texts = [norm(" ".join(paragraphs)) for attributes, paragraphs in tipos_boe.block(boe_id, block_id)
             if version_id is None or attributes["id_norma"] == version_id]
    if not texts:
        raise SystemExit(f"{boe_id}/{block_id}: no hay versión {version_id}")
    return texts


def check_row(row: dict, bulletins: bool) -> list[str]:
    errors = []
    for check in row["checks"]:
        if len(check) == 2:
            if not bulletins:
                continue
            name, needle = check
            if norm(needle) not in bulletin(name):
                errors.append(f"'{needle}' no está en {name}")
            continue
        boe_id, block_id, version_id, needle = check
        if not any(norm(needle) in text for text in boe_texts(boe_id, block_id, version_id)):
            errors.append(f"'{needle}' no está en {boe_id}/{block_id}@{version_id}")
    return errors


def iso(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:]}" if re.fullmatch(r"\d{8}", value) else value


def latest_version(boe_id: str, block_id: str) -> tuple[dict, str]:
    key = (boe_id, block_id)
    if key not in _LATEST:
        versions = tipos_boe.block(boe_id, block_id, fresh=True)
        attributes, paragraphs = max(versions, key=lambda v: (v[0].get("fecha_vigencia", ""), v[0].get("fecha_publicacion", "")))
        _LATEST[key] = (attributes, norm(" ".join(paragraphs)))
    return _LATEST[key]


def check_current(row: dict, today: str) -> list[str]:
    if row["valid_to"] and row["valid_to"] < today:
        return []
    needles: dict[tuple, list[str]] = {}
    for check in row["checks"]:
        if len(check) == 4:
            needles.setdefault(check[:2], []).append(norm(check[3]))
    errors = []
    for (boe_id, block_id), texts in needles.items():
        attributes, latest = latest_version(boe_id, block_id)
        if not any(text in latest for text in texts):
            errors.append(
                f"{row['tax']} {row['territory'] or 'ES'} {row['rate_type']} {row['rate']} %: la última versión de "
                f"{boe_id}/{block_id} ({attributes.get('id_norma')}, vigente desde {iso(attributes.get('fecha_vigencia', ''))}) "
                f"ya no recoge este tipo; revisa la fila y añade el tipo nuevo"
            )
    return errors


def check_dates(rows: list[dict]) -> list[str]:
    errors = []
    for row in rows:
        if not ISO_DATE.match(row["valid_from"]) or (row["valid_to"] and not ISO_DATE.match(row["valid_to"])):
            errors.append(f"fecha no ISO: {row['valid_from']} {row['valid_to']}")
        elif row["valid_to"] and date.fromisoformat(row["valid_to"]) < date.fromisoformat(row["valid_from"]):
            errors.append(f"fechas invertidas: {row['valid_from']} {row['valid_to']}")
    return errors


def check_overlaps(rows: list[dict]) -> list[str]:
    errors = []
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        if row["rate_type"] != "temporal":
            key = (row["tax"], row["territory"], row["rate_type"], row["rate"], row["applies_to"])
            groups.setdefault(key, []).append(row)
    for key, group in groups.items():
        group = sorted(group, key=lambda r: r["valid_from"])
        for a, b in zip(group, group[1:]):
            end = date.fromisoformat(a["valid_to"]) if a["valid_to"] else date.max
            if end >= date.fromisoformat(b["valid_from"]):
                errors.append(f"solape {key}: {a['valid_from']}..{a['valid_to']} / {b['valid_from']}")
    return errors


def sort_key(row: dict) -> tuple:
    return (TAX_ORDER[row["tax"]], row["territory"], row["rate_type"] == "temporal",
            TYPE_ORDER.get(row["rate_type"], 99), row["valid_from"], float(row["rate"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba los tipos de IVA, IGIC e IPSI contra sus normas y escribe el CSV.")
    parser.add_argument("--sin-boletines", action="store_true",
                        help="no comprueba los boletines de Ceuta y Melilla, que son publicaciones cerradas")
    args = parser.parse_args()
    rows = IVA_ROWS + IGIC_ROWS + IPSI_ROWS
    today = date.today().isoformat()
    errors = [error for row in rows for error in check_row(row, not args.sin_boletines)]
    errors += [error for row in rows for error in check_current(row, today)]
    errors += check_dates(rows) + check_overlaps(rows)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=sort_key))
    print(f"{OUTPUT.relative_to(REPO)}: {len(rows)} filas")


if __name__ == "__main__":
    main()
