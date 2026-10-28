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
import bancos_gleif as gleif

REPO = Path(__file__).resolve().parents[2]
GLEIF_LIST_URL = "https://mapping.gleif.org/api/v2/bic-lei?page%5Bnumber%5D=1&page%5Bsize%5D=100"
ECB_PAGE_URL = "https://www.ecb.europa.eu/stats/financial_corporations/list_of_financial_institutions/html/daily_list-MID.en.html"
ECB_BASE_URL = "https://www.ecb.europa.eu"
ECB_FILE = re.compile(r'href="(/stats/money/mfi/general/html/dla/mfi_MID/mfi_csv_\d{6}\.csv\.gz)"')
GLEIF_DATE = re.compile(r"(\d{4})(\d{2})(\d{2})")
BRANCH_TYPES = ("sucursal_ue", "sucursal_extracomunitaria")
HEADER = ["bank_code", "bic", "lei", "bic_source_date", "match", "bic_origin"]

LEI_SEARCHES = {
    "1581": ("MORGAN STANLEY EUROPE SE SUCURSAL EN ESPAÑA", "ES"),
    "1582": ("Citigroup Global Markets Europe AG", "DE"),
    "1590": ("MONZO BANK EUROPE DESIGNATED ACTIVITY COMPANY", "IE"),
    "8640": ("CA AUTO BANK SPA BRANCH IN SPAIN", "ES"),
}


class Target(NamedTuple):
    code: str
    name: str
    lei: str
    branch: bool
    current_bic: str
    is_new: bool


class Leis(NamedTuple):
    own: str
    head: str


class Result(NamedTuple):
    target: Target
    bic: str
    lei: str
    match: str
    origin: str
    candidates: tuple
    holder: str


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


def read_local_mfi(path: Path) -> bytes:
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


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
    return [Target(row[0], row[1], row[3], row[4] in BRANCH_TYPES, "", True) for row in bde.new_bank_rows(entries, banks)]


def searched_leis(targets: list, mfi: dict) -> dict:
    pending = [t for t in targets if t.code in LEI_SEARCHES and not t.lei and not any(mfi.get("ES" + t.code, ("", "")))]
    found = {}

    for target in pending:
        record = gleif.search(*LEI_SEARCHES[target.code])
        print(f"LEI de {target.code} en GLEIF: {record.lei} {record.name!r} ({record.country}, {record.status}, {record.category})")

        if record.category == "BRANCH" and record.country == "ES":
            head = gleif.related(record.lei, "head-office")
            found = {**found, target.code: Leis(record.lei, head.lei if head else "")}
        else:
            found = {**found, target.code: Leis("", record.lei)}

    return found


def target_leis(target: Target, mfi: dict, found: dict) -> Leis:
    mfi_lei, head_lei = mfi.get("ES" + target.code, ("", ""))
    searched = found.get(target.code, Leis("", ""))
    own = target.lei or mfi_lei or searched.own
    head = head_lei or searched.head
    return Leis(own, head if target.branch else "")


def country_of(bic: str) -> str:
    return bic[4:6]


def choose(bics: tuple, country: str) -> tuple:
    if len(bics) == 1:
        return bics[0], "unique"

    main = [bic for bic in bics if country_of(bic) == country and bic.endswith("XXX")]
    return (main[0] if len(main) == 1 else ""), "multiple"


def result(target: Target, lei: str, bics: tuple, country: str, origin: str, holder: str = "") -> Result:
    bic, match = choose(bics, country)
    return Result(target, bic, lei, match, origin if bic else "none", bics, holder)


def select(target: Target, leis: Leis, by_lei: dict, heads: dict) -> Result:
    own = by_lei.get(leis.own, ()) if leis.own else ()

    if own:
        return result(target, leis.own, own, "ES", "own")

    head_bics = by_lei.get(leis.head, ()) if leis.head else ()
    spanish = tuple(bic for bic in head_bics if country_of(bic) == "ES")

    if spanish:
        return result(target, leis.head, spanish, "ES", "own")

    head = heads.get(leis.head)
    home = tuple(bic for bic in head_bics if head and head.status == "ACTIVE" and country_of(bic) == head.country)

    if home:
        return result(target, leis.head, home, head.country, "parent", f"{head.name} ({head.country})")

    return Result(target, "", leis.head or leis.own, "none", "none", (), "")


def resolve_all(targets: list, by_lei: dict, mfi: dict) -> list:
    found = searched_leis(targets, mfi)
    leis = [(target, target_leis(target, mfi, found)) for target in targets]
    heads = gleif.records([pair.head for _, pair in leis if pair.head])
    return [select(target, pair, by_lei, heads) for target, pair in leis]


def write_csv(path: Path, results: list, source_date: str) -> None:
    rows = [[r.target.code, r.bic, r.lei, source_date, r.match, r.origin] for r in sorted(results, key=lambda r: r.target.code)]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    print(f"{path}: {len(rows)} filas")


def summary(results: list) -> str:
    counts = {origin: sum(1 for r in results if r.origin == origin) for origin in ("own", "parent", "none")}
    ambiguous = sum(1 for r in results if r.match == "multiple" and not r.bic)
    return f"{len(results)} filas: {counts['own']} con BIC propio, {counts['parent']} con BIC de la matriz, {counts['none']} sin BIC ({ambiguous} ambiguos)"


def report_current(results: list, by_bic: dict) -> None:
    print("Discrepancias con los BIC de bancos_es.csv:")

    for r in results:
        if r.bic == r.target.current_bic:
            continue

        known = by_bic.get(r.target.current_bic)
        where = f"en GLEIF con LEI {', '.join(known)}" if known else "no está en GLEIF"
        current = r.target.current_bic or "(vacío)"
        print(f"  {r.target.code} {r.target.name!r}: actual {current} ({where}); GLEIF {r.bic or '-'} [{r.match}, {r.origin}, LEI {r.lei or '-'}]")


def report_new(results: list) -> None:
    print("Entidades nuevas:")

    for r in results:
        flag = " (no acaba en XXX)" if r.origin == "parent" and not r.bic.endswith("XXX") else ""
        holder = f", matriz {r.holder}" if r.holder else ""
        print(f"  {r.target.code} {r.target.name[:60]!r}: {r.bic or '-'} [{r.origin}, {r.match}{holder}]{flag}")


def missing_reason(r: Result, by_lei: dict) -> str:
    if not r.lei:
        return "sin LEI en el registro del BdE, en el BCE ni en LEI_SEARCHES"

    if r.match == "multiple":
        return f"varios BIC posibles para el LEI {r.lei}: {', '.join(r.candidates)}"

    parent = gleif.related(r.lei, "direct-parent")

    if parent is None:
        return f"el LEI {r.lei} no tiene BIC en GLEIF ni matriz declarada"

    parent_bic, _ = choose(by_lei.get(parent.lei, ()), parent.country) if by_lei.get(parent.lei) else ("", "")
    return f"el LEI {r.lei} no tiene BIC; su matriz es {parent.name} ({parent.country}, {parent.lei}), con BIC {parent_bic or '-'}, otra entidad jurídica"


def report_missing(results: list, by_lei: dict) -> None:
    print("Sin BIC:")

    for r in results:
        if not r.bic:
            print(f"  {r.target.code} {r.target.name[:60]!r}: {missing_reason(r, by_lei)}")


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
    print(f"Fichero BIC-LEI de GLEIF del {source_date}: {len(by_bic)} BIC; API de GLEIF del {gleif.publish_date()}")

    results = resolve_all(current_targets(banks, index) + new_targets(entries, banks), by_lei, mfi)
    current = [r for r in results if not r.target.is_new]
    new = [r for r in results if r.target.is_new]
    write_csv(args.out, results, source_date)
    print(f"Actuales: {summary(current)}")
    print(f"Nuevas: {summary(new)}")
    report_current(current, by_bic)
    report_new(new)
    report_missing(new, by_lei)


if __name__ == "__main__":
    main()
