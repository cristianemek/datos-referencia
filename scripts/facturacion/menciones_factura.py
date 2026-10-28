import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DESTINO = REPO / "facturacion" / "menciones_factura_es.csv"

RF = "RD 1619/2012 (BOE-A-2012-14696)"
LIVA = "Ley 37/1992 (BOE-A-1992-28740)"
RIVA = "RD 1624/1992 (BOE-A-1992-28925)"
OM = "Orden HAC/1177/2024 (BOE-A-2024-22138)"
RF_EX = f"{RF}, art. 6.1.j y 7.1.i"
RF_ISP = f"{RF}, art. 6.1.m y 7.1.i"
RF_ISP_SERIE = f"{RF}, art. 6.1.a.4.º, 6.1.m y 7.1.i"

HEADER = ["code", "case", "mention", "mention_type", "verifactu_code", "verifactu_field", "regulation"]

GENERAL = [
    ("FACT_DESTINATARIO", "Factura expedida materialmente por el destinatario en nombre y por cuenta del proveedor (art. 5 del Reglamento)", "facturación por el destinatario", "literal", "D", "EmitidaPorTerceroODestinatario", f"{RF}, art. 5.2, 6.1.l y 7.1.i"),
    ("DUPLICADO", "Ejemplar duplicado del original (varios destinatarios de una misma operación o pérdida del original)", "duplicado", "literal", "", "", f"{RF}, art. 14.4"),
    ("VERIFACTU", "Factura expedida por un Sistema de emisión de facturas verificables (VERI*FACTU) que remite todos los registros a la AEAT; alternativa a VERIFACTU_SEDE", "VERI*FACTU", "literal", "", "", f"{RF}, art. 6.5.b y 7.5; {OM}, art. 20.1.b"),
    ("VERIFACTU_SEDE", "Factura expedida por un Sistema de emisión de facturas verificables (VERI*FACTU) que remite todos los registros a la AEAT; alternativa a VERIFACTU", "Factura verificable en la sede electrónica de la AEAT", "literal", "", "", f"{RF}, art. 6.5.b y 7.5; {OM}, art. 20.1.b"),
]

ART20 = [
    ("01", "Servicio postal universal prestado por el operador u operadores que se comprometen a prestarlo"),
    ("02", "Hospitalización o asistencia sanitaria por entidades de Derecho público o privadas en régimen de precios autorizados o comunicados"),
    ("03", "Asistencia a personas físicas por profesionales médicos o sanitarios"),
    ("04", "Entregas de sangre, plasma y demás fluidos, tejidos y elementos del cuerpo humano para fines médicos o de investigación"),
    ("05", "Servicios de estomatólogos, odontólogos, mecánicos dentistas y protésicos dentales, y entrega, reparación y colocación de prótesis dentales y ortopedias maxilares por ellos"),
    ("06", "Servicios prestados a sus miembros por uniones, agrupaciones o entidades autónomas (incluidas AIE) de personas con actividad exenta o no sujeta sin derecho a deducción"),
    ("07", "Entregas y servicios de la Seguridad Social para el cumplimiento de sus fines específicos"),
    ("08", "Servicios de asistencia social de entidades de Derecho público o privadas de carácter social"),
    ("09", "Educación de la infancia y la juventud, guarda y custodia de niños, enseñanza escolar, universitaria y de postgrado, idiomas y formación profesional por entidades públicas o privadas autorizadas"),
    ("10", "Clases particulares por personas físicas sobre materias de los planes de estudios del sistema educativo"),
    ("11", "Cesiones de personal por entidades religiosas inscritas para hospitalización, asistencia social o educación"),
    ("12", "Servicios a sus miembros de entidades sin finalidad lucrativa de naturaleza política, sindical, religiosa, patriótica, filantrópica o cívica (incluidos colegios profesionales, cámaras y organizaciones patronales)"),
    ("13", "Servicios directamente relacionados con el deporte o la educación física prestados a personas físicas por entidades públicas, federaciones deportivas, COE, CPE o entidades deportivas privadas de carácter social"),
    ("14", "Servicios de bibliotecas, archivos, museos, monumentos, representaciones artísticas y exposiciones por entidades públicas o culturales privadas de carácter social"),
    ("15", "Transporte de enfermos o heridos en ambulancias o vehículos especialmente adaptados"),
    ("16", "Operaciones de seguro, reaseguro y capitalización, y su mediación"),
    ("17", "Entregas de sellos de Correos y efectos timbrados de curso legal por importe no superior a su valor facial"),
    ("18", "Operaciones financieras: depósitos, créditos y préstamos, garantías, medios de pago, divisas, valores, su mediación y gestión de IIC y fondos (letras a) a n))"),
    ("19", "Loterías, apuestas y juegos de SELAE, ONCE y organismos autonómicos, y actividades sujetas a los tributos sobre el juego"),
    ("20", "Entregas de terrenos rústicos y demás no edificables"),
    ("22", "Segundas y ulteriores entregas de edificaciones, incluidos los terrenos en que se hallen enclavadas"),
    ("23", "Arrendamientos y derechos reales de goce y disfrute sobre terrenos y edificios destinados exclusivamente a vivienda"),
    ("24", "Entregas de bienes utilizados en operaciones exentas del art. 20 sin derecho a deducción"),
    ("25", "Entregas de bienes cuya adquisición determinó la exclusión total del derecho a deducir (arts. 95 y 96)"),
    ("26", "Servicios profesionales de artistas plásticos, escritores, colaboradores de prensa, compositores, autores audiovisuales, traductores y adaptadores"),
    ("28", "Entregas y servicios de partidos políticos en manifestaciones destinadas a su apoyo financiero"),
]

ART21 = [
    ("1", "1.º", "Exportación de bienes expedidos o transportados fuera de la Comunidad por el transmitente o por su cuenta"),
    ("2", "2.º", "Exportación de bienes expedidos o transportados fuera de la Comunidad por el adquirente no establecido o por su cuenta"),
    ("2B", "2.º.B)", "Entregas en tiendas libres de impuestos bajo control aduanero o a bordo de buques o aeronaves con destino a territorios terceros"),
    ("3", "3.º", "Trabajos sobre bienes muebles adquiridos o importados para ello y expedidos después fuera de la Comunidad"),
    ("4", "4.º", "Entregas a organismos reconocidos que los exporten en el marco de actividades humanitarias, caritativas o educativas"),
    ("5", "5.º", "Servicios, incluidos transporte y operaciones accesorias, directamente relacionados con exportaciones"),
    ("6", "6.º", "Servicios de intermediarios en nombre y por cuenta ajena en operaciones exentas del art. 21"),
    ("7", "7.º", "Exportación de bienes por quien ostente la condición de exportador distinto del transmitente y del adquirente no establecido"),
]

ART22 = [
    ("01", "Uno", "Entregas, construcción, transformación, reparación, mantenimiento, fletamento y arrendamiento de buques de navegación marítima internacional, salvamento, pesca costera o de guerra"),
    ("02", "Dos", "Entregas, arrendamientos, reparaciones y mantenimiento de objetos incorporados o a bordo de esos buques"),
    ("03", "Tres", "Entregas de productos de avituallamiento para esos buques"),
    ("04", "Cuatro", "Entregas, transformación, reparación, mantenimiento, fletamento total o arrendamiento de aeronaves de compañías de navegación aérea internacional o de entidades públicas"),
    ("05", "Cinco", "Entregas, arrendamientos, reparaciones y mantenimiento de objetos incorporados o a bordo de esas aeronaves"),
    ("06", "Seis", "Entregas de productos de avituallamiento para esas aeronaves"),
    ("07", "Siete", "Servicios para las necesidades directas de esos buques y aeronaves o de su cargamento"),
    ("08", "Ocho", "Entregas y servicios en el marco de las relaciones diplomáticas y consulares"),
    ("09", "Nueve", "Entregas y servicios a organismos internacionales reconocidos por España, incluidos los de la Unión, o a su personal con estatuto diplomático"),
    ("10", "Diez", "Entregas y servicios para fuerzas de la OTAN o fuerzas armadas de otros Estados miembros en la política común de seguridad y defensa"),
    ("11", "Once", "Entregas y servicios con destino a otro Estado miembro para fuerzas de la OTAN o fuerzas armadas de otro Estado miembro"),
    ("12", "Doce", "Entregas de oro al Banco de España"),
    ("13", "Trece", "Transporte de viajeros y sus equipajes por vía marítima o aérea con origen o destino fuera del ámbito espacial del impuesto"),
    ("14", "Catorce", "Transporte intracomunitario de bienes con destino o procedencia en las islas Azores o Madeira"),
    ("15", "Quince", "Servicios de intermediarios en nombre y por cuenta ajena en operaciones exentas del art. 22"),
]

ART23 = [
    ("1", "Entregas de bienes en depósito temporal y servicios relacionados con ellas o prestados mientras sigan en esa situación"),
    ("2", "Entregas de bienes conducidos al mar territorial para plataformas de perforación o explotación, y su avituallamiento"),
    ("3", "Servicios relacionados con esas entregas o con importaciones de bienes destinados a esas situaciones"),
    ("4", "Entregas de bienes que se encuentren en esa situación y servicios prestados mientras se mantengan en ella"),
]

ART24 = [
    ("1", "Entregas de bienes vinculados o destinados a zona franca, perfeccionamiento activo, importación temporal, tránsito, depósito aduanero o depósito distinto del aduanero"),
    ("2", "Servicios directamente relacionados con esas entregas"),
    ("3", "Servicios directamente relacionados con importaciones de bienes que se vinculen a esos regímenes o con los bienes vinculados a ellos"),
]

ART25 = [
    ("1", "Uno", "Entrega intracomunitaria de bienes a empresario o persona jurídica con NIF-IVA de otro Estado miembro (exige el NIF del destinatario)"),
    ("2", "Dos", "Entregas de medios de transporte nuevos a otro Estado miembro a particulares o a adquirentes cuyas adquisiciones no estén sujetas en destino"),
    ("3", "Tres", "Transferencia de bienes propios a otro Estado miembro (art. 9.3.º) a la que se aplicaría la exención del apartado Uno"),
    ("4", "Cuatro", "Entregas en el marco de un acuerdo de ventas de bienes en consigna (art. 9 bis.Dos)"),
]

OTHER_EX = [
    ("EX_20BIS", "Entregas de bienes a favor del empresario que facilita la venta a través de una interfaz digital (art. 8 bis.b)", "Artículo 20 bis de la Ley 37/1992", "E6", f"{RF_EX}; {LIVA}, art. 20 bis"),
    ("EX_140BIS_1", "Entregas de oro de inversión, incluidos préstamos, permutas y derivados que transmitan su poder de disposición", "Artículo 140 bis.Uno.1.º de la Ley 37/1992", "E6", f"{RF_EX}; {LIVA}, art. 140 bis.Uno.1.º"),
    ("EX_140BIS_2", "Servicios de mediación en nombre y por cuenta ajena en entregas exentas de oro de inversión", "Artículo 140 bis.Uno.2.º de la Ley 37/1992", "E6", f"{RF_EX}; {LIVA}, art. 140 bis.Uno.2.º"),
    ("EX_143", "Servicios de agencias de viajes en régimen especial cuando los bienes y servicios del viaje se realizan fuera de la Comunidad (junto con REAV)", "Artículo 143 de la Ley 37/1992", "E6", f"{RF_EX}; {LIVA}, art. 143"),
]

ISP = [
    ("ISP_84_2A", "Operaciones sujetas realizadas por no establecidos en el TAI para empresarios o profesionales; el Reglamento solo rige la factura si la expide el destinatario (art. 2.3.b).a'))", "84.Uno.2.º.a", RF_ISP),
    ("ISP_84_2B", "Entregas de oro sin elaborar o de productos semielaborados de oro de ley igual o superior a 325 milésimas", "84.Uno.2.º.b", RF_ISP),
    ("ISP_84_2C", "Entregas de chatarra, desechos y materiales de recuperación (metales, plástico, papel, cartón, vidrio, textiles) y su selección, corte, fragmentación y prensado", "84.Uno.2.º.c", RF_ISP),
    ("ISP_84_2D", "Servicios que tengan por objeto derechos de emisión, reducciones certificadas o unidades de reducción de emisiones de gases de efecto invernadero", "84.Uno.2.º.d", RF_ISP),
    ("ISP_84_2E", "Entregas de inmuebles en proceso concursal, con renuncia a la exención del art. 20.Uno.20.º o 22.º, o en ejecución de garantía", "84.Uno.2.º.e", RF_ISP),
    ("ISP_84_2F", "Ejecuciones de obra y cesiones de personal entre promotor y contratista (o con subcontratistas) para urbanizar terrenos o construir o rehabilitar edificaciones", "84.Uno.2.º.f", RF_ISP),
    ("ISP_84_2G_METALES", "Entregas de plata, platino y paladio en bruto, en polvo o semilabrados; factura en serie especial", "84.Uno.2.º.g", RF_ISP_SERIE),
    ("ISP_84_2G_DISPOSITIVOS", "Entregas de teléfonos móviles, consolas de videojuegos, ordenadores portátiles y tabletas digitales a revendedor, o a otro empresario si superan 10.000 euros sin IVA en la misma factura; factura en serie especial", "84.Uno.2.º.g", RF_ISP_SERIE),
    ("ISP_84_3", "Entregas del art. 26.Tres o servicios de los arts. 69 y 70 por no establecidos a personas jurídicas no empresarias con NIF-IVA español; el Reglamento solo rige la factura si la expide el destinatario (art. 2.3.b).a'))", "84.Uno.3.º", RF_ISP),
    ("ISP_84_4", "Entregas de gas, electricidad, calor o frío por redes localizadas en el TAI por no establecidos a destinatarios con NIF-IVA español; el Reglamento solo rige la factura si la expide el destinatario (art. 2.3.b).a'))", "84.Uno.4.º", RF_ISP),
    ("ISP_140QUINQUE", "Entregas de oro de inversión gravadas por renuncia a la exención (art. 140 ter)", "140 quinque", RF_ISP),
]

SPECIAL = [
    ("ISP_OTRO_EM", "Entrega o servicio de empresario establecido en el TAI, localizado en otro Estado miembro, en el que el sujeto pasivo es el destinatario (p. ej. servicios B2B del art. 69.Uno.1.º)", "inversión del sujeto pasivo", "literal", "N2", "CalificacionOperacion", f"{RF}, art. 2.3.b).b').a''), 6.1.m y 7.1.i"),
    ("MTN_DATOS", "Entregas de medios de transporte nuevos a otro Estado miembro (art. 25 de la Ley 37/1992)", "Características del medio de transporte, fecha de su primera puesta en servicio y distancias recorridas u horas de navegación o vuelo realizadas hasta su entrega", "data", "", "", f"{RF}, art. 6.1.k y 7.1.i; {LIVA}, art. 25"),
    ("REAV", "Operaciones a las que se aplica el régimen especial de las agencias de viajes", "régimen especial de las agencias de viajes", "literal", "05", "ClaveRegimen", f"{RF}, art. 6.1.n, 7.1.i y 16.3; {LIVA}, art. 141"),
    ("REAV_MEDIACION", "Factura de agencia de viajes mediadora en nombre y por cuenta ajena (disp. adic. 4.ª); debe indicar expresamente que se expide al amparo de esa disposición; serie separada", "Disposición adicional cuarta del Reglamento por el que se regulan las obligaciones de facturación (Real Decreto 1619/2012)", "reference", "09", "ClaveRegimen", f"{RF}, disp. adic. 4.ª.2.a"),
    ("REBU_USADOS", "Entregas de bienes usados por revendedores con el régimen especial de bienes usados, objetos de arte, antigüedades y objetos de colección", "régimen especial de los bienes usados", "literal", "03", "ClaveRegimen", f"{RF}, art. 6.1.o, 7.1.i y 16.2.b; {LIVA}, art. 135"),
    ("REBU_ARTE", "Entregas de objetos de arte por revendedores con el régimen especial de bienes usados, objetos de arte, antigüedades y objetos de colección", "régimen especial de los objetos de arte", "literal", "03", "ClaveRegimen", f"{RF}, art. 6.1.o, 7.1.i y 16.2.b; {LIVA}, art. 135"),
    ("REBU_ANTIGUEDADES", "Entregas de antigüedades u objetos de colección por revendedores con el régimen especial de bienes usados, objetos de arte, antigüedades y objetos de colección", "régimen especial de las antigüedades y objetos de colección", "literal", "03", "ClaveRegimen", f"{RF}, art. 6.1.o, 7.1.i y 16.2.b; {LIVA}, art. 135"),
    ("RECC", "Operaciones a las que se aplica el régimen especial del criterio de caja", "régimen especial del criterio de caja", "literal", "07", "ClaveRegimen", f"{RF}, art. 6.1.p y 7.1.i; {RIVA}, art. 61 undecies.1; {LIVA}, art. 163 decies"),
    ("RE_RECARGO", "Entregas de bienes a comerciantes minoristas en recargo de equivalencia; se documentan en factura separada", "Tipo del recargo de equivalencia aplicado y su importe", "data", "", "", f"{RF}, art. 16.4; {LIVA}, art. 154"),
]


def exemption(code, case, mention, vf, regulation):
    return (code, case, mention, "reference", vf, "OperacionExenta", regulation)


def rows():
    out = list(GENERAL)
    out += [exemption(f"EX_20_{n}", case, f"Artículo 20.Uno.{int(n)}.º de la Ley 37/1992", "E1", f"{RF_EX}; {LIVA}, art. 20.Uno.{int(n)}.º") for n, case in ART20]
    out += [exemption(c, case, m, vf, reg) for c, case, m, vf, reg in OTHER_EX[:1]]
    out += [exemption(f"EX_21_{c}", case, f"Artículo 21.{p} de la Ley 37/1992", "E2", f"{RF_EX}; {LIVA}, art. 21.{p}") for c, p, case in ART21]
    out += [exemption(f"EX_22_{c}", case, f"Artículo 22.{p} de la Ley 37/1992", "E3", f"{RF_EX}; {LIVA}, art. 22.{p}") for c, p, case in ART22]
    out += [exemption(f"EX_23_{n}", case, f"Artículo 23.Uno.{n}.º de la Ley 37/1992", "E4", f"{RF_EX}; {LIVA}, art. 23.Uno.{n}.º") for n, case in ART23]
    out += [exemption(f"EX_24_{n}", case, f"Artículo 24.Uno.{n}.º de la Ley 37/1992", "E4", f"{RF_EX}; {LIVA}, art. 24.Uno.{n}.º") for n, case in ART24]
    out += [exemption(f"EX_25_{c}", case, f"Artículo 25.{p} de la Ley 37/1992", "E5", f"{RF_EX}; {LIVA}, art. 25.{p}") for c, p, case in ART25]
    out += [exemption(c, case, m, vf, reg) for c, case, m, vf, reg in OTHER_EX[1:]]
    out += [(code, case, "inversión del sujeto pasivo", "literal", "S2", "CalificacionOperacion", f"{rf}; {LIVA}, art. {art}") for code, case, art, rf in ISP]
    out += SPECIAL
    return out


def main():
    data = rows()
    codes = [r[0] for r in data]
    if len(codes) != len(set(codes)):
        raise SystemExit("códigos duplicados")
    if any(len(r) != len(HEADER) for r in data):
        raise SystemExit("número de columnas incorrecto")
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(data)
    print(f"{DESTINO.relative_to(REPO)}: {len(data)} filas")


main()
