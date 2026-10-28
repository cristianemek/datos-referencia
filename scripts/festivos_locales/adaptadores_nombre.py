import datetime
import re
from collections import defaultdict

from comun import AFFIXES, ARTICLES, MONTHS, FormatChanged, Holiday, clean_name, display_name, fold, movable_date, tidy
from descargas import ckan_resource, datos_gob_items, decode, distribution_urls, fetch, read_table, read_xlsx, table_records
from referencia import Context

ANDALUCIA_URL = "https://datos.juntadeandalucia.es/api/v0/work-calendar/all?format=csv"
ASTURIAS_URL = "https://descargas.asturias.es/asturias/opendata/CulturayOcio/calendario/dataset_calendario_festivos.csv"
BALEARES_PACKAGE = "https://intranet.caib.es/opendatacataleg/api/3/action/package_show?id=calendari-laboral-general-i-local-illes-balears-{year}"
NAVARRA_PACKAGE = "https://datosabiertos.navarra.es/api/3/action/package_show?id=calendario-de-dias-festivos-de-la-comunidad-foral-de-navarra"
NAVARRA_COMMON = (12, 3, "San Francisco Javier, Día de Navarra")
EXTREMADURA_DATASET = "a11002926-festivos-locales-en-extremadura"


def andalucia(context: Context) -> list[Holiday] | None:
    records = read_table(decode(fetch(ANDALUCIA_URL)), ANDALUCIA_URL, ["date", "municipality", "province", "type", "year"])
    local = [record for record in records if record["year"] == str(context.year) and record["type"] == "LOCAL"]

    if not local:
        return None

    rows, places = [], {}

    for record in local:
        key = (record["province"], record["municipality"])

        if key not in places:
            province = context.reference.province(record["province"])

            if province is None:
                raise FormatChanged(f"{ANDALUCIA_URL}: provincia desconocida «{record['province']}»")

            places[key] = context.match_place([province], record["municipality"], affixes=AFFIXES)

        day = context.date(record["date"], ANDALUCIA_URL, record["municipality"])

        if places[key] and day:
            rows.append(context.holiday(day, places[key][0], places[key][1], ""))

    return rows


def asturias(context: Context) -> list[Holiday] | None:
    records = read_table(decode(fetch(ASTURIAS_URL)), ASTURIAS_URL, ["AMBITO", "COMUNIDAD - MUNICIPIO", "FECHA", "FIESTA - LOCALIDAD"])
    grouped = defaultdict(dict)

    for record in records:
        if record["AMBITO"] != "LOCAL" or not record["FECHA"].endswith(str(context.year)):
            continue

        day = context.date(record["FECHA"], ASTURIAS_URL, record["COMUNIDAD - MUNICIPIO"])

        if day is None:
            continue

        grouped[" ".join(record["COMUNIDAD - MUNICIPIO"].split())].setdefault(day, record["FIESTA - LOCALIDAD"].strip())

    if not grouped:
        return None

    rows = []

    for label, items in grouped.items():
        code = context.match_municipality(["33"], label, affixes=AFFIXES)

        if code is None:
            continue

        scoped = asturias_scopes(items) if len(items) > 2 else {"": list(items.items())}

        if scoped is None:
            context.note(f"{label}: más de dos fiestas sin ámbito reconocible: {items}")
            continue

        for locality, entries in scoped.items():
            rows.extend(
                context.holiday(day, code, locality, asturias_name(text) if len(items) > 2 else clean_name(text))
                for day, text in entries
            )

    return rows


def asturias_name(text: str) -> str:
    head = re.split(r"\s*\(excepto|,?\s*(?:solamente\s+)?\ben\s+|,\s*excepto\b", text, maxsplit=1, flags=re.I)[0]
    extra = re.search(r"\(([^)]*)\)\s*$", text)

    if head.strip(" ,-"):
        return clean_name(head.strip(" ,-"))

    return clean_name(extra.group(1)) if extra and not fold(extra.group(1)).startswith("excepto") else ""


def asturias_scopes(items: dict[datetime.date, str]) -> dict[str, list] | None:
    general, everywhere, specific = [], [], defaultdict(list)

    for day, text in items.items():
        folded = fold(text)
        place = re.findall(r"\ben\s+(?:la\s+parroquia\s+(?:rural\s+)?de\s+|el\s+valle\s+de\s+)?([^,(]+?)\s*(?:\(.*\))?\s*$", text, re.I)

        if "excepto" in folded or re.search(r"\by (?:resto del )?concejo\b", folded):
            general.append((day, text))
        elif re.search(r"\b(?:todo|toda) el (?:municipio|concejo)\b", folded):
            everywhere.append((day, text))
        elif place:
            locality = re.sub(r"\s+y\s+(?:parroquia|concejo)$", "", place[-1].strip(), flags=re.I)
            specific[display_name(tidy(locality))].append((day, text))
        else:
            general.append((day, text))

    scoped = {"": general + everywhere, **{place: entries + everywhere for place, entries in specific.items()}}

    if any(len(entries) > 2 or not entries for entries in scoped.values()):
        return None

    return scoped


def baleares(context: Context) -> list[Holiday] | None:
    url = ckan_resource(BALEARES_PACKAGE.format(year=context.year), context.year, ("csv", "xlsx"))

    if url is None:
        return None

    required = ["Àmbit", "Municipi", "Localitat", "Data", "Nom festa"]
    data = fetch(url)
    records = table_records(read_xlsx(data, url), url, required) if url.lower().endswith(".xlsx") else read_table(decode(data), url, required)
    grouped = defaultdict(lambda: defaultdict(list))
    previous = {}

    for record in records:
        if fold(record["Àmbit"]) != "local":
            continue

        municipality = " ".join(record["Municipi"].split())
        locality = " ".join(record["Localitat"].split()) or previous.get(municipality, municipality)
        previous[municipality] = locality
        day = context.date(record["Data"], url, locality)

        if day:
            grouped[municipality][locality].append((day, clean_name(record["Nom festa"])))

    rows = []

    for municipality, localities in grouped.items():
        code = context.match_municipality(["07"], municipality, affixes=AFFIXES)

        if code is None:
            continue

        main = next(iter(localities))

        for locality, items in localities.items():
            label = "" if locality == main else display_name(locality)
            rows.extend(context.holiday(day, code, label, name) for day, name in items)

    return rows


def navarra(context: Context) -> list[Holiday] | None:
    url = ckan_resource(NAVARRA_PACKAGE, context.year, ("csv",))

    if url is None:
        return None

    records = read_table(decode(fetch(url)), url, ["LOCALIDAD", "DIA", "MES", "NOTAS"])
    qualified = {fold(match.group(1)) for record in records for match in [re.match(r"^(.*?)\s*\(([^()]+)\)$", record["LOCALIDAD"].strip())] if match}
    rows = []

    for record in records:
        day = navarra_date(record, context.year)
        label = " ".join(record["LOCALIDAD"].split())

        if day is None:
            context.note(f"fecha no reconocida: {label} {record['DIA']} {record['MES']} «{record['NOTAS']}»")
            continue

        if fold(label) in qualified and context.reference.municipality(["31"], label)[0] is None:
            context.matches["sin cruzar"] += 1
            context.note(f"sin cruzar: «{label}» es ambiguo porque otra localidad del mismo nombre lleva el municipio entre paréntesis")
            continue

        place = navarra_place(context, label)

        if place:
            rows.append(context.holiday(day, place[0], place[1], ""))

    month, day, name = NAVARRA_COMMON
    common = datetime.date(context.year, month, day)

    if common.weekday() == 6:
        context.note(f"el {common.isoformat()} es domingo: no se añade {name}")
        return rows

    localities = defaultdict(lambda: {""})

    for row in rows:
        localities[row.municipality_code].add(row.locality)

    return rows + [
        context.holiday(common, code, locality, name)
        for code in context.reference.by_province["31"] for locality in localities[code]
    ]


def navarra_date(record: dict[str, str], year: int) -> datetime.date | None:
    month = MONTHS.get(fold(record["MES"]))

    try:
        if record["DIA"].isdigit() and month:
            return datetime.date(year, month, int(record["DIA"]))

        return movable_date(record["NOTAS"], year)
    except ValueError:
        return None


def navarra_place(context: Context, label: str) -> tuple[str, str] | None:
    match = re.match(r"^(.*?)\s*\(([^()]+)\)$", label)

    if match and fold(match.group(2)) not in ARTICLES:
        parent, _ = context.reference.municipality(["31"], match.group(2), ("prefijo", "sufijo", "variante ortográfica"))

        if parent:
            return context.match_place(["31"], match.group(1), parent)

    return context.match_place(["31"], label, affixes=("localidad del municipio",))


def extremadura(context: Context) -> list[Holiday] | None:
    items = datos_gob_items(EXTREMADURA_DATASET)
    urls = [url for entry in items for url in distribution_urls(entry) if url.lower().endswith(".xlsx") and str(context.year) in url]

    if not urls:
        return None

    url = urls[0]
    records = table_records(read_xlsx(fetch(url), url), url, ["LOCALIDAD", "FECHA"])
    rows, places = [], {}

    for record in records:
        label = " ".join(record["LOCALIDAD"].split())

        if label not in places:
            places[label] = context.match_place(["06", "10"], label, affixes=AFFIXES)

        day = context.date(record["FECHA"], url, label)

        if places[label] and day:
            rows.append(context.holiday(day, places[label][0], places[label][1], ""))

    return rows
