import csv
import hashlib
import json
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ENTITY_OVERRIDES = {"HOLY SEE (THE)": "VA"}
PARENT_ENTITY = {"XI": "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND (THE)"}
NOT_TENDER = "false"
WITHDRAWN_MONTH = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
USER_AGENT = "datos-referencia/1.0"
TIMEOUT = 120
CLDR_VERSION = "49.0.0"
ISO_CODES_TAG = "v4.20.1"
SIX_URL = "https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists"
CLDR_URL = f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR_VERSION}/cldr-json"
ISO_CODES_URL = f"https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/{ISO_CODES_TAG}/data"
DOWNLOADS = {
    "list-one.xml": f"{SIX_URL}/list-one.xml",
    "list-three.xml": f"{SIX_URL}/list-three.xml",
    "cldr-core_package.json": f"{CLDR_URL}/cldr-core/package.json",
    "cldr-core_supplemental_currencyData.json": f"{CLDR_URL}/cldr-core/supplemental/currencyData.json",
    "cldr-numbers-full_package.json": f"{CLDR_URL}/cldr-numbers-full/package.json",
    "cldr-numbers-full_main_es_currencies.json": f"{CLDR_URL}/cldr-numbers-full/main/es/currencies.json",
    "cldr-numbers-full_main_und_currencies.json": f"{CLDR_URL}/cldr-numbers-full/main/und/currencies.json",
    "iso-codes_iso_3166-1.json": f"{ISO_CODES_URL}/iso_3166-1.json",
}


def download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data, headers = response.read(), response.headers
    except OSError as error:
        raise OSError(f"No se pudo descargar {url}: {error}") from error
    if not data or headers.get_content_type() == "text/html":
        raise ValueError(f"Respuesta vacía o HTML en lugar de datos: {url}")
    target.write_bytes(data)
    (target.parent / f"hdr_{target.name}.txt").write_text(str(headers), encoding="utf-8")


def fetch_all(cache, refresh):
    cache.mkdir(parents=True, exist_ok=True)
    for name, url in DOWNLOADS.items():
        target = cache / name
        if refresh or not target.exists() or target.stat().st_size == 0:
            download(url, target)
    sums = [f"{hashlib.sha256((cache / n).read_bytes()).hexdigest()}  {n}\n" for n in DOWNLOADS]
    (cache / "SHA256SUMS").write_text("".join(sums), encoding="utf-8")


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def read_csv(path):
    csv.field_size_limit(2**31 - 1)
    with open(path, encoding="utf-8", newline="") as fh:
        return tuple(csv.DictReader(fh))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def six_current(path):
    root = ET.parse(path).getroot()
    entries = tuple(
        {"entity": clean(e.findtext("CtryNm")), "code": clean(e.findtext("Ccy"))}
        for e in root.find("CcyTbl").findall("CcyNtry")
    )
    return root.attrib["Pblshd"], entries


def six_historic_entry(node):
    name_node = node.find("CcyNm")
    return {
        "code": clean(node.findtext("Ccy")),
        "numeric": clean(node.findtext("CcyNbr")),
        "six_name": clean(node.findtext("CcyNm")),
        "entity": clean(node.findtext("CtryNm")),
        "entity_raw": node.findtext("CtryNm") or "",
        "withdrawn": clean(node.findtext("WthdrwlDt")),
        "is_fund_attr": name_node.attrib.get("IsFund", "") if name_node is not None else "",
    }


def six_historic(path):
    root = ET.parse(path).getroot()
    nodes = root.find("HstrcCcyTbl").findall("HstrcCcyNtry")
    return root.attrib["Pblshd"], tuple(six_historic_entry(n) for n in nodes)


def cldr_currencies(path, locale):
    return read_json(path)["main"][locale]["numbers"]["currencies"]


def cldr_currency_data(path):
    supplemental = read_json(path)["supplemental"]
    data = supplemental["currencyData"]
    regions = {
        region: tuple(next(iter(item.items())) for item in items)
        for region, items in data["region"].items()
    }
    return supplemental["version"]["_cldrVersion"], data["fractions"], regions


def resolve(tables, code, keys):
    for key in keys:
        for table in tables:
            value = table.get(code, {}).get(key)
            if value:
                return value
    return None


def is_current_tender(attrs):
    return "_to" not in attrs and attrs.get("_tender") != NOT_TENDER


def name_key(text):
    decomposed = unicodedata.normalize("NFKD", text.upper())
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    plain = re.sub(r"[’']", "", plain)
    tokens = re.sub(r"[^A-Z0-9]+", " ", plain).split()
    return " ".join(t for t in tokens if t != "THE")


def iso3166_index(path):
    index = {}
    for country in read_json(path)["3166-1"]:
        for field in ("name", "official_name", "common_name"):
            if field in country:
                index.setdefault(name_key(country[field]), set()).add(country["alpha_2"])
    ambiguous = {k: v for k, v in index.items() if len(v) > 1}
    if ambiguous:
        raise ValueError(f"Nombres ISO 3166 ambiguos: {ambiguous}")
    return {k: next(iter(v)) for k, v in index.items()}


def entity_alpha2(entity, index):
    return ENTITY_OVERRIDES.get(entity) or index.get(name_key(entity))


def entity_currencies(six_entries, entity):
    codes = tuple(dict.fromkeys(e["code"] for e in six_entries if e["entity"] == entity and e["code"]))
    if not codes:
        raise ValueError(f"SIX list-one no tiene divisa para {entity}")
    return codes
