import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "build" / "cache" / "lugares"
REPORTS = RAW / "informes"
OUT = REPO / "lugares"
DIRECCIONES = REPO / "direcciones"
SPAIN_BBOX = (-18.5, 27.4, 4.6, 44.0)

csv.field_size_limit(sys.maxsize)


def read_csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_municipios() -> dict:
    return {r["municipality_code"]: r for r in read_csv(DIRECCIONES / "municipios_es.csv")}


def read_provincias() -> dict:
    return {r["province_code"]: r for r in read_csv(DIRECCIONES / "provincias_es.csv")}


def read_codigos_postales() -> list:
    return read_csv(DIRECCIONES / "codigos_postales_es.csv")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


ARTICLES = {"el", "la", "los", "las", "o", "a", "os", "as", "l", "els", "les", "es", "sa", "ses", "lo", "d", "de", "del", "dels", "y", "i", "e"}


def name_key(text: str) -> str:
    return " ".join(w for w in norm(text).split() if w not in ARTICLES)


def name_variants(text: str) -> set:
    variants = set()
    for part in re.split(r"\s*/\s*|\s+-\s+", text or ""):
        part = part.strip()
        if not part:
            continue
        variants.add(part)
        m = re.match(r"^(.*),\s*(\S+)$", part)
        if m:
            variants.add(f"{m.group(2)} {m.group(1)}")
            variants.add(m.group(1))
        variants.add(re.sub(r"\s*\(.*?\)\s*", " ", part).strip())
        variants.update(x.strip() for x in re.findall(r"\(([^)]{3,})\)", part))
    keys = {name_key(v) for v in variants}
    return {k for k in keys if k}


def clean(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def phone_list(text) -> str:
    found = []
    for chunk in re.split(r"[,;/|]| y | - ", clean(text)):
        digits = re.sub(r"\D", "", chunk)
        if digits.startswith("0034"):
            digits = digits[4:]
        elif digits.startswith("34") and len(digits) == 11:
            digits = digits[2:]
        if len(digits) == 9 and digits[0] in "6789" and digits not in found and len(set(digits)) > 1:
            found.append(digits)
    return "|".join(found)


def in_spain_bbox(lat: float, lon: float) -> bool:
    w, s, e, n = SPAIN_BBOX
    return s <= lat <= n and w <= lon <= e


def write_csv(path: Path, header: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(["" if row.get(h) is None else row.get(h) for h in header])


def report(name: str, lines: list) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text("\n".join(str(x) for x in lines) + "\n", encoding="utf-8")
    for line in lines:
        if line.count("\t") == 1:
            print(line)
