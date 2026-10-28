L20 = "BOE-A-1991-14463"
L4 = "BOE-A-2012-9282"
L11 = "BOE-A-2012-1256"
TR = "BOC-j-2025-90249"
TRV = "BOE-A-2025-90249"

REG20 = "Ley 20/1991 (BOE-A-1991-14463), disp. adic. 8.ª"
REG4 = "Ley 4/2012 de Canarias (BOE-A-2012-9282), art. 51"
REGTR = "Decreto Legislativo 1/2025 de Canarias (BOC n.º 207, 20/10/2025; consolidado BOC-j-2025-90249), art. 32.1"
RE58 = "recargo, art. 58 bis.3"
RE4 = "recargo, art. 51.5"
RETR = "recargo, art. 70.Uno.a"
START_NOTE = "aplicación desde el 1/1/1993: Ley 14/1992, BOE-A-1992-13445, art. 1"

START = (L20, "df", "BOE-A-1992-13445", "el comienzo de la aplicación del IGIC es el 1 de enero de 1993")
DA8_1991 = (L20, "octava", L20)
DA8_1993 = (L20, "octava", "BOE-A-1993-13663")
DA8_1997 = (L20, "octava", "BOE-A-1996-29117")
DA8_2001 = (L20, "octava", "BOE-A-2000-24357")
A51_2012 = (L4, "a5-3", L4)
A51_2019 = (L4, "a5-3", "BOE-A-2019-860")
A51_2020 = (L4, "a5-3", "BOE-A-2020-1566")
A51_2024 = (L4, "a5-3", "BOE-A-2024-10011")
A32 = (TR, "a3-4", TRV)
A32_26 = (TR, "a3-4", "BOE-A-2026-7560")
A70 = (TR, "a7-2", TRV)
A70_26 = (TR, "a7-2", "BOE-A-2026-7560")


def row(rate_type, rate, surcharge, valid_from, valid_to, applies_to, regulation, checks):
    return {"tax": "IGIC", "territory": "05", "rate_type": rate_type, "rate": rate,
            "surcharge_rate": surcharge, "valid_from": valid_from, "valid_to": valid_to,
            "applies_to": applies_to, "regulation": regulation, "checks": checks}


def c(base, needle):
    return base + (needle,)


def r58(version, needle):
    return (L20, "a58bis", version, needle)


LEY_20_1991 = [
    row("cero", "0", "", "1993-01-01", "2012-06-30", "", f"{REG20}.Uno.1 ({START_NOTE})",
        [START, c(DA8_1991, "El tipo cero se aplicará"), c(DA8_2001, "El tipo cero se aplicará")]),
    row("reducido", "2", "", "1993-01-01", "1993-05-26", "",
        f"{REG20}.Uno.2, redacción original ({START_NOTE})",
        [START, c(DA8_1991, "El tipo reducido será del 2 por 100")]),
    row("reducido", "2", "0.2", "1993-05-27", "2012-06-30", "",
        f"{REG20}.Uno.2 (RDL 7/1993, BOE-A-1993-13663, art. 8.1); {RE58} (añadido por RDL 7/1993, art. 3.9)",
        [c(DA8_1993, "El tipo reducido será del 2 por 100"), c(DA8_2001, "El tipo reducido será del 2 por 100"),
         r58("BOE-A-1993-13663", "tipo del 2 por 100 en el Impuesto General Indirecto Canario, el 0,20 por 100"),
         r58("BOE-A-2001-24965", "tipo del 2 por 100 en el Impuesto General Indirecto Canario, el 0,20 por 100")]),
    row("general", "4", "", "1993-01-01", "1993-05-26", "",
        f"{REG20}.Uno.3, redacción original ({START_NOTE})",
        [START, c(DA8_1991, "El tipo general será del 4 por 100")]),
    row("general", "4", "0.4", "1993-05-27", "1996-12-31", "",
        f"{REG20}.Uno.3 (RDL 7/1993, BOE-A-1993-13663, art. 8.1); {RE58} (RDL 7/1993, art. 3.9)",
        [c(DA8_1993, "El tipo general será del 4 por 100"),
         r58("BOE-A-1993-13663", "tipo del 4 por 100 en el Impuesto General Indirecto Canario, el 0,40 por 100")]),
    row("general", "4.5", "0.45", "1997-01-01", "2000-12-31", "",
        f"{REG20}.Uno.3 (Ley 13/1996, BOE-A-1996-29117, art. 64.4); {RE58} (Ley 13/1996, art. 64.3)",
        [c(DA8_1997, "El tipo general será del 4,5 por 100"),
         r58("BOE-A-1996-29117", "tipo del 4,5 por 100 en el Impuesto General Indirecto Canario, el 0,45 por 100")]),
    row("general", "5", "0.5", "2001-01-01", "2012-06-30", "",
        f"{REG20}.Uno.3 (Ley 14/2000, BOE-A-2000-24357, art. 8.1.23); {RE58} (Ley 14/2000, art. 8.1.21)",
        [c(DA8_2001, "El tipo general será del 5 por 100"),
         r58("BOE-A-2000-24357", "tipo del 5 por 100 en el Impuesto General Indirecto Canario, el 0,5 por 100")]),
    row("incrementado", "12", "", "1993-01-01", "1993-05-26", "",
        f"{REG20}.Uno.4, redacción original ({START_NOTE})",
        [START, c(DA8_1991, "Los tipos incrementados se fijan en el 12 por 100 y en el 24 por 100")]),
    row("incrementado", "24", "", "1993-01-01", "1993-05-26", "",
        f"{REG20}.Uno.4, redacción original ({START_NOTE}); suprimido por RDL 7/1993 (BOE-A-1993-13663), art. 8.1",
        [START, c(DA8_1991, "Los tipos incrementados se fijan en el 12 por 100 y en el 24 por 100"),
         c(DA8_1993, "El tipo incrementado será del 12 por 100")]),
    row("incrementado", "12", "1.2", "1993-05-27", "1996-12-31", "",
        f"{REG20}.Uno.4 (RDL 7/1993, BOE-A-1993-13663, art. 8.1); {RE58} (RDL 7/1993, art. 3.9)",
        [c(DA8_1993, "El tipo incrementado será del 12 por 100"),
         r58("BOE-A-1993-13663", "tipo del 12 por 100 en el Impuesto General Indirecto Canario, el 1,20 por 100")]),
    row("incrementado", "13", "1.3", "1997-01-01", "2012-06-30", "",
        f"{REG20}.Uno.4 (Ley 13/1996, BOE-A-1996-29117, art. 64.4; Ley 14/2000, BOE-A-2000-24357, art. 8.1.23); {RE58}",
        [c(DA8_1997, "El tipo incrementado será del 13 por 100"),
         c(DA8_2001, "Los tipos incrementados se fijan en el 9 por 100 y en el 13 por 100"),
         r58("BOE-A-1996-29117", "tipo del 13 por 100 en el Impuesto General Indirecto Canario, el 1,30 por 100"),
         r58("BOE-A-2000-24357", "tipo del 13 por 100 en el Impuesto General Indirecto Canario, el 1,3 por 100")]),
    row("incrementado", "9", "0.9", "2001-01-01", "2012-06-30", "",
        f"{REG20}.Uno.4 (Ley 14/2000, BOE-A-2000-24357, art. 8.1.23); {RE58} (Ley 14/2000, art. 8.1.21)",
        [c(DA8_2001, "Los tipos incrementados se fijan en el 9 por 100 y en el 13 por 100"),
         r58("BOE-A-2000-24357", "tipo del 9 por 100 en el Impuesto General Indirecto Canario, el 0,9 por 100")]),
    row("especial", "20", "2", "2001-01-01", "2012-06-30", "Labores de tabaco negro",
        f"{REG20}.Dos.a y Tres.a (Ley 14/2000, BOE-A-2000-24357, art. 8.1.23)",
        [c(DA8_2001, "Para labores de tabaco negro: 20 por 100"),
         c(DA8_2001, "Importaciones de labores de tabaco negro: 2 por 100")]),
    row("especial", "35", "3.5", "2001-01-01", "2012-06-30", "Labores de tabaco rubio y sucedáneos del tabaco",
        f"{REG20}.Dos.b y Tres.b (Ley 14/2000, BOE-A-2000-24357, art. 8.1.23)",
        [c(DA8_2001, "Para labores de tabaco rubio y sucedáneos del tabaco: 35 por 100"),
         c(DA8_2001, "Importaciones de labores de tabaco rubio y sucedáneos del tabaco: 3,5 por 100")]),
    row("reducido", "2.75", "", "2011-12-31", "2012-12-31",
        "Primeras entregas de viviendas destinadas a primera vivienda habitual, con base imponible de hasta 150.000 euros",
        "Ley 11/2011 de Canarias (BOE-A-2012-1256), arts. 1 y 2 (vigencia hasta el 31/12/2012); desde el 1/7/2012, Ley 4/2012 de Canarias (BOE-A-2012-9282), arts. 51.1.b y 53, que remiten al art. 2 de la Ley 11/2011",
        [(L11, "a1", None, "serán del 2 por ciento y del 2,75 por ciento"),
         (L11, "a2", None,
          "Con vigencia hasta el 31 de diciembre de 2012, se aplicará el tipo de gravamen reducido del 2,75 por ciento"),
         (L11, "a2", None, "no sea superior a 150.000 euros"),
         c(A51_2012, "El tipo reducido del 2,75 por ciento"),
         (L4, "a5-5", L4, "en los términos previstos en el artículo 2 de la Ley 11/2011")]),
]

TOBACCO_4 = ("Labores del tabaco, salvo los cigarros puros (desde el 1/1/2024, salvo cigarros y cigarritos; "
             "incluye los cigarrillos electrónicos desechables)")
VEHICLES = ("Determinados vehículos, embarcaciones y aeronaves y las ejecuciones de obra para producirlos "
            "(arts. 55 y 59 a 61)")
VEHICLES_TR = "Determinados vehículos, embarcaciones y aeronaves y las ejecuciones de obra sobre ellos (arts. 39 a 41)"

LEY_4_2012 = [
    row("cero", "0", "0", "2012-07-01", "2025-10-20", "", f"{REG4}.1.a y art. 52; {RE4}.a",
        [c(A51_2012, "a) El tipo cero, aplicable"),
         c(A51_2012, "a) El tipo cero, para las importaciones sujetas al tipo cero")]),
    row("reducido", "3", "0.3", "2012-07-01", "2025-10-20", "", f"{REG4}.1 y art. 54; {RE4}",
        [c(A51_2012, "El tipo reducido del 3 por ciento"), c(A51_2012, "El tipo del 0,3 por ciento"),
         c(A51_2024, "El tipo reducido del 3 por ciento"), c(A51_2024, "El tipo del 0,3 por ciento")]),
    row("reducido", "5", "0.5", "2024-01-01", "2025-10-20",
        "Bebidas refrescantes y gaseosas con azúcares o edulcorantes añadidos (en 2024 también las bebidas energéticas)",
        f"{REG4}.1.c y art. 54 bis (añadidos por Ley 7/2023 de Canarias, BOE-A-2024-10011, disp. final 7.ª); {RE4}.c",
        [c(A51_2024, "El tipo reducido del 5 por ciento"), c(A51_2024, "El tipo del 0,5 por ciento"),
         (L4, "a5-12", "BOE-A-2024-10011", "bebidas energéticas y bebidas refrescantes y gaseosas")]),
    row("general", "7", "0.7", "2012-07-01", "2018-12-31", "", f"{REG4}.1.d; {RE4}.c",
        [c(A51_2012, "El tipo general del 7 por ciento"), c(A51_2012, "El tipo del 0,7 por ciento")]),
    row("general", "6.5", "0.65", "2019-01-01", "2019-12-31", "",
        f"{REG4}.1.d y 5.c, redacción de Ley 7/2018 de Canarias (BOE-A-2019-860), disp. final 7.ª.5 y 6",
        [c(A51_2019, "El tipo general del 6,5 por ciento"), c(A51_2019, "El tipo del 0,65 por ciento")]),
    row("general", "7", "0.7", "2020-01-01", "2025-10-20", "",
        f"{REG4}.1 y 5, redacción de Ley 19/2019 de Canarias (BOE-A-2020-1566), disp. final 6.ª.1",
        [c(A51_2020, "El tipo general del 7 por ciento"), c(A51_2020, "El tipo del 0,7 por ciento")]),
    row("incrementado", "9.5", "0.95", "2012-07-01", "2025-10-20", VEHICLES, f"{REG4}.1 y art. 55; {RE4}",
        [c(A51_2012, "El tipo incrementado del 9,5 por ciento"), c(A51_2012, "El tipo del 0,95 por ciento"),
         c(A51_2024, "El tipo del 0,95 por ciento")]),
    row("incrementado", "13.5", "1.35", "2012-07-01", "2019-12-31", "", f"{REG4}.1.f y art. 56; {RE4}.e",
        [c(A51_2012, "El tipo incrementado del 13,5 por ciento"), c(A51_2012, "El tipo del 1,35 por ciento"),
         c(A51_2019, "El tipo incrementado del 13,5 por ciento")]),
    row("incrementado", "15", "1.5", "2020-01-01", "2025-10-20", "",
        f"{REG4}.1 y 5 y art. 56, redacción de Ley 19/2019 de Canarias (BOE-A-2020-1566), disp. final 6.ª",
        [c(A51_2020, "El tipo incrementado del 15 por ciento"), c(A51_2020, "El tipo del 1,5 por ciento")]),
    row("especial", "20", "2", "2012-07-01", "2025-10-20", TOBACCO_4, f"{REG4}.1 y art. 57; {RE4}",
        [c(A51_2012, "El tipo especial del 20 por ciento"), c(A51_2012, "El tipo del 2 por ciento"),
         (L4, "a5-9", L4, "con excepción de los cigarros puros"),
         (L4, "a5-9", "BOE-A-2024-10011", "con excepción de los cigarros y cigarritos")]),
]

TEXTO_REFUNDIDO = [
    row("cero", "0", "0", "2025-10-21", "", "", f"{REGTR}.a y art. 33; {RETR}",
        [c(A32, "a) El tipo cero"), c(A70, "El tipo cero, para las importaciones sujetas al tipo cero"),
         c(A70_26, "El tipo cero, para las importaciones sujetas al tipo cero")]),
    row("superreducido", "3", "0.3", "2025-10-21", "", "", f"{REGTR} y art. 34; {RETR}",
        [c(A32, "El tipo superreducido del 3 por ciento"), c(A70, "El tipo del 0,3 por ciento"),
         c(A32_26, "El tipo superreducido del 3 %"), c(A70_26, "El tipo del 0,3 %")]),
    row("reducido", "5", "0.5", "2025-10-21", "",
        "Bebidas refrescantes y gaseosas con azúcares o edulcorantes añadidos (desde el 1/1/2026, refrescos con azúcar añadido de hasta 5 g/100 ml)",
        f"{REGTR} y art. 35 (redacción de Ley 9/2025 de Canarias, BOE-A-2026-7560, disp. final 9.ª.8); {RETR}",
        [c(A32, "El tipo reducido del 5 por ciento"), c(A70, "El tipo del 0,5 por ciento"),
         c(A32_26, "El tipo reducido del 5 %"), c(A70_26, "El tipo del 0,5%"),
         (TR, "a3-7", "BOE-A-2026-7560", "inferior o igual a 5 gramos por 100 mililitros")]),
    row("general", "7", "0.7", "2025-10-21", "", "", f"{REGTR}; {RETR}",
        [c(A32, "El tipo general en el Impuesto General Indirecto Canario es el 7 por ciento"),
         c(A70, "El tipo del 0,7 por ciento"),
         c(A32_26, "El tipo general en el impuesto general indirecto canario es el 7 %"),
         c(A70_26, "El tipo del 0,7%")]),
    row("especifico", "1", "0.1", "2026-01-01", "",
        "Petróleo y productos derivados del refino del petróleo, incluso mezclados con biocarburantes; desde el 1/7/2026 también el gas",
        f"{REGTR}.b y art. 33 bis (añadidos por Ley 9/2025 de Canarias, BOE-A-2026-7560, disp. final 9.ª; art. 33 bis modificado por Decreto-ley 3/2026, BOE-A-2026-12302, art. 2.2); {RETR}",
        [c(A32_26, "El tipo específico del 1 %"),
         c(A70_26, "El tipo del 0,1%, para las importaciones sujetas al tipo específico del 1%"),
         (TR, "a3-13", "BOE-A-2026-12302", "y el gas")]),
    row("incrementado", "9.5", "0.95", "2025-10-21", "", VEHICLES_TR, f"{REGTR} y arts. 39 a 41; {RETR}",
        [c(A32, "El tipo incrementado del 9,5 por ciento"), c(A70, "El tipo del 0,95 por ciento"),
         c(A32_26, "El tipo incrementado del 9,5%"), c(A70_26, "El tipo del 0,95%")]),
    row("incrementado", "15", "1.5", "2025-10-21", "", "", f"{REGTR} y art. 36; {RETR}",
        [c(A32, "El tipo incrementado del 15 por ciento"), c(A70, "El tipo del 1,5 por ciento"),
         c(A32_26, "El tipo incrementado del 15 %"), c(A70_26, "El tipo del 1,5%")]),
    row("especial", "20", "2", "2025-10-21", "",
        "Labores del tabaco, salvo cigarros y cigarritos (incluye los cigarrillos electrónicos desechables)",
        f"{REGTR} y art. 37; {RETR}",
        [c(A32, "El tipo especial del 20 por ciento"), c(A70, "El tipo del 2 por ciento"),
         c(A32_26, "El tipo especial del 20 %"), c(A70_26, "El tipo del 2%"),
         (TR, "a3-9", TRV, "con excepción de los cigarros y cigarritos")]),
]

IGIC_ROWS = LEY_20_1991 + LEY_4_2012 + TEXTO_REFUNDIDO
