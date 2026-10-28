from canon_boe import OUT_DIR, write_csv
from canon_digital import RD_CODES

OUT = OUT_DIR / "canon_digital_reglas_es.csv"

TRLPI = "RDLeg 1/1996 (BOE-A-1996-8930)"
RDL = "RDL 12/2017 (BOE-A-2017-7718)"
RD1398 = "RD 1398/2018 (BOE-A-2018-16903)"
RD209 = "RD 209/2023 (BOE-A-2023-7941)"
LAW_FROM = "2017-08-01"
RD1398_FROM = "2019-01-02"
RD209_FROM = "2023-07-01"


def codes(*nums):
    return ";".join(RD_CODES[n] for n in nums)


FIELDS = ["code", "type", "description", "applies_to",
          "valid_from", "valid_to", "regulation"]

RULES = [
    ("non_cumulative", "non_cumulative",
     "A ordenadores (portátiles o de sobremesa), tabletas, relojes inteligentes, lectores de libro "
     "electrónico y teléfonos móviles, inteligentes o no, no se les puede aplicar más de una cantidad "
     "del anexo: de las cantidades concurrentes solo se aplica la de mayor cuantía",
     codes(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 35, 36, 37), RD209_FROM, "", f"{RD209}, art. 4.2"),
    ("non_cumulative_2017", "non_cumulative",
     "No se puede aplicar más de una cantidad a los ordenadores, portátiles o de sobremesa, "
     "ni a los dispositivos de las letras g) y h)",
     "portable_player_touchscreen;mobile_phone_media", LAW_FROM, "2023-06-30",
     f"{RDL}, disp. trans. 2.ª, apdo. 1, último párrafo"),
    ("excluded_game_console_disk", "excluded_product",
     "Quedan exceptuados los discos integrados en videoconsolas que no permitan realizar "
     "reproducciones amparadas por el límite de copia privada",
     codes(17, 18, 19), RD209_FROM, "", f"{RD209}, anexo, n.º 17 a 19"),
    ("excluded_game_console_decoder_disk_2017", "excluded_product",
     "Quedan exceptuados los discos integrados en videoconsolas que no permitan realizar "
     "reproducciones amparadas por el límite de copia privada y en decodificadores de señales "
     "de televisión digital",
     "disk_integrated", LAW_FROM, "2023-06-30", f"{RDL}, disp. trans. 2.ª, apdo. 1.f)"),
    ("professional_equipment", "not_subject",
     "No están sujetos los equipos, aparatos y soportes concebidos manifiestamente para uso "
     "profesional que no se hayan puesto, de derecho o de hecho, a disposición de usuarios "
     "privados para hacer copias privadas",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.5.d)"),
    ("public_sector", "exemption",
     "Adquisiciones de entidades del sector público, Congreso, Senado, CGPJ, Tribunal de Cuentas, "
     "Defensor del Pueblo, asambleas legislativas autonómicas e instituciones autonómicas "
     "análogas; se acredita con una certificación del órgano competente",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.7.a)"),
    ("professional_use_certificate", "exemption",
     "Adquisiciones de personas físicas o jurídicas que actúen como consumidores finales con destino "
     "exclusivamente profesional, sin ponerlos a disposición de usuarios privados; se acredita con "
     "el certificado de exceptuación de la persona jurídica de las entidades de gestión (art. 25.10)",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.7.b); {RD1398}, arts. 3.a).2.º y 10"),
    ("authorized_reproduction", "exemption",
     "Adquisiciones de quienes tengan autorización para reproducir obras, prestaciones, fonogramas "
     "o videogramas en su actividad; se acredita con certificado de la persona jurídica (art. 25.10)",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.7.c); {RD1398}, arts. 3.a).3.º y 10.3"),
    ("travellers", "exemption",
     "Adquisiciones de personas físicas para uso privado fuera del territorio español en régimen "
     "de viajeros",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.7.d)"),
    ("exempt_without_certificate", "refund",
     "Sin certificado, los sujetos exceptuados pueden pedir el reembolso de la compensación pagada",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.7, último párrafo; {RD1398}, art. 10.10"),
    ("refund_professional_use", "refund",
     "Los consumidores finales no exceptuados que justifiquen un destino exclusivamente profesional "
     "pueden pedir el reembolso; mínimo 25 euros salvo que se acumulen las compras de un ejercicio; "
     "plazo de un año desde la fecha de la factura (desde la última en las acumuladas)",
     "", LAW_FROM, "",
     f"{TRLPI}, art. 25.8.a) y párrafos finales (plazo añadido por RDL 2/2018, BOE-A-2018-5059, "
     f"y Ley 2/2019, BOE-A-2019-2974); {RD1398}, art. 11"),
    ("refund_export", "refund",
     "Reembolso cuando los equipos se destinen a la exportación o a una entrega intracomunitaria; "
     "deudores y distribuidores deducen esas unidades en su relación trimestral",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.8.b); {RD1398}, art. 6.1.a) y 6.2.b)"),
    ("distributor_refund_exempt_sales", "refund",
     "Los distribuidores, mayoristas y minoristas pueden pedir a las entidades de gestión la "
     "devolución de la compensación correspondiente a sus ventas a sujetos exceptuados",
     "", LAW_FROM, "", f"{TRLPI}, art. 25.3, párr. 3.º; {RD1398}, art. 6.2.b)"),
    ("distributor_quarterly_report", "obligation",
     "Los distribuidores presentan, en los 30 días naturales siguientes a cada trimestre, la "
     "relación de unidades compradas en España a deudores que no les repercutieron la compensación "
     "en factura (responden solidariamente de su pago) y de las exportadas o vendidas a titulares "
     "de certificado de exceptuación",
     "", RD1398_FROM, "", f"{TRLPI}, art. 25.3; {RD1398}, art. 6.2"),
    ("invoice_separate_line", "invoicing",
     "Deudores y distribuidores incluyen el importe de la compensación de forma separada en la "
     "factura, salvo que el cliente tenga certificado de exceptuación vigente; si no aparece "
     "separado se presume no satisfecha, y el distribuidor no debe aceptar suministros sujetos que "
     "no vengan facturados así",
     "", RD1398_FROM, "", f"{RD1398}, art. 5.1 y 5.4"),
    ("exemption_certificate_check", "invoicing",
     "El certificado de exceptuación solo vale para operaciones posteriores a su emisión; debe "
     "presentarse y estar vigente al firmar la venta y antes de emitir la factura (se comprueba en "
     "el listado público de la persona jurídica) y la factura se emite a nombre de su titular",
     "", RD1398_FROM, "", f"{RD1398}, art. 10.7 a 10.9"),
    ("vat_on_compensation", "invoicing",
     "El importe de la compensación queda sujeto al IVA, al IGIC o al IPSI, según proceda",
     "", RD1398_FROM, "", f"{RD1398}, art. 5.1, párr. 2.º"),
    ("consumer_information", "invoicing",
     "Si el cliente es consumidor final sin certificado de exceptuación, hay que ponerle a "
     "disposición un documento sobre su derecho a pedir el certificado de exceptuación y el "
     "reembolso (la persona jurídica publica un modelo en su web)",
     "", RD1398_FROM, "", f"{RD1398}, art. 5.2 y 5.3"),
    ("transitional_stock_2023", "transitional",
     "A los equipos adquiridos antes del 1 de julio de 2023 y comercializados después se les aplica "
     "el importe del RDL 12/2017 si se acredita unidad a unidad con las facturas y documentos de "
     "adquisición, venta y entrega; no vale para fabricantes ni para quienes los adquieran fuera "
     "de España para distribuirlos aquí; solo durante los 30 días naturales siguientes a la "
     "entrada en vigor del RD 209/2023",
     "", RD209_FROM, "2023-07-31", f"{RD209}, disp. trans. única"),
]


def main():
    write_csv(OUT, FIELDS, RULES)


if __name__ == "__main__":
    main()
