import csv
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLDR_VERSION = "49.0.0"
CLDR_BASE = f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR_VERSION}/cldr-json"
CLDR_NAMES = CLDR_BASE + "/cldr-localenames-full/main/{locale}/languages.json"
CLDR_LOCALES = CLDR_BASE + "/cldr-core/availableLocales.json"
ISO_639_2 = "https://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
HEADER = ["code", "alpha3_b", "alpha3_t", "name", "native_name", "official_in_es"]
SPECIAL_CODES = {"mis", "mul", "und", "zxx"}

SPAIN = (
    "ES-AN", "ES-AR", "ES-AS", "ES-CB", "ES-CE", "ES-CL", "ES-CM", "ES-CN", "ES-CT", "ES-EX",
    "ES-GA", "ES-IB", "ES-MC", "ES-MD", "ES-ML", "ES-NC", "ES-PV", "ES-RI", "ES-VC",
)
OFFICIAL_IN_ES = {
    "es": SPAIN,
    "ca": ("ES-CT", "ES-IB", "ES-VC"),
    "eu": ("ES-NC", "ES-PV"),
    "gl": ("ES-GA",),
    "oc": ("ES-CT",),
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def cldr_languages(locale: str) -> dict:
    try:
        data = json.loads(fetch(CLDR_NAMES.format(locale=locale)))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {}
        raise

    return data["main"][locale]["localeDisplayNames"]["languages"]


def iso_entries() -> list:
    lines = fetch(ISO_639_2).decode("utf-8-sig").splitlines()
    entries = []

    for line in filter(None, (line.strip() for line in lines)):
        fields = line.split("|")

        if len(fields) != 5:
            raise RuntimeError(f"Línea ISO 639-2 con formato inesperado: {line!r}")

        bibliographic, terminologic, alpha2 = fields[:3]
        entries.append({"alpha3_b": bibliographic, "alpha3_t": terminologic or bibliographic, "alpha2": alpha2})

    return entries


def select(entries: list, spanish: dict, locales: set) -> list:
    selected = []

    for entry in entries:
        code = entry["alpha2"] or entry["alpha3_t"]

        if entry["alpha2"]:
            if code not in spanish:
                raise RuntimeError(f"CLDR no tiene nombre en español para {code}")
        elif code in SPECIAL_CODES or code not in locales or code not in spanish:
            continue

        selected.append({**entry, "code": code})

    return sorted(selected, key=lambda entry: entry["code"])


def main() -> None:
    output = (Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "catalogos") / "idiomas.csv"
    spanish = cldr_languages("es")
    locales = {locale for locale in json.loads(fetch(CLDR_LOCALES))["availableLocales"]["full"] if "-" not in locale}
    selected = select(iso_entries(), spanish, locales)
    unknown = set(OFFICIAL_IN_ES) - {entry["code"] for entry in selected}

    if unknown:
        raise RuntimeError(f"Lenguas cooficiales sin fila: {sorted(unknown)}")

    rows = []

    for entry in selected:
        code = entry["code"]
        native = cldr_languages(code).get(code, "") if code in locales else ""
        official = "|".join(sorted(OFFICIAL_IN_ES.get(code, ())))
        rows.append([code, entry["alpha3_b"], entry["alpha3_t"], spanish[code], native, official])

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    output.write_text(buffer.getvalue(), encoding="utf-8")
    alpha2 = sum(1 for entry in selected if entry["alpha2"])
    natives = sum(1 for row in rows if row[4])
    print(f"Idiomas (CLDR {CLDR_VERSION}): {len(rows)} filas ({alpha2} con ISO 639-1), {natives} con autónimo, en {output}")


if __name__ == "__main__":
    sys.exit(main())
