import re
from decimal import Decimal

from canon_boe import OUT_DIR, consolidated, official, options, pdf_text, text_of, write_csv

OUT = OUT_DIR / "canon_digital_es.csv"

RDL_ID = "BOE-A-2017-7718"
RD_ID = "BOE-A-2023-7941"
RDL_PDF = "https://www.boe.es/boe/dias/2017/07/04/pdfs/BOE-A-2017-7718.pdf"
RD_PDF = "https://www.boe.es/boe/dias/2023/03/29/pdfs/BOE-A-2023-7941.pdf"
RDL_FROM, RDL_TO = "2017-08-01", "2023-06-30"
RD_FROM = "2023-07-01"
RD_ANNEX_VIGENCIA = "20230701"
UNIT = "per_unit"

RDL_CODES = {
    ("a", "1"): "multifunction_inkjet_laser",
    ("a", "2"): "single_function_upto_39ppm",
    ("b", "1"): "cd_burner_specific",
    ("b", "2"): "cd_burner_mixed",
    ("b", "3"): "dvd_burner_specific",
    ("b", "4"): "dvd_burner_mixed",
    ("c", "1"): "cd_r",
    ("c", "2"): "cd_rw",
    ("c", "3"): "dvd_r",
    ("c", "4"): "dvd_rw",
    ("d", ""): "memory_usb_card",
    ("e", ""): "disk_non_integrated",
    ("f", ""): "disk_integrated",
    ("g", ""): "portable_player_touchscreen",
    ("h", ""): "mobile_phone_media",
}

RD_CODES = {
    1: "tablet_upto_32gb",
    2: "tablet_32gb_to_64gb",
    3: "tablet_over_64gb",
    4: "smartphone_upto_64gb",
    5: "smartphone_64gb_to_128gb",
    6: "smartphone_over_128gb",
    7: "smartwatch_multimedia",
    8: "pc_upto_1tb",
    9: "pc_1tb_to_6tb",
    10: "pc_over_6tb",
    11: "hdd_internal_upto_1tb",
    12: "hdd_internal_1tb_to_6tb",
    13: "hdd_internal_over_6tb",
    14: "ssd_internal_upto_256gb",
    15: "ssd_internal_256gb_to_1tb",
    16: "ssd_internal_over_1tb",
    17: "device_with_disk_upto_1tb",
    18: "device_with_disk_1tb_to_6tb",
    19: "device_with_disk_over_6tb",
    20: "multifunction_upto_39_copies",
    21: "multifunction_over_39_copies",
    22: "printer_single_function_upto_39_copies",
    23: "printer_single_function_over_39_copies",
    24: "scanner_exposure_screen_upto_29ppm",
    25: "scanner_handheld",
    26: "hdd_external_upto_6tb",
    27: "hdd_external_over_6tb",
    28: "ssd_external_upto_1tb",
    29: "ssd_external_over_1tb",
    30: "memory_card_upto_64gb",
    31: "memory_card_over_64gb",
    32: "usb_memory_upto_64gb",
    33: "usb_memory_over_64gb",
    34: "mp3_mp4_player",
    35: "mobile_phone_basic_mp3",
    36: "ereader_single_function",
    37: "ereader_multimedia",
    38: "cd_recordable",
    39: "dvd_bluray_recordable",
    40: "optical_burner_cd_dvd",
}

FIELDS = ["code", "description", "definition", "unit", "amount_eur",
          "valid_from", "valid_to", "regulation"]


def clean(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return re.sub(r"[.:]$", "", text).strip()


def euros(text):
    m = re.search(r"(\d+(?:,\d+)?)\s*(?:€|euros)", text)
    if not m:
        raise SystemExit(f"Importe no encontrado en: {text!r}")
    return f"{Decimal(m.group(1).replace(',', '.')):.2f}"


def rdl_rows(root):
    paras = [text_of(p) for p in root.find("texto")]
    start = next((i for i, p in enumerate(paras)
                  if p.startswith("Disposición transitoria segunda")), None)
    if start is None:
        raise SystemExit("RDL 12/2017: no se encuentra la disposición transitoria segunda")
    rows, letter, heading = [], None, ""
    for p in paras[start + 2:]:
        if p.startswith("No podrá aplicarse"):
            break
        m_letter = re.match(r"^([a-h])\)\s*(.*)$", p)
        m_ord = re.match(r"^(\d)\.º\s*(.*)$", p)
        if m_letter:
            letter, body = m_letter.groups()
            if "euros por unidad" not in body:
                heading = clean(body)
                continue
            heading, ordinal = "", ""
        elif m_ord and letter:
            ordinal, body = m_ord.groups()
        else:
            raise SystemExit(f"RDL 12/2017: párrafo inesperado: {p!r}")
        desc = re.sub(r":\s*\d+(?:,\d+)?\s*euros por unidad\.?", ".", body)
        ref = f"{letter}).{ordinal}.º" if ordinal else f"{letter})"
        rows.append({
            "code": RDL_CODES[(letter, ordinal)],
            "description": clean(desc),
            "definition": heading,
            "unit": UNIT,
            "amount_eur": euros(body),
            "valid_from": RDL_FROM,
            "valid_to": RDL_TO,
            "regulation": f"RDL 12/2017 ({RDL_ID}), disp. trans. 2.ª, apdo. 1.{ref}",
        })
    if len(rows) != len(RDL_CODES):
        raise SystemExit(f"RDL 12/2017: {len(rows)} filas, se esperaban {len(RDL_CODES)}")
    return rows


def annex_table(root):
    annex = next((b for b in root.iter("bloque") if b.get("id") == "an"), None)
    if annex is None:
        raise SystemExit("RD 209/2023: no se encuentra el anexo")
    versions = annex.findall("version")
    if len(versions) != 1 or versions[0].get("fecha_vigencia") != RD_ANNEX_VIGENCIA:
        raise SystemExit("RD 209/2023: el anexo tiene una versión nueva en el BOE; hay que revisar el script")
    return versions[0].find(".//table")


def rd_rows(root):
    rows, definition, span_left = [], "", 0
    for tr in annex_table(root).find("tbody").findall("tr"):
        cells = tr.findall("td")
        num, tipo, cuantia = (text_of(c) for c in cells[:3])
        if span_left == 0:
            dcell = cells[3]
            definition = clean(text_of(dcell))
            span_left = int(dcell.get("rowspan", "1"))
        span_left -= 1
        n = int(num)
        rows.append({
            "code": RD_CODES[n],
            "description": clean(tipo),
            "definition": definition,
            "unit": UNIT,
            "amount_eur": euros(cuantia),
            "valid_from": RD_FROM,
            "valid_to": "",
            "regulation": f"RD 209/2023 ({RD_ID}), art. 3 y anexo, n.º {n}",
        })
    if len(rows) != len(RD_CODES):
        raise SystemExit(f"RD 209/2023: {len(rows)} filas, se esperaban {len(RD_CODES)}")
    return rows


def check_pdfs(rows, refresh):
    rd_pdf = pdf_text(RD_PDF, f"{RD_ID}.pdf", refresh)
    rdl_pdf = re.sub(r"\s+", " ", pdf_text(RDL_PDF, f"{RDL_ID}.pdf", refresh))
    for row in rows:
        amount = row["amount_eur"].replace(".", ",")
        if row["valid_from"] == RD_FROM:
            n = int(re.search(r"n\.º (\d+)$", row["regulation"]).group(1))
            shown = "0€" if amount == "0,00" else f"{amount} €"
            found = re.search(rf"^\s*{n}\s+.*?{re.escape(shown)}", rd_pdf, re.M)
        else:
            start = rdl_pdf.find(row["description"][:40])
            found = start >= 0 and f"{amount} euros por unidad" in rdl_pdf[start:start + 400]
        if not found:
            raise SystemExit(f"{row['code']}: el importe {amount} no coincide con el PDF del BOE")


def main():
    args = options("Genera fiscal/canon_digital_es.csv a partir del BOE")
    rows = rdl_rows(official(RDL_ID, args.refrescar)) + rd_rows(consolidated(RD_ID, args.refrescar))
    codes = [r["code"] for r in rows]
    if len(codes) != len(set(codes)):
        raise SystemExit("Hay códigos duplicados")
    check_pdfs(rows, args.refrescar)
    write_csv(OUT, FIELDS, [[r[f] for f in FIELDS] for r in rows])


if __name__ == "__main__":
    main()
