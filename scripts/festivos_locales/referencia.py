import csv
import datetime
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from comun import (
    ARAN, ENTITIES, GENERIC_PREFIXES, MUNICIPALITIES, POSTAL, PROVINCES, REGIONAL, Holiday,
    display_name, fold, loose, name_forms, name_parts, parse_date, single_forms, spelling_variant, tidy,
)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


class Reference:
    def __init__(self) -> None:
        self.municipalities = {row["municipality_code"]: row for row in load_csv(MUNICIPALITIES)}
        provinces = load_csv(PROVINCES)
        self.province_ccaa = {row["province_code"]: row["ccaa_code"] for row in provinces}
        self.province_names = {form: row["province_code"] for row in provinces for form in name_forms(row["province"])}
        self.by_province = defaultdict(list)
        self.exact, self.loose, self.minor, self.places = (defaultdict(set) for _ in range(4))
        self.forms = {}
        self.regional = defaultdict(list)

        for code, row in self.municipalities.items():
            self.by_province[row["province_code"]].append(code)
            self.forms[code] = name_forms(row["municipality"])

            for form in self.forms[code]:
                self.exact[(row["province_code"], form)].add(code)
                self.loose[(row["province_code"], loose(form))].add(code)

        for row in load_csv(ENTITIES):
            if row["type"] == "entidad_local_menor" and row["municipality_code"] in self.municipalities:
                self.index_place(self.minor, row["province_code"], row["municipality_code"], row["name"])

        for row in load_csv(POSTAL) if POSTAL.exists() else []:
            if row["municipality_code"] in self.municipalities and row["locality"]:
                self.index_place(self.places, row["province_code"], row["municipality_code"], row["locality"])

        for row in load_csv(REGIONAL) if REGIONAL.exists() else []:
            self.regional[(row["date"][:4], row["ccaa_code"])].append(row)

    @staticmethod
    def index_place(index: dict, province: str, code: str, name: str) -> None:
        for form in name_forms(name):
            for key in {form, loose(form)}:
                index[(province, key)].add((code, display_name(name)))

    def ccaa(self, code: str) -> str:
        return self.province_ccaa.get(code[:2], "")

    def province(self, name: str) -> str | None:
        return next((self.province_names[form] for form in name_forms(name) if form in self.province_names), None)

    def has_regional(self, year: int, ccaa: str) -> bool:
        return bool(self.regional.get((str(year), ccaa)))

    def regional_dates(self, year: int, ccaa: str, code: str) -> set[str]:
        island = self.municipalities.get(code, {}).get("island_code", "")
        dates = set()

        for row in self.regional.get((str(year), ccaa), []):
            if row["island_code"] and row["island_code"] != island:
                continue

            if row["territory"] == "Arán" and code not in ARAN:
                continue

            if row["territory"] == "Cataluña excepto Arán" and code in ARAN:
                continue

            dates.add(row["date"])

        return dates

    def lookup(self, index: dict, provinces: list[str], name: str, transform) -> set:
        def collect(text: str) -> set:
            keys = {transform(form) for form in single_forms(text)}

            return {item for province in provinces for key in keys for item in index.get((province, key), set())}

        found = collect(name)
        parts = name_parts(name)

        if len(parts) > 1:
            found |= set.intersection(*(collect(part) for part in parts))

        return found

    def municipality(self, provinces: list[str], name: str, affixes: tuple[str, ...] = ()) -> tuple[str | None, str]:
        for method, index, transform in (("exacto", self.exact, str), ("aproximado", self.loose, loose)):
            found = self.lookup(index, provinces, name, transform)

            if len(found) == 1:
                return found.pop(), method

            if len(found) > 1:
                return None, f"ambiguo ({', '.join(sorted(found))})"

        if affixes:
            return self.affix(provinces, name, affixes)

        return None, "sin coincidencia"

    def affix(self, provinces: list[str], name: str, affixes: tuple[str, ...]) -> tuple[str | None, str]:
        found = defaultdict(set)

        for form in single_forms(name):
            tokens = loose(form).split()

            for province in provinces:
                for code in self.by_province[province]:
                    for other in (loose(item).split() for item in self.forms[code]):
                        short, long_ = sorted((tokens, other), key=len)

                        if len("".join(short)) < 4 or short == long_:
                            continue

                        if long_[:len(short)] == short:
                            found["prefijo"].add(code)
                        elif long_[-len(short):] == short and long_ is tokens:
                            found["localidad del municipio"].add(code)
                        elif long_[-len(short):] == short and set(long_[:-len(short)]) <= GENERIC_PREFIXES:
                            found["sufijo"].add(code)
                        elif len(" ".join(tokens)) >= 8 and spelling_variant(" ".join(tokens), " ".join(other)):
                            found["variante ortográfica"].add(code)

        for method in affixes:
            if len(found[method]) == 1:
                return next(iter(found[method])), method

            if found[method]:
                return None, f"ambiguo ({', '.join(sorted(found[method]))})"

        return None, "sin coincidencia"

    def locality(self, provinces: list[str], name: str, parent: str | None = None) -> tuple[str, str, str] | None:
        forms = name_forms(name)

        for method, index in (("entidad local menor", self.minor), ("localidad postal", self.places)):
            found = {
                item for transform in (str, loose) for item in self.lookup(index, provinces, name, transform)
                if parent is None or item[0] == parent
            }

            if len({code for code, _ in found}) == 1:
                code, label = sorted(found)[0]

                return code, "" if forms & self.forms[code] else label, method

        return None


@dataclass
class Context:
    reference: Reference
    year: int
    ccaa: str
    notes: list[str] = field(default_factory=list)
    matches: Counter = field(default_factory=Counter)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def holiday(self, day: datetime.date, code: str, locality: str, name: str) -> Holiday:
        return Holiday(day.isoformat(), code, locality, name, self.ccaa)

    def date(self, value: str, source: str, where: str) -> datetime.date | None:
        day = parse_date(value, self.year, source)

        if day is None:
            self.note(f"fecha imposible: {where} «{value}»")

        return day

    def describe(self, code: str) -> str:
        return f"{code} {self.reference.municipalities[code]['municipality']}"

    def match_municipality(self, provinces: list[str], name: str, affixes: tuple[str, ...] = ()) -> str | None:
        code, method = self.reference.municipality(provinces, name, affixes)
        self.matches[method if code else "sin cruzar"] += 1

        if code and method != "exacto":
            self.note(f"cruce {method}: «{name}» → {self.describe(code)}")

        return code

    def match_place(self, provinces: list[str], name: str, parent: str | None = None, affixes: tuple[str, ...] = ()) -> tuple[str, str] | None:
        reference = self.reference

        if parent is None:
            code, method = reference.municipality(provinces, name)

            if code:
                self.matches[method] += 1

                if method != "exacto":
                    self.note(f"cruce {method}: «{name}» → {self.describe(code)}")

                return code, ""

        found = reference.locality(provinces, name, parent)

        if found:
            self.matches[found[2]] += 1
            self.note(f"cruce por {found[2]}: «{name}» → {self.describe(found[0])} / {found[1] or '(municipio)'}")
            return found[0], found[1]

        if parent:
            self.matches["municipio indicado"] += 1
            return parent, display_name(tidy(name))

        if affixes:
            code, method = reference.municipality(provinces, name, affixes)

            if code:
                self.matches[method] += 1
                self.note(f"cruce por {method}: «{name}» → {self.describe(code)}")
                return code, display_name(tidy(name)) if method == "localidad del municipio" else ""

        self.matches["sin cruzar"] += 1
        self.note(f"sin cruzar: «{name}»")

        return None


def split_label(label: str, forms: set[str]) -> str:
    for match in re.finditer(r"\s*[-–]\s*", label):
        left, right = label[:match.start()], label[match.end():]

        if right and (name_forms(left) | {loose(form) for form in name_forms(left)}) & (forms | {loose(form) for form in forms}):
            return right

    return label


def clean_locality(text: str) -> str:
    return display_name(tidy(re.sub(r"\(\s*anejo\s*\)", "", text, flags=re.I).strip(" -–")))


def assign_localities(groups: dict[str, list], forms: set[str]) -> dict[str, str]:
    labels = list(dict.fromkeys(groups))

    if len(labels) == 1:
        return {labels[0]: ""}

    return {label: "" if name_forms(label) & forms else clean_locality(split_label(label, forms)) for label in labels}


def merge_labels(groups: dict[str, list]) -> dict[str, list]:
    merged = {}

    for label, items in groups.items():
        key = next((existing for existing in merged if fold(existing) == fold(label)), label)
        merged[key] = merged.get(key, []) + items

    return merged
