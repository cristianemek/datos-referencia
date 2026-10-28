import re
from html.parser import HTMLParser

COLUMNS = {"1": "name", "2": "official_name", "3": "code", "4": "capital", "5": "demonym"}
EMPTY = {"—", "-", "–"}


class AnnexTable(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.rows: list[list[dict]] = []
        self.row: list[dict] | None = None
        self.cell: dict | None = None
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class") or ""
        if tag == "table" and (self.depth or "annex-5-desktop-table" in classes):
            self.depth += 1
            return
        if not self.depth:
            return
        if tag == "tr":
            self.row = []
        elif tag == "td" and self.row is not None:
            headers = [h.rsplit("__", 1)[-1] for h in (attributes.get("headers") or "").split()]
            self.cell = {"headers": headers, "text": ""}
        elif self.cell is not None and tag == "span" and (self.skip or "fn-marker" in classes):
            self.skip += 1
        elif self.cell is not None and tag == "br":
            self.cell["text"] += " "

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if tag == "table":
            self.depth -= 1
        elif tag == "span" and self.skip:
            self.skip -= 1
        elif tag == "td" and self.cell is not None and self.row is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data: str) -> None:
        if self.cell is not None and not self.skip:
            self.cell["text"] += data


def clean(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return "" if value in EMPTY else value


def parse_annex(document: str) -> list[dict]:
    parser = AnnexTable()
    parser.feed(document)
    entries = []
    for row in parser.rows:
        cells = {c["headers"][0]: clean(c["text"]) for c in row if len(c["headers"]) == 1}
        if not cells.get("3"):
            continue
        entries.append({field: cells.get(column, "") for column, field in COLUMNS.items()})
    if len(entries) < 200:
        raise SystemExit(f"El anexo A5 tiene solo {len(entries)} filas con código: ¿ha cambiado el formato?")
    leftovers = [e["code"] for e in entries if any(re.search(r"\(\d+\)", v) for v in e.values())]
    if leftovers:
        raise SystemExit(f"Quedan llamadas a notas en el anexo A5: {leftovers}")
    return entries
