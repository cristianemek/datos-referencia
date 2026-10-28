import csv
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
EC_BASE = "https://ec.europa.eu"
EC_REGISTRY = EC_BASE + "/digital-building-blocks/sites/display/DIGITAL/Registry+of+supporting+artefacts+to+implement+EN16931"
EC_DEFAULT = EC_BASE + "/digital-building-blocks/sites/download/attachments/467108974/digital-genericodes-2026-11-15.zip?version=1&modificationDate=1793009563110&api=v2"
FACTURAE_XSD = "https://www.facturae.gob.es/content/dam/facturae/formato/versiones/Facturaev3_2_2.xml"
XS = "{http://www.w3.org/2001/XMLSchema}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SUFFIX = re.compile(r"-([A-Za-z0-9]{2,3})$")

FACTURAE_TO_UNECE = {
    "02": "HUR", "03": "KGM", "04": "LTR", "06": "XBX", "07": "XDS", "08": "XBA", "09": "XJY", "10": "XBG",
    "11": "XCO", "12": "XBO", "13": "XCI", "15": "CLT", "16": "CMT", "17": "XBI", "18": "DZN", "19": "XCS",
    "20": "XDJ", "21": "GRM", "22": "KMT", "23": "XCA", "24": "XBH", "25": "MTR", "26": "MMT", "28": "XPK",
    "30": "XRO", "31": "XEN", "32": "XTB", "33": "MTQ", "34": "SEC", "35": "WTT", "36": "KWH",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except OSError as error:
        raise RuntimeError(f"No se pudo descargar {url}: {error}") from error


def latest_genericodes_url() -> str:
    page = fetch(EC_REGISTRY).decode("utf-8", "replace")
    found = re.findall(r'href="(/digital-building-blocks/[^"]*?digital-genericodes-(\d{4}-\d{2}-\d{2})\.zip[^"]*)"', page)
    if not found:
        return EC_DEFAULT
    path, _ = max(found, key=lambda item: item[1])
    return EC_BASE + path.replace("&amp;", "&")


def recommendation(code: str) -> str:
    return "21" if len(code) == 3 and code.startswith("X") else "20"


def unece_units(url: str) -> tuple[str, list[dict]]:
    with zipfile.ZipFile(io.BytesIO(fetch(url))) as archive:
        root = ET.fromstring(archive.read("Unit.gc"))
    version = root.findtext("Identification/Version") or ""
    units = []
    for row in root.iter("Row"):
        values = {value.get("ColumnRef"): value.findtext("SimpleValue") or "" for value in row.findall("Value")}
        units.append({"code": values["Code"], "name": values["Name"], "recommendation": recommendation(values["Code"])})
    codes = [unit["code"] for unit in units]
    if len(codes) != len(set(codes)) or len(codes) < 2000:
        raise RuntimeError(f"Unit.gc no tiene el contenido esperado ({len(codes)} códigos)")
    return version, units


def facturae_units() -> list[dict]:
    root = ET.fromstring(fetch(FACTURAE_XSD))
    simple = next((s for s in root.iter(f"{XS}simpleType") if s.get("name") == "UnitOfMeasureType"), None)
    if simple is None:
        raise RuntimeError("El XSD de Facturae no define UnitOfMeasureType")
    units = []
    for enumeration in simple.iter(f"{XS}enumeration"):
        docs = {doc.get(XML_LANG): (doc.text or "").strip() for doc in enumeration.iter(f"{XS}documentation")}
        units.append({"code": enumeration.get("value"), "name_en": docs.get("en", ""), "name_es": docs.get("es", "")})
    return units


def strip_suffix(name: str) -> str:
    return SUFFIX.sub("", name).strip()


def check_mapping(unit: dict, unece: dict) -> None:
    code = FACTURAE_TO_UNECE[unit["code"]]
    match = SUFFIX.search(unit["name_en"])
    expected = code[1:] if unece[code]["recommendation"] == "21" else code
    if match and match.group(1).upper() != expected:
        raise RuntimeError(f"Facturae {unit['code']} indica {match.group(1)}, no {code}")
    if strip_suffix(unit["name_en"])[:3].lower() != unece[code]["name"][:3].lower():
        raise RuntimeError(f"Facturae {unit['code']} ({unit['name_en']}) no coincide con {code} ({unece[code]['name']})")


def build(units: list[dict], facturae: list[dict]) -> list[dict]:
    unece = {unit["code"]: unit for unit in units}
    by_code = {unit["code"]: unit for unit in facturae}
    missing = [f"{key}->{value}" for key, value in FACTURAE_TO_UNECE.items() if key not in by_code or value not in unece]
    if missing:
        raise RuntimeError(f"Equivalencias sin código en origen: {missing}")
    for unit in facturae:
        if unit["code"] in FACTURAE_TO_UNECE:
            check_mapping(unit, unece)
    reverse = {value: by_code[key] for key, value in FACTURAE_TO_UNECE.items()}
    return [
        {
            **unit,
            "facturae_code": reverse[unit["code"]]["code"] if unit["code"] in reverse else "",
            "name_es": strip_suffix(reverse[unit["code"]]["name_es"]) if unit["code"] in reverse else "",
        }
        for unit in units
    ]


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} filas")


def main() -> None:
    url = latest_genericodes_url()
    version, units = unece_units(url)
    print(f"Unit.gc {version}: {url}")
    rows = build(units, facturae_units())
    write_csv(REPO / "catalogos" / "unidades_medida.csv", ["code", "name", "recommendation", "facturae_code", "name_es"], rows)


if __name__ == "__main__":
    main()
