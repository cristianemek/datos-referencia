import re
from collections import Counter, defaultdict

from comun import AFFIXES, ARTICLES, FormatChanged, Holiday, clean_name, display_name, fold, numeric_date
from descargas import decode, fetch, fetch_json, read_table
from referencia import Context, assign_localities, merge_labels

CYL_URL = "https://datosabiertos.jcyl.es/web/jcyl/risp/es/empleo/fiestas-locales/1284952783683-{index}.csv"
ARAGON_PACKAGE = "https://opendata.aragon.es/ckan/api/3/action/package_show?id=calendario-de-festivos-en-comunidad-de-aragon-{year}"


def castilla_leon(context: Context) -> list[Holiday] | None:
    for index in range(1, 40):
        url = CYL_URL.format(index=index)
        data = fetch(url, missing_ok=True)

        if not data:
            return None

        records = read_table(decode(data), url, ["Municipio", "Fecha fiesta", "Nombre fiesta", "INE"])
        years = Counter(match.group(1) for record in records for match in [re.search(r"(\d{4})$", record["Fecha fiesta"])] if match)

        if years and years.most_common(1)[0][0] == str(context.year):
            return castilla_leon_rows(context, records)

    return None


def castilla_leon_rows(context: Context, records: list[dict[str, str]]) -> list[Holiday]:
    labelled = defaultdict(lambda: defaultdict(list))

    for record in records:
        if "no comunicada" in fold(record["Fecha fiesta"] + " " + record["Nombre fiesta"]):
            continue

        try:
            day = numeric_date(record["Fecha fiesta"])
        except ValueError:
            day = None

        if day is None:
            context.note(f"fecha no reconocida: {record['Municipio']} «{record['Fecha fiesta']}» {record['Nombre fiesta']}")
            continue

        if day.year != context.year:
            context.note(f"fecha de otro año: {record['Municipio']} {day.isoformat()}")
            continue

        label = " ".join(record["Municipio"].split())
        code = castilla_leon_code(context, record, label)

        if code:
            labelled[code][label].append((day, clean_name(record["Nombre fiesta"])))

    rows = []

    for code, groups in labelled.items():
        merged = merge_labels(groups)
        localities = assign_localities(merged, context.reference.forms.get(code, set()))

        for label, items in merged.items():
            rows.extend(context.holiday(day, code, localities[label], name) for day, name in items)

    return rows


def castilla_leon_code(context: Context, record: dict[str, str], label: str) -> str | None:
    code = str(int(float(record["INE"]))).zfill(5) if re.fullmatch(r"\d+(?:\.0+)?", record["INE"]) else ""
    province = context.reference.province(record.get("Provincia", ""))

    if code in context.reference.municipalities and (province is None or code[:2] == province):
        return code

    fixed, _ = context.reference.municipality([province], re.split(r"\s+-\s+", label)[0]) if province else (None, "")

    if fixed:
        context.note(f"código INE «{record['INE']}» corregido por nombre: «{label}» → {fixed}")
    else:
        context.note(f"código INE «{record['INE']}» inexistente y sin cruce por nombre: «{label}»")

    return fixed


def aragon(context: Context) -> list[Holiday] | None:
    package = fetch_json(ARAGON_PACKAGE.format(year=context.year), missing_ok=True)

    if not package or not package.get("success"):
        return None

    for resource in package["result"].get("resources", []):
        url = resource.get("url", "")

        if not url.lower().endswith(".csv"):
            continue

        text = decode(fetch(url))

        if "CodigoINE" in text.split("\n", 1)[0]:
            return aragon_rows(context, read_table(text, url, ["Provincia", "CodigoINE", "Municipio", "Fecha", "NombreFestivo"]), url)

    context.note("el conjunto del año no tiene un CSV con código INE")

    return None


def aragon_rows(context: Context, records: list[dict[str, str]], url: str) -> list[Holiday]:
    coded, rows, places = defaultdict(lambda: defaultdict(list)), [], {}

    for record in records:
        label = " ".join(record["Municipio"].split())
        day = context.date(record["Fecha"], url, label)
        name = clean_name(record["NombreFestivo"])

        if day is None:
            continue

        if record["CodigoINE"]:
            coded[record["CodigoINE"].zfill(5)][label].append((day, name))
            continue

        if (record["Provincia"], label) not in places:
            province = context.reference.province(record["Provincia"])

            if province is None:
                raise FormatChanged(f"{url}: provincia desconocida «{record['Provincia']}»")

            places[(record["Provincia"], label)] = aragon_place(context, province, label)

        place = places[(record["Provincia"], label)]

        if place:
            rows.append(context.holiday(day, place[0], place[1], name))

    for code, groups in coded.items():
        localities = assign_localities(groups, context.reference.forms.get(code, set()))

        for label, items in groups.items():
            rows.extend(context.holiday(day, code, localities[label], name) for day, name in items)

    return rows


def aragon_place(context: Context, province: str, label: str) -> tuple[str, str] | None:
    match = re.match(r"^(.*?)\s*\(([^()]+)\)$", label)

    if match and fold(match.group(2)) not in ARTICLES:
        parent, _ = context.reference.municipality([province], match.group(2), AFFIXES)

        if parent:
            return context.match_place([province], match.group(1), parent)

    for separator in re.finditer(r"\s*[–-]\s*", label):
        parent, _ = context.reference.municipality([province], label[:separator.start()])

        if parent and label[separator.end():]:
            context.matches["municipio indicado"] += 1
            return parent, display_name(label[separator.end():])

    return context.match_place([province], label, affixes=AFFIXES)
