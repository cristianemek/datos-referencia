import re
import time

from comun import META, NAMES, RAW, SELECTION, fail_if, http_get, read_json, write_json

PAUSE = 1


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.rsplit(".", 1)[0]).strip("_")


def main() -> None:
    selection = read_json(SELECTION, "select_flags.py")
    meta = read_json(META, "fetch_meta.py")
    files = sorted({s["file"] for s in selection.values() if s["file"]})
    RAW.mkdir(parents=True, exist_ok=True)
    names, downloaded = {}, 0
    for name in files:
        target = RAW / f"{slug(name)}.svg"
        fail_if([name] if target.name in names.values() else [], "Dos banderas con el mismo nombre local")
        names[name] = target.name
        if target.exists() and target.stat().st_size == meta[name]["size"]:
            continue
        data = http_get(meta[name]["url"])
        fail_if([f"{name}: {len(data)} bytes, Commons indica {meta[name]['size']}"] if len(data) != meta[name]["size"] else [],
                "Descarga incompleta")
        target.write_bytes(data)
        downloaded += 1
        time.sleep(PAUSE)
    write_json(NAMES, names)
    print(f"SVG originales: {len(names)} ({downloaded} descargados ahora)")


if __name__ == "__main__":
    main()
