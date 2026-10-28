import subprocess

from tipos_boe import CACHE, download

LEY8 = "BOE-A-1991-7645"
C2019 = "bocce_extra2_2019-01-30"
C2020A = "bocce_5973_2020-03-13"
C2020B = "bocce_extra54_2020-06-29"
C2024 = "bocce_6391_2024-03-15"
C2025 = "bocce_extra16_2025-05-08"
M2021 = "bome_5857_2021-05-04"
CEUTA_URL = "https://www.ceuta.es/ceuta/component/jdownloads/finish/"
BULLETINS = {
    C2019: CEUTA_URL + "1583-enero/9410-bocce-extra2-30-01-2019?Itemid=534",
    C2020A: CEUTA_URL + "1619-marzo/20188-bocce-5973-13-03-2020",
    C2020B: CEUTA_URL + "1830-junio/20334-bocce-extra54-29-06-2020",
    C2024: CEUTA_URL + "1931-marzo/22347-bocce-6391-15-03-2024",
    C2025: CEUTA_URL + "1955-mayo/22801-bocce-extra16-08-05-2025",
    M2021: "https://bomemelilla.es/bome/descargar/BOME-A-2021-410.pdf",
}

CEUTA = ("Ordenanza Fiscal del IPSI de Ceuta, texto refundido (BOCCE extraordinario n.º 2, 30/01/2019; "
         "en vigor el 31/01/2019)")
MELILLA = ("Ordenanza Fiscal del IPSI (Operaciones Interiores) de Melilla, texto íntegro (BOME n.º 5857, "
           "04/05/2021, Decreto 584 de 30/04/2021; en vigor el 05/05/2021)")
C_VIGOR = (C2019, "tendrá el día siguiente al de su publicación en el Boletín Oficial de la Ciudad de Ceuta")
M_VIGOR = (M2021, "entrará en vigor al día siguiente de su publicación definitiva")
TRIMESTRE = "entrando en vigor el acto acordado el día primero del trimestre natural siguiente al día de la publicación"


def row(territory, rate_type, rate, valid_from, valid_to, applies_to, regulation, checks):
    return {"tax": "IPSI", "territory": territory, "rate_type": rate_type, "rate": rate,
            "surcharge_rate": "", "valid_from": valid_from, "valid_to": valid_to,
            "applies_to": applies_to, "regulation": regulation, "checks": checks}


def legal_range(territory):
    note = ("Horquilla legal: cada ciudad fija en su ordenanza los tipos concretos dentro de este intervalo; "
            "no puede distinguir entre producción e importación de bienes")
    reg = "Ley 8/1991 (BOE-A-1991-7645), art. 18.1, redacción de Ley 13/1996 (BOE-A-1996-29117), art. 68.2"
    check = (LEY8, "art18", "BOE-A-1996-29117",
             "Los tipos de gravamen serán fijados en las Ordenanzas por las Ciudades respectivas y estarán comprendidos entre 0,5 por 100 y el 10 por 100")
    return [row(territory, "minimo", "0.5", "1997-01-01", "", note, reg, [check]),
            row(territory, "maximo", "10", "1997-01-01", "", note, reg, [check])]


CEUTA_ROWS = [
    row("18", "general", "4", "2019-01-31", "", "Prestaciones de servicios (tipo general)",
        f"{CEUTA}, art. 33.Dos",
        [C_VIGOR, (C2019, "Las prestaciones de servicios tributarán al tipo general del 4%")]),
    row("18", "sectorial", "10", "2019-01-31", "", "Servicios de telecomunicaciones, radiodifusión y televisión",
        f"{CEUTA}, art. 33.Dos.1",
        [(C2019, "Se aplicará el tipo de gravamen del 10% a los servicios de telecomunicaciones")]),
    row("18", "sectorial", "9", "2019-01-31", "",
        "Actividades de la agrupación 84 del IAE (desde el 01/07/2020, salvo los epígrafes del anexo 3, que van al tipo general) y servicios de saneamiento y limpieza de la agrupación 92",
        f"{CEUTA}, art. 33.Dos.2; redacción del apdo. 2.a publicada en BOCCE extraordinario n.º 54, 29/06/2020",
        [(C2019, "tributarán a un tipo de gravamen del 9% las siguientes actividades"),
         (C2020B, "a excepción de los epígrafes de ésta agrupación contemplados en el anexo 3 de esta Ordenanza fiscal, que tributaran al tipo general"),
         (C2020B, TRIMESTRE)]),
    row("18", "sectorial", "6", "2019-01-31", "",
        "Servicios de limpieza del epígrafe 922.1 del IAE cuando el destinatario no pertenece al sector público",
        f"{CEUTA}, art. 33.Dos.2.b",
        [(C2019, "a excepción de las correspondientes a la agrupación 9221.1 que tributarán al 6% cuando el destinatario de los servicios no pertenezca al Sector Público")]),
    row("18", "sectorial", "6", "2019-01-31", "2020-03-31",
        "Actividades profesionales, artísticas y empresariales del anexo 3 de la ordenanza y actividades de la agrupación 75 del IAE",
        f"{CEUTA}, art. 33.Dos.5 (el anexo 3 pasó al tipo general por la modificación publicada en BOCCE n.º 5973, 13/03/2020)",
        [(C2019, "Tributarán a un tipo de gravamen de 6% las actividades profesionales, artísticas y empresariales incluidas en el Anexo 3"),
         (C2020A, "5. Tributarán a un tipo de gravamen de 6% las actividades incluidas en la agrupación 75"),
         (C2020A, TRIMESTRE)]),
    row("18", "sectorial", "6", "2020-04-01", "", "Actividades de la agrupación 75 del IAE (actividades anexas a los transportes)",
        "Ordenanza Fiscal del IPSI de Ceuta, art. 33.Dos.5, redacción publicada en BOCCE n.º 5973, 13/03/2020 (en vigor el 01/04/2020)",
        [(C2020A, "5. Tributarán a un tipo de gravamen de 6% las actividades incluidas en la agrupación 75"),
         (C2020A, TRIMESTRE)]),
    row("18", "reducido", "2", "2019-01-31", "",
        "Restaurantes de un tenedor, bares y cafeterías (epígrafe 673.2 del IAE), restauración del epígrafe 677.9, autotaxis y transporte terrestre urbano colectivo de viajeros",
        f"{CEUTA}, art. 33.Dos.3",
        [(C2019, "Tributarán al tipo reducido del 2% las siguientes prestaciones de servicios"),
         (C2019, "Los servicios de auto taxis, así como los de transporte terrestre urbano colectivo de viajeros")]),
    row("18", "sectorial", "1", "2019-01-31", "", "Abastecimiento de agua potable",
        f"{CEUTA}, art. 33.Dos.4",
        [(C2019, "La prestación del servicio de abastecimiento de agua potable tributará al tipo de gravamen del 1%")]),
    row("18", "superreducido", "0.5", "2019-01-31", "",
        "Publicidad (grupos 844 y 751 del IAE), atención al cliente (call center) y servicios prestados por vía electrónica",
        f"{CEUTA}, art. 33.Dos.6 (añadido por el mismo acuerdo)",
        [(C2019, "Adición de los números 6 y 7 del apartado DOS del artículo 33"),
         (C2019, "tributarán al tipo súper reducido del 0.5 % las prestaciones de servicios que a continuación se detallan"),
         (C2019, "Servicios de atención al cliente (call center)")]),
    row("18", "superreducido", "0.5", "2019-01-31", "",
        "Asesoramiento y tratamiento de datos prestados a operadores de juego en línea con residencia fiscal en Ceuta",
        f"{CEUTA}, art. 33.Dos.7 (añadido por el mismo acuerdo)",
        [(C2019, "en relación con la operación de juego online")]),
    row("18", "general", "4", "2019-01-31", "",
        "Construcción y primera transmisión de bienes inmuebles y ejecución de obra inmobiliaria (regla general)",
        f"{CEUTA}, art. 33.Tres; redacción publicada en BOCCE extraordinario n.º 16, 08/05/2025",
        [(C2019, "tributarán con carácter general al tipo del 4%"),
         (C2025, "tributarán con carácter general al tipo del 4 %")]),
    row("18", "sectorial", "2", "2019-01-31", "2025-05-08",
        "Transmisión de viviendas de protección oficial de régimen especial o de promoción pública",
        f"{CEUTA}, art. 33.Tres.a (suprimido por la redacción publicada en BOCCE extraordinario n.º 16, 08/05/2025)",
        [(C2019, "promoción pública, que tributarán al tipo del 2 por 100")]),
    row("18", "sectorial", "10", "2019-01-31", "",
        "Obras públicas contratadas con el sector público (desde el 09/05/2025, salvo edificaciones destinadas mayoritariamente a vivienda, al 0,5 %)",
        f"{CEUTA}, art. 33.Tres.b; redacción publicada en BOCCE extraordinario n.º 16, 08/05/2025",
        [(C2019, "La ejecución de obras públicas contratadas con el sector público tributarán al tipo del 10 %"),
         (C2025, "La ejecución de obras públicas contratadas con el sector público tributarán al tipo del 10 %")]),
    row("18", "sectorial", "0.5", "2025-05-09", "",
        "Construcción y primera transmisión de inmuebles y obra inmobiliaria directamente relacionadas con la construcción de nuevas viviendas en Ceuta",
        "Ordenanza Fiscal del IPSI de Ceuta, art. 33.Tres.a, redacción publicada en BOCCE extraordinario n.º 16, 08/05/2025 (aprobación definitiva; en vigor el día siguiente)",
        [(C2025, "tamente relacionadas con la construcción de nuevas viviendas en Ceuta, tributarán al tipo del 0.5 %"),
         (C2025, "La entrada en vigor de las modificaciones propuestas se produzca el día siguiente a la publicación")]),
    row("18", "sectorial", "0.5", "2025-05-09", "",
        "Obras públicas contratadas con el sector público cuyo objeto son edificaciones destinadas mayoritariamente a viviendas",
        "Ordenanza Fiscal del IPSI de Ceuta, art. 33.Tres.b, redacción publicada en BOCCE extraordinario n.º 16, 08/05/2025",
        [(C2025, "destinado a viviendas, tributarán al 0.5%")]),
    row("18", "sectorial", "1", "2019-01-31", "", "Consumo de energía eléctrica",
        f"{CEUTA}, art. 33.Cuatro",
        [(C2019, "El consumo de energía eléctrica tributará al tipo del 1 %")]),
    row("18", "sectorial", "0.5", "2024-03-16", "",
        "Operaciones realizadas en ejecución de proyectos declarados de interés estratégico por el Pleno de la Asamblea (energía, ciclo del agua, telecomunicaciones); surte efectos desde el inicio de la ejecución de cada proyecto",
        "Ordenanza Fiscal del IPSI de Ceuta, art. 33.Cinco, añadido por la modificación publicada en BOCCE n.º 6391, 15/03/2024",
        [(C2024, "tributarán al 0,5% cuando se realicen en ejecución de un proyecto de interés estratégico"),
         (C2024, "Esta modificación entrará en vigor el día siguiente al de la publicación del acuerdo de aprobación defini")]),
]

MELILLA_ROWS = [
    row("19", "general", "4", "2021-05-05", "", "Prestaciones de servicios (tipo general)",
        f"{MELILLA}, anexo 1.Cuarto",
        [M_VIGOR, (M2021, "Las prestaciones de servicios tributarán al tipo general del 4 %")]),
    row("19", "sectorial", "0.5", "2021-05-05", "",
        "Transporte terrestre colectivo de viajeros, publicidad y marketing, servicios por vía electrónica, servicios de gestión accesorios al juego y arrendamiento de medios de transporte",
        f"{MELILLA}, anexo 1.Cuarto.1.º",
        [(M2021, "1º.-Tributarán al 0,5 % los siguientes servicios"),
         (M2021, "Los arrendamientos de medios de transporte")]),
    row("19", "sectorial", "1", "2021-05-05", "", "Autotaxis; restaurantes de un tenedor y demás cafés y bares",
        f"{MELILLA}, anexo 1.Cuarto.2.º y 3.º",
        [(M2021, "Los servicios de transporte de viajeros (autotaxis), tributarán al tipo del 1%"),
         (M2021, "Los servicios de restaurante de un tenedor y demás cafés y bares tributaran al tipo del 1%")]),
    row("19", "sectorial", "2", "2021-05-05", "",
        "Restaurantes de dos o más tenedores, cafés y bares de categoría especial y demás servicios de hostelería",
        f"{MELILLA}, anexo 1.Cuarto.4.º",
        [(M2021, "demás servicios de hostelería tributarán al 2 %")]),
    row("19", "sectorial", "8", "2021-05-05", "", "Servicios de telecomunicaciones, radiodifusión y televisión",
        f"{MELILLA}, anexo 1.Cuarto.5.º",
        [(M2021, "Los servicios de telecomunicaciones, los servicios de radiodifusión y de televisión tributarán al 8 %")]),
    row("19", "general", "4", "2021-05-05", "", "Entregas de bienes inmuebles (regla general)",
        f"{MELILLA}, anexo 1.Tercero",
        [(M2021, "La entrega de Bienes Inmuebles, tributarán al tipo del 4%")]),
    row("19", "sectorial", "0.5", "2021-05-05", "",
        "Primera transmisión de viviendas de protección oficial por sus promotores, con garajes (hasta dos) y anexos",
        f"{MELILLA}, anexo 1.Tercero.1.º",
        [(M2021, "Tributarán al tipo del 0,5% la primera transmisión de viviendas calificadas administrativamente como de protección oficial")]),
    row("19", "sectorial", "10", "2021-05-05", "", "Construcción y ejecución de obras inmobiliarias (regla general de las obras)",
        f"{MELILLA}, anexo 1.Tercero.2.º",
        [(M2021, "Tributarán al tipo del 10% la construcción y la ejecución de obras inmobiliarias")]),
    row("19", "sectorial", "0.5", "2021-05-05", "",
        "Obras contratadas directamente entre promotor y contratista para construir edificaciones destinadas principalmente a viviendas que serán objeto de primera entrega",
        f"{MELILLA}, anexo 1.Tercero.2.1",
        [(M2021, "Tributarán al tipo del 0,5 % la construcción y la ejecución de obras inmobiliarias, consecuencia de contratos directamente formalizados entre el promotor y el contratista")]),
    row("19", "sectorial", "4", "2021-05-05", "",
        "Resto de obras de edificaciones destinadas principalmente a viviendas y obras de reforma, mejora o rehabilitación de viviendas y locales de negocio ya terminados",
        f"{MELILLA}, anexo 1.Tercero.2.2 y 2.3",
        [(M2021, "2.2.- Tributarán al tipo del 4% la construcción y la ejecución de obras inmobiliarias"),
         (M2021, "2.3.- Tributarán al tipo del 4 % la construcción y la ejecución de obras inmobiliarias consistentes en la reforma")]),
    row("19", "sectorial", "1", "2021-05-05", "", "Consumo de energía eléctrica",
        f"{MELILLA}, anexo 1.Segundo",
        [(M2021, "El consumo de energía eléctrica tributará al tipo del 1%")]),
]

IPSI_ROWS = legal_range("18") + legal_range("19") + CEUTA_ROWS + MELILLA_ROWS


def bulletin_text(name: str) -> str:
    pdf = CACHE / "boletines" / f"{name}.pdf"
    txt = pdf.with_suffix(".txt")
    if not pdf.exists():
        data = download(BULLETINS[name], "application/pdf")
        if not data.startswith(b"%PDF"):
            raise SystemExit(f"{name}: la descarga no es un PDF")
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(data)
    if not txt.exists():
        try:
            subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(f"No se pudo convertir {pdf.name} con pdftotext: {error}") from error
    return txt.read_text(encoding="utf-8")
