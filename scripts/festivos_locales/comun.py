import calendar
import datetime
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "calendario" / "festivos_locales_es.csv"
REGIONAL = REPO / "calendario" / "festivos_es.csv"
MUNICIPALITIES = REPO / "direcciones" / "municipios_es.csv"
PROVINCES = REPO / "direcciones" / "provincias_es.csv"
ENTITIES = REPO / "direcciones" / "entidades_locales_es.csv"
POSTAL = REPO / "direcciones" / "codigos_postales_es.csv"
HEADER = ["date", "municipality_code", "locality", "name", "ccaa_code"]

ARAN = {"25025", "25032", "25046", "25059", "25064", "25081", "25120", "25243", "25247"}
MONTHS = {
    "enero": 1, "gener": 1, "febrero": 2, "febrer": 2, "marzo": 3, "marc": 3, "abril": 4, "mayo": 5, "maig": 5,
    "junio": 6, "juny": 6, "julio": 7, "juliol": 7, "agosto": 8, "agost": 8, "septiembre": 9, "setiembre": 9,
    "setembre": 9, "octubre": 10, "noviembre": 11, "novembre": 11, "diciembre": 12, "desembre": 12,
}
WEEKDAYS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}
ORDINALS = {"primer": 1, "primero": 1, "segundo": 2, "tercer": 3, "tercero": 3, "cuarto": 4, "quinto": 5, "ultimo": -1}
EASTER_OFFSETS = {
    "jueves de carnaval": -52, "viernes de carnaval": -51, "lunes de carnaval": -48, "martes de carnaval": -47,
    "lunes de pascua": 1, "festividad de la ascension": 39, "ascension": 39, "lunes de pentecostes": 50,
    "segundo dia de pentecostes": 50, "corpus christi": 60,
}
ARTICLES = {"el", "la", "los", "las", "els", "l", "lo", "les", "es", "sa", "ses", "s", "o", "a", "os", "as", "na"}
STOPWORDS = ARTICLES | {"de", "del", "d", "y", "i", "e"}
SMALL_WORDS = {"de", "del", "la", "las", "el", "los", "y", "e", "i", "en", "al", "a", "o"}
SPELLING_VARIANTS = {frozenset(pair) for pair in ("jg", "bv", "yi", "zc", "sz", "xj", "kc")}
AFFIXES = ("prefijo", "sufijo", "localidad del municipio", "variante ortográfica")
GENERIC_PREFIXES = {"villa", "valle", "val", "cendea", "concejo", "real", "sitio"}
GENERIC_NAMES = {"", "fiesta local", "festiu local", "festa local", "fiesta", "festivo", "festivo local", "nan", "null"}


class FormatChanged(Exception):
    pass


@dataclass(frozen=True)
class Holiday:
    date: str
    municipality_code: str
    locality: str
    name: str
    ccaa_code: str

    def row(self) -> list[str]:
        return [self.date, self.municipality_code, self.locality, self.name, self.ccaa_code]


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("’", "'").replace("·", "")).lower()
    text = "".join(char for char in text if not unicodedata.combining(char))

    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def loose(form: str) -> str:
    tokens = form.split()

    return " ".join([token for token in tokens[:-1] if token not in STOPWORDS] + tokens[-1:])


def spelling_variant(first: str, second: str) -> bool:
    if len(first) == len(second):
        differences = [frozenset(pair) for pair in zip(first, second) if pair[0] != pair[1]]

        return len(differences) == 1 and differences[0] in SPELLING_VARIANTS

    shorter, longer = sorted((first, second), key=len)

    return len(longer) == len(shorter) + 1 and any(
        longer[index] == "h" and longer[:index] + longer[index + 1:] == shorter for index in range(len(longer))
    )


def single_forms(name: str) -> set[str]:
    text = " ".join(name.split())
    forms = {text}

    for pattern in (r"^(.*?)\s*\(([^()]+)\)$", r"^(.*?),\s*([^,]+)$"):
        match = re.match(pattern, text)

        if match and fold(match.group(2)) in ARTICLES:
            forms.add(f"{match.group(2)} {match.group(1)}")

    return {fold(form) for form in forms if fold(form)}


def name_parts(name: str) -> list[str]:
    return [part for part in re.split(r"\s*/\s*", " ".join(name.split())) if part]


def name_forms(name: str) -> set[str]:
    return set().union(single_forms(name), *(single_forms(part) for part in name_parts(name)))


def display_name(name: str) -> str:
    text = " ".join(name.split())

    for pattern in (r"^(.*?)\s*\(([^()]+)\)$", r"^(.*?),\s*([^,]+)$"):
        match = re.match(pattern, text)

        if match and fold(match.group(2)) in ARTICLES:
            article = match.group(2).strip().capitalize()

            return f"{article}{'' if article.endswith(chr(39)) else ' '}{match.group(1)}"

    return text


def tidy(text: str) -> str:
    text = " ".join(text.replace(chr(0xA0), " ").split())

    if not text or text != text.upper() or not any(char.isalpha() for char in text):
        return text

    words = re.sub(r"[^\W\d_]+", lambda match: match.group(0).capitalize(), text.lower()).split(" ")
    output = []

    for index, word in enumerate(words):
        previous = output[-1] if output else ""
        joined = index > 0 and previous not in {"-", "–", "/"} and not previous.endswith("(")
        output.append(word.lower() if joined and word.lower() in SMALL_WORDS else word)

    return " ".join(output)


def clean_name(text: str) -> str:
    name = tidy(text)

    try:
        is_date = text_date(name, 2000) is not None
    except ValueError:
        is_date = True

    if fold(name) in GENERIC_NAMES or is_date:
        return ""

    return name


def easter(year: int) -> datetime.date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (2 * e + 2 * i - h - k + 32) % 7
    m = (a + 11 * h + 19 * l) // 433
    month = (h + l - 7 * m + 90) // 25

    return datetime.date(year, month, (h + l - 7 * m + 33 * month + 19) % 32)


def nth_weekday(year: int, month: int, weekday: int, nth: int) -> datetime.date:
    if nth > 0:
        first = datetime.date(year, month, 1)
        day = first + datetime.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (nth - 1))

        if day.month != month:
            raise ValueError("ordinal fuera del mes")

        return day

    last = datetime.date(year, month, calendar.monthrange(year, month)[1])

    return last - datetime.timedelta(days=(last.weekday() - weekday) % 7)


def movable_date(text: str, year: int) -> datetime.date | None:
    folded = fold(text)
    days, ordinals, months = "|".join(WEEKDAYS), "|".join(ORDINALS), "|".join(MONTHS)

    if folded in EASTER_OFFSETS:
        return easter(year) + datetime.timedelta(days=EASTER_OFFSETS[folded])

    relative = re.fullmatch(rf"({days}) (siguiente|posterior|anterior) al? ({ordinals}) ({days}) de ({months})", folded)

    if relative:
        anchor = nth_weekday(year, MONTHS[relative.group(5)], WEEKDAYS[relative.group(4)], ORDINALS[relative.group(3)])
        target = WEEKDAYS[relative.group(1)]
        shift = (target - anchor.weekday()) % 7 or 7

        return anchor + datetime.timedelta(days=shift if relative.group(2) != "anterior" else shift - 7)

    plain = re.fullmatch(rf"({ordinals}) ({days}) de ({months})", folded)

    if plain:
        return nth_weekday(year, MONTHS[plain.group(3)], WEEKDAYS[plain.group(2)], ORDINALS[plain.group(1)])

    return None


def numeric_date(value: str) -> datetime.date | None:
    value = value.strip()
    patterns = [
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ].*)?$", (1, 2, 3)),
        (r"^(\d{4})/(\d{1,2})/(\d{1,2})$", (1, 2, 3)),
        (r"^(\d{4})(\d{2})(\d{2})$", (1, 2, 3)),
        (r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})$", (3, 2, 1)),
    ]

    for pattern, (y, m, d) in patterns:
        match = re.match(pattern, value)

        if match:
            year = int(match.group(y))

            return datetime.date(year + 2000 if year < 100 else year, int(match.group(m)), int(match.group(d)))

    if re.fullmatch(r"\d{5}(?:\.0+)?", value):
        return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(value)))

    return None


def text_date(value: str, year: int) -> datetime.date | None:
    match = re.match(r"^(\d{1,2}) (?:de |d )?([a-z]+)$", fold(value))
    month = MONTHS.get(match.group(2)) if match else None

    return datetime.date(year, month, int(match.group(1))) if month else None


def parse_date(value: str, year: int, source: str) -> datetime.date | None:
    try:
        day = numeric_date(value) or text_date(value, year)
    except ValueError:
        return None

    if day is None:
        raise FormatChanged(f"{source}: formato de fecha desconocido «{value}»")

    return day
