import argparse
import csv
import html
import io
import json
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple, Optional

REPO = Path(__file__).resolve().parents[2]
CSV_PATH = REPO / "envios" / "agencias_envio_es.csv"
BUILD = REPO / "build"
OUTPUT = "agencias_envio_registro.csv"
REGISTER_PAGE = (
    "https://www.transportes.gob.es/el-ministerio/servicios-postales/"
    "registro-general-de-empresas-prestadoras-de-servicios-postales"
)
REGISTER_LINK = re.compile(r'href="([^"]*empresas_por_orden_alfabetico_?(\d{8})\.pdf)"')
VIES_URL = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
BROWSER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
TIMEOUT = 60
CHECK_TIMEOUT = 30
PAGE_BYTES = 1_000_000
ATTEMPTS = 3
PAUSE = 2.0
TRACKING_SAMPLE = "ZX98765432101"
BLOCKED_STATUSES = {401, 403, 429}

HEADER = [
    "code", "name", "legal_name", "nif", "group", "website", "tracking_url", "tracking_page", "tracking_number_pattern", "services",
    "postal_authorization", "logo_on_dark", "logo",
]
OUTPUT_HEADER = ["code", "postal_authorization"]
SERVICES = {"home_delivery", "pickup_point", "locker", "international", "cash_on_delivery", "same_day", "express"}
AUTHORIZATIONS = {"Tipo A": "A", "Tipo B": "B", "Tipos A y B": "A|B"}
CODE = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*")
NIF = re.compile(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]")
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">([^<]*)</word>')
COLUMNS = ("NOMBRE", "PROVINCIA", "LOCALIDAD", "AUTORIZACION")
AS_OF = re.compile(r"A FECHA:\s*(\d{2}/\d{2}/\d{4})")
ROW_TOLERANCE = 1.5
TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
ERROR_TITLE = re.compile(r"\b404\b|not found|no encontrad|no existe", re.I)
LEGAL_WORDS = {
    "A", "E", "L", "M", "S", "U", "Y", "EN", "SA", "SAU", "SASU", "SL", "SLU", "SM", "SME", "SNC", "SRC", "LTD", "CIA",
    "SOCIEDAD", "ANONIMA", "LIMITADA", "UNIPERSONAL",
}


class Word(NamedTuple):
    x: float
    y: float
    text: str


class Inscription(NamedTuple):
    name: str
    province: str
    locality: str
    authorization: str


class Register(NamedTuple):
    as_of: str
    url: str
    inscriptions: tuple


class Agency(NamedTuple):
    code: str
    name: str
    legal_name: str
    nif: str
    tracking_url: str
    tracking_page: str
    postal_authorization: str


def fetch(url: str, agent: str = USER_AGENT, data: Optional[bytes] = None, headers: Optional[dict] = None) -> bytes:
    request = urllib.request.Request(url, data=data, headers={"User-Agent": agent, **(headers or {})})
    last_error = None

    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(PAUSE * attempt)

        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500:
                raise RuntimeError(f"{url} respondió {error.code}") from None
            last_error = error
        except OSError as error:
            last_error = error

    raise RuntimeError(f"No se pudo descargar {url}: {last_error}")


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9&]+", " ", plain).split())


def name_key(text: str) -> str:
    return " ".join(word for word in normalize(re.sub(r"\([^)]*\)", " ", text)).split() if word not in LEGAL_WORDS)


def read_agencies(path: Path) -> list:
    csv.field_size_limit(sys.maxsize)

    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        header = list(reader.fieldnames or [])
        rows = list(reader)

    if header != HEADER:
        raise ValueError(f"{path.name}: la cabecera no es la esperada: {header}")

    problems = [problem for index, row in enumerate(rows, 2) for problem in row_problems(index, row)]
    repeated = [code for code, count in Counter(row["code"] for row in rows).items() if count > 1]

    if repeated:
        problems.append(f"códigos repetidos: {', '.join(repeated)}")

    if problems:
        raise ValueError(f"{path.name} tiene errores de formato:\n  " + "\n  ".join(problems))

    return rows


def valid_pattern(pattern: str) -> bool:
    try:
        re.compile(pattern)
    except re.error:
        return False

    return pattern.startswith("^") and pattern.endswith("$")


def row_problems(index: int, row: dict) -> list:
    services = set(row["services"].split("|")) if row["services"] else set()
    checks = [
        (CODE.fullmatch(row["code"]), "code no es un slug en minúsculas"),
        (row["name"] and row["legal_name"], "faltan name o legal_name"),
        (NIF.fullmatch(row["nif"]), f"NIF no válido: {row['nif']!r}"),
        (row["website"].startswith("https://"), "website debe empezar por https://"),
        (not row["tracking_url"] or (row["tracking_url"].startswith("https://") and row["tracking_url"].count("{tracking}") == 1),
         "tracking_url debe ser https y llevar {tracking} una vez"),
        (row["tracking_page"].startswith("https://") and "{" not in row["tracking_page"], "tracking_page debe ser una URL https sin plantilla"),
        (not row["tracking_number_pattern"] or valid_pattern(row["tracking_number_pattern"]), "tracking_number_pattern no es una expresión regular válida"),
        (services <= SERVICES, f"servicios desconocidos: {sorted(services - SERVICES)}"),
        (row["postal_authorization"] in {"", *AUTHORIZATIONS.values()}, f"postal_authorization no válido: {row['postal_authorization']!r}"),
        (row["logo_on_dark"] in {"0", "1"}, "logo_on_dark debe ser 0 o 1"),
        (row["logo"].startswith("<svg") and "\n" not in row["logo"], "logo debe ser un SVG de una sola línea"),
    ]

    return [f"fila {index} ({row['code']}): {message}" for ok, message in checks if not ok]


def register_link(page: bytes) -> tuple:
    links = {(urllib.parse.urljoin(REGISTER_PAGE, href), date) for href, date in REGISTER_LINK.findall(page.decode("utf-8", "replace"))}

    if not links:
        raise ValueError("La página del registro postal ya no enlaza el listado alfabético de operadores")

    return max(links, key=lambda link: link[1])


def pdf_words(data: bytes) -> list:
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "registro.pdf"
        source.write_bytes(data)

        try:
            result = subprocess.run(
                ["pdftotext", "-bbox-layout", str(source), "-"], capture_output=True, check=True, timeout=300,
            )
        except FileNotFoundError:
            raise RuntimeError("Falta pdftotext (poppler-utils)") from None
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"pdftotext no pudo leer el registro: {error.stderr.decode(errors='replace')}") from None

    text = result.stdout.decode("utf-8", "replace")
    return [[Word(float(x), float(y), html.unescape(word)) for x, y, word in WORD.findall(page)] for page in text.split("<page ")[1:]]


def column_starts(words: list) -> tuple:
    found = {word.text: word.x for page in words for word in page if word.text in COLUMNS}
    missing = [column for column in COLUMNS if column not in found]

    if missing:
        raise ValueError(f"El listado del registro ya no tiene las columnas {', '.join(missing)}")

    starts = tuple(found[column] for column in COLUMNS)

    if list(starts) != sorted(starts):
        raise ValueError("Las columnas del listado del registro no están en el orden esperado")

    return starts


def column_of(word: Word, starts: tuple) -> int:
    return max(index for index, start in enumerate(starts) if word.x >= start - ROW_TOLERANCE) if word.x >= starts[0] - ROW_TOLERANCE else -1


def page_rows(page: list) -> list:
    rows = []

    for word in sorted(page, key=lambda item: (item.y, item.x)):
        if rows and abs(rows[-1][0].y - word.y) <= ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    return rows


def split_row(row: list, starts: tuple) -> list:
    cells = [[] for _ in starts]

    for word in sorted(row, key=lambda item: item.x):
        index = column_of(word, starts)

        if index >= 0:
            cells[index].append(word.text)

    return [" ".join(cell) for cell in cells]


def parse_register(words: list) -> tuple:
    starts = column_starts(words)
    entries = []

    for page in words:
        for row in page_rows(page):
            name, province, locality, authorization = split_row(row, starts)

            if authorization in AUTHORIZATIONS:
                entries.append([name, province, locality, AUTHORIZATIONS[authorization]])
            elif entries and not authorization and (name or locality) and not province and name not in COLUMNS:
                entries[-1] = [f"{entries[-1][0]} {name}".strip(), entries[-1][1], f"{entries[-1][2]} {locality}".strip(), entries[-1][3]]

    if len(entries) < 1000:
        raise ValueError(f"El listado del registro solo tiene {len(entries)} inscripciones: ¿ha cambiado el formato?")

    return tuple(Inscription(*entry) for entry in entries)


def read_register(pdf: Optional[Path]) -> Register:
    if pdf:
        data, url = pdf.read_bytes(), str(pdf)
    else:
        url, _ = register_link(fetch(REGISTER_PAGE, BROWSER_AGENT))
        time.sleep(PAUSE)
        data = fetch(url, BROWSER_AGENT)

    words = pdf_words(data)
    match = AS_OF.search(" ".join(word.text for word in words[0])) if words else None

    if not match:
        raise ValueError("El listado del registro no indica su fecha")

    return Register(match.group(1), url, parse_register(words))


def to_agency(row: dict) -> Agency:
    return Agency(
        row["code"], row["name"], row["legal_name"], row["nif"], row["tracking_url"], row["tracking_page"], row["postal_authorization"],
    )


def register_problems(agency: Agency, index: dict) -> tuple:
    found = index.get(name_key(agency.legal_name), ())

    if len(found) > 1:
        return [f"{agency.code}: {agency.legal_name!r} aparece {len(found)} veces en el registro postal"], agency.postal_authorization

    if not found and agency.postal_authorization:
        return [f"{agency.code}: {agency.legal_name!r} ya no figura en el registro postal (baja o cambio de razón social)"], ""

    current = found[0].authorization if found else ""

    if current != agency.postal_authorization:
        print(f"  {agency.code}: la autorización postal pasa de {agency.postal_authorization or '(sin inscribir)'} a {current or '(sin inscribir)'}")

    return [], current


def vies_check(agency: Agency) -> dict:
    payload = json.dumps({"countryCode": "ES", "vatNumber": agency.nif, "traderName": agency.legal_name}).encode()

    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(PAUSE * 3 * attempt)

        answer = json.loads(fetch(VIES_URL, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}))

        if "valid" in answer and not answer.get("errorWrappers"):
            return answer

    raise RuntimeError(f"VIES no ha podido comprobar el NIF {agency.nif}: {answer.get('errorWrappers') or answer}")


def nif_problems(agency: Agency) -> list:
    try:
        answer = vies_check(agency)
    except RuntimeError as error:
        return [f"{agency.code}: {error}"]

    if not answer["valid"]:
        return [f"{agency.code}: VIES da el NIF {agency.nif} como no válido"]

    if answer.get("traderNameMatch") != "VALID":
        return [f"{agency.code}: según VIES, el NIF {agency.nif} no corresponde a {agency.legal_name!r} ({answer.get('traderNameMatch')})"]

    return []


def page_title(body: bytes) -> str:
    match = TITLE.search(body)
    return " ".join(html.unescape(match.group(1).decode("utf-8", "replace")).split()) if match else ""


def timed_out(error: OSError) -> bool:
    return isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError)


def url_problems(code: str, label: str, url: str) -> list:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER_AGENT, "Accept-Language": "es-ES,es;q=0.9"})

    try:
        with urllib.request.urlopen(request, timeout=CHECK_TIMEOUT) as response:
            final = response.geturl()
            title = page_title(response.read(PAGE_BYTES))
    except urllib.error.HTTPError as error:
        if error.code in BLOCKED_STATUSES:
            print(f"  {code}: {label} responde {error.code} a peticiones automáticas; no se puede comprobar")
            return []
        return [f"{code}: {label} responde {error.code} ({url})"]
    except OSError as error:
        if timed_out(error):
            print(f"  {code}: {label} no contesta en {CHECK_TIMEOUT} s (posible bloqueo de robots); no se puede comprobar")
            return []
        return [f"{code}: {label} no responde ({url}): {error}"]

    expected = urllib.parse.urlsplit(url).path.strip("/")
    landed = urllib.parse.urlsplit(final).path.strip("/")

    if expected and not landed:
        return [f"{code}: {label} redirige a la portada ({url} -> {final})"]

    if ERROR_TITLE.search(title):
        return [f"{code}: {label} muestra una página de error ({title!r}, {final})"]

    return []


def tracking_problems(agency: Agency) -> list:
    sample = agency.tracking_url.replace("{tracking}", TRACKING_SAMPLE)
    template = url_problems(agency.code, "tracking_url", sample) if agency.tracking_url else []
    time.sleep(PAUSE)
    return template + url_problems(agency.code, "tracking_page", agency.tracking_page)


def register_index(inscriptions: tuple) -> dict:
    index = defaultdict(list)

    for inscription in inscriptions:
        index[name_key(inscription.name)].append(inscription)

    return {name: tuple(found) for name, found in index.items()}


def check_agency(agency: Agency, index: dict) -> tuple:
    found, authorization = register_problems(agency, index)
    time.sleep(PAUSE)
    problems = found + nif_problems(agency) + tracking_problems(agency)
    return problems, [agency.code, authorization]


def write_csv(path: Path, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(OUTPUT_HEADER)
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")
    print(f"{path}: {len(rows)} filas")


def run(args: argparse.Namespace) -> list:
    agencies = [to_agency(row) for row in read_agencies(args.csv)]
    register = read_register(args.pdf)
    print(f"Registro postal a {register.as_of}: {len(register.inscriptions)} inscripciones ({register.url})")
    index = register_index(register.inscriptions)
    results = [check_agency(agency, index) for agency in agencies]
    problems = [problem for found, _ in results for problem in found]

    if not problems:
        args.build.mkdir(parents=True, exist_ok=True)
        write_csv(args.build / OUTPUT, [row for _, row in results])

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprueba agencias_envio_es.csv contra el registro postal, VIES y las webs de seguimiento.")
    parser.add_argument("--csv", type=Path, default=CSV_PATH)
    parser.add_argument("--pdf", type=Path, help="listado alfabético del registro postal ya descargado")
    parser.add_argument("--build", type=Path, default=BUILD)
    args = parser.parse_args()

    try:
        problems = run(args)
    except (RuntimeError, ValueError, OSError) as error:
        sys.exit(f"No se ha podido comprobar agencias_envio_es.csv: {error}")

    if problems:
        sys.exit("agencias_envio_es.csv no cuadra con las fuentes oficiales; no se escribe nada:\n  " + "\n  ".join(problems))

    print("agencias_envio_es.csv cuadra con el registro postal, VIES y las webs de seguimiento")


if __name__ == "__main__":
    main()
