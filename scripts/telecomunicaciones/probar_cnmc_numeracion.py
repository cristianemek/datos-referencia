import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).resolve().parent / "cnmc_numeracion.py"
CACHE = REPO / "build" / "cache" / "telecomunicaciones"
BD_NUM = CACHE / "bd-num.zip"
ROSCE = CACHE / "rosce.zip"
WORK = CACHE / "pruebas"
SOURCES = {BD_NUM: "https://numeracionyoperadores.cnmc.es/bd-num.zip", ROSCE: "https://numeracionyoperadores.cnmc.es/rosce.zip"}
USER_AGENT = "datos-referencia (https://github.com/cristianemek/datos-referencia)"

ROSCE_ROW = "{name};{nif};Calle Falsa 1 - 28001 Madrid (Madrid);Calle Falsa 1 - 28001 Madrid (Madrid);2020-01-01;SERVICIO TELEFÓNICO FIJO - SERVICIO TELEFÓNICO FIJO;Nacional;01/01/2020"


def ensure_sources() -> None:
    for path, url in SOURCES.items():
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

            with urllib.request.urlopen(request, timeout=120) as response:
                path.write_bytes(response.read())


def rewrite(source: Path, target: Path, member: str | None, change=None, drop=False, extra=None) -> Path:
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename == member and drop:
                continue

            data = zin.read(info.filename)
            zout.writestr(info, change(data) if info.filename == member and change else data)

        if extra:
            zout.writestr(*extra)

    return target


def utf16(change):
    return lambda data: change(data.decode("utf-16-le")).encode("utf-16-le")


def add_rosce_rows(*rows):
    return utf16(lambda text: text + "".join(row + "\r\n" for row in rows))


def run(name: str, bd_num: Path = BD_NUM, rosce: Path = ROSCE, repo: Path = REPO, output: Path | None = None, force=False):
    output = output or WORK / name
    command = [sys.executable, str(SCRIPT), "--bd-num", str(bd_num), "--rosce", str(rosce), "--repo", str(repo), "--salida", str(output)]
    result = subprocess.run(command + (["--forzar"] if force else []), capture_output=True, text=True)

    return result, output


def outputs_text(output: Path) -> str:
    return "".join(path.read_text(encoding="utf-8") for path in output.glob("*.csv"))


def expect_error(name: str, fragment: str, **kwargs) -> bool:
    result, output = run(name, **kwargs)
    message = (result.stderr.strip().splitlines() or [""])[-1]
    ok = result.returncode == 1 and fragment in message and not list(output.glob("*.csv"))
    print(f"{'OK ' if ok else 'MAL'} {name}: {message[:170]}")

    return ok


def expect_success(name: str, absent=(), present=(), **kwargs) -> bool:
    result, output = run(name, **kwargs)
    text = outputs_text(output) + result.stdout + result.stderr
    leaked = [value for value in absent if value in text]
    missing = [value for value in present if value not in outputs_text(output)]
    ok = result.returncode == 0 and not leaked and not missing
    detail = f"filtrado {leaked}" if leaked else (f"falta {missing}" if missing else (result.stderr.strip().splitlines() or ["sin avisos"])[0])
    print(f"{'OK ' if ok else 'MAL'} {name}: {detail[:170]}")

    return ok


def format_cases() -> list[bool]:
    cases = {
        "campo_extra": (BD_NUM, "geograficos.txt", lambda d: d.replace(b"\r\n", b"#X\r\n", 1), "se esperaban 6 campos"),
        "estado_nuevo": (BD_NUM, "moviles.txt", lambda d: d.replace(b"#Asignado#", b"#Reservado#", 1), "estado desconocido"),
        "fecha_iso": (BD_NUM, "tarifasespeciales.txt", lambda d: d.replace(b"#08/07/1999#", b"#1999-07-08#", 1), "fecha no válida"),
        "provincia_rara": (BD_NUM, "geograficos.txt", lambda d: d.replace(b"#Madrid#", b"#Comunidad de Madrid#", 1), "provincia desconocida"),
        "utf8": (BD_NUM, "cortos.txt", lambda d: d.decode("latin-1").encode("utf-8"), "está en UTF-8"),
        "byte_no_cp1252": (BD_NUM, "cortos.txt", lambda d: d.replace(b"\r\n", b"\x81\r\n", 1), "no son cp1252"),
        "bloque_no_numerico": (BD_NUM, "svn_nogeo.txt", lambda d: d.replace(b"511#001#", b"511#0A1#", 1), "debería ser numérico"),
        "rosce_cabecera": (ROSCE, "rosce.csv", utf16(lambda t: t.replace("Ámbito", "Ambito", 1)), "Cabecera inesperada"),
        "rosce_utf8": (ROSCE, "rosce.csv", lambda d: d.decode("utf-16-le").encode("utf-8"), "ya no parece UTF-16"),
        "rosce_campo_desplazado": (ROSCE, "rosce.csv", utf16(lambda t: t.replace(";Nacional;", ";Nacional;extra;", 1)), "sobran campos"),
        "rosce_fecha_imposible": (ROSCE, "rosce.csv", add_rosce_rows(ROSCE_ROW.format(name="X, S.L.", nif="B00000000").replace("2020-01-01", "2020-13-45")), "fecha de notificación no válida"),
    }
    results = []

    for name, (source, member, change, fragment) in cases.items():
        target = rewrite(source, WORK / f"{name}.zip", member, change)
        results.append(expect_error(name, fragment, **({"bd_num": target} if source == BD_NUM else {"rosce": target})))

    results.append(expect_error("falta_fichero", "Faltan en bd-num.zip", bd_num=rewrite(BD_NUM, WORK / "falta.zip", "irm.txt", drop=True)))
    (WORK / "html.zip").write_text("<html>Error 503</html>")
    results.append(expect_error("no_es_zip", "no es un fichero ZIP", bd_num=WORK / "html.zip"))
    results.append(expect_error("zip_inexistente", "No se encuentra", bd_num=WORK / "nada.zip"))
    results.append(expect_error("sin_repo", "No se encuentra", repo=WORK / "no_existe"))
    sms = rewrite(BD_NUM, WORK / "sms_fuera.zip", "sms_mms.txt", lambda d: d + b"29000#EUROCONCURSOS, S.A.#SMS/MMS Premium#01/01/2020#Asignado\r\n")
    results.append(expect_error("sms_fuera_de_catalogo", "no encaja con los tipos esperados", bd_num=sms))
    geo = rewrite(BD_NUM, WORK / "geo_fuera.zip", "geograficos.txt", lambda d: d + b"890#00#Madrid#Asignado#XTRA TELECOM, S.A. UNIPERSONAL#01/01/2020\r\n")
    results.append(expect_error("geografico_fuera_de_catalogo", "no encaja con los tipos esperados", bd_num=geo))

    return results


def privacy_cases() -> list[bool]:
    people = [("PERSONA SIN LETRA", "X1234567"), ("PERSONA NIE OCHO", "X12345678L"), ("PERSONA CON IVA", "ES12345678Z"),
              ("PERSONA SOLO CIFRAS", "12345678"), ("PERSONA CON PREFIJO", "DNI 12345678Z"), ("PÉREZ GARCÍA, JUAN", "00000001R"),
              ("MIEMBROS DE LA COMUNIDAD DE BIENES PRUEBA", "E00000001")]
    rosce = rewrite(ROSCE, WORK / "rosce_personas.zip", "rosce.csv", add_rosce_rows(*(ROSCE_ROW.format(name=n, nif=f) for n, f in people)))
    geo_rows = b"915#99#Madrid#Asignado#PEREZ GARCIA, JUAN#01/01/2020\r\n852#999#M\xe1laga#Asignado#JUAN NADIE#01/01/2020\r\n"
    bd_num = rewrite(BD_NUM, WORK / "bdnum_personas.zip", "geograficos.txt", lambda d: d + geo_rows)
    absent = [name for name, _ in people] + [nif for _, nif in people] + ["PEREZ GARCIA", "JUAN NADIE"]

    return [expect_success("personas_fisicas", absent=absent, present=["91599,915990000"], bd_num=bd_num, rosce=rosce)]


def robustness_cases() -> list[bool]:
    cp1252 = rewrite(BD_NUM, WORK / "cp1252.zip", "cortos.txt", lambda d: d.replace(b"#SINEASEN, S.L.#", b"#SINEASEN\x92S, S.L.#", 1))
    semicolon = rewrite(ROSCE, WORK / "rosce_punto_coma.zip", "rosce.csv", utf16(lambda t: t.replace("Calle Mateu Ferran 6", "Calle Mateu; Ferran 6", 1)))
    entity = rewrite(ROSCE, WORK / "rosce_entidad.zip", "rosce.csv", add_rosce_rows(ROSCE_ROW.format(name="ACME&COPY TELECOM, S.L.", nif="B99999990")))
    nuevo = rewrite(BD_NUM, WORK / "nuevo.zip", None, extra=("nuevo.txt", "x"))
    sin_nomadas = rewrite(BD_NUM, WORK / "sin_svn_geo.zip", "svn_geo.txt", drop=True)
    nomadas_vacio = rewrite(BD_NUM, WORK / "svn_geo_vacio.zip", "svn_geo.txt", lambda d: b"")

    return [
        expect_success("caracter_cp1252", present=["SINEASEN’S, S.L."], bd_num=cp1252),
        expect_success("punto_y_coma_en_domicilio", present=["B65213472"], rosce=semicolon),
        expect_success("entidad_html_sin_punto_y_coma", present=["ACME&COPY TELECOM, S.L."], rosce=entity),
        expect_success("fichero_nuevo_en_zip", bd_num=nuevo),
        expect_success("sin_svn_geo", bd_num=sin_nomadas),
        expect_success("svn_geo_vacio", bd_num=nomadas_vacio),
    ]


def drop_case() -> list[bool]:
    output = WORK / "caida"
    run("caida_base", output=output)
    truncated = rewrite(BD_NUM, WORK / "truncado.zip", "geograficos.txt", lambda d: b"\r\n".join(d.split(b"\r\n")[:100]) + b"\r\n")
    result, _ = run("caida", bd_num=truncated, output=output)
    blocked = result.returncode == 1 and "bajaría de" in result.stderr
    forced, _ = run("caida_forzada", bd_num=truncated, output=output, force=True)
    print(f"{'OK ' if blocked else 'MAL'} caida_de_filas: {result.stderr.strip()[:170]}")
    print(f"{'OK ' if forced.returncode == 0 else 'MAL'} caida_con_forzar: exit={forced.returncode}")

    return [blocked, forced.returncode == 0]


def main() -> None:
    ensure_sources()
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True)
    results = format_cases() + privacy_cases() + robustness_cases() + drop_case()
    print(f"\n{sum(results)} de {len(results)} pruebas superadas")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
