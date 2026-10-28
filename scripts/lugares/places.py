import collections
import difflib
import io
import re
import zipfile

from common import RAW, name_variants

NOMENCLATOR = RAW / "nomenclator_2025.zip"
MEMBER = "Nomdef2025_sex.txt"
LINE = re.compile(r"^(\d{11})(.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")


def load_entities(municipios: dict) -> list:
    with zipfile.ZipFile(NOMENCLATOR) as zf, zf.open(MEMBER) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8")
        entities = []
        for line in text:
            m = LINE.match(line.rstrip("\r\n"))
            if not m:
                continue
            code, name = m.group(1), m.group(2).strip()
            if code[5:] == "000000" or name.startswith("*") or code[9:] == "99":
                continue
            muni = code[:5]
            if muni in municipios:
                entities.append((muni, name, int(m.group(3))))
    return entities


def similarity(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    small = a if len(sa) <= len(sb) else b
    if (sa <= sb or sb <= sa) and a.split()[:1] == b.split()[:1] and len(small) >= 5:
        return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()


class PlaceIndex:
    def __init__(self, municipios: dict, cps: list = None) -> None:
        self.municipios = municipios
        self.muni = collections.defaultdict(set)
        self.entity = collections.defaultdict(set)
        self.locality = collections.defaultdict(set)
        self.keys_by_muni = collections.defaultdict(set)
        for code, row in municipios.items():
            for key in name_variants(row["municipality"]):
                self.muni[key].add(code)
                self.keys_by_muni[code].add(key)
        for muni, name, _ in load_entities(municipios):
            for key in name_variants(name):
                self.entity[key].add(muni)
                self.keys_by_muni[muni].add(key)
        for row in cps or []:
            for key in name_variants(row["locality"]):
                self.locality[key].add(row["municipality_code"])

    @staticmethod
    def _filter(codes: set, provinces) -> set:
        return {c for c in codes if provinces is None or c[:2] in provinces}

    def match(self, names, provinces=None) -> tuple:
        keys = set()
        for n in names:
            keys |= name_variants(n)
        for label, table in (("municipio", self.muni), ("entidad", self.entity), ("localidad", self.locality)):
            found = set()
            for k in keys:
                found |= self._filter(table.get(k, set()), provinces)
            if found:
                return found, label
        return set(), ""

    def fuzzy(self, names, candidates, threshold: float, margin: float) -> tuple:
        keys = set()
        for n in names:
            keys |= name_variants(n)
        scores = []
        for code in candidates:
            best = max((similarity(k, c) for k in keys for c in self.keys_by_muni.get(code, ())), default=0.0)
            scores.append((best, code))
        scores.sort(reverse=True)
        if not scores or scores[0][0] < threshold:
            return "", 0.0
        if len(scores) > 1 and scores[0][0] - scores[1][0] < margin:
            return "", 0.0
        return scores[0][1], scores[0][0]
