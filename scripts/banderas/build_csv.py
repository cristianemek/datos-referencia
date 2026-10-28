import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter

from comun import BUILD, CACHE, META, NAMES, PAISES, RESULTS, SELECTION, fail_if, read_csv, read_json, write_csv

OUTPUT = BUILD / "paises_banderas.csv"
FINAL = CACHE / "final"
HEADER = ["code", "flag_svg", "flag_url", "flag_page_url", "flag_license", "flag_author"]
SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
FORBIDDEN = {"script", "image", "foreignObject"}
EXTERNAL_URL = re.compile(r"url\(\s*[\"']?(?!#)")


def element_problems(element: ET.Element) -> list[str]:
    local = element.tag.split("}")[-1]
    problems = [f"contiene <{local}>"] if local in FORBIDDEN else []
    for name, value in element.attrib.items():
        local_name = name.split("}")[-1]
        if local_name.lower().startswith("on"):
            problems.append(f"atributo {local_name}")
        if name in ("href", XLINK_HREF) and not value.startswith("#"):
            problems.append(f"referencia no local: {value[:60]}")
        if EXTERNAL_URL.search(value):
            problems.append(f"url() no local en {local_name}")
    if local == "style" and (EXTERNAL_URL.search(element.text or "") or "@import" in (element.text or "")):
        problems.append("<style> con referencias externas")
    return problems


def validate(svg: str) -> list[str]:
    problems = ["más de una línea"] if "\n" in svg or "\r" in svg else []
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as error:
        return problems + [f"XML no válido: {error}"]
    root_tag = re.match(r"<svg\b[^>]*>", svg)
    if root.tag != SVG_NS + "svg" or not root_tag:
        problems.append("la raíz no es <svg> en el espacio de nombres SVG")
    elif len(re.findall(r'\sxmlns="', root_tag.group(0))) != 1:
        problems.append("la raíz no tiene exactamente un xmlns")
    if "viewBox" not in root.attrib:
        problems.append("sin viewBox")
    for element in root.iter():
        problems.extend(element_problems(element))
    if re.search(r"https?://", re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", svg)):
        problems.append("contiene http(s):// fuera de las declaraciones xmlns")
    return problems


def main() -> None:
    selection = read_json(SELECTION, "select_flags.py")
    meta = read_json(META, "fetch_meta.py")
    names = read_json(NAMES, "download.py")
    results = read_json(RESULTS, "pipeline.py")
    FINAL.mkdir(parents=True, exist_ok=True)
    rows, problems, sizes, chosen = [], [], {}, Counter()
    for country in read_csv(PAISES):
        code = country["code"]
        file_name = selection[code]["file"]
        if not file_name:
            rows.append({key: code if key == "code" else "" for key in HEADER})
            continue
        report = results[names[file_name][:-len(".svg")]]
        source = CACHE / report["path"]
        svg = source.read_text(encoding="utf-8")
        problems.extend(f"{code}: {issue}" for issue in validate(svg))
        shutil.copyfile(source, FINAL / f"{code}.svg")
        sizes[code] = len(svg.encode("utf-8"))
        chosen[report["chosen"]] += 1
        info = meta[file_name]
        rows.append({
            "code": code, "flag_svg": svg, "flag_url": info["url"], "flag_page_url": info["page_url"],
            "flag_license": info["license"], "flag_author": info["author"],
        })
    fail_if(problems, "SVG que no pasan la validación")
    write_csv(OUTPUT, HEADER, rows)
    print(f"  sin bandera: {', '.join(r['code'] for r in rows if not r['flag_svg'])}")
    print(f"  más pesadas: {', '.join(f'{c} {s}' for c, s in sorted(sizes.items(), key=lambda i: -i[1])[:5])}")
    print(f"  licencias: {dict(Counter(r['flag_license'] for r in rows if r['flag_svg']))}")
    print(f"  variantes: {dict(chosen)}")


if __name__ == "__main__":
    main()
