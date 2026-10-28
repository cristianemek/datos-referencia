import re
import sys
from collections import Counter
from pathlib import Path

PATH_TAG = re.compile(r"<path\b([^>]*?)/>")
ATTRIBUTE = re.compile(r'\s([a-zA-Z:-]+)="([^"]*)"')


def main() -> None:
    source, output = Path(sys.argv[1]), Path(sys.argv[2])
    minimum = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    svg = source.read_text(encoding="utf-8")

    if "<use" in svg or re.search(r"\sid=\"", svg) or "<style" in svg:
        sys.exit("El SVG ya usa <use>, id o <style>: no se deduplica para no alterar referencias ni estilos.")

    paths = [dict(ATTRIBUTE.findall(" " + match.group(1))) for match in PATH_TAG.finditer(svg)]
    counts = Counter(attributes.get("d") for attributes in paths if attributes.get("d"))
    shared = {d: f"p{index}" for index, (d, count) in enumerate(counts.most_common()) if count >= minimum}

    def replace(match: re.Match) -> str:
        attributes = dict(ATTRIBUTE.findall(" " + match.group(1)))
        d = attributes.pop("d", None)

        if d not in shared:
            return match.group(0)

        rest = "".join(f' {name}="{value}"' for name, value in attributes.items())

        return f'<use xlink:href="#{shared[d]}"{rest}/>'

    body = PATH_TAG.sub(replace, svg)
    defs = "<defs>" + "".join(f'<path id="{name}" d="{d}"/>' for d, name in shared.items()) + "</defs>"
    root = re.match(r"<svg\b[^>]*>", body).group(0)
    new_root = root if "xmlns:xlink" in root else root[:-1] + ' xmlns:xlink="http://www.w3.org/1999/xlink">'
    result = new_root + defs + body[len(root):]
    output.write_text(result, encoding="utf-8")
    print(f"trazados compartidos: {len(shared)} | apariciones sustituidas: {sum(counts[d] for d in shared)} | {len(svg)} → {len(result)} bytes")


if __name__ == "__main__":
    main()
