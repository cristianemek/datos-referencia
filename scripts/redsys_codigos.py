import csv
import html
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUTPUT = REPO / "pagos" / "redsys_codigos.csv"
DOWNLOADS_PAGE = "https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/librerias-de-integracion/"
USER_AGENT = "Mozilla/5.0 (compatible; datos-referencia; +https://github.com/cristianemek/datos-referencia)"
LANGUAGES = {"1": "es", "2": "en", "3": "ca", "10": "va", "12": "gl", "13": "eu"}
CATALOGS = {"codResponseDescription": "response", "sisErrorDescription": "sis_error"}

SPANISH_FIXES = [
    (r"\bOperacion\b", "Operación"), (r"\boperacion\b", "operación"),
    (r"\bAutenticacion\b", "Autenticación"), (r"\bautenticacion\b", "autenticación"),
    (r"\bConfirmacion\b", "Confirmación"), (r"\bconfirmacion\b", "confirmación"),
    (r"\bTransaccion\b", "Transacción"), (r"\btransaccion\b", "transacción"),
    (r"\bCodigo\b", "Código"), (r"\bcodigo\b", "código"),
    (r"\bparametros\b", "parámetros"), (r"\bparametro\b", "parámetro"), (r"\bparémtro\b", "parámetro"),
    (r"\bdevolucion\b", "devolución"), (r"\bpreautorizacion\b", "preautorización"),
    (r"\bdomiciliacion\b", "domiciliación"), (r"\bvalidacion\b", "validación"),
    (r"\bnotificacion\b", "notificación"), (r"\bredireccion\b", "redirección"),
    (r"\bconexion\b", "conexión"), (r"\bmensajeria\b", "mensajería"), (r"\bnumericas\b", "numéricas"),
    (r"\bdias\b", "días"), (r"\bdebito\b", "débito"), (r"\bmetodo\b", "método"), (r"\bmétoco\b", "método"),
    (r"\bmaximo\b", "máximo"), (r"\bnumero\b", "número"), (r"\bno valido\b", "no válido"),
    (r"\bno esta\b", "no está"), (r"\bEnvia\b", "Envía"),
    (r"\bperdico\b", "perdido"), (r"\bcomecio\b", "comercio"), (r"\bcomerci$", "comercio"),
    (r"\bexcecido\b", "excedido"), (r"\bcnfigurado\b", "configurado"), (r"\baunteticada\b", "autenticada"),
    (r"\bEnrrutamiento\b", "Enrutamiento"), (r"\bBUZUM\b", "BIZUM"), (r"\bcompetada\b", "completada"),
    (r"para genera el\b", "para generar el"), (r"Error en La validación", "Error en la validación"),
    (r"pago Adicional\. se ha", "pago adicional. Se ha"), (r" {2,}", " "),
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def php_library_url() -> str:
    page = fetch(DOWNLOADS_PAGE).decode("utf-8", "replace")

    for match in re.finditer(r'<a[^>]+href="(https://pagosonline\.redsys\.es/download/\d+/[^"]*)"[^>]*>(.*?)</a>', page, re.S):
        if "integración en PHP" in html.unescape(re.sub(r"<[^>]+>", " ", match.group(2))):
            return html.unescape(match.group(1))

    raise RuntimeError("No se encuentra el enlace a la librería PHP en la web de Redsys")


def fix_spanish(text: str) -> str:
    for pattern, replacement in SPANISH_FIXES:
        text = re.sub(pattern, replacement, text)

    return text.strip()


def sort_key(code: str) -> tuple:
    return (code == "z", int(code) if code.isdigit() else 0, code)


def main() -> None:
    url = php_library_url()
    archive = zipfile.ZipFile(io.BytesIO(fetch(url)))
    version = next(
        (re.search(r'VERSION = "([^"]+)"', archive.read(name).decode()).group(1)
         for name in archive.namelist() if name.endswith("src/Version.php")),
        "desconocida",
    )
    rows = []

    for folder, kind in CATALOGS.items():
        catalogs = {
            language: json.loads(archive.read(next(n for n in archive.namelist() if n.endswith(f"resources/{folder}/{number}.json"))))
            for number, language in LANGUAGES.items()
        }
        codes = set(catalogs["es"])

        if any(set(catalog) != codes for catalog in catalogs.values()):
            raise RuntimeError(f"Los idiomas de {folder} no tienen los mismos códigos")

        for code in sorted(codes, key=sort_key):
            published = code.zfill(4) if kind == "response" and code.isdigit() else code
            descriptions = [catalogs[language][code].strip() for language in LANGUAGES.values()]
            rows.append([kind, published, fix_spanish(descriptions[0]), *descriptions[1:]])

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["kind", "code", *(f"description_{language}" for language in LANGUAGES.values())])
    writer.writerows(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"Redsys {version}: {len(rows)} códigos en {OUTPUT.relative_to(REPO)}")


if __name__ == "__main__":
    sys.exit(main())
