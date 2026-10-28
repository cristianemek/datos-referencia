import argparse
import csv
import html
import io
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
WS = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/"
ORDER_URL = "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-22138"
ORDER_SOURCE = "Orden HAC/1177/2024 (BOE-A-2024-22138), anexo, apartado 6, lista {}"
VALIDATIONS_SOURCE = "AEAT, Validaciones y errores VERI*FACTU v1.2.2, apartado {}"
XS = "{http://www.w3.org/2001/XMLSchema}"
LANG = "{http://www.w3.org/XML/1998/namespace}lang"
SCHEMAS = ("SuministroInformacion.xsd", "RespuestaSuministro.xsd", "RespuestaConsultaLR.xsd")

CATEGORIES = (
    ("rechazo del envío completo", "submission_rejected"),
    ("rechazo de la factura", "invoice_rejected"),
    ("aceptación del registro", "accepted_with_errors"),
)

XSD_LISTS = {
    "tax_type": ("SuministroInformacion.xsd", "ImpuestoType"),
    "invoice_type": ("SuministroInformacion.xsd", "ClaveTipoFacturaType"),
    "rectification_type": ("SuministroInformacion.xsd", "ClaveTipoRectificativaType"),
    "operation_qualification": ("SuministroInformacion.xsd", "CalificacionOperacionType"),
    "id_type": ("SuministroInformacion.xsd", "PersonaFisicaJuridicaIDTypeType"),
    "third_party_or_recipient": ("SuministroInformacion.xsd", "TercerosODestinatarioType"),
    "generated_by": ("SuministroInformacion.xsd", "GeneradoPorType"),
    "previous_rejection": ("SuministroInformacion.xsd", "RechazoPrevioType"),
    "hash_type": ("SuministroInformacion.xsd", "TipoHuellaType"),
    "operation_type": ("SuministroInformacion.xsd", "TipoOperacionType"),
    "submission_status": ("RespuestaSuministro.xsd", "EstadoEnvioType"),
    "record_status": ("RespuestaSuministro.xsd", "EstadoRegistroType"),
    "duplicate_record_status": ("SuministroInformacion.xsd", "EstadoRegistroSFType"),
    "query_record_status": ("RespuestaConsultaLR.xsd", "EstadoRegistroType"),
}

ORDER_LISTS = {"exemption_cause_iva": "L10", "regime_key_iva": "L8A", "regime_key_igic": "L8B"}

DL_1_2025 = (
    "Decreto Legislativo 1/2025, de 13 de octubre, por el que se aprueba el texto refundido de las normas "
    "legales aprobadas por la Comunidad Autónoma de Canarias en relación con el Impuesto General Indirecto "
    "Canario y el Arbitrio sobre Importaciones y Entregas de Mercancías en las Islas Canarias"
)

VALIDATION_LISTS = {
    "exemption_cause_igic": (
        ("E1", f"Operación exenta según el capítulo I del {DL_1_2025}", "5.2.2"),
        ("E2", "Operación exenta según el artículo 11 de la Ley 20/1991, de 7 de junio, del IGIC.", "5.2.2"),
        ("E3", "Operación exenta según el artículo 12 de la Ley 20/1991, de 7 de junio, del IGIC.", "5.2.2"),
        ("E4", "Operación exenta según el artículo 13 de la Ley 20/1991, de 7 de junio, del IGIC.", "5.2.2"),
        ("E5", "Operación exenta según el artículo 25 de la Ley 19/1994, de 6 de julio, del IGIC.", "5.2.2"),
        ("E6", "Operación exenta según el artículo 47 de la Ley 19/1994, de 6 de julio, del IGIC.", "5.2.2"),
        ("E7", f"Operación exenta según el artículo 90 del {DL_1_2025}", "5.2.2"),
        ("E8", "Operación exenta según la Ley 20/1991, de 7 de junio, del IGIC.", "5.2.2"),
    ),
    "exemption_cause_ipsi": (
        ("E1", "Operación exenta según el artículo 7 de la Ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
        ("E2", "Operación exenta según el artículo 8 de la Ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
        ("E3", "Operación exenta según el artículo 8 de la Ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
        ("E4", "Operación exenta según los artículos 9 y 10 de la ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
        ("E5", "Operación exenta según el artículo 8 de la Ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
        ("E6", "Operación exenta según la Ley 8/1991, de 25 de marzo, del IPSI.", "5.2.3"),
    ),
    "regime_key_igic": (
        ("20", "Operaciones sujetas al IPSI", "15.6 y 15.6.10"),
        ("21", "Régimen simplificado", "15.6.11"),
    ),
    "regime_key_ipsi": (
        ("01", "Operación de régimen general.", "15.6"),
        ("08", "Operaciones sujetas al IGIC / IVA (Impuesto General Indirecto Canario / Impuesto sobre el Valor Añadido).", "15.6"),
        ("11", "Operaciones de arrendamiento de local de negocio.", "15.6"),
        ("18", "Operaciones recogidas en el artículo 73. 4 y 5 de la Ordenanza fiscal IPSI. (Sólo Ceuta).", "15.6"),
        ("19", "Operaciones interiores exentas.", "15.6"),
        ("20", "Régimen estimación objetiva.", "15.6"),
    ),
}

LIST_ORDER = (
    "tax_type", "invoice_type", "rectification_type", "operation_qualification",
    "exemption_cause_iva", "exemption_cause_igic", "exemption_cause_ipsi",
    "regime_key_iva", "regime_key_igic", "regime_key_ipsi",
    "id_type", "third_party_or_recipient", "generated_by", "previous_rejection", "hash_type",
    "operation_type", "submission_status", "record_status", "duplicate_record_status", "query_record_status",
)

COVERAGE = {
    "OperacionExentaType": ("exemption_cause_iva", "exemption_cause_igic", "exemption_cause_ipsi"),
    "IdOperacionesTrascendenciaTributariaType": ("regime_key_iva", "regime_key_igic", "regime_key_ipsi"),
}

EXPECTED_SIZES = {"exemption_cause_iva": 6, "regime_key_iva": 17, "regime_key_igic": 18}

TEXT_FIXES = {
    "El registro se almacenado sin errores": "El registro se ha almacenado sin errores",
    "El registro se almacenado tiene algunos errores. Ver detalle del error":
        "El registro que se ha almacenado tiene algunos errores. Ver detalle del error",
}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def clean(text: str) -> str:
    return " ".join(html.unescape(text or "").split())


def decode_properties(raw: bytes) -> str:
    lines = []

    for line in raw.splitlines():
        try:
            lines.append(line.decode("utf-8"))
        except UnicodeDecodeError:
            lines.append(line.decode("cp1252"))

    text = "\n".join(lines)

    if re.search("[ÃÂ\x80-\x9f�]", text):
        raise RuntimeError("errores.properties tiene caracteres con la codificación dañada")

    return text


def parse_errors(text: str) -> list:
    rows = []
    category = None

    for line in (raw.strip() for raw in text.splitlines()):
        if line.startswith("*"):
            category = next((value for key, value in CATEGORIES if key in line), None)

            if category is None:
                raise RuntimeError(f"Sección desconocida en errores.properties: {line}")
        elif line:
            match = re.fullmatch(r"(\d+)\s*=\s*(.*)", line)

            if not match or category is None:
                raise RuntimeError(f"Línea inesperada en errores.properties: {line}")

            rows.append((category, match.group(1), clean(match.group(2))))

    codes = [code for _, code, _ in rows]

    if len(codes) != len(set(codes)):
        raise RuntimeError("Hay códigos de error repetidos en errores.properties")

    order = [value for _, value in CATEGORIES]
    return sorted(rows, key=lambda row: (order.index(row[0]), int(row[1])))


def schema_enumerations(schemas: dict) -> dict:
    result = {}

    for name, root in schemas.items():
        for simple_type in root.iter(XS + "simpleType"):
            enumerations = simple_type.findall(f"{XS}restriction/{XS}enumeration")

            if simple_type.get("name") and enumerations:
                result[(name, simple_type.get("name"))] = [
                    (item.get("value"), clean(next(
                        ("".join(doc.itertext()) for doc in item.iter(XS + "documentation") if doc.get(LANG) == "es"), "")))
                    for item in enumerations
                ]

    return result


def xsd_lists(enumerations: dict) -> dict:
    result = {}

    for list_name, (schema, type_name) in XSD_LISTS.items():
        items = enumerations[(schema, type_name)]
        missing = [code for code, description in items if not description]

        if missing:
            raise RuntimeError(f"{schema} no documenta {type_name}: {missing}")

        result[list_name] = [(code, TEXT_FIXES.get(description, description), f"{schema}, {type_name}") for code, description in items]

    return result


def strip_tags(fragment: str) -> str:
    return clean(re.sub(r"<[^>]+>", " ", fragment))


def table_rows(body: str, name: str) -> list:
    rows = []

    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", body, re.S):
        cells = [strip_tags(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]

        if len(cells) != 2 or not all(cells):
            raise RuntimeError(f"Fila inesperada en la lista {name} de la Orden HAC/1177/2024: {cells}")

        rows.append(tuple(cells))

    return rows


def order_tables(page: str) -> dict:
    tables = {}

    for table in re.findall(r'<table class="tabla">(.*?)</table>', page, re.S):
        caption = re.search(r"<caption>(.*?)</caption>", table, re.S)
        body = re.search(r"<tbody>(.*?)</tbody>", table, re.S)
        name = strip_tags(caption.group(1)) if caption else ""

        if name in ORDER_LISTS.values():
            tables[name] = table_rows(body.group(1) if body else "", name)

    return tables


def documented_lists(tables: dict) -> dict:
    result = {}

    for list_name, table in ORDER_LISTS.items():
        if not tables.get(table):
            raise RuntimeError(f"No se encuentra la lista {table} en la Orden HAC/1177/2024")

        result[list_name] = [(code, text, ORDER_SOURCE.format(table)) for code, text in tables[table]]

    for list_name, items in VALIDATION_LISTS.items():
        result[list_name] = result.get(list_name, []) + [
            (code, text, VALIDATIONS_SOURCE.format(section)) for code, text, section in items
        ]

    return result


def check_coverage(enumerations: dict, lists: dict) -> None:
    for type_name, list_names in COVERAGE.items():
        allowed = {code for code, _ in enumerations[("SuministroInformacion.xsd", type_name)]}
        documented = {code for name in list_names for code, _, _ in lists[name]}
        outside = {name: sorted({code for code, _, _ in lists[name]} - allowed) for name in list_names}

        if allowed != documented or any(outside.values()):
            raise RuntimeError(f"{type_name}: sin descripción {sorted(allowed - documented)}, fuera del XSD {outside}")

    for name, expected in EXPECTED_SIZES.items():
        if len(lists[name]) != expected:
            raise RuntimeError(f"La lista {name} tiene {len(lists[name])} códigos y se esperaban {expected}")

    for name, items in lists.items():
        codes = [code for code, _, _ in items]

        if len(codes) != len(set(codes)):
            raise RuntimeError(f"Códigos repetidos en la lista {name}")


def write_csv(path: Path, header: list, rows: list) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buffer.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Códigos de error y listas de claves de VERI*FACTU (AEAT)")
    parser.add_argument("--output-dir", type=Path, default=REPO / "facturacion")
    output = parser.parse_args().output_dir

    errors = parse_errors(decode_properties(fetch(WS + "errores.properties")))
    schemas = {name: ET.fromstring(fetch(WS + name)) for name in SCHEMAS}
    enumerations = schema_enumerations(schemas)
    lists = {**xsd_lists(enumerations), **documented_lists(order_tables(fetch(ORDER_URL).decode("utf-8")))}
    check_coverage(enumerations, lists)

    keys = [(name, code, text, source) for name in LIST_ORDER for code, text, source in lists[name]]
    write_csv(output / "verifactu_errores.csv", ["category", "code", "description"], errors)
    write_csv(output / "verifactu_claves.csv", ["list", "code", "description", "source"], keys)
    print(f"VERI*FACTU: {len(errors)} códigos de error y {len(keys)} claves en {len(LIST_ORDER)} listas")


if __name__ == "__main__":
    sys.exit(main())
