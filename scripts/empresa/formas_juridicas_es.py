import csv
import html
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
ELF_PAGE = "https://www.gleif.org/lei-data/code-lists/iso-20275-entity-legal-forms-code-list"
ELF_DEFAULT = ELF_PAGE + "/2026-02-19-elf-code-list-v1.6.csv"
BOE_API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id}/texto/bloque/{block}"
ORDER_ID = "BOE-A-2008-3580"
ORDER_REF = "Orden EHA/451/2008 (BOE-A-2008-3580)"
EXPECTED_LETTERS = set("ABCDEFGHJNPQRSUVW")
STATUS = {"ACTV": "activa", "INAC": "retirada"}

NIF_LETTERS = {
    "5RDO": "A", "AJ9U": "A", "R2L8": "A", "9FPZ": "A", "8EHB": "A", "7U8O": "A", "AXS5": "A", "DDES": "A",
    "DP3Q": "B", "R6UT": "B", "JB2M": "B", "1G29": "B", "956I": "B",
    "S6X7": "C", "1ZHJ": "C",
    "TDD5": "D", "VFIU": "D", "GJL1": "D", "GJTL": "D",
    "UFBW": "E",
    "1QU8": "F", "B0V5": "F", "HRQA": "F", "SS0L": "F",
    "A0J6": "G",
    "2W1A": "J", "ARDP": "J", "K6L9": "J",
    "S6MS": "R",
}

EXTRA_LETTERS = {
    "a4": ("N", r"Para las (.+?), el número de identificación fiscal comenzará con la letra N\b", "art. 4"),
    "a5": ("W", r"Para los (.+?), el número de identificación fiscal comenzará con la letra W\b", "art. 5.2"),
}


def fetch(url: str, accept: str = "*/*") -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except OSError as error:
        raise RuntimeError(f"No se pudo descargar {url}: {error}") from error


def latest_elf_url() -> str:
    page = fetch(ELF_PAGE).decode("utf-8", "replace")
    found = re.findall(r'((?:https?:)?//www\.gleif\.org[^"\'\s]*?elf-code-list-v(\d+)\.(\d+)\.csv)', page)
    if not found:
        return ELF_DEFAULT
    url, _, _ = max(found, key=lambda item: (int(item[1]), int(item[2])))
    return url if url.startswith("http") else "https:" + url


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def legal_forms(url: str) -> list[dict]:
    text = fetch(url).decode("utf-8-sig")
    rows = [row for row in csv.DictReader(io.StringIO(text)) if row["Country Code (ISO 3166-1)"] == "ES"]
    if not rows:
        raise RuntimeError("La lista ELF no contiene formas jurídicas de España")
    unknown = set(NIF_LETTERS) - {row["ELF Code"] for row in rows}
    if unknown:
        raise RuntimeError(f"Códigos ELF de la tabla NIF que ya no están en la lista: {sorted(unknown)}")
    return sorted(
        (
            {
                "elf_code": row["ELF Code"],
                "name": clean(row["Entity Legal Form name Local name"]),
                "abbreviations": "|".join(clean(a) for a in row["Abbreviations Local language"].split(";") if clean(a)),
                "status": STATUS[row["ELF Status ACTV/INAC"]],
                "nif_letter": NIF_LETTERS.get(row["ELF Code"], ""),
            }
            for row in rows
        ),
        key=lambda item: item["elf_code"],
    )


def block_versions(block: str) -> list[tuple[str, list[str]]]:
    xml = fetch(BOE_API.format(id=ORDER_ID, block=block), "application/xml")
    root = ET.fromstring(xml)
    versions = [
        (version.get("id_norma"), [clean(html.unescape("".join(p.itertext()))) for p in version.iter("p")])
        for version in root.iter("version")
    ]
    if not versions:
        raise RuntimeError(f"El bloque {block} de {ORDER_ID} no tiene texto")
    return versions


def letter_paragraphs(paragraphs: list[str]) -> dict[str, str]:
    matches = (re.match(r"^([A-Z])\. (.+?)\.?$", paragraph) for paragraph in paragraphs)
    return dict(match.groups() for match in matches if match)


def article_3_letters() -> list[dict]:
    versions = block_versions("a3")
    original, current = letter_paragraphs(versions[0][1]), letter_paragraphs(versions[-1][1])
    modifier = versions[-1][0]
    return [
        {
            "letter": letter,
            "description": description,
            "regulation": f"{ORDER_REF}, art. 3"
            + (f"; mod. {modifier}" if original.get(letter) != description and modifier != ORDER_ID else ""),
        }
        for letter, description in current.items()
    ]


def extra_letters() -> list[dict]:
    result = []
    for block, (letter, pattern, article) in EXTRA_LETTERS.items():
        text = " ".join(block_versions(block)[-1][1])
        match = re.search(pattern, text)
        if not match:
            raise RuntimeError(f"No se encuentra la letra {letter} en el bloque {block} de {ORDER_ID}")
        description = match.group(1)
        result.append({
            "letter": letter,
            "description": description[0].upper() + description[1:],
            "regulation": f"{ORDER_REF}, {article}",
        })
    return result


def nif_letters() -> list[dict]:
    letters = sorted(article_3_letters() + extra_letters(), key=lambda item: item["letter"])
    found = {item["letter"] for item in letters}
    if found != EXPECTED_LETTERS:
        raise RuntimeError(f"Letras NIF inesperadas: faltan {sorted(EXPECTED_LETTERS - found)}, sobran {sorted(found - EXPECTED_LETTERS)}")
    return letters


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} filas")


def main() -> None:
    letters = nif_letters()
    valid = {item["letter"] for item in letters}
    forms = legal_forms(latest_elf_url())
    invalid = {form["nif_letter"] for form in forms if form["nif_letter"]} - valid
    if invalid:
        raise RuntimeError(f"Letras NIF asignadas que no están en la Orden: {sorted(invalid)}")
    write_csv(REPO / "catalogos" / "formas_juridicas_es.csv", ["elf_code", "name", "abbreviations", "status", "nif_letter"], forms)
    write_csv(REPO / "catalogos" / "letras_nif_es.csv", ["letter", "description", "regulation"], letters)


if __name__ == "__main__":
    main()
