import collections
import re

import openpyxl

from common import OUT, RAW, clean, phone_list, read_municipios, read_provincias, report, write_csv

SHEET = "DIRECTORIO DE HOSPITALES"
HEADER = [
    "hospital_code", "regcess_code", "name", "address", "postal_code", "province_code", "municipality_code",
    "phone", "beds", "class_code", "class", "dependency_code", "dependency", "complex_code", "complex_name",
]
TEXT_FIXES = {
    "Otras Entidades u o rganismos Públicos": "Otras Entidades u Organismos Públicos",
    "Mútuas Colaboradoras con La Seguridad Social": "Mutuas Colaboradoras con la Seguridad Social",
    "Servicios e Institutos de Salud de Las Comunidades Autónomas": "Servicios e Institutos de Salud de las Comunidades Autónomas",
}
COLUMNS = {
    "CCN": "regcess_code", "CODCNH": "hospital_code", "Nombre Centro": "name", "Dirección": "address",
    "Teléfono": "phone", "Cód. Municipio": "muni6", "Cód. Provincia": "province_code", "Código Postal": "postal_code",
    "CAMAS": "beds", "Cód. Clase de Centro": "class_code", "Clase de Centro": "class",
    "Cód. Dep. Funcional": "dependency_code", "Dependencia Funcional": "dependency",
    "CODIDCOM": "complex_code", "Nombre del Complejo": "complex_name",
}
KEEP = ("name", "class_code", "class", "dependency_code", "complex_code", "complex_name")


def load() -> list:
    wb = openpyxl.load_workbook(RAW / "CNH_2025.xlsx", read_only=True)
    rows = list(wb[SHEET].iter_rows(values_only=True))
    head = [clean(h) for h in rows[0]]
    missing = set(COLUMNS) - set(head)
    if missing:
        raise RuntimeError(f"Columnas ausentes en el CNH: {sorted(missing)}")
    pos = {COLUMNS[h]: i for i, h in enumerate(head) if h in COLUMNS}
    return [{k: clean(r[i]) for k, i in pos.items()} for r in rows[1:] if any(r)]


def address(text: str) -> str:
    return re.sub(r"\s*-\s*$", "", text).strip()


def main() -> None:
    municipios, provincias = read_municipios(), read_provincias()
    stats, issues, rows = collections.Counter(), [], []
    for src in load():
        muni6 = src["muni6"].zfill(6)
        muni = muni6[:5]
        prov = src["province_code"].zfill(2)
        if muni not in municipios:
            stats["municipio_inexistente"] += 1
            issues.append(f"municipio_inexistente\t{src['hospital_code']}\t{muni6}")
            muni = ""
        elif municipios[muni]["check_digit"] != muni6[5]:
            stats["digito_control_distinto"] += 1
            issues.append(f"digito_control\t{src['hospital_code']}\t{muni6}")
        if prov not in provincias or (muni and muni[:2] != prov):
            stats["provincia_incoherente"] += 1
            issues.append(f"provincia\t{src['hospital_code']}\t{prov}\t{muni}")
        beds = re.sub(r"\D", "", src["beds"])
        phone = phone_list(src["phone"])
        if src["phone"] and not phone:
            stats["telefono_descartado"] += 1
            issues.append(f"telefono\t{src['hospital_code']}\t{src['phone']}")
        rows.append({
            **{k: src[k] for k in KEEP},
            "hospital_code": src["hospital_code"].zfill(6),
            "regcess_code": src["regcess_code"].zfill(10),
            "address": address(src["address"]),
            "postal_code": src["postal_code"].zfill(5) if src["postal_code"] else "",
            "province_code": prov,
            "municipality_code": muni,
            "phone": phone,
            "beds": str(int(beds)) if beds else "",
            "dependency": TEXT_FIXES.get(src["dependency"], src["dependency"]),
        })
    rows.sort(key=lambda r: r["hospital_code"])
    write_csv(OUT / "hospitales_es.csv", HEADER, rows)
    lines = [f"filas\t{len(rows)}"] + [f"{k}\t{v}" for k, v in sorted(stats.items())] + issues
    report("hospitales.tsv", lines)


if __name__ == "__main__":
    main()
