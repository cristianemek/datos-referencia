import json
import pickle
from pathlib import Path

import numpy as np

from common import RAW
from http_client import Session

DIR = RAW / "ign"
OUT = DIR / "municipios_ign.pkl"
URL = "https://www.ign.es/wfs-inspire/unidades-administrativas"


def fetch(s: Session, prov: str) -> Path:
    path = DIR / f"prov_{prov}.json"
    if path.exists() and path.stat().st_size > 1000:
        return path
    filt = (
        '<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" '
        'xmlns:au="http://inspire.ec.europa.eu/schemas/au/4.0">'
        '<fes:PropertyIsLike wildCard="*" singleChar="?" escapeChar="!">'
        "<fes:ValueReference>au:nationalCode</fes:ValueReference>"
        f"<fes:Literal>34??{prov}*</fes:Literal></fes:PropertyIsLike></fes:Filter>"
    )
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "au:AdministrativeUnit",
        "outputFormat": "application/geo+json", "filter": filt,
    }
    content = s.request("GET", URL, params=params).content
    if len(content) <= 1000:
        raise SystemExit(f"No se pudo descargar la provincia {prov}")
    path.write_bytes(content)
    return path


def parse(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    units = []
    for feat in data["features"]:
        props = feat["properties"]
        if props["nationalLevelName"]["LocalisedCharacterString"] != "Municipio":
            continue
        code = props["nationalCode"]
        name = props["name"]["GeographicalName"]["spelling"]["SpellingOfName"]["text"]
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = [[np.asarray(r, dtype=np.float64) for r in poly] for poly in polys]
        allpts = np.concatenate([r for poly in rings for r in poly])
        bbox = (allpts[:, 0].min(), allpts[:, 1].min(), allpts[:, 0].max(), allpts[:, 1].max())
        units.append({"natcode": code, "ine": code[-5:], "name": name, "polys": rings, "bbox": bbox})
    return units


def main() -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    s = Session()
    allunits = []
    for prov in (f"{i:02d}" for i in range(1, 53)):
        path = fetch(s, prov)
        units = parse(path)
        print(prov, len(units), flush=True)
        allunits.extend(units)
        path.unlink()
    with OUT.open("wb") as fh:
        pickle.dump(allunits, fh)
    print("total", len(allunits))


if __name__ == "__main__":
    main()
