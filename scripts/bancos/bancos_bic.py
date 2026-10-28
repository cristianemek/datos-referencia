import argparse
import csv
import gzip
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

import bancos_bde as bde

REPO = Path(__file__).resolve().parents[2]
GLEIF_LIST_URL = "https://mapping.gleif.org/api/v2/bic-lei?page%5Bnumber%5D=1&page%5Bsize%5D=100"
ECB_PAGE_URL = "https://www.ecb.europa.eu/stats/financial_corporations/list_of_financial_institutions/html/daily_list-MID.en.html"
ECB_BASE_URL = "https://www.ecb.europa.eu"
ECB_FILE = re.compile(r'href="(/stats/money/mfi/general/html/dla/mfi_MID/mfi_csv_\d{6}\.csv\.gz)"')
GLEIF_DATE = re.compile(r"(\d{4})(\d{2})(\d{2})")
BRANCH_TYPES = ("sucursal_ue", "sucursal_extracomunitaria")
HEADER = ["bank_code", "bic", "lei", "bic_source_date", "match"]


class Target(NamedTuple):
    code: str
    name: str
    lei: str
    branch: bool
    current_bic: str
    is_new: bool


class Result(NamedTuple):
    target: Target
    bic: str
    lei: str
    match: str
    candidates: tuple
    foreign: tuple


def gleif_date(name: str) -> str:
    match = GLEIF_DATE.search(name)

    if not match:
        raise ValueError(f"No se reconoce la fecha del fichero GLEIF {name!r}")

    return "-".join(match.groups())


def latest_gleif() -> tuple:
    listing = json.loads(bde.fetch(GLEIF_LIST_URL))
    files = [item["attributes"] for item in listing.get("data", ()) if item["attributes"].get("valid")]

    if not files:
        raise RuntimeError("GLEIF no publica ningún fichero BIC-LEI válido")

    latest = max(files, key=lambda attributes: attributes["uploadedAt"])
    return bde.fetch(latest["downloadLink"]), gleif_date(latest["fileName"])


def read_gleif(data: bytes) -> tuple:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]

        if len(names) != 1:
            raise ValueError("El zip de GLEIF debe contener un único CSV")

        rows = list(csv.DictReader(io.TextIOWrapper(archive.open(names[0]), encoding="utf-8-sig")))

    by_lei = defaultdict(set)
    by_bic = defaultdict(set)

    for row in rows:
        by_lei[row["LEI"].strip()].add(row["BIC"].strip())
        by_bic[row["BIC"].strip()].add(row["LEI"].strip())

    return {k: tuple(sorted(v)) for k, v in by_lei.items()}, {k: tuple(sorted(v)) for k, v in by_bic.items()}


def latest_mfi() -> bytes:
    page = bde.fetch(ECB_PAGE_URL).decode("utf-8", "replace")
    match = ECB_FILE.search(page)

    if not match:
        raise RuntimeError("No se encuentra la lista diaria de IFM en la web del BCE")

    print(f"Lista de IFM del BCE: {ECB_BASE_URL}{match.group(1)}")
    return gzip.decompress(bde.fetch(ECB_BASE_URL + match.group(1)))


def read_mfi(data: bytes) -> dict:
    rows = csv.DictReader(io.StringIO(data.decode("utf-16")), delimiter="\t")
    return {row["RIAD_CODE"]: (row["LEI"].strip(), row["HEAD_LEI"].strip()) for row in rows if row["RIAD_CODE"].startswith("ES")}


def current_targets(banks: list, index: bde.Index) -> list:
    targets = []

    for bank in banks:
        code = bank["bank_code"]
        entry = bde.current_or_last(code, index) or (bde.renumbered_holder(code, index) if code in bde.RENUMBERED else None)

        if entry is None:
            raise ValueError(f"El código {code} de bancos_es.csv no está en el registro del BdE")

        branch = bde.entity_type(entry.type_code) in BRANCH_TYPES
        targets.append(Target(code, bank["bank_name"], entry.lei, branch, bank.get("bic", ""), False))

    return targets


def new_targets(entries: tuple, banks: list) -> list:
    return [
        Target(row[0], row[1], row[3], row[4] in BRANCH_TYPES, "", True)
        for row in bde.new_bank_rows(entries, banks)
    ]


def is_spanish(bic: str) -> bool:
    return bic[4:6] == "ES"


def candidates(target: Target, by_lei: dict, mfi: dict) -> tuple:
    mfi_lei, head_lei = mfi.get("ES" + target.code, ("", ""))
    own_lei = target.lei or mfi_lei
    own = by_lei.get(own_lei, ()) if own_lei else ()

    if own or not target.branch or not head_lei:
        return own_lei, own, ()

    head = by_lei.get(head_lei, ())
    return head_lei, tuple(bic for bic in head if is_spanish(bic)), tuple(bic for bic in head if not is_spanish(bic))


def choose(bics: tuple) -> tuple:
    if not bics:
        return "", "none"

    if len(bics) == 1:
        return bics[0], "unique"

    main = [bic for bic in bics if is_spanish(bic) and bic.endswith("XXX")]
    return (main[0] if len(main) == 1 else ""), "multiple"


def resolve(target: Target, by_lei: dict, mfi: dict) -> Result:
    lei, bics, foreign = candidates(target, by_lei, mfi)
    bic, match = choose(bics)
    return Result(target, bic, lei, match, bics, foreign)


def write_csv(path: Path, results: list, source_date: str) -> None:
    rows = [[r.target.code, r.bic, r.lei, source_date, r.match] for r in sorted(results, key=lambda r: r.target.code)]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    print(f"{path}: {len(rows)} filas")


def summary(results: list) -> str:
    unique = sum(1 for r in results if r.match == "unique")
    chosen = sum(1 for r in results if r.match == "multiple" and r.bic)
    ambiguous = sum(1 for r in results if r.match == "multiple" and not r.bic)
    none = sum(1 for r in results if r.match == "none")
    return f"{len(results)} filas: {unique} con BIC único, {chosen} elegidos entre varios, {ambiguous} ambiguos, {none} sin BIC"


def report_current(results: list, by_bic: dict) -> None:
    print("Discrepancias con los BIC de bancos_es.csv:")

    for r in results:
        if r.bic == r.target.current_bic:
            continue

        known = by_bic.get(r.target.current_bic)
        where = f"en GLEIF con LEI {', '.join(known)}" if known else "no está en GLEIF"
        current = r.target.current_bic or "(vacío)"
        print(f"  {r.target.code} {r.target.name!r}: actual {current} ({where}); GLEIF {r.bic or '-'} [{r.match}, LEI {r.lei or '-'}]")


def report_pending(results: list) -> None:
    print("Sin BIC en las entidades nuevas:")

    for r in results:
        if not r.bic:
            foreign = f", BIC de la matriz fuera de España: {len(r.foreign)}" if r.foreign else ""
            print(f"  {r.target.code} {r.target.name!r}: {r.match}, LEI {r.lei or '-'}, candidatos {', '.join(r.candidates) or '-'}{foreign}")


def read_local_mfi(path: Path) -> bytes:
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def main() -> None:
    parser = argparse.ArgumentParser(description="Cruza los bancos con el fichero BIC-LEI de GLEIF y SWIFT.")
    parser.add_argument("--xlsx", type=Path, help="Registro_Entidades.xlsx ya descargado")
    parser.add_argument("--gleif", type=Path, help="zip LEI-BIC de GLEIF ya descargado")
    parser.add_argument("--mfi", type=Path, help="lista de IFM del BCE ya descargada (csv o csv.gz)")
    parser.add_argument("--bancos", type=Path, default=REPO / "bancos" / "bancos_es.csv")
    parser.add_argument("--out", type=Path, default=REPO / "build" / "bancos_bic.csv")
    args = parser.parse_args()

    _, entries = bde.read_register(args.xlsx.read_bytes() if args.xlsx else bde.fetch(bde.SOURCE_URL))
    index = bde.build_index(entries)
    banks = bde.read_banks(args.bancos)
    gleif_data, source_date = (args.gleif.read_bytes(), gleif_date(args.gleif.name)) if args.gleif else latest_gleif()
    by_lei, by_bic = read_gleif(gleif_data)
    mfi = read_mfi(read_local_mfi(args.mfi) if args.mfi else latest_mfi())
    print(f"Fichero BIC-LEI de GLEIF del {source_date}: {len(by_bic)} BIC")

    current = [resolve(target, by_lei, mfi) for target in current_targets(banks, index)]
    new = [resolve(target, by_lei, mfi) for target in new_targets(entries, banks)]
    write_csv(args.out, current + new, source_date)
    print(f"Actuales: {summary(current)}")
    print(f"Nuevas: {summary(new)}")
    report_current(current, by_bic)
    report_pending(new)


if __name__ == "__main__":
    main()
