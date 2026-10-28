import argparse
import csv
import io
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import shapefile
from pyproj import Geod, Transformer

REPO = Path(__file__).resolve().parents[2]
MUNICIPALITIES = REPO / "direcciones" / "municipios_es.csv"
OUTPUT = REPO / "direcciones" / "secciones_censales_es.csv"
CACHE = REPO / "build" / "cache" / "poblacion"
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"
SECTIONS_URL = "https://www.ine.es/prodyser/cartografia/seccionado_{year}.zip"
SOURCE_CRS = "EPSG:25830"
EQUAL_AREA_CRS = "EPSG:3035"
TARGET_CRS = "EPSG:4326"
HEADER = ["section_code", "municipality_code", "district_code", "latitude", "longitude", "area_km2"]
COORDINATE_DECIMALS = 6
AREA_DECIMALS = 4


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read()
        except OSError as error:
            if attempt == 4:
                raise RuntimeError(f"No se puede descargar {url}: {error}") from error

            time.sleep(2 ** attempt)

    raise RuntimeError(f"No se puede descargar {url}")


def check_projection(prj: str) -> None:
    if "UTM_Zone_30N" not in prj or "ETRS_1989" not in prj:
        raise ValueError(f"El seccionado no está en ETRS89 UTM 30N: {prj}")


def ring_moments(xs: list, ys: list) -> tuple[float, float, float]:
    x0, y0 = xs[0], ys[0]
    area = moment_x = moment_y = 0.0

    for index in range(len(xs) - 1):
        x1, y1 = xs[index] - x0, ys[index] - y0
        x2, y2 = xs[index + 1] - x0, ys[index + 1] - y0
        cross = x1 * y2 - x2 * y1
        area += cross
        moment_x += (x1 + x2) * cross
        moment_y += (y1 + y2) * cross

    return area / 2, moment_x / 6 + x0 * area / 2, moment_y / 6 + y0 * area / 2


def section_geometry(shape, to_lonlat: Transformer, to_equal_area: Transformer, geod: Geod) -> tuple:
    bounds = list(shape.parts) + [len(shape.points)]
    planar = moment_x = moment_y = geodesic = 0.0

    for start, end in zip(bounds, bounds[1:]):
        xs = [x for x, _ in shape.points[start:end]]
        ys = [y for _, y in shape.points[start:end]]
        lons, lats = to_lonlat.transform(xs, ys)
        geodesic += geod.polygon_area_perimeter(lons, lats)[0]
        ex, ey = to_equal_area.transform(lons, lats)
        area, mx, my = ring_moments(list(ex), list(ey))
        planar += area
        moment_x += mx
        moment_y += my

    if planar >= 0 or geodesic >= 0:
        raise ValueError("Orientación de anillos inesperada")

    longitude, latitude = to_equal_area.transform(moment_x / planar, moment_y / planar, direction="INVERSE")

    return latitude, longitude, -geodesic / 1_000_000


def read_municipalities(path: Path) -> set:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["municipality_code"] for row in csv.DictReader(handle)}


def build_rows(folder: Path) -> list[dict]:
    shp = next(folder.rglob("*.shp"))
    check_projection(shp.with_suffix(".prj").read_text(encoding="utf-8", errors="replace"))
    to_lonlat = Transformer.from_crs(SOURCE_CRS, TARGET_CRS, always_xy=True)
    to_equal_area = Transformer.from_crs(TARGET_CRS, EQUAL_AREA_CRS, always_xy=True)
    geod = Geod(ellps="GRS80")
    rows = []

    with shapefile.Reader(str(shp.with_suffix("")), encoding="utf-8") as reader:
        for item in reader.iterShapeRecords():
            record = item.record.as_dict()
            code = record["CUSEC"]

            if item.shape.shapeType != shapefile.POLYGON or not item.shape.points:
                raise ValueError(f"Sección {code} sin geometría poligonal")

            if code != record["CUMUN"] + record["CDIS"] + record["CSEC"] or record["CUDIS"] != record["CUMUN"] + record["CDIS"]:
                raise ValueError(f"Códigos incoherentes en la sección {code}")

            try:
                latitude, longitude, area = section_geometry(item.shape, to_lonlat, to_equal_area, geod)
            except ValueError as error:
                raise ValueError(f"Sección {code}: {error}") from error

            rows.append({
                "section_code": code,
                "municipality_code": record["CUMUN"],
                "district_code": record["CUDIS"],
                "latitude": f"{latitude:.{COORDINATE_DECIMALS}f}",
                "longitude": f"{longitude:.{COORDINATE_DECIMALS}f}",
                "area_km2": f"{area:.{AREA_DECIMALS}f}",
            })

    return sorted(rows, key=lambda row: row["section_code"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--municipalities", type=Path, default=MUNICIPALITIES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    municipalities = read_municipalities(args.municipalities)
    CACHE.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=CACHE) as workdir:
        zipfile.ZipFile(io.BytesIO(fetch(SECTIONS_URL.format(year=args.year)))).extractall(workdir)
        rows = build_rows(Path(workdir))

    codes = [row["section_code"] for row in rows]

    if len(set(codes)) != len(codes):
        raise ValueError("Hay códigos de sección repetidos")

    present = {row["municipality_code"] for row in rows}

    if present - municipalities:
        raise ValueError(f"Municipios del seccionado que no están en {args.municipalities.name}: {sorted(present - municipalities)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    total = sum(float(row["area_km2"]) for row in rows)
    print(f"Secciones: {len(rows)} en {len(present)} municipios; superficie total {total:,.0f} km²")
    print(f"Municipios sin secciones: {sorted(municipalities - present)}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        sys.exit(str(error))
