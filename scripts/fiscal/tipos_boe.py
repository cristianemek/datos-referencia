import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "build" / "cache" / "fiscal_tipos"
API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}/texto/bloque/{block_id}"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"


def download(url: str, accept: str = "*/*") -> bytes:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()
    except OSError as error:
        raise SystemExit(f"No se pudo descargar {url}: {error}") from error


def block(boe_id: str, block_id: str, fresh: bool = False) -> list[tuple[dict, list[str]]]:
    path = CACHE / "boe" / f"{boe_id}_{block_id}.xml"
    if fresh or not path.exists():
        data = download(API.format(boe_id=boe_id, block_id=block_id), "application/xml")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    root = ET.parse(path).getroot()
    return [(dict(version.attrib), ["".join(p.itertext()) for p in version.iter("p")])
            for version in root.iter("version")]
