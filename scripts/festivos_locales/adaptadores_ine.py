import re
import urllib.parse
from collections import Counter, defaultdict

from comun import FormatChanged, Holiday, clean_name, display_name, fold, tidy
from descargas import DATOS_GOB_TITLE, datos_gob_items, decode, distribution_urls, fetch, fetch_json, read_table
from referencia import Context

EUSKADI_URL = "https://opendata.euskadi.eus/contenidos/ds_eventos/calendario_laboral_{year}/opendata/calendario_laboral_{year}.csv"
EUSKADI_TERRITORIES = {"bizkaia": "48", "gipuzkoa": "20", "alava araba": "01", "araba": "01", "alava": "01"}
CATALUNYA_URL = "https://analisi.transparenciacatalunya.cat/resource/b4eh-r8up.csv?any_calendari={year}"
GALICIA_PUBLISHER = "a12002994"
MADRID_URLS = [
    "https://datos.comunidad.madrid/dataset/f160eb6c-6715-471e-9bc0-38497aae950f/resource/ba59e7e8-3d8d-4221-a5fa-b5e78b82707f/download/festivos_locales.csv",
    "https://datos.comunidad.madrid/dataset/02c712b5-5009-4ffb-b388-3cfb4fca207d/resource/22d7957e-8b3a-4f00-9549-bf501f4ea741/download/festivos_locales_historicos.csv",
]
MURCIA_URL = "https://datosabiertos.carm.es/odata/transparencia/INSPE_Dias_Inhabiles_{year}.csv"


def euskadi(context: Context) -> list[Holiday] | None:
    url = EUSKADI_URL.format(year=context.year)
    data = fetch(url, missing_ok=True)

    if data is None:
        return None

    records = read_table(decode(data), url, ["date", "descripcionEs", "municipalityEs", "territory", "municipalitycode"])
    territorial, labelled = defaultdict(list), defaultdict(lambda: defaultdict(list))

    for record in records:
        territory = fold(record["territory"])

        if not record["date"] or territory in ("todos denak", "todos", "denak"):
            continue

        province = EUSKADI_TERRITORIES.get(territory)

        if province is None:
            raise FormatChanged(f"{url}: territorio desconocido «{record['territory']}»")

        label = " ".join(record["municipalityEs"].split())
        day = context.date(record["date"], url, label)

        if day is None:
            continue

        if re.fullmatch(r"\d{1,3}(?:\.0+)?", record["municipalitycode"]):
            code = province + f"{int(float(record['municipalitycode'])):03d}"
        elif record["municipalitycode"]:
            raise FormatChanged(f"{url}: código de municipio no reconocido «{record['municipalitycode']}»")
        elif EUSKADI_TERRITORIES.get(fold(label)) == province:
            territorial[province].append((day, clean_name(record["descripcionEs"])))
            continue
        else:
            code = context.match_municipality([province], label)

            if code is None:
                continue

        labelled[code][label].append((day, clean_name(record["descripcionEs"])))

    if not labelled:
        raise FormatChanged(f"{url}: no hay fiestas con código de municipio")

    rows = []

    for code, groups in labelled.items():
        for label, items in groups.items():
            locality = "" if len(groups) == 1 else re.split(r"\s+-\s*|\s*-\s+", label)[-1].strip()
            rows.extend(context.holiday(day, code, locality, name) for day, name in items)

    localities = defaultdict(lambda: {""})

    for row in rows:
        localities[row.municipality_code].add(row.locality)

    for province, items in territorial.items():
        for code in context.reference.by_province[province]:
            for locality in localities[code]:
                rows.extend(context.holiday(day, code, locality, name) for day, name in items)

    return rows


def cataluna(context: Context) -> list[Holiday] | None:
    url = CATALUNYA_URL.format(year=context.year)
    records = read_table(decode(fetch(url + "&$limit=200000")), url,
                         ["any_calendari", "data", "ajuntament_o_nucli_municipal", "codi_municipi_ine", "pedania", "festiu"])

    if not records:
        return None

    rows, junk = [], Counter()

    for record in records:
        place = record["ajuntament_o_nucli_municipal"]

        if fold(record["festiu"]) != "festiu local" or fold(place).startswith(("c a de catalunya", "null")):
            junk[record["festiu"]] += 1
            continue

        locality = "" if record["pedania"] in ("", "000") else display_name(place)
        day = context.date(record["data"], url, place)

        if day:
            rows.append(context.holiday(day, record["codi_municipi_ine"].zfill(5), locality, ""))

    if junk:
        context.note(f"filas descartadas por no ser festivos locales válidos: {dict(junk)}")

    return rows


def galicia(context: Context) -> list[Holiday] | None:
    url = galicia_resource(context.year)

    if url is None:
        return None

    records = read_table(decode(fetch(url)), url, ["fecha", "descripcion", "ambito"])
    unknown = {record["ambito"] for record in records} - {"estatal", "autonómico", "municipal"}

    if unknown:
        raise FormatChanged(f"{url}: ámbitos desconocidos {sorted(unknown)}")

    local = [record for record in records if record["ambito"] == "municipal"]

    if not local:
        return None

    if "id_municipio" not in local[0]:
        raise FormatChanged(f"{url}: falta la columna id_municipio")

    return [
        context.holiday(day, record["id_municipio"].zfill(5), "", clean_name(record["descripcion"]))
        for record in local for day in [context.date(record["fecha"], url, record.get("lugar", ""))] if day
    ]


def galicia_resource(year: int) -> str | None:
    items = datos_gob_items(f"{GALICIA_PUBLISHER}-calendario-laboral-{year}")

    if not items:
        search = fetch_json(DATOS_GOB_TITLE.format(title=urllib.parse.quote(f"calendario laboral {year}"))) or {}
        items = [item for item in search.get("result", {}).get("items", []) if f"/{GALICIA_PUBLISHER}-" in item.get("_about", "")]

    for item in items:
        for url in distribution_urls(item):
            if "abertos.xunta.gal" in url and url.endswith(".csv") and str(year) in url:
                return url

    return None


def madrid(context: Context) -> list[Holiday] | None:
    for url in MADRID_URLS:
        records = read_table(decode(fetch(url)), url, ["año", "municipio_codigo", "entidad_codigo", "entidad_nombre", "fecha_festivo"])
        selected = [record for record in records if record["año"] == str(context.year)]

        if selected:
            return [
                context.holiday(
                    day, "28" + record["municipio_codigo"].zfill(3),
                    "" if int(record["entidad_codigo"] or 0) == 0 else display_name(tidy(record["entidad_nombre"])), "",
                )
                for record in selected for day in [context.date(record["fecha_festivo"], url, record["entidad_nombre"])] if day
            ]

    return None


def murcia(context: Context) -> list[Holiday] | None:
    url = MURCIA_URL.format(year=context.year)
    data = fetch(url, missing_ok=True)

    if data is None:
        return None

    records = read_table(decode(data), url, ["FECHA", "COD_MUNICIPIO", "AMBITO"])

    return [
        context.holiday(day, record["COD_MUNICIPIO"].zfill(5), "", "")
        for record in records if record["COD_MUNICIPIO"] and record["COD_MUNICIPIO"] != "30000"
        for day in [context.date(record["FECHA"], url, record["AMBITO"])] if day
    ]
