import re

import openpyxl

from common import RAW, norm

NAMES_FILE = RAW / "ine_nombres.xlsx"
MIN_FREQ = 500
TITLES = {"dr", "dra", "doctor", "doctora", "don", "dona", "sr", "sra"}
PARTICLES = {"de", "del", "la", "las", "los", "y", "i"}
NOT_NAMES = {"el", "la", "los", "las", "san", "santa", "sant", "santo", "virgen", "nuestra", "senora", "cruz", "nino", "jesus"}
PRACTICE = re.compile(r"^(consulta|consultas|clinica|clinic|gabinete|despacho|consultorio medico|centro medico)\s+")


def load_given_names() -> set:
    wb = openpyxl.load_workbook(NAMES_FILE, read_only=True)
    names = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            if isinstance(row[0], int) and isinstance(row[2], (int, float)) and row[2] >= MIN_FREQ:
                key = norm(str(row[1]))
                if key and " " not in key and key not in NOT_NAMES:
                    names.add(key)
    return names


def looks_like_person(name: str, given: set, places: set) -> bool:
    text = PRACTICE.sub("", norm(name))
    words = text.split()
    titled = bool(words) and words[0] in TITLES
    core = [w for w in (words[1:] if titled else words) if w not in PARTICLES]
    if len(core) < 2 or len(core) > 6:
        return False
    if any(w.isdigit() or len(w) == 1 for w in core) or core[0] not in given:
        return False
    if not titled and all(w in places for w in core):
        return False
    return titled or any(w not in given for w in core[1:])
