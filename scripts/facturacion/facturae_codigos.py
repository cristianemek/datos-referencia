import argparse
import csv
import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
SCHEMA_URL = "https://www.facturae.gob.es/content/dam/facturae/formato/versiones/Facturaev3_2_2.xml"
XS = "{http://www.w3.org/2001/XMLSchema}"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"
QUOTES = "\"'“”«»"

LISTS = {
    "TaxTypeCodeType": "tax_type",
    "SpecialTaxableEventCodeType": "special_taxable_event",
    "PaymentMeansType": "payment_means",
    "InvoiceDocumentTypeType": "invoice_document_type",
    "InvoiceClassType": "invoice_class",
    "ReasonCodeType": "correction_reason",
    "CorrectionMethodType": "correction_method",
    "UnitOfMeasureType": "unit_of_measure",
    "InvoiceIssuerTypeType": "invoice_issuer_type",
    "PersonTypeCodeType": "person_type",
    "ResidenceTypeCodeType": "residence_type",
    "RoleTypeCodeType": "administrative_centre_role",
    "ModalityType": "modality",
    "LanguageCodeType": "language",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(text: str) -> str:
    return " ".join((text or "").split()).strip(QUOTES).strip()


def documentation(element: ET.Element) -> dict:
    return {doc.get(LANG): clean("".join(doc.itertext())) for doc in element.iter(XS + "documentation")}


def code_lists(root: ET.Element) -> list:
    types = {item.get("name"): item for item in root.iter(XS + "simpleType") if item.get("name") in LISTS}
    missing_types = sorted(set(LISTS) - set(types))

    if missing_types:
        raise RuntimeError(f"El XSD de Facturae no contiene {missing_types}")

    rows = []

    for type_name, list_name in LISTS.items():
        enumerations = types[type_name].findall(f"{XS}restriction/{XS}enumeration")

        if not enumerations:
            raise RuntimeError(f"El tipo {type_name} de Facturae no tiene valores")

        for enumeration in enumerations:
            docs = documentation(enumeration)

            if not docs.get("es") or not docs.get("en"):
                raise RuntimeError(f"{type_name} {enumeration.get('value')} no tiene descripción en español e inglés")

            rows.append((list_name, enumeration.get("value"), docs["es"], docs["en"]))

    return rows


def write_csv(path: Path, header: list, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Listas de códigos del formato Facturae")
    parser.add_argument("--output-dir", type=Path, default=REPO / "facturacion")
    output = parser.parse_args().output_dir

    root = ET.fromstring(fetch(SCHEMA_URL))
    version = root.get("version", "desconocida")
    rows = code_lists(root)
    keys = [(row[0], row[1]) for row in rows]

    if len(keys) != len(set(keys)):
        raise RuntimeError("Hay códigos repetidos en una misma lista de Facturae")

    if version != "3.2.2":
        raise RuntimeError(f"Versión de Facturae inesperada: {version}")

    write_csv(output / "facturae_codigos.csv", ["list", "code", "description_es", "description_en"], rows)
    print(f"Facturae {version}: {len(rows)} códigos en {len(LISTS)} listas")


if __name__ == "__main__":
    sys.exit(main())
