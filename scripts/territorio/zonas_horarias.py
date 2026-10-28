import re
import tarfile
import xml.etree.ElementTree as ET
import zoneinfo
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from comun import BUILD, REPO, fail_if, fetch, read_csv, write_csv

TZDATA_URL = "https://data.iana.org/time-zones/tzdata-latest.tar.gz"
BOE_XML = "https://www.boe.es/diario_boe/xml.php?id={}"
COMMUNICATION_2027_URL = "https://publications.europa.eu/resource/oj/C_202601660.SPA.xhtml.C_202601660ES.html"
FIRST_YEAR, LAST_YEAR = 1996, 2031

MADRID, CANARY, CEUTA = "Europe/Madrid", "Atlantic/Canary", "Africa/Ceuta"
ES_ZONES = {MADRID: "Spain (mainland)", CEUTA: "Ceuta, Melilla", CANARY: "Canary Islands"}
CCAA_ZONES = {"05": CANARY, "18": CEUTA, "19": CEUTA}

RD_236_2002 = "RD 236/2002 (BOE-A-2002-4221)"
CALENDARS = [
    (1996, 1997, "Directiva 94/21/CE (DOCE L 164 de 30.6.1994), arts. 2 y 3", None),
    (1998, 2001, "Directiva 97/44/CE (DOCE L 206 de 1.8.1997), arts. 2 y 3", None),
    (2002, 2006, f"{RD_236_2002}, anexo", "BOE-A-2002-4221"),
    (2007, 2011, "Orden PRE/2211/2006 (BOE-A-2006-12441)", "BOE-A-2006-12441"),
    (2012, 2016, "Orden PRE/2767/2011 (BOE-A-2011-16280)", "BOE-A-2011-16280"),
    (2017, 2021, "Orden PRA/157/2017 (BOE-A-2017-2065)", "BOE-A-2017-2065"),
    (2022, 2026, "Orden PCM/186/2022 (BOE-A-2022-4026)", "BOE-A-2022-4026"),
    (2027, 2031, f"{RD_236_2002}, arts. 2 y 3; Comunicación de la Comisión C/2026/1660 (DOUE C de 18.3.2026)", "C/2026/1660"),
]
DIRECTIVE_DATES = {
    1996: ("03-31", "10-27"), 1997: ("03-30", "10-26"),
    1998: ("03-29", "10-25"), 1999: ("03-28", "10-31"), 2000: ("03-26", "10-29"), 2001: ("03-25", "10-28"),
}
MONTHS = {"marzo": 3, "octubre": 10}
HEADER = [
    "year", "starts_utc", "ends_utc", "starts_local_peninsula", "ends_local_peninsula",
    "starts_local_canarias", "ends_local_canarias", "regulation",
]


def tzdata() -> tuple[str, list[str]]:
    with tarfile.open(fetch(TZDATA_URL, "tzdata-latest.tar.gz")) as archive:
        version = archive.extractfile("version").read().decode().strip()
        table = archive.extractfile("zone1970.tab").read().decode("utf-8").splitlines()
    return version, table


def check_zone_table(version: str, table: list[str]) -> None:
    spain = {}
    for line in table:
        if line.startswith("#") or not line.strip():
            continue
        fields = line.split("\t")
        if "ES" in fields[0].split(","):
            spain[fields[2]] = fields[3] if len(fields) > 3 else ""
    fail_if([] if spain == ES_ZONES else [f"{spain}"], f"Zonas de España inesperadas en zone1970.tab {version}")
    system = system_tzdata_version()
    if system != version:
        print(f"Aviso: tzdata del sistema {system}, IANA {version}; los cambios de hora se contrastan con las fechas oficiales")


def system_tzdata_version() -> str:
    for base in zoneinfo.TZPATH:
        candidate = Path(base) / "tzdata.zi"
        if candidate.exists():
            first = candidate.read_text(encoding="utf-8").splitlines()[0]
            return first.replace("# version", "").strip()
    return "desconocida"


def timezone_tables() -> None:
    comunidades = read_csv(REPO / "direcciones" / "comunidades_es.csv")
    provincias = read_csv(REPO / "direcciones" / "provincias_es.csv")
    ccaa_rows = [{"ccaa_code": c["ccaa_code"], "timezone": CCAA_ZONES.get(c["ccaa_code"], MADRID)} for c in comunidades]
    by_ccaa = {r["ccaa_code"]: r["timezone"] for r in ccaa_rows}
    province_rows = [{"province_code": p["province_code"], "timezone": by_ccaa[p["ccaa_code"]]} for p in provincias]
    expected = {"35": CANARY, "38": CANARY, "51": CEUTA, "52": CEUTA}
    fail_if([p["province_code"] for p in province_rows if p["timezone"] != expected.get(p["province_code"], MADRID)],
            "Provincias con zona horaria inesperada")
    write_csv(BUILD / "comunidades_timezone.csv", ["ccaa_code", "timezone"], ccaa_rows)
    write_csv(BUILD / "provincias_timezone.csv", ["province_code", "timezone"], province_rows)


def transitions(zone: str, year: int) -> list[tuple[datetime, timedelta, timedelta]]:
    tz = zoneinfo.ZoneInfo(zone)
    moment = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    previous = moment.astimezone(tz).utcoffset()
    found = []
    while moment < end:
        moment += timedelta(hours=1)
        current = moment.astimezone(tz).utcoffset()
        if current != previous:
            before = (moment - timedelta(seconds=1)).astimezone(tz).utcoffset()
            fail_if([] if before == previous else [f"{zone} {moment}"], "Transición fuera de hora en punto")
            found.append((moment, previous, current))
            previous = current
    fail_if([] if len(found) == 2 else [f"{zone} {year}: {len(found)}"], "Número de cambios de hora inesperado")
    return found


def iso_offset(offset: timedelta) -> str:
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    return f"{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"


def local(moment: datetime, offset: timedelta) -> str:
    return f"{(moment + offset).replace(tzinfo=None).isoformat(timespec='seconds')}{iso_offset(offset)}"


def utc(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def plain_text(xml: bytes) -> str:
    root = ET.fromstring(xml)
    body = root.find("texto")
    return re.sub(r"\s+", " ", " ".join((body if body is not None else root).itertext()))


def official_dates() -> dict:
    dates = {y: (date.fromisoformat(f"{y}-{s}"), date.fromisoformat(f"{y}-{e}")) for y, (s, e) in DIRECTIVE_DATES.items()}
    for first, last, _, source in CALENDARS:
        if source is None:
            continue
        if source.startswith("BOE-"):
            text = plain_text(fetch(BOE_XML.format(source), f"{source}.xml").read_bytes())
        else:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fetch(COMMUNICATION_2027_URL, "C_202601660ES.html").read_text(encoding="utf-8")))
        found = {}
        for year, day, month in re.findall(r"(\d{4}): [Dd]omingo, (\d{1,2}) de (marzo|octubre)", text):
            found.setdefault(int(year), {})[MONTHS[month]] = int(day)
        for year, march, october in re.findall(r"(?:en )?(\d{4}): (?:los )?[Dd]omingos (\d{1,2}) de marzo y (\d{1,2}) de octubre", text):
            found.setdefault(int(year), {}).update({3: int(march), 10: int(october)})
        years = list(range(first, last + 1))
        fail_if([str(y) for y in years if set(found.get(y, {})) != {3, 10}], f"Fechas no encontradas en {source}")
        dates.update({y: (date(y, 3, found[y][3]), date(y, 10, found[y][10])) for y in years})
    return dates


def regulation(year: int) -> str:
    return next(label for first, last, label, _ in CALENDARS if first <= year <= last)


def changes() -> list[dict]:
    official = official_dates()
    rows, problems = [], []
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        (start, p_std, p_dst), (end, _, _) = transitions(MADRID, year)
        (c_start, c_std, c_dst), (c_end, _, _) = transitions(CANARY, year)
        ceuta = [t[0] for t in transitions(CEUTA, year)]
        if [start, end] != [c_start, c_end] or ceuta != [start, end]:
            problems.append(f"{year}: instantes distintos entre zonas")
        if (start.date(), end.date()) != official[year] or start.hour != 1 or end.hour != 1:
            problems.append(f"{year}: tzdata {start.date()} {end.date()} / oficial {official[year]}")
        row = {
            "year": str(year), "starts_utc": utc(start), "ends_utc": utc(end),
            "starts_local_peninsula": local(start, p_std), "ends_local_peninsula": local(end, p_dst),
            "starts_local_canarias": local(c_start, c_std), "ends_local_canarias": local(c_end, c_dst),
            "regulation": regulation(year),
        }
        hours = [row[k][11:13] for k in HEADER[3:7]]
        if hours != ["02", "03", "01", "02"]:
            problems.append(f"{year}: horas locales {hours}")
        rows.append(row)
    fail_if(problems, "Discrepancias entre tzdata y el calendario oficial")
    return rows


def main() -> None:
    version, table = tzdata()
    check_zone_table(version, table)
    timezone_tables()
    write_csv(REPO / "calendario" / "cambios_hora_es.csv", HEADER, changes())
    print(f"tzdata {version}")


if __name__ == "__main__":
    main()
