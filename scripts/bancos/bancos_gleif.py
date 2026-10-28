import json
import urllib.error
import urllib.parse
import urllib.request
from typing import NamedTuple, Optional

API_URL = "https://api.gleif.org/api/v1/lei-records"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
BATCH_SIZE = 100


class LeiRecord(NamedTuple):
    lei: str
    name: str
    country: str
    status: str
    category: str


def get(url: str, params: Optional[dict] = None) -> Optional[dict]:
    full = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    request = urllib.request.Request(full, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.api+json"})

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f"La API de GLEIF respondió {error.code} a {full}") from error
    except OSError as error:
        raise RuntimeError(f"No se pudo consultar la API de GLEIF ({full}): {error}") from error


def to_record(item: dict) -> LeiRecord:
    attributes = item["attributes"]
    entity = attributes["entity"]
    return LeiRecord(
        attributes["lei"], entity["legalName"]["name"], entity["legalAddress"]["country"], entity["status"], entity["category"] or "",
    )


def records(leis: list) -> dict:
    unique = sorted(set(leis))
    found = {}

    for start in range(0, len(unique), BATCH_SIZE):
        chunk = unique[start:start + BATCH_SIZE]
        payload = get(API_URL, {"filter[lei]": ",".join(chunk), "page[size]": str(BATCH_SIZE)}) or {}
        found = {**found, **{record.lei: record for record in map(to_record, payload.get("data", ()))}}

    return found


def search(name: str, country: str) -> LeiRecord:
    payload = get(API_URL, {"filter[entity.legalName]": name, "filter[entity.legalAddress.country]": country}) or {}
    matches = [
        record for record in map(to_record, payload.get("data", ()))
        if record.name.casefold() == name.casefold() and record.country == country and record.status == "ACTIVE"
    ]

    if len(matches) != 1:
        raise ValueError(f"GLEIF no devuelve un único LEI activo para {name!r} ({country}): {len(matches)}")

    return matches[0]


def related(lei: str, relation: str) -> Optional[LeiRecord]:
    payload = get(f"{API_URL}/{lei}/{relation}")
    return to_record(payload["data"]) if payload and payload.get("data") else None


def publish_date() -> str:
    payload = get(API_URL, {"page[size]": "1"}) or {}
    return payload.get("meta", {}).get("goldenCopy", {}).get("publishDate", "")[:10]
