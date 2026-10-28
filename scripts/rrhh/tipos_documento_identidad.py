import csv
import html
import io
import re
import shutil
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VERIFACTU_XSD = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/SuministroInformacion.xsd"
VERIFACTU_ORDER = "https://www.boe.es/buscar/act.php?id=BOE-A-2024-22138"
TGSS_T11 = "https://www.seg-social.es/descarga/214608"
RGAT = "https://www.boe.es/buscar/act.php?id=BOE-A-2007-15984"
NIE_ORDER = "https://www.boe.es/buscar/doc.php?id=BOE-A-2008-12050"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
HEADER = ["code", "name", "scope", "context", "regulation"]
XSD_NS = {"xs": "http://www.w3.org/2001/XMLSchema"}
NATURAL = "natural_person"
ANY_PERSON = "natural_or_legal_person"

VERIFACTU_REGULATION = "Orden HAC/1177/2024 (BOE-A-2024-22138), anexo, apdo. 6, lista L7"
RGAT_19_1 = "RD 1065/2007 (BOE-A-2007-15984), art. 19.1"
RGAT_19_2 = "RD 1065/2007 (BOE-A-2007-15984), art. 19.2"
RGAT_20_2 = "RD 1065/2007 (BOE-A-2007-15984), art. 20.2"
NIE_REGULATION = "Orden de 7 de febrero de 1997 (BOE-A-1997-3364), apdo. sexto.a), redacción de la Orden INT/2058/2008 (BOE-A-2008-12050)"

TGSS_REGULATIONS = {
    "1": f"RD 1553/2005 (BOE-A-2005-21163); {RGAT_19_1}",
    "2": "RD 896/2003 (BOE-A-2003-13978), pasaporte español",
    "6": "RD 1155/2024 (BOE-A-2024-24099), art. 205; Orden INT/2058/2008 (BOE-A-2008-12050)",
    "L": RGAT_19_2,
    "M": RGAT_20_2,
}

LETTERS = [
    ("K", "Españoles residentes en España menores de 14 años sin DNI (NIF asignado por la AEAT)", "nif_initial_letter", RGAT_19_2),
    ("L", "Españoles residentes en el extranjero sin DNI (NIF asignado por la AEAT)", "nif_initial_letter", RGAT_19_2),
    ("M", "Extranjeros sin número de identidad de extranjero (NIF asignado por la AEAT)", "nif_initial_letter", RGAT_20_2),
    ("X", "Número de identidad de extranjero (NIE), primera serie", "nie_initial_letter", NIE_REGULATION),
    ("Y", "Número de identidad de extranjero (NIE), serie que sigue a la X por orden alfabético", "nie_initial_letter", NIE_REGULATION),
    ("Z", "Número de identidad de extranjero (NIE), serie que sigue a la Y por orden alfabético", "nie_initial_letter", NIE_REGULATION),
]

EVIDENCE = {
    RGAT: [
        "Artículo 19. El número de identificación fiscal de las personas físicas de nacionalidad española.",
        "una letra inicial destinada a indicar la naturaleza de este número, que será la L para los españoles residentes "
        "en el extranjero y la K para los españoles que, residiendo en España, sean menores de 14 años",
        "Artículo 20. El número de identificación fiscal de las personas físicas de nacionalidad extranjera.",
        "Las personas físicas que carezcan de la nacionalidad española y no dispongan del número de identidad de extranjero",
        "una letra inicial, que será la M, destinada a indicar la naturaleza de este número",
    ],
    NIE_ORDER: [
        "Se añade a la letra a) del apartado sexto un segundo párrafo",
        "Una letra inicial, que será la X, seguida de siete dígitos o caracteres numéricos",
        "Una vez agotada la serie numérica correspondiente a la letra X, se continuará siguiendo el orden alfabético",
    ],
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def plain_text(page: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page))).replace(" ,", ",").strip()


def verifactu_codes() -> dict:
    root = ET.fromstring(fetch(VERIFACTU_XSD))
    simple_type = root.find("xs:simpleType[@name='PersonaFisicaJuridicaIDTypeType']", XSD_NS)

    if simple_type is None:
        raise RuntimeError("El XSD de VeriFactu no contiene PersonaFisicaJuridicaIDTypeType")

    return {
        item.get("value"): item.findtext("xs:annotation/xs:documentation", "", XSD_NS).strip()
        for item in simple_type.iterfind("xs:restriction/xs:enumeration", XSD_NS)
    }


def verifactu_rows() -> list:
    codes = verifactu_codes()
    page = fetch(VERIFACTU_ORDER).decode("utf-8")
    table = re.search(r'<table[^>]*>\s*<caption>\s*<p[^>]*>L7</p>.*?</table>', page, re.S)

    if not table:
        raise RuntimeError("No se encuentra la lista L7 en la Orden HAC/1177/2024")

    listed = [
        (plain_text(code), plain_text(name).removesuffix("."))
        for code, name in re.findall(r"<tr>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>", table.group(0), re.S)
    ]

    if [code for code, _ in listed] != list(codes):
        raise RuntimeError(f"La lista L7 del BOE {listed} no coincide con el XSD {codes}")

    return [[code, name, NATURAL if code == "03" else ANY_PERSON, "verifactu_id_type", VERIFACTU_REGULATION]
            for code, name in listed]


def pdf_text(content: bytes) -> str:
    if not shutil.which("pdftotext"):
        raise RuntimeError("Hace falta pdftotext (poppler-utils) para leer la tabla T-11")

    result = subprocess.run(["pdftotext", "-layout", "-", "-"], input=content, capture_output=True, check=True)

    return result.stdout.decode("utf-8")


def tgss_rows() -> list:
    text = pdf_text(fetch(TGSS_T11))

    if "T-11" not in text or "Tipo de identificador de Persona Física" not in text:
        raise RuntimeError("El PDF descargado no es la tabla T-11 de la TGSS")

    body = text.split("Comentarios", 1)[1].split("____", 1)[0]
    entries = re.findall(r"^\s*([0-9A-Z])\s{2,}(\S.*?)\s*$", body, re.M)

    if [code for code, _ in entries] != list(TGSS_REGULATIONS):
        raise RuntimeError(f"La tabla T-11 ha cambiado: {entries}")

    return [[code, name, NATURAL, "tgss_t11", TGSS_REGULATIONS[code]] for code, name in entries]


def verify_letters() -> None:
    for url, sentences in EVIDENCE.items():
        text = plain_text(fetch(url).decode("utf-8"))
        missing = [sentence for sentence in sentences if sentence not in text]

        if missing:
            raise RuntimeError(f"No se encuentra en {url}: {missing}")


def main() -> None:
    output = (Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "catalogos") / "tipos_documento_identidad.csv"
    verify_letters()
    rows = [*verifactu_rows(), *tgss_rows(), *([code, name, NATURAL, context, regulation]
                                              for code, name, context, regulation in LETTERS)]

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows)
    output.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"Tipos de documento de identidad: {len(rows)} filas en {output}")


if __name__ == "__main__":
    sys.exit(main())
