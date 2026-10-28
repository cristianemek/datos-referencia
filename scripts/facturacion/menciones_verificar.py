import csv
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "build" / "cache" / "menciones"
CSV_PATH = REPO / "facturacion" / "menciones_factura_es.csv"
HOY = "20261027"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
BOE_API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{}/texto"
AEAT_WS = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/"
HEADER = ["code", "case", "mention", "mention_type", "verifactu_code", "verifactu_field", "regulation"]

RF = "BOE-A-2012-14696"
LIVA = "BOE-A-1992-28740"
RIVA = "BOE-A-1992-28925"
OM = "BOE-A-2024-22138"

FUENTES = {
    f"{RF}.xml": (BOE_API.format(RF), "application/xml"),
    f"{LIVA}.xml": (BOE_API.format(LIVA), "application/xml"),
    f"{RIVA}.xml": (BOE_API.format(RIVA), "application/xml"),
    f"{OM}.xml": (BOE_API.format(OM), "application/xml"),
    "SuministroInformacion.xsd": (AEAT_WS + "SuministroInformacion.xsd", "application/xml"),
}

LITERAL_SOURCES = {
    "facturación por el destinatario": [(RF, "a6")],
    "duplicado": [(RF, "a14")],
    "VERI*FACTU": [(RF, "a6"), (OM, "a2-2")],
    "Factura verificable en la sede electrónica de la AEAT": [(RF, "a6"), (OM, "a2-2")],
    "inversión del sujeto pasivo": [(RF, "a6")],
    "régimen especial de las agencias de viajes": [(RF, "a6")],
    "régimen especial de los bienes usados": [(RF, "a6")],
    "régimen especial de los objetos de arte": [(RF, "a6")],
    "régimen especial de las antigüedades y objetos de colección": [(RF, "a6")],
    "régimen especial del criterio de caja": [(RF, "a6"), (RIVA, "a61undecies")],
}

EXTRA_PHRASES = {
    "EX": [(RF, "a6", "una referencia a las disposiciones correspondientes de la Directiva 2006/112/CE"), (RF, "a7", "En los supuestos a que se refieren las letras j) a p) del artículo 6.1")],
    "MTN_DATOS": [(RF, "a6", "sus características, la fecha de su primera puesta en servicio y las distancias recorridas u horas de navegación o vuelo realizadas hasta su entrega")],
    "RE_RECARGO": [(RF, "a16", "consignando en ellas el tipo del recargo que se haya aplicado y su importe")],
    "REAV_MEDIACION": [(RF, "dacuaa", "La indicación expresa de que se trata de una factura expedida por la agencia de viajes al amparo de lo previsto en esta disposición adicional")],
    "ISP_OTRO_EM": [(RF, "a2-2", "Cuando la operación esté sujeta en otro Estado miembro, el sujeto pasivo del Impuesto sea el destinatario")],
    "ISP_84_2G_DISPOSITIVOS": [(LIVA, "a84", "Consolas de videojuegos, ordenadores portátiles y tabletas digitales"), (LIVA, "a84", "Teléfonos móviles"), (RF, "a6", "artículo 84, apartado uno, número 2.º, letra g)")],
}

VF_FIELDS = {
    "OperacionExenta": ("OperacionExentaType", "L10"),
    "CalificacionOperacion": ("CalificacionOperacionType", "L9"),
    "ClaveRegimen": ("IdOperacionesTrascendenciaTributariaType", "L8A"),
    "EmitidaPorTerceroODestinatario": ("TercerosODestinatarioType", "L6"),
}

APARTADOS = ["Uno", "Dos", "Tres", "Cuatro", "Cinco", "Seis", "Siete", "Ocho", "Nueve", "Diez", "Once", "Doce", "Trece", "Catorce", "Quince", "Dieciséis"]

errores = []


def fallo(msg):
    errores.append(msg)


def descargar(nombre, forzar):
    destino = CACHE / nombre
    if destino.exists() and destino.stat().st_size > 0 and not forzar:
        return destino
    url, aceptar = FUENTES[nombre]
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": aceptar})
    try:
        with urllib.request.urlopen(peticion, timeout=180) as respuesta:
            datos = respuesta.read()
    except OSError as error:
        raise SystemExit(f"No se pudo descargar {url}: {error}") from error
    if not datos:
        raise SystemExit(f"Descarga vacía: {url}")
    CACHE.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    print(f"descargado {nombre} ({len(datos)} bytes)")
    return destino


def vigente(versiones):
    previas = [v for v in versiones if (v.get("fecha_vigencia") or v.get("fecha_publicacion")) <= HOY]
    return sorted(previas, key=lambda v: (v.get("fecha_vigencia") or "", v.get("fecha_publicacion") or ""))[-1]


def cargar(norma):
    try:
        raiz = ET.parse(CACHE / f"{norma}.xml").getroot()
    except ET.ParseError as error:
        raise SystemExit(f"El texto de {norma} no es XML válido; vuelve a ejecutar con --descargar: {error}") from error
    if raiz.findtext("status/code") != "200":
        raise SystemExit(f"La API del BOE no devolvió el texto de {norma}; vuelve a ejecutar con --descargar")
    bloques = {}
    titulos = {}
    for b in raiz.iter("bloque"):
        versiones = b.findall("version")
        if not versiones:
            continue
        v = vigente(versiones)
        parrafos = ["".join(p.itertext()).strip() for p in v]
        bloques[b.get("id")] = (parrafos, v.get("id_norma"), v.get("fecha_vigencia"))
        if b.get("titulo"):
            titulos[b.get("titulo")] = b.get("id")
    return bloques, titulos


NORMAS = {}
USADOS = set()


def texto(norma, bloque):
    USADOS.add((norma, bloque))
    return "\n".join(NORMAS[norma][0][bloque][0])


def comprobar_formato():
    crudo = CSV_PATH.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        fallo("el CSV tiene BOM")
    if b"\r" in crudo:
        fallo("el CSV contiene CR")
    if not crudo.endswith(b"\n"):
        fallo("el CSV no termina en LF")
    crudo.decode("utf-8")


def comprobar_literal(fila):
    for norma, bloque in LITERAL_SOURCES.get(fila["mention"], []):
        t = texto(norma, bloque)
        abre = [q for q in ("«", "“") if q + fila["mention"] in t]
        if not abre:
            fallo(f"{fila['code']}: literal no encontrado en {norma} {bloque}")
            continue
        cierre = {"«": "»", "“": "”"}[abre[0]]
        if abre[0] + fila["mention"] + cierre not in t:
            print(f"aviso {fila['code']}: en {norma} {bloque} falta la comilla de cierre tras «{fila['mention']}")
    if fila["mention"] not in LITERAL_SOURCES:
        fallo(f"{fila['code']}: literal sin fuente de verificación")


def patron_parte(parte):
    if parte in APARTADOS:
        return re.compile(rf"^{parte}\.")
    m = re.fullmatch(r"(\d+)\.º", parte)
    if m:
        return re.compile(rf"^{m.group(1)}\.?[º°]")
    m = re.fullmatch(r"([A-Z])\)", parte)
    if m:
        return re.compile(rf"^{m.group(1)}\)")
    if re.fullmatch(r"[a-z]", parte):
        return re.compile(rf"^{parte}\)")
    raise ValueError(parte)


def buscar_partes(parrafos, partes):
    desde = 0
    for parte in partes:
        patron = patron_parte(parte)
        idx = next((i for i in range(desde, len(parrafos)) if patron.match(parrafos[i])), None)
        if idx is None:
            return parte
        desde = idx + 1
    return None


def comprobar_isp(fila):
    m = re.search(r"Ley 37/1992 \(BOE-A-1992-28740\), art\. (\d+(?: [a-z]+)?)((?:\.[^ ;]+)?)$", fila["regulation"])
    if not m:
        fallo(f"{fila['code']}: precepto de la Ley no reconocido")
        return
    bloque = NORMAS[LIVA][1].get(f"Artículo {m.group(1)}")
    if not bloque:
        fallo(f"{fila['code']}: artículo {m.group(1)} no encontrado")
        return
    USADOS.add((LIVA, bloque))
    partes = [p for p in re.split(r"\.(?=[A-Za-z0-9])", m.group(2).lstrip(".")) if p]
    falta = buscar_partes(NORMAS[LIVA][0][bloque][0], partes)
    if falta:
        fallo(f"{fila['code']}: no se encuentra {falta} en el art. {m.group(1)}")


def comprobar_letras_reglamento():
    parrafos = NORMAS[RF][0]["a6"][0]
    for letra in "abcdefghijklmnop":
        if not any(p.startswith(f"{letra})") for p in parrafos):
            fallo(f"art. 6.1.{letra} del Reglamento no encontrado")
    for bloque, inicio in (("a7", "i)"), ("a7", "5."), ("a14", "4."), ("a16", "2."), ("a16", "3."), ("a16", "4."), ("a5", "2.")):
        if not any(p.startswith(inicio) for p in NORMAS[RF][0][bloque][0]):
            fallo(f"{bloque} {inicio} del Reglamento no encontrado")


def comprobar_referencia_ley(fila):
    m = re.fullmatch(r"Artículo (\d+(?: bis)?)((?:\.[^ ]+)?) de la Ley 37/1992", fila["mention"])
    if not m:
        fallo(f"{fila['code']}: referencia con formato inesperado")
        return
    bloque = NORMAS[LIVA][1].get(f"Artículo {m.group(1)}")
    if not bloque:
        fallo(f"{fila['code']}: artículo {m.group(1)} no encontrado")
        return
    USADOS.add((LIVA, bloque))
    parrafos = NORMAS[LIVA][0][bloque][0]
    partes = [p for p in re.split(r"\.(?=[A-Z0-9])", m.group(2).lstrip(".")) if p]
    desde = 0
    for parte in partes:
        patron = patron_parte(parte)
        idx = next((i for i in range(desde, len(parrafos)) if patron.match(parrafos[i])), None)
        if idx is None:
            fallo(f"{fila['code']}: no se encuentra {parte} en el art. {m.group(1)}")
            return
        if "(Suprimid" in parrafos[idx]:
            fallo(f"{fila['code']}: {parte} está suprimido")
        desde = idx + 1
    if f"art. {m.group(1)}{m.group(2)}" not in fila["regulation"]:
        fallo(f"{fila['code']}: la columna regulation no cita el mismo precepto")


def comprobar_frases(fila):
    clave = "EX" if fila["code"].startswith("EX_") else fila["code"]
    for norma, bloque, frase in EXTRA_PHRASES.get(clave, []):
        if frase not in texto(norma, bloque):
            fallo(f"{fila['code']}: frase no encontrada en {norma} {bloque}: {frase[:60]}")


def enumeraciones_xsd():
    raiz = ET.parse(CACHE / "SuministroInformacion.xsd").getroot()
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    salida = {}
    for st in raiz.iter("{http://www.w3.org/2001/XMLSchema}simpleType"):
        salida[st.get("name")] = {e.get("value") for e in st.iterfind(".//xs:enumeration", ns)}
    return salida


def listas_om():
    lineas = [l.strip() for l in texto(OM, "an").splitlines() if l.strip()]
    listas = {}
    actual = None
    for l in lineas:
        if re.fullmatch(r"L\d+[A-Z]?", l):
            actual = l
            listas[actual] = set()
        elif actual:
            listas[actual].add(l)
    return listas


def comprobar_verifactu(filas):
    xsd = enumeraciones_xsd()
    om = listas_om()
    for f in filas:
        if not f["verifactu_code"] and not f["verifactu_field"]:
            continue
        tipo, lista = VF_FIELDS.get(f["verifactu_field"], (None, None))
        if not tipo:
            fallo(f"{f['code']}: campo VeriFactu desconocido {f['verifactu_field']}")
            continue
        if f["verifactu_code"] not in xsd.get(tipo, set()):
            fallo(f"{f['code']}: {f['verifactu_code']} no está en {tipo} del XSD")
        if f["verifactu_code"] not in om.get(lista, set()):
            fallo(f"{f['code']}: {f['verifactu_code']} no está en la lista {lista} de la Orden")


def main():
    forzar = "--descargar" in sys.argv[1:]
    for nombre in FUENTES:
        descargar(nombre, forzar)
    NORMAS.update({n: cargar(n) for n in (RF, LIVA, RIVA, OM)})
    if not CSV_PATH.exists():
        raise SystemExit(f"No existe {CSV_PATH.relative_to(REPO)}; ejecuta antes scripts/facturacion/menciones_factura.py")
    comprobar_formato()
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        lector = csv.DictReader(fh)
        if lector.fieldnames != HEADER:
            fallo("cabecera incorrecta")
        filas = list(lector)
    for f in filas:
        if f["mention_type"] == "literal":
            comprobar_literal(f)
        elif f["mention_type"] == "reference" and f["mention"].endswith("Ley 37/1992"):
            comprobar_referencia_ley(f)
        elif f["mention_type"] not in ("reference", "data"):
            fallo(f"{f['code']}: mention_type desconocido")
        if f["code"].startswith("ISP_") and f["code"] != "ISP_OTRO_EM":
            comprobar_isp(f)
        comprobar_frases(f)
    comprobar_letras_reglamento()
    comprobar_verifactu(filas)
    print(f"filas: {len(filas)}")
    for tipo in ("literal", "reference", "data"):
        print(f"  {tipo}: {sum(1 for f in filas if f['mention_type'] == tipo)}")
    print("redacciones vigentes usadas:")
    for norma, bloque in sorted(USADOS):
        parrafos, id_norma, fecha = NORMAS[norma][0][bloque]
        print(f"  {norma} {bloque}: {parrafos[0][:60]} | versión {id_norma} vigente desde {fecha}")
    if errores:
        print("ERRORES:")
        for e in errores:
            print("  " + e)
        sys.exit(1)
    print("OK")


main()
