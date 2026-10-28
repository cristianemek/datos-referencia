import re
from datetime import date, timedelta
from decimal import Decimal

from canon_boe import (OUT_DIR, block, consolidated, last_version_text, options, pdf_text,
                       require, text_of, write_csv)

OUT = OUT_DIR / "gravamenes_producto_es.csv"

LEY_ID = "BOE-A-2022-5809"
NAVARRA_ID = "BOE-A-2023-10923"
CONCIERTO_ID = "BOE-A-2002-9969"
LEY_PDF = "https://www.boe.es/boe/dias/2022/04/09/pdfs/BOE-A-2022-5809.pdf"
NAVARRA_PDF = "https://www.boe.es/boe/dias/2023/05/08/pdfs/BOE-A-2023-10923.pdf"

MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
          "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
RATE = re.compile(r"El tipo impositivo será de (\d+(?:,\d+)?) euros por kilogramo")

FIELDS = ["code", "name", "description", "territory", "unit", "amount_eur",
          "valid_from", "valid_to", "regulation", "notes"]

CODE = "plastic_packaging_tax"
NAME = "Impuesto especial sobre los envases de plástico no reutilizables"
DESCRIPTION = ("Plástico no reciclado contenido en envases no reutilizables, productos "
               "semielaborados para obtenerlos y productos de cierre, comercialización o "
               "presentación de esos envases")
UNIT = "per_kg"

STATE_REGULATION = "Ley 7/2022 (BOE-A-2022-5809), arts. 68, 77 y 78; disp. final 13.ª"
STATE_NOTES = (
    "Grava la fabricación, importación y adquisición intracomunitaria (art. 72). Exentas la "
    "importación y la adquisición intracomunitaria de envases con no más de 5 kg de plástico no "
    "reciclado al mes (art. 75.f). Solo el fabricante repercute la cuota en factura en la primera "
    "entrega (art. 82.9.a); en las demás ventas, si el adquirente lo pide, se indica en certificado "
    "o factura el impuesto satisfecho y los kg (art. 82.9.b). En el País Vasco es tributo "
    "concertado con las normas del Estado (Ley 12/2002, BOE-A-2002-9969, art. 33 bis, añadido por "
    "Ley 9/2023, BOE-A-2023-8455)")
NAVARRA_REGULATION = "Ley Foral 14/2023 de Navarra (BOE-A-2023-10923), art. 11; disp. final 3.ª"
NAVARRA_NOTES = ("Ley foral propia con el mismo tipo; efectos desde el 1 de enero de 2023, sin "
                 "perjuicio de la disp. trans. 7.ª del Convenio Económico")

STATE_CHECKS = [
    ("Artículo 68", "Los envases no reutilizables que contengan plástico"),
    ("Artículo 68", "Los productos plásticos semielaborados destinados a la obtención de los envases"),
    ("Artículo 68", "destinados a permitir el cierre, la comercialización o la presentación de envases no reutilizables"),
    ("Artículo 72", "Están sujetas al impuesto la fabricación, la importación o la adquisición intracomunitaria"),
    ("Artículo 75", "no exceda de 5 kilogramos en un mes"),
    ("Artículo 77", "cantidad de plástico no reciclado, expresada en kilogramos"),
    ("Artículo 82", "los fabricantes deberán repercutir al adquirente el importe de las cuotas"),
    ("Artículo 82", "previa solicitud del adquirente"),
]
CONCIERTO_CHECKS = [
    ("Artículo 33 bis", "se regirá por las mismas normas sustantivas y formales establecidas en cada momento por el Estado"),
]
NAVARRA_CHECKS = [
    ("Disposición final tercera", "sin perjuicio de lo establecido en la disposición transitoria séptima del Convenio Económico"),
]


def spanish_date(text, prefix, where):
    m = re.search(prefix + r" (\d{1,2}) de ([a-z]+) de (\d{4})", text)
    if not m or m.group(2) not in MONTHS:
        raise SystemExit(f"{where}: no se encuentra la fecha de efectos")
    return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))


def boe_date(value):
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def run_checks(root, checks, where):
    for title, fragment in checks:
        require(last_version_text(root, title), fragment, f"{where}, {title}")


def rate_rows(root, boe_id, article, effects_from, territory, regulation, notes):
    versions = block(root, article).findall("version")
    starts = [effects_from] + [boe_date(v.get("fecha_vigencia")) for v in versions[1:]]
    rows = []
    for i, version in enumerate(versions):
        m = RATE.search(text_of(version))
        if not m:
            raise SystemExit(f"{boe_id}, {article}: no se encuentra el tipo impositivo")
        source = version.get("id_norma")
        valid_to = (starts[i + 1] - timedelta(days=1)).isoformat() if i + 1 < len(versions) else ""
        reference = regulation if source == boe_id else f"{regulation}; redacción de {source}"
        rows.append([CODE, NAME, DESCRIPTION, territory, UNIT,
                     f"{Decimal(m.group(1).replace(',', '.')):.2f}",
                     starts[i].isoformat(), valid_to, reference, notes, source])
    return rows


def check_pdf(rows, boe_id, url, refresh):
    text = re.sub(r"\s+", " ", pdf_text(url, f"{boe_id}.pdf", refresh))
    for row in rows:
        if row[-1] != boe_id:
            continue
        phrase = f"El tipo impositivo será de {row[5].replace('.', ',')} euros por kilogramo"
        if phrase not in text:
            raise SystemExit(f"{boe_id}: el tipo {row[5]} no coincide con el PDF del BOE")


def state_rows(refresh):
    root = consolidated(LEY_ID, refresh)
    run_checks(root, STATE_CHECKS, "Ley 7/2022")
    run_checks(consolidated(CONCIERTO_ID, refresh), CONCIERTO_CHECKS, "Concierto Económico")
    effects = spanish_date(last_version_text(root, "Disposición final decimotercera"),
                           "la entrada en vigor del Título VII de esta ley se producirá el",
                           "Ley 7/2022")
    rows = rate_rows(root, LEY_ID, "Artículo 78", effects, "ES", STATE_REGULATION, STATE_NOTES)
    check_pdf(rows, LEY_ID, LEY_PDF, refresh)
    return rows


def navarra_rows(refresh):
    root = consolidated(NAVARRA_ID, refresh)
    run_checks(root, NAVARRA_CHECKS, "Ley Foral 14/2023")
    effects = spanish_date(last_version_text(root, "Disposición final tercera"),
                           "El impuesto especial sobre los envases de plástico no reutilizables "
                           "tendrá efectos desde el", "Ley Foral 14/2023")
    rows = rate_rows(root, NAVARRA_ID, "Artículo 11", effects, "ES-NC",
                     NAVARRA_REGULATION, NAVARRA_NOTES)
    check_pdf(rows, NAVARRA_ID, NAVARRA_PDF, refresh)
    return rows


def main():
    args = options("Genera fiscal/gravamenes_producto_es.csv a partir del BOE")
    rows = state_rows(args.refrescar) + navarra_rows(args.refrescar)
    write_csv(OUT, FIELDS, [row[:-1] for row in rows])


if __name__ == "__main__":
    main()
