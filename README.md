# Datos de referencia

Datos reutilizables en cualquier lenguaje, extraídos de Feten-Back (octubre 2026).

Todos los CSV usan UTF-8 sin BOM, coma como separador, comillas dobles (RFC 4180), fin de línea `\n` y una fila de cabecera. Los booleanos son `1`/`0`.

> Los códigos (`postal_code`, `bank_code`, `province_code`, `municipality_code`) son **texto**: tienen ceros a la izquierda. Al abrirlos en Excel, impórtalos como texto o perderás los ceros.

## bancos/

### `bancos_es.csv`: 94 entidades españolas

| Columna | Ejemplo | Notas |
|---|---|---|
| `country_code` | `ES` | ISO 3166-1 alfa-2 |
| `bank_code` | `0049` | Código de entidad (NRBE) |
| `bic` | `BSCHESMMXXX` | BIC/SWIFT de 11 caracteres |
| `bank_name` | `Banco Santander, S.A.` | Nombre legal |
| `logo` | `<svg …>` | SVG en línea o vacío |

Fuente: lista mensual del BCE de entidades sujetas a reservas mínimas (`fi_mrr_csv`, agosto 2026). Cajasur (0237) y EVO Banco (0239) no aparecen en esa lista y se comprobaron a mano.

### `iban_paises.csv`: estructura del IBAN en 37 países SEPA

| Columna | Ejemplo | Notas |
|---|---|---|
| `country_code` | `ES` | |
| `iban_length` | `24` | Longitud total del IBAN |
| `bank_offset` | `4` | Posición (desde 0) donde empieza el código de entidad |
| `bank_length` | `4` | Longitud del código de entidad |

Fuente: IBAN Registry de SWIFT.

## direcciones/

### `codigos_postales_es.csv`: 40.194 filas

| Columna | Ejemplo | Notas |
|---|---|---|
| `postal_code` | `01001` | |
| `province_code` | `01` | Código INE de provincia |
| `province` | `Araba/Álava` | |
| `municipality_code` | `01059` | Código INE de municipio (5 dígitos) |
| `municipality` | `Vitoria-Gasteiz` | |
| `locality` | `Vitoria-Gasteiz` | Población o núcleo; puede estar vacía |

Un código postal puede tener **varias filas**: hay códigos que abarcan varios municipios, e incluso varias provincias. Por eso la provincia sale de las dos primeras cifras del código INE del municipio y no de las del código postal. Para autorrellenar una dirección, filtra por `postal_code` y agrupa por `municipality_code`.

Fuente: Callejero del Censo Electoral del INE.

### `provincias_es.csv`: 52 provincias

`province_code` (código INE, `01`–`52`) y `province` (nombre oficial, bilingüe donde corresponde).

### `paises.csv`: 250 países

| Columna | Ejemplo | Notas |
|---|---|---|
| `code` | `ES` | ISO 3166-1 alfa-2 |
| `alpha3` | `ESP` | ISO 3166-1 alfa-3 |
| `name` | `España` | Nombre en español (CLDR) |
| `phone_prefix` | `+34` | Puede estar vacío o llevar espacio (`+1 268`) |
| `is_eu` | `1` | Si es miembro de la UE |

## Validar un IBAN

Para portar a cualquier lenguaje:

1. **Normalizar:** quitar todo lo que no sea alfanumérico y pasar a mayúsculas.
2. **Formato:** debe cumplir `^[A-Z]{2}[0-9]{2}[A-Z0-9]+$`.
3. **País:** las dos primeras letras deben estar en `iban_paises.csv`.
4. **Longitud:** debe ser igual a `iban_length`.
5. **Mod-97 (ISO 7064):** mover los 4 primeros caracteres al final, sustituir cada letra por su valor (`A`=10 … `Z`=35) y calcular el número resultante módulo 97. Debe dar `1`. Para no necesitar enteros grandes, se procesa en trozos de 7 dígitos: `resto = int(str(resto) + trozo) % 97`.
6. **Solo España:** comprobar también los dígitos de control del antiguo CCC (ver abajo).

Para obtener el banco, el código de entidad es `iban.substr(bank_offset, bank_length)`. Con ese código se busca en `bancos_es.csv` por `country_code` + `bank_code`, y de ahí salen el BIC, el nombre y el logo.

### Dígitos de control españoles (CCC)

Estructura de un IBAN español: `ES` + 2 dígitos de control IBAN + entidad (4) + oficina (4) + DC (2) + cuenta (10).

```
pesos = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]

digito(diez_digitos):
    d = 11 - (Σ diez_digitos[i] * pesos[i]) % 11
    si d == 10 → 1;  si d == 11 → 0;  si no → d

DC esperado = digito("00" + entidad + oficina) + digito(cuenta)
```

El IBAN es válido si las posiciones 12–13 (desde 0) coinciden con el DC esperado.
