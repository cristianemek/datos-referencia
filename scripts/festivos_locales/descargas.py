import csv
import functools
import http.client
import io
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

from comun import FormatChanged

USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
DATOS_GOB_DATASET = "https://datos.gob.es/apidata/catalog/dataset/{id}.json"
DATOS_GOB_TITLE = "https://datos.gob.es/apidata/catalog/dataset/title/{title}.json?_pageSize=50"


@functools.lru_cache(maxsize=None)
def fetch(url: str, missing_ok: bool = False) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None

    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if missing_ok and error.code in (404, 410):
                return None

            last_error = error

            if 400 <= error.code < 500 and error.code != 429:
                break
        except (OSError, http.client.HTTPException) as error:
            last_error = error

        time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"no se pudo descargar {url}: {last_error}")


def fetch_json(url: str, missing_ok: bool = False) -> dict | None:
    data = fetch(url, missing_ok)

    if data is None:
        return None

    try:
        return json.loads(data)
    except json.JSONDecodeError as error:
        raise FormatChanged(f"{url}: la respuesta no es JSON ({error})") from error


def decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("latin-1")


def read_table(text: str, source: str, required: list[str]) -> list[dict[str, str]]:
    text = text.lstrip(chr(0xFEFF))
    first = text.split("\n", 1)[0]
    delimiter = max(";,|\t§", key=first.count)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))

    return table_records(rows, source, required)


def table_records(rows: list[list[str]], source: str, required: list[str]) -> list[dict[str, str]]:
    for index, row in enumerate(rows[:20]):
        header = [cell.strip() for cell in row]

        if all(column in header for column in required):
            return [
                dict(zip(header, [cell.strip() for cell in values]))
                for values in rows[index + 1:] if any(cell.strip() for cell in values)
            ]

    found = [cell.strip() for cell in rows[0]] if rows else []
    raise FormatChanged(f"{source}: no se encuentran las columnas {required} (cabecera: {found})")


def read_xlsx(data: bytes, source: str) -> list[list[str]]:
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    relation = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

    try:
        book = zipfile.ZipFile(io.BytesIO(data))
        shared = []

        if "xl/sharedStrings.xml" in book.namelist():
            shared = ["".join(node.text or "" for node in item.iter(namespace + "t"))
                      for item in ET.fromstring(book.read("xl/sharedStrings.xml")).findall(namespace + "si")]

        targets = {node.get("Id"): node.get("Target") for node in ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))}
        sheets = [targets[node.get(relation)] for node in ET.fromstring(book.read("xl/workbook.xml")).iter(namespace + "sheet")]
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as error:
        raise FormatChanged(f"{source}: no es un XLSX válido ({error})") from error

    for target in sheets:
        path = target.lstrip("/") if target.lstrip("/").startswith("xl/") else f"xl/{target}"

        try:
            rows = [sheet_row(row, shared, namespace) for row in ET.fromstring(book.read(path)).iter(namespace + "row")]
        except (KeyError, IndexError, ValueError, ET.ParseError) as error:
            raise FormatChanged(f"{source}: no se puede leer la hoja {path} ({error})") from error

        if any(any(cell.strip() for cell in row) for row in rows):
            return rows

    raise FormatChanged(f"{source}: el XLSX no tiene datos")


def sheet_row(row: ET.Element, shared: list[str], namespace: str) -> list[str]:
    cells = {}

    for position, cell in enumerate(row.findall(namespace + "c")):
        value = cell.find(namespace + "v")
        text = value.text if value is not None and value.text else ""

        if cell.get("t") == "s":
            text = shared[int(text)]
        elif cell.get("t") == "inlineStr":
            text = "".join(node.text or "" for node in cell.iter(namespace + "t"))

        cells[column_index(cell.get("r")) if cell.get("r") else position] = text

    return [cells.get(index, "") for index in range(max(cells, default=-1) + 1)]


def column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference).group(0)

    return sum((ord(char) - 64) * 26 ** power for power, char in enumerate(reversed(letters))) - 1


def ckan_resource(package_url: str, year: int, formats: tuple[str, ...]) -> str | None:
    package = fetch_json(package_url, missing_ok=True)

    if not package or not package.get("success"):
        return None

    resources = package["result"].get("resources", [])

    for wanted in formats:
        for resource in resources:
            url = resource.get("url", "")
            label = f"{resource.get('name') or ''} {url}"

            if url.lower().endswith(f".{wanted}") and (str(year) in label or str(year) in package["result"].get("name", "")):
                return url

    return None


def datos_gob_items(dataset: str) -> list[dict]:
    return (fetch_json(DATOS_GOB_DATASET.format(id=dataset)) or {}).get("result", {}).get("items", [])


def distribution_urls(item: dict) -> list[str]:
    distribution = item.get("distribution") or []
    distribution = [distribution] if isinstance(distribution, dict) else distribution

    return [entry.get("accessURL", "") for entry in distribution if isinstance(entry, dict)]
