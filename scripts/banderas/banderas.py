import build_csv
import download
import fetch_meta
import pipeline
import select_flags
from comun import require_node


def main() -> None:
    require_node()
    for step in (select_flags, fetch_meta, download, pipeline, build_csv):
        step.main()


if __name__ == "__main__":
    main()
