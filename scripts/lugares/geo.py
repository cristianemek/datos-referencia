import math
import pickle
from pathlib import Path

import numpy as np

from common import RAW

PKL = RAW / "ign" / "municipios_ign.pkl"
EARTH_KM = 6371.0


class MunicipalityIndex:
    def __init__(self, path: Path = PKL) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Falta {path}: ejecuta scripts/ign_download.py")
        with path.open("rb") as fh:
            self.units = pickle.load(fh)
        self.bboxes = np.array([u["bbox"] for u in self.units])

    @staticmethod
    def _in_ring(x: float, y: float, ring: np.ndarray) -> bool:
        xs, ys = ring[:, 0], ring[:, 1]
        xj, yj = np.roll(xs, 1), np.roll(ys, 1)
        cond = (ys > y) != (yj > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xj - xs) * (y - ys) / (yj - ys) + xs
        return bool(np.count_nonzero(cond & (x < xint)) % 2)

    def _in_unit(self, x: float, y: float, unit: dict) -> bool:
        for poly in unit["polys"]:
            if self._in_ring(x, y, poly[0]) and not any(self._in_ring(x, y, h) for h in poly[1:]):
                return True
        return False

    def _candidates(self, lon: float, lat: float, pad: float = 0.0):
        b = self.bboxes
        mask = (b[:, 0] - pad <= lon) & (b[:, 2] + pad >= lon) & (b[:, 1] - pad <= lat) & (b[:, 3] + pad >= lat)
        return np.nonzero(mask)[0]

    def locate(self, lon: float, lat: float) -> list:
        return [self.units[i] for i in self._candidates(lon, lat) if self._in_unit(lon, lat, self.units[i])]

    @staticmethod
    def _dist_to_ring_km(lon: float, lat: float, ring: np.ndarray) -> float:
        kx = math.cos(math.radians(lat)) * math.pi / 180 * EARTH_KM
        ky = math.pi / 180 * EARTH_KM
        px, py = (ring[:, 0] - lon) * kx, (ring[:, 1] - lat) * ky
        ax, ay, bx, by = px[:-1], py[:-1], px[1:], py[1:]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(seg2 > 0, -(ax * dx + ay * dy) / seg2, 0.0)
        t = np.clip(t, 0, 1)
        cx, cy = ax + t * dx, ay + t * dy
        return float(np.sqrt(cx * cx + cy * cy).min())

    def unit_distance_km(self, lon: float, lat: float, unit: dict) -> float:
        if self._in_unit(lon, lat, unit):
            return 0.0
        return min(self._dist_to_ring_km(lon, lat, r) for poly in unit["polys"] for r in poly)

    def nearest(self, lon: float, lat: float, max_km: float = 5.0) -> tuple:
        best, best_d = None, float("inf")
        for i in self._candidates(lon, lat, max_km / 80.0):
            unit = self.units[i]
            d = min(self._dist_to_ring_km(lon, lat, poly[0]) for poly in unit["polys"])
            if d < best_d:
                best, best_d = unit, d
        if best is None or best_d > max_km:
            return None, None
        return best, best_d

    def near(self, lon: float, lat: float, km: float) -> list:
        found = []
        for i in self._candidates(lon, lat, km / 80.0):
            unit = self.units[i]
            d = self.unit_distance_km(lon, lat, unit)
            if d <= km:
                found.append((unit, d))
        return sorted(found, key=lambda x: x[1])

    def by_ine(self) -> dict:
        return {u["ine"]: u for u in self.units}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


def assign(idx: MunicipalityIndex, municipios: dict, lon: float, lat: float, coast_km: float = 0.0) -> tuple:
    units = idx.locate(lon, lat)
    method = "dentro"
    if not units and coast_km > 0:
        unit, _ = idx.nearest(lon, lat, max_km=coast_km)
        units = [unit] if unit else []
        method = "costa"
    if not units:
        return "", "", "fuera"
    unit = units[0]
    prov = unit["natcode"][4:6]
    muni = unit["ine"] if unit["ine"] in municipios else ""
    return prov, muni, method if muni else "condominio"
