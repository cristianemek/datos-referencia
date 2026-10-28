import argparse
import datetime
import html
import json
import re
from pathlib import Path

from common import RAW
from http_client import Response, Session

LOG = RAW / "descargas.tsv"
CNH = "https://www.sanidad.gob.es/estadEstudios/estadisticas/sisInfSanSNS/ofertaRecursos/hospitales/docs/CNH_2025.xlsx"
REGCESS = "https://regcesslm.sanidad.gob.es/recesAdminWeb/lm/GetExcelListadoMensual?tipoListado=C2"
INE_NOMBRES = "https://www.ine.es/daco/daco42/nombyapel/nombres_por_edad_media.xlsx"
IDEE = "https://api-features.idee.es/collections/{}/items?f=json&limit=1000"
OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
UNLOCODE = "https://unlocode.unece.org/downloads/unlocode-latest.zip"
TRLPEMM = "https://www.boe.es/buscar/act.php?id=BOE-A-2011-16467"
NOMENCLATOR = "https://www.ine.es/nomen2/Descarga"
EDU = "https://www.educacion.gob.es/centros"
RUCT = "https://www.educacion.gob.es/ruct"
EDU_FORM = {
    "nivel": "0", "idComunidad": "todo", "idProvincia": "", "naturaleza": "0", "concertado": "0",
    "familia": "0", "ensenanza": "0", "modalidad": "0", "tipoCentro": "0", "provincial": "",
    "comarca": "", "pais": "", "localidad": "0", "codCentro": "", "nombreCentro": "",
    "denominacion": "0", "ensenanzaFP": "",
}
RUCT_LINK = r'universidad\.action\?codigoUniversidad=(\d+)&amp;actual=universidades">([^<]+)<'


def log(name: str, url: str, resp: Response) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    modified = resp.headers.get("Last-Modified", "") or ""
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{name}\t{url}\t{stamp}\t{modified}\t{len(resp.content)}\n")


def save(s: Session, name: str, url: str, path: Path, force: bool, method: str = "GET", data: dict = None) -> None:
    if path.exists() and path.stat().st_size > 0 and not force:
        return
    resp = s.request(method, url, data=data)
    if not resp.content:
        raise SystemExit(f"Descarga vacía: {url}")
    path.write_bytes(resp.content)
    log(name, url, resp)
    print(f"{name}: {len(resp.content)} bytes")


def idee(s: Session, collection: str, force: bool) -> None:
    path = RAW / f"{collection}.json"
    if path.exists() and not force:
        return
    url, features, data, resp = IDEE.format(collection), [], {}, None
    while url:
        resp = s.request("GET", url)
        data = json.loads(resp.content)
        features.extend(data["features"])
        url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "next"), None)
    if len(features) != data.get("numberMatched", len(features)):
        raise SystemExit(f"{collection}: {len(features)} de {data.get('numberMatched')}")
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
    log(collection, IDEE.format(collection), resp)
    print(f"{collection}: {len(features)} elementos")


def educacion(force: bool) -> None:
    path = RAW / "centros_educativos.xls"
    if path.exists() and not force:
        return
    s = Session()
    s.request("GET", f"{EDU}/")
    s.request("POST", f"{EDU}/verBuscadorComunidad", data={"idComunidad": "todo"})
    resp = s.request("POST", f"{EDU}/exportarListadoCentrosExcel", data=EDU_FORM)
    if not resp.content.startswith(b"\xd0\xcf\x11\xe0"):
        raise SystemExit("La exportación del Registro Estatal de Centros Docentes no es un fichero Excel")
    path.write_bytes(resp.content)
    log("centros_educativos", f"{EDU}/exportarListadoCentrosExcel", resp)
    print(f"centros_educativos: {len(resp.content)} bytes")


def ruct_listing(s: Session) -> dict:
    s.request("GET", f"{RUCT}/consultauniversidades?actual=universidades")
    resp = s.request("POST", f"{RUCT}/listauniversidades.action?actual=universidades",
                     data={"consulta": "1", "cccaa": "", "codigoUniversidad": "", "tipo_univ": ""})
    text = resp.content.decode("latin-1")
    total = int(re.search(r"(\d+) registros encontrados", text).group(1))
    param = re.search(r"(d-\d+-p)=\d+", text).group(1)
    entries = dict(re.findall(RUCT_LINK, text))
    page = 2
    while len(entries) < total:
        url = f"{RUCT}/listauniversidades?actual=universidades&cccaa=&codigoUniversidad=&consulta=1&{param}={page}"
        found = dict(re.findall(RUCT_LINK, s.request("GET", url).content.decode("latin-1")))
        if not found:
            break
        entries.update(found)
        page += 1
    if len(entries) != total:
        raise SystemExit(f"RUCT: {len(entries)} de {total} universidades")
    log("ruct_lista", f"{RUCT}/listauniversidades.action", resp)
    print(f"ruct: {total} entradas")
    return {k: html.unescape(v).strip() for k, v in entries.items()}


def ruct(force: bool) -> None:
    folder = RAW / "ruct"
    folder.mkdir(parents=True, exist_ok=True)
    listing = folder / "lista.json"
    s = Session()
    if force or not listing.exists():
        listing.write_text(json.dumps(ruct_listing(s), ensure_ascii=False, indent=1), encoding="utf-8")
    for code in json.loads(listing.read_text(encoding="utf-8")):
        path = folder / f"universidad_{code}.html"
        if path.exists() and not force:
            continue
        url = f"{RUCT}/universidad.action?codigoUniversidad={code}&actual=universidades"
        path.write_bytes(s.request("GET", url).content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    s = Session()
    save(s, "cnh", CNH, RAW / "CNH_2025.xlsx", args.force)
    save(s, "regcess_c2", REGCESS, RAW / "regcess_C2.xlsx", args.force)
    save(s, "ine_nombres", INE_NOMBRES, RAW / "ine_nombres.xlsx", args.force)
    idee(s, "aerodromenode", args.force)
    idee(s, "portnode", args.force)
    save(s, "ourairports", OURAIRPORTS, RAW / "ourairports_airports.csv", args.force)
    save(s, "unlocode", UNLOCODE, RAW / "unlocode-latest.zip", args.force)
    save(s, "trlpemm", TRLPEMM, RAW / "boe_trlpemm.html", args.force)
    save(s, "nomenclator", NOMENCLATOR, RAW / "nomenclator_2025.zip", args.force, method="POST",
         data={"anioNacional": "2025"})
    educacion(args.force)
    ruct(args.force)


if __name__ == "__main__":
    main()
