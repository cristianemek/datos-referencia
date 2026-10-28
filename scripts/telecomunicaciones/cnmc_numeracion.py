import argparse
import collections
import csv
import datetime
import html
import io
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BD_NUM_URL = "https://numeracionyoperadores.cnmc.es/bd-num.zip"
ROSCE_URL = "https://numeracionyoperadores.cnmc.es/rosce.zip"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
DOWNLOAD_ATTEMPTS = 4
DOWNLOAD_TIMEOUT = 120
MAX_DROP = 0.10
PROVINCES_FILE = Path("direcciones") / "provincias_es.csv"
CATALOG_FILE = Path("catalogos") / "numeracion_telefonica_es.csv"
OUTPUT_DIR = Path("telecomunicaciones")
NUMBERING_OUTPUT = "numeracion_asignada_es.csv"
OPERATORS_OUTPUT = "operadores_telecom_es.csv"
MNC_OUTPUT = "mnc_es.csv"

NUMBERING_HEADER = [
    "prefix", "range_start", "range_end", "size", "type", "service", "province_code",
    "status", "operator_name", "operator_nif", "assigned_on", "released_on",
]
OPERATORS_HEADER = ["nif", "name", "activities", "scope", "registered_on"]
MNC_HEADER = ["mcc", "mnc", "status", "operator_name", "operator_nif", "assigned_on"]

ROSCE_MEMBER = "rosce.csv"
ROSCE_HEADER = [
    "Nombre", "Nif", "Domicilio social", "Domicilio de notificación",
    "Fecha de notificación inicial", "Actividad", "Ámbito", "Fecha resolución",
]
HTML_ENTITY = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")

STATUSES = {"Asignado": "assigned", "Subasignado": "subassigned", "Compartido": "shared", "Libre con Portados": "free_with_ported"}
STATUS_ORDER = list(STATUSES.values())
STATUS_PATTERN = re.compile(r"(Asignado|Subasignado|Compartido|Libre con Portados)(?: ([0-9](?:\s*,\s*[0-9])*))?")
FREE = "free_with_ported"

GEOGRAPHIC_FIELDS = ("ndc", "block", "province", "status", "operator", "date")
BLOCK_FIELDS = ("ndc", "block", "operator", "date", "status")
SHORT_FIELDS = ("number", "operator", "service", "date", "status")
SOURCES = {
    "geograficos.txt": {"fields": GEOGRAPHIC_FIELDS, "types": {"geographic"}, "length": 9},
    "svn_geo.txt": {"fields": GEOGRAPHIC_FIELDS, "types": {"geographic"}, "length": 9, "service": "Nómada geográfica", "optional": True},
    "moviles.txt": {"fields": ("ndc", "block", "unused", "status", "operator", "date"), "types": {"mobile"}, "length": 9},
    "personal.txt": {"fields": BLOCK_FIELDS, "types": {"personal"}, "length": 9},
    "tarifasespeciales.txt": {
        "fields": BLOCK_FIELDS, "length": 9,
        "types": {"freephone", "premium_rate", "shared_cost", "caller_pays", "mass_calling"},
    },
    "ai.txt": {"fields": BLOCK_FIELDS, "types": {"internet_access"}, "length": 9},
    "svn_nogeo.txt": {"fields": BLOCK_FIELDS, "types": {"nomadic"}, "length": 9},
    "llamadas_comerciales.txt": {"fields": ("ndc", "block", "status", "operator", "date"), "types": {"commercial_calls"}, "length": 9},
    "m2m.txt": {"fields": ("ndc", "block", "operator", "description", "date", "status"), "types": {"m2m"}, "length": 13},
    "cortos.txt": {"fields": SHORT_FIELDS, "types": None, "length": None},
    "sms_mms.txt": {"fields": SHORT_FIELDS, "types": {"sms"}, "length": None},
}
SERVICE_SOURCES = {member for member, spec in SOURCES.items() if "service" in spec["fields"]}
GEOGRAPHIC_TYPES = ("geographic",)
REQUIRED_SOURCES = {member for member, spec in SOURCES.items() if not spec.get("optional")}
MNC_SOURCE = "irm.txt"
MNC_FIELDS = ("mcc", "mnc", "status", "operator", "date")
KNOWN_MEMBERS = set(SOURCES) | {
    MNC_SOURCE, "aut_subasignaciones.txt", "cird.txt", "cpsi.txt", "cpsn.txt", "nrn2.txt", "tetrairm.txt",
}
FIELD_LABELS = {"ndc": "indicativo", "block": "bloque", "number": "número", "mcc": "MCC", "mnc": "MNC"}
DIGITS = {
    "ndc": re.compile(r"\d{2,3}"), "block": re.compile(r"\d{0,6}"), "number": re.compile(r"\d{3,6}"),
    "mcc": re.compile(r"\d{3}"), "mnc": re.compile(r"\d{2,3}"),
}

LEGAL_NIF = re.compile(r"[ABCDFGHNPQRSUVW]\d{7}[0-9A-J]")
NO_PERSONALITY_NIF = re.compile(r"[EJ]\d{7}[0-9A-J]")
PERSON_NIF = re.compile(r"(?:ES)?(?:\d{7,8}|[KLMXYZ]\d{7,8})[A-Z]")
DIGITS_ONLY_NIF = re.compile(r"(?:ES)?[KLMXYZ]?\d{7,8}")
FOREIGN_TAX_ID = re.compile(r"(?!ES)[A-Z]{2,3}\d[0-9A-Z]{6,13}|N\d{7}[A-Z]{1,2}")
LEGAL_FORM = re.compile(
    r"[\s,.](?:S\.?\s?[AL]\.?(?:\s?U\.?)?|S\.?\s?L\.?\s?L|S\.?\s?R\.?\s?L|S\.?\s?P\.?\s?A|S\.?\s?[AÀ]\.?\s?R\.?\s?L|S\.?\s?A\.?\s?C"
    r"|E\.?\s?I\.?\s?R\.?\s?L|LTD|LIMITED|GMBH|B\.?\s?V|N\.?\s?V|INC|LLC|L\.?\s?P|L\.?\s?C|A/S|APS|AB|AG|KG|LDA|PLC|KFT"
    r"|EOOD|UAB|OÜ|PTE|SE|SPRL|SAS|SARL|CORP|CORPORATION|COMPANY|AKTIEBOLAG)\.?(?:\s*\(PUBL\)|\s+UNIPERSONAL)?$",
    re.I,
)
PUBLIC_BODY = re.compile(
    r"\b(?:UNIVERSI|GOBIERNO|GOVERN|MINISTERI|AUTORIDAD|AYUNTAMIENTO|AJUNTAMENT|CONCELLO|DIPUTACI|GENERALITAT|JUNTA|XUNTA"
    r"|CABILDO|CONSELL|CONSEJER|CONSORCI|ENTIDAD|ENTITAT|ORGANISMO|ORGANISME|INSTITUT|AGENCIA|FUNDACI|ASOCIACI|ASSOCIACI"
    r"|COLEGIO|PRINCIPADO|COMUNIDAD AUT|REGI[ÓO]N DE)",
    re.I,
)


class FormatoError(Exception):
    pass


def fetch_zip(url: str, label: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None

    for attempt in range(DOWNLOAD_ATTEMPTS):
        if attempt:
            time.sleep(2 * attempt)

        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
                data = response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500:
                raise RuntimeError(f"La CNMC ha respondido {error.code} al descargar {url}") from None

            last_error = error
            continue
        except (urllib.error.URLError, OSError) as error:
            last_error = error
            continue

        if zipfile.is_zipfile(io.BytesIO(data)):
            return data

        last_error = f"la respuesta no es un ZIP ({len(data)} bytes)"

    raise RuntimeError(f"No se pudo descargar {label} de {url}: {last_error}")


def open_zip(data: bytes, label: str) -> zipfile.ZipFile:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise FormatoError(f"{label} no es un fichero ZIP válido (¿ha cambiado la URL o la CNMC devuelve una página de error?)")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        broken = archive.testzip()
    except (zipfile.BadZipFile, zlib.error, NotImplementedError) as error:
        raise FormatoError(f"{label} está dañado: {error}") from None

    if broken:
        raise FormatoError(f"{label}: el fichero {broken} del ZIP está dañado")

    return archive


def load_archive(path: str | None, url: str, label: str) -> zipfile.ZipFile:
    if path and not Path(path).is_file():
        raise FormatoError(f"No se encuentra {path}")

    return open_zip(Path(path).read_bytes() if path else fetch_zip(url, label), label)


def read_member(archive: zipfile.ZipFile, member: str) -> bytes:
    try:
        return archive.read(member)
    except (KeyError, zipfile.BadZipFile, zlib.error, NotImplementedError) as error:
        raise FormatoError(f"No se puede leer {member} del ZIP: {error}") from None


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)

    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def name_key(name: str) -> str:
    return " ".join(re.findall(r"[0-9a-z]+", plain(name)))


def iso_date(value: str, where: str) -> str:
    try:
        return datetime.datetime.strptime(value, "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise FormatoError(f"{where}: fecha no válida «{value}» (se esperaba dd/mm/aaaa)") from None


def check_iso_date(value: str, where: str) -> str:
    try:
        return datetime.date.fromisoformat(value).isoformat() if value else ""
    except ValueError:
        raise FormatoError(f"{where}: fecha de notificación no válida «{value}» (se esperaba aaaa-mm-dd)") from None


def decode_cp1252(raw: bytes, member: str) -> str:
    if not raw.isascii():
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            raise FormatoError(f"{member} está en UTF-8 y se esperaba latin-1/cp1252: revisa la codificación")

    try:
        return raw.decode("cp1252")
    except UnicodeDecodeError as error:
        raise FormatoError(f"{member} tiene bytes que no son cp1252 (posición {error.start}): la codificación ha cambiado") from None


def member_records(archive: zipfile.ZipFile, member: str, fields: tuple, optional: bool = False) -> list[dict]:
    text = decode_cp1252(read_member(archive, member), member)
    records = []

    for number, line in enumerate(re.split(r"\r?\n", text), start=1):
        if not line.strip():
            continue

        values = line.split("#")

        if len(values) != len(fields):
            raise FormatoError(f"{member}, línea {number}: se esperaban {len(fields)} campos separados por «#» y hay {len(values)}")

        records.append({**dict(zip(fields, map(clean, values))), "_where": f"{member}, línea {number}"})

    if not records and not optional:
        raise FormatoError(f"{member} está vacío")

    return records


def check_digits(record: dict) -> None:
    for field, pattern in DIGITS.items():
        if field in record and not pattern.fullmatch(record[field]):
            raise FormatoError(f"{record['_where']}: el {FIELD_LABELS[field]} debería ser numérico y vale «{record[field]}»")

    if record.get("unused"):
        raise FormatoError(f"{record['_where']}: el tercer campo de moviles.txt ya no está vacío («{record['unused']}»)")


def parse_status(value: str, where: str) -> tuple[str, list[str]]:
    match = STATUS_PATTERN.fullmatch(value)

    if not match:
        raise FormatoError(f"{where}: estado desconocido «{value}»")

    if match.group(2) and match.group(1) != "Subasignado":
        raise FormatoError(f"{where}: el estado «{value}» lleva subbloques y no es una subasignación")

    subblocks = [digit.strip() for digit in match.group(2).split(",")] if match.group(2) else [""]

    return STATUSES[match.group(1)], subblocks


def read_csv(path: Path, required: set) -> list[dict]:
    if not path.is_file():
        raise FormatoError(f"No se encuentra {path}")

    try:
        with path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            columns = set(reader.fieldnames or [])
    except (UnicodeDecodeError, csv.Error) as error:
        raise FormatoError(f"No se puede leer {path}: {error}") from None

    if required - columns:
        raise FormatoError(f"{path}: faltan las columnas {', '.join(sorted(required - columns))}")

    return rows


def province_key(name: str) -> str:
    match = re.fullmatch(r"(.+), (A|O|As|Os|La|Las|Los|El|Els|Les|Illes)", name)

    return plain(f"{match.group(2)} {match.group(1)}" if match else name)


def load_provinces(path: Path) -> tuple[dict, dict]:
    index, prefixes = {}, {}

    for row in read_csv(path, {"province_code", "province", "phone_prefixes"}):
        for name in [row["province"], *row["province"].split("/")]:
            index[province_key(name)] = row["province_code"]

        prefixes[row["province_code"]] = row["phone_prefixes"].split("|")

    return index, prefixes


def load_catalog(path: Path) -> list[tuple[str, str]]:
    rows = read_csv(path, {"prefix", "type"})

    return sorted(((row["prefix"], row["type"]) for row in rows), key=lambda item: -len(item[0]))


def catalog_type(catalog: list, number: str) -> str | None:
    return next((kind for prefix, kind in catalog if number.startswith(prefix)), None)


def normalize_nif(value: str) -> str:
    compact = re.sub(r"[\s.\-]", "", value.upper())
    patterns = (LEGAL_NIF, NO_PERSONALITY_NIF, PERSON_NIF, DIGITS_ONLY_NIF)

    return compact if any(pattern.fullmatch(compact) for pattern in patterns) else clean(value)


def nif_kind(nif: str, name: str) -> str:
    if NO_PERSONALITY_NIF.fullmatch(nif):
        return "no_personality"

    if LEGAL_NIF.fullmatch(nif):
        return "legal"

    if PERSON_NIF.fullmatch(nif):
        return "natural_person"

    if DIGITS_ONLY_NIF.fullmatch(nif):
        return "legal" if LEGAL_FORM.search(name) else "natural_person"

    if FOREIGN_TAX_ID.fullmatch(nif) or LEGAL_FORM.search(name):
        return "legal"

    return "unknown"


def activity_label(text: str) -> str:
    parts = text.split(" - ")

    return parts[0] if len(parts) == 2 and parts[0] == parts[1] else text


def decode_utf16(raw: bytes) -> str:
    try:
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return raw.decode("utf-16")

        if len(raw) > 1 and raw[1] == 0 and raw[0] != 0:
            return raw.decode("utf-16-le")
    except UnicodeDecodeError as error:
        raise FormatoError(f"{ROSCE_MEMBER} no es UTF-16 válido: {error}") from None

    raise FormatoError(f"{ROSCE_MEMBER} ya no parece UTF-16: revisa la codificación")


def rosce_lines(archive: zipfile.ZipFile) -> list[tuple[int, str]]:
    if archive.namelist() != [ROSCE_MEMBER]:
        raise FormatoError(f"rosce.zip debería contener solo {ROSCE_MEMBER} y contiene {archive.namelist()}")

    lines = [(number, line) for number, line in enumerate(re.split(r"\r?\n", decode_utf16(read_member(archive, ROSCE_MEMBER))), start=1)]
    lines = [(number, line) for number, line in lines if line.strip()]
    header = [clean(value) for value in lines[0][1].lstrip("﻿").split(";")] if lines else []

    if header != ROSCE_HEADER:
        raise FormatoError(f"Cabecera inesperada en {ROSCE_MEMBER}: {header}")

    return lines[1:]


def rosce_values(line: str, where: str) -> list[str]:
    values = [clean(value) for value in HTML_ENTITY.sub(lambda match: html.unescape(match.group(0)), line).split(";")]

    if len(values) < len(ROSCE_HEADER):
        raise FormatoError(f"{where}: se esperaban {len(ROSCE_HEADER)} campos separados por «;» y hay {len(values)}")

    if len(values) > len(ROSCE_HEADER):
        values = values[:2] + ["", ""] + values[-4:]

        if nif_kind(normalize_nif(values[1]), values[0]) == "unknown" or not re.fullmatch(r"(\d{4}-\d{2}-\d{2})?", values[4]):
            raise FormatoError(f"{where}: sobran campos separados por «;» y no se reconocen el NIF o las fechas (¿un «;» suelto en un domicilio o en el nombre?)")

    return values


def rosce_record(line: str, number: int) -> dict:
    where = f"{ROSCE_MEMBER}, línea {number}"
    name, nif, _, _, notified, activity, scope, resolved = rosce_values(line, where)

    if not name or not nif or not activity:
        raise FormatoError(f"{where}: faltan el nombre, el NIF o la actividad")

    if "|" in activity or "|" in scope:
        raise FormatoError(f"{where}: la actividad o el ámbito contienen «|», que es el separador de salida")

    return {
        "name": name, "nif": normalize_nif(nif), "notified": check_iso_date(notified, where), "scope": scope,
        "activity": activity_label(activity), "resolved": iso_date(resolved, where),
    }


def load_registry(archive: zipfile.ZipFile) -> dict:
    registry = {}

    for number, line in rosce_lines(archive):
        record = rosce_record(line, number)
        entry = registry.setdefault(record["nif"], {
            "names": collections.Counter(), "activities": set(), "scopes": {}, "dates": set(),
        })
        entry["names"][record["name"]] += 1
        entry["activities"].add(record["activity"])
        entry["scopes"].setdefault(plain(record["scope"]), set()).add(record["scope"])
        entry["dates"].update({record["notified"], record["resolved"]} - {""})

    if not registry:
        raise FormatoError(f"{ROSCE_MEMBER} no contiene operadores")

    return {nif: {**entry, "name": entry["names"].most_common(1)[0][0]} for nif, entry in registry.items()}


def operator_kinds(registry: dict) -> dict:
    return {nif: nif_kind(nif, entry["name"]) for nif, entry in registry.items()}


def operator_rows(registry: dict, kinds: dict) -> tuple[list[dict], collections.Counter]:
    rows, excluded = [], collections.Counter()

    for nif, entry in registry.items():
        if kinds[nif] != "legal":
            excluded[kinds[nif]] += 1
            continue

        scopes = [min(variants) for key, variants in entry["scopes"].items() if key]
        rows.append({
            "nif": nif, "name": entry["name"], "activities": "|".join(sorted(entry["activities"])),
            "scope": "|".join(sorted(scopes)), "registered_on": min(entry["dates"]),
        })

    return sorted(rows, key=lambda row: (plain(row["name"]), row["nif"])), excluded


def name_index(registry: dict) -> dict:
    index = collections.defaultdict(set)

    for nif, entry in registry.items():
        for name in entry["names"]:
            index[name_key(name)].add(nif)

    return index


def resolve_operator(name: str, context: dict) -> dict:
    nifs = context["names"].get(name_key(name), set()) if name else set()
    unknown_person = name and not nifs and not (LEGAL_FORM.search(name) or PUBLIC_BODY.search(name))

    if any(context["kinds"][nif] != "legal" for nif in nifs) or unknown_person:
        return {"operator_name": "", "operator_nif": "", "_redacted": True}

    issue = "ambiguous" if len(nifs) > 1 else ("missing" if name and not nifs else "")

    return {"operator_name": name, "operator_nif": next(iter(nifs)) if len(nifs) == 1 else "", "_nif_issue": issue}


def number_range(prefix: str, length: int | None, where: str) -> dict:
    if length is None:
        return {"prefix": prefix, "range_start": prefix, "range_end": prefix, "size": "1"}

    rest = length - len(prefix)

    if rest < 0:
        raise FormatoError(f"{where}: el bloque {prefix} tiene más de {length} cifras")

    return {"prefix": prefix, "range_start": prefix + "0" * rest, "range_end": prefix + "9" * rest, "size": str(10 ** rest)}


def block_type(spec: dict, prefix: str, catalog: list, where: str) -> str:
    kind = catalog_type(catalog, prefix)

    if kind is None or (spec["types"] is not None and kind not in spec["types"]):
        raise FormatoError(f"{where}: el prefijo {prefix} no encaja con los tipos esperados ({kind or 'sin tipo en el catálogo'})")

    return kind


def block_rows(member: str, record: dict, context: dict) -> list[dict]:
    spec, where = SOURCES[member], record["_where"]
    check_digits(record)
    status, subblocks = parse_status(record["status"], where)

    if status != FREE and not record["operator"]:
        raise FormatoError(f"{where}: bloque en estado «{record['status']}» sin operador")

    base = record.get("number") or record["ndc"] + record["block"]
    operator = {"operator_name": "", "operator_nif": ""} if status == FREE else resolve_operator(record["operator"], context)
    date = iso_date(record["date"], where)

    return [
        {
            **number_range(base + digit, spec["length"], where), **operator,
            "type": block_type(spec, base + digit, context["catalog"], where),
            "service": record.get("service") or spec.get("service", ""), "status": status,
            "assigned_on": "" if status == FREE else date, "released_on": date if status == FREE else "",
            "_province": record.get("province", ""), "_ndc": record.get("ndc", ""), "_where": where, "_source": member,
        }
        for digit in subblocks
    ]


def province_codes(rows: list[dict], provinces: tuple[dict, dict]) -> list[dict]:
    index, prefixes = provinces
    by_ndc = collections.defaultdict(set)
    named = []

    for row in rows:
        code = index.get(province_key(row["_province"]), "") if row["_province"] else ""

        if row["_province"] and not code:
            raise FormatoError(f"{row['_where']}: provincia desconocida «{row['_province']}»")

        if code:
            by_ndc[row["_ndc"]].add(code)

        named.append({**row, "province_code": code})

    filled = [fill_province(row, by_ndc) for row in named]
    unexpected = {
        (row["_ndc"], row["province_code"]) for row in filled
        if row["province_code"] and not any(row["_ndc"].startswith(prefix) for prefix in prefixes.get(row["province_code"], []))
    }

    for ndc, code in sorted(unexpected):
        print(f"Aviso: el indicativo {ndc} no figura entre los prefijos de la provincia {code} en {PROVINCES_FILE}", file=sys.stderr)

    return filled


def fill_province(row: dict, by_ndc: dict) -> dict:
    if row["province_code"] or row["type"] not in GEOGRAPHIC_TYPES:
        return row

    candidates = by_ndc.get(row["_ndc"], set())

    return {**row, "province_code": next(iter(candidates)) if len(candidates) == 1 else ""}


def fill_services(rows: list[dict]) -> list[dict]:
    services = {(row["_source"], row["prefix"]): row["service"] for row in rows if row["service"] and row["status"] == "assigned"}

    return [
        {**row, "service": services.get((row["_source"], row["prefix"]), "")}
        if row["_source"] in SERVICE_SOURCES and not row["service"] else row
        for row in rows
    ]


def unique_sorted(rows: list[dict], header: list[str], primary) -> tuple[list[dict], int]:
    seen, output = set(), []

    for row in sorted(rows, key=lambda row: (*primary(row), *(row.get(field, "") for field in header))):
        signature = tuple(row.get(field, "") for field in header)

        if signature not in seen:
            seen.add(signature)
            output.append(row)

    return output, len(rows) - len(output)


def numbering_rows(archive: zipfile.ZipFile, context: dict) -> tuple[list[dict], int]:
    rows = []

    for member, spec in SOURCES.items():
        if member not in archive.namelist():
            continue

        for record in member_records(archive, member, spec["fields"], spec.get("optional", False)):
            rows.extend(block_rows(member, record, context))

    rows = fill_services(province_codes(rows, context["provinces"]))

    return unique_sorted(rows, NUMBERING_HEADER, lambda row: (row["prefix"], STATUS_ORDER.index(row["status"]), plain(row["operator_name"])))


def mnc_row(record: dict, context: dict) -> dict:
    where = record["_where"]
    check_digits(record)
    status, subblocks = parse_status(record["status"], where)

    if subblocks != [""]:
        raise FormatoError(f"{where}: un MNC no debería tener subbloques («{record['status']}»)")

    if status == FREE or not record["operator"]:
        raise FormatoError(f"{where}: MNC libre o sin operador («{record['status']}»)")

    return {
        "mcc": record["mcc"], "mnc": record["mnc"], "status": status,
        **resolve_operator(record["operator"], context), "assigned_on": iso_date(record["date"], where),
    }


def mnc_rows(archive: zipfile.ZipFile, context: dict) -> list[dict]:
    rows = [mnc_row(record, context) for record in member_records(archive, MNC_SOURCE, MNC_FIELDS)]
    primary = lambda row: (row["mcc"], len(row["mnc"]), row["mnc"], STATUS_ORDER.index(row["status"]), plain(row["operator_name"]))

    return unique_sorted(rows, MNC_HEADER, primary)[0]


def check_members(archive: zipfile.ZipFile) -> None:
    members = set(archive.namelist())
    missing = (REQUIRED_SOURCES | {MNC_SOURCE}) - members
    unknown = members - KNOWN_MEMBERS
    absent = sorted(set(SOURCES) - REQUIRED_SOURCES - members)

    if missing:
        raise FormatoError(f"Faltan en bd-num.zip los ficheros {', '.join(sorted(missing))}")

    if absent:
        print(f"Aviso: bd-num.zip ya no incluye {', '.join(absent)}; se omite", file=sys.stderr)

    if unknown:
        print(f"Aviso: bd-num.zip trae ficheros nuevos que no se procesan: {', '.join(sorted(unknown))}", file=sys.stderr)


def data_date(archive: zipfile.ZipFile) -> str:
    try:
        return datetime.datetime(*max(info.date_time for info in archive.infolist())).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return "fecha desconocida"


def check_drop(path: Path, rows: list[dict]) -> None:
    if not path.is_file():
        return

    with path.open(encoding="utf-8", newline="") as file:
        previous = max(sum(1 for _ in file) - 1, 0)

    if previous and len(rows) < previous * (1 - MAX_DROP):
        raise FormatoError(
            f"{path.name} bajaría de {previous} a {len(rows)} filas (más de un {MAX_DROP:.0%} menos): "
            "revisa los ficheros de la CNMC o usa --forzar"
        )


def write_outputs(outputs: dict, force: bool) -> None:
    if not force:
        for path, (_, rows) in outputs.items():
            check_drop(path, rows)

    try:
        for path, (header, rows) in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)

            with path.with_suffix(".csv.tmp").open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=header, lineterminator="\n", extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

        for path in outputs:
            os.replace(path.with_suffix(".csv.tmp"), path)
    except OSError as error:
        raise FormatoError(f"No se pudieron escribir los CSV: {error}") from None


def percent(part: int, total: int) -> str:
    return f"{part} de {total} ({100 * part / total:.1f} %)" if total else "0 de 0"


def nif_coverage(rows: list[dict]) -> str:
    with_operator = [row for row in rows if row["operator_name"]]

    return percent(sum(1 for row in with_operator if row["operator_nif"]), len(with_operator))


def report(numbering: list[dict], mnc: list[dict], operators: list[dict], excluded: collections.Counter) -> None:
    types = collections.Counter(row["type"] for row in numbering).most_common()
    geographic = [row for row in numbering if row["type"] in GEOGRAPHIC_TYPES]
    issues = collections.Counter((row["_nif_issue"], row["operator_name"]) for row in numbering + mnc if row.get("_nif_issue"))
    redacted = sum(1 for row in numbering + mnc if row.get("_redacted"))

    print(f"{NUMBERING_OUTPUT}: {len(numbering)} filas ({', '.join(f'{kind} {count}' for kind, count in types)})")
    print(f"{MNC_OUTPUT}: {len(mnc)} filas")
    print(
        f"{OPERATORS_OUTPUT}: {len(operators)} operadores; excluidos {excluded['natural_person']} NIF de personas físicas, "
        f"{excluded['no_personality']} comunidades de bienes o sociedades civiles y {excluded['unknown']} NIF no reconocidos"
    )
    print(f"Bloques con NIF del operador: {nif_coverage(numbering)}")
    print(f"MNC con NIF del operador: {nif_coverage(mnc)}")
    print(f"Bloques geográficos con provincia: {percent(sum(1 for row in geographic if row['province_code']), len(geographic))}")

    if redacted:
        print(f"Filas con el titular oculto por ser o poder ser persona física: {redacted}")

    for (issue, name), count in sorted(issues.items(), key=lambda item: -item[1]):
        reason = "no está en el ROSCE" if issue == "missing" else "corresponde a varios NIF del ROSCE"
        print(f"  Sin NIF ({reason}): {name} ({count} filas)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenera la numeración asignada, los operadores y los MNC a partir de los ficheros de la CNMC.")
    parser.add_argument("--bd-num", help="ruta local de bd-num.zip (por defecto se descarga)")
    parser.add_argument("--rosce", help="ruta local de rosce.zip (por defecto se descarga)")
    parser.add_argument("--repo", type=Path, default=REPO, help="carpeta del repositorio de la que se leen provincias y catálogo")
    parser.add_argument("--salida", type=Path, help="carpeta de salida (por defecto, telecomunicaciones/ del repositorio)")
    parser.add_argument("--forzar", action="store_true", help="escribe aunque el número de filas caiga mucho respecto a los CSV actuales")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.salida or args.repo / OUTPUT_DIR

    try:
        bd_num = load_archive(args.bd_num, BD_NUM_URL, "bd-num.zip")
        check_members(bd_num)
        registry = load_registry(load_archive(args.rosce, ROSCE_URL, "rosce.zip"))
        kinds = operator_kinds(registry)
        context = {
            "names": name_index(registry), "kinds": kinds, "catalog": load_catalog(args.repo / CATALOG_FILE),
            "provinces": load_provinces(args.repo / PROVINCES_FILE),
        }
        numbering, duplicates = numbering_rows(bd_num, context)
        mnc = mnc_rows(bd_num, context)
        operators, excluded = operator_rows(registry, kinds)
        write_outputs({
            output / NUMBERING_OUTPUT: (NUMBERING_HEADER, numbering),
            output / OPERATORS_OUTPUT: (OPERATORS_HEADER, operators),
            output / MNC_OUTPUT: (MNC_HEADER, mnc),
        }, args.forzar)
    except (FormatoError, RuntimeError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Datos de la CNMC del {data_date(bd_num)} escritos en {output}")

    if duplicates:
        print(f"Se han descartado {duplicates} filas repetidas")

    report(numbering, mnc, operators, excluded)


if __name__ == "__main__":
    main()
