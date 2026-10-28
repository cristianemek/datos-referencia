# Datos de referencia

Datos de España en CSV para reutilizar en cualquier proyecto: bancos, territorio, calendario, catálogos oficiales, facturación, fiscalidad, lugares y telecomunicaciones. Todo sale de fuentes oficiales, citadas en [FUENTES.md](FUENTES.md), y se regenera con los scripts del repo.

## Formato

- UTF-8 sin BOM, separado por comas, saltos de línea LF y una fila de cabecera con nombres en inglés (`snake_case`).
- Los códigos son texto: hay que leerlos como cadenas para no perder los ceros a la izquierda (`01001`, `0049`).
- Fechas en ISO 8601 (`2026-10-12`), decimales con punto y booleanos como `1` y `0`.
- Si una celda tiene varios valores, van separados por `|`.
- Coordenadas en grados decimales WGS84.
- Logos, banderas y escudos van incrustados como SVG en una sola línea. Algunos pasan de 128 KB, el límite por defecto del módulo `csv` de Python (ver [FUENTES.md](FUENTES.md#nota-sobre-python)).

## Uso

Python:

```python
import csv

with open("direcciones/municipios_es.csv", encoding="utf-8", newline="") as f:
    municipios = {fila["municipality_code"]: fila for fila in csv.DictReader(f)}

print(municipios["28079"]["municipality"])  # Madrid
```

Con pandas, `pd.read_csv(ruta, dtype=str)` mantiene los códigos como texto.

PHP:

```php
$fichero = fopen('bancos/bancos_es.csv', 'r');
$cabecera = fgetcsv($fichero);
while (($fila = fgetcsv($fichero)) !== false) {
    $banco = array_combine($cabecera, $fila);
}
```

Las tablas se relacionan por sus códigos: `municipality_code`, `province_code` y `ccaa_code` son los del INE, y los países usan ISO 3166-1 alfa-2.

## [bancos/](bancos/)

- [`bancos_es.csv`](bancos/bancos_es.csv): entidades de crédito con código de entidad, BIC, nombre, NIF, LEI, tipo, situación (con fecha de baja y entidad sucesora) y logo en SVG (`logo_on_dark` indica los que solo se ven sobre fondo oscuro).
- [`bancos_historicos_es.csv`](bancos/bancos_historicos_es.csv): códigos de entidad dados de baja, con motivo y sucesora.
- [`entidades_pago_es.csv`](bancos/entidades_pago_es.csv): entidades de pago, de dinero electrónico y establecimientos financieros de crédito.
- [`tipos_entidad_bde.csv`](bancos/tipos_entidad_bde.csv): tipos de entidad del registro del Banco de España.
- [`iban_paises.csv`](bancos/iban_paises.csv): estructura del IBAN en los países SEPA.

## [direcciones/](direcciones/)

- [`comunidades_es.csv`](direcciones/comunidades_es.csv): comunidades y ciudades autónomas con código INE, ISO 3166-2, NUTS, zona horaria, coordenadas, bandera y escudo en SVG.
- [`provincias_es.csv`](direcciones/provincias_es.csv): provincias con código INE, comunidad, ISO 3166-2, matrícula, prefijos telefónicos, zona horaria y coordenadas de la capital.
- [`municipios_es.csv`](direcciones/municipios_es.csv): municipios con código INE, dígito de control, código DIR3, isla, NUTS3, partido judicial, población, superficie, grado de urbanización, ciudad y área urbana de Eurostat, coordenadas y altitud de la capital.
- [`partidos_judiciales_es.csv`](direcciones/partidos_judiciales_es.csv): partidos judiciales con su provincia.
- [`entidades_poblacion_es.csv`](direcciones/entidades_poblacion_es.csv): entidades colectivas, singulares, núcleos y diseminados del Nomenclátor, con población y coordenadas.
- [`secciones_censales_es.csv`](direcciones/secciones_censales_es.csv): secciones censales con su distrito, centroide y superficie.
- [`codigos_postales_es.csv`](direcciones/codigos_postales_es.csv): códigos postales con su municipio y localidad.
- [`tipos_via.csv`](direcciones/tipos_via.csv): tipos de vía con su abreviatura y sus sinónimos.
- [`entidades_locales_es.csv`](direcciones/entidades_locales_es.csv): ayuntamientos, diputaciones, cabildos, comarcas, mancomunidades y entidades locales menores.
- [`nuts_es.csv`](direcciones/nuts_es.csv): regiones NUTS de España.
- [`simbolos_es.csv`](direcciones/simbolos_es.csv): enlaces a la bandera y el escudo de comunidades, provincias y municipios en Wikimedia Commons.
- [`paises.csv`](direcciones/paises.csv): países con códigos ISO, nombre y nombre oficial en español, capital, gentilicio, prefijos telefónico y de IVA, divisa, pertenencia a la UE, región, código INE, coordenadas y bandera en SVG.
- [`subdivisiones.csv`](direcciones/subdivisiones.csv): provincias, estados o regiones de 52 países.

## [calendario/](calendario/)

- [`festivos_es.csv`](calendario/festivos_es.csv): fiestas laborales nacionales, autonómicas e insulares de cada año.
- [`festivos_locales_es.csv`](calendario/festivos_locales_es.csv): fiestas locales de cada municipio, en las comunidades que las publican como datos abiertos.
- [`cambios_hora_es.csv`](calendario/cambios_hora_es.csv): fechas y horas de los cambios de hora desde 1996.

## [catalogos/](catalogos/)

- [`cnae_2025.csv`](catalogos/cnae_2025.csv): actividades económicas (CNAE-2025) con su equivalencia en la CNAE-2009.
- [`cno_11.csv`](catalogos/cno_11.csv): ocupaciones (CNO-11) con su equivalencia en la CIUO-08.
- [`cned_2014_niveles.csv`](catalogos/cned_2014_niveles.csv) y [`cned_2014_sectores.csv`](catalogos/cned_2014_sectores.csv): niveles de formación y sectores de estudio (CNED-2014).
- [`formas_juridicas_es.csv`](catalogos/formas_juridicas_es.csv): formas jurídicas (ISO 20275) con sus abreviaturas y la letra del NIF.
- [`letras_nif_es.csv`](catalogos/letras_nif_es.csv): letras iniciales del NIF de personas jurídicas y entidades sin personalidad jurídica.
- [`tipos_documento_identidad.csv`](catalogos/tipos_documento_identidad.csv): tipos de documento de identidad de VeriFactu y de la Seguridad Social, y letras del NIF y del NIE de personas físicas.
- [`idiomas.csv`](catalogos/idiomas.csv): idiomas con códigos ISO 639, nombre en español y en la propia lengua, y comunidades donde son cooficiales.
- [`divisas.csv`](catalogos/divisas.csv): divisas ISO 4217 con nombre, plural, símbolos, países de curso legal y redondeo en efectivo.
- [`divisas_historicas.csv`](catalogos/divisas_historicas.csv): divisas retiradas, como la peseta, con su fecha de retirada.
- [`unidades_medida.csv`](catalogos/unidades_medida.csv): unidades de medida de la factura electrónica (CEPE/ONU) con su equivalencia en Facturae.
- [`numeracion_telefonica_es.csv`](catalogos/numeracion_telefonica_es.csv): tipos de número de teléfono por prefijo.
- [`matriculas_especiales_es.csv`](catalogos/matriculas_especiales_es.csv): matrículas especiales (diplomáticas, militares, cuerpos de seguridad…).

## [comercio_exterior/](comercio_exterior/)

- [`nomenclatura_combinada_2026.csv`](comercio_exterior/nomenclatura_combinada_2026.csv): códigos de producto de 8 dígitos de la Nomenclatura Combinada (la base del TARIC) con su jerarquía y unidad suplementaria.
- [`incoterms.csv`](comercio_exterior/incoterms.csv): condiciones de entrega del DUA y de Intrastat.
- [`intrastat_naturaleza_transaccion.csv`](comercio_exterior/intrastat_naturaleza_transaccion.csv) y [`intrastat_modos_transporte.csv`](comercio_exterior/intrastat_modos_transporte.csv): listas de la declaración Intrastat.

## [contabilidad/](contabilidad/)

- [`pgc_es.csv`](contabilidad/pgc_es.csv): cuadro de cuentas del Plan General Contable.

## [facturacion/](facturacion/)

- [`menciones_factura_es.csv`](facturacion/menciones_factura_es.csv): textos que debe llevar la factura en cada caso (exenciones, inversión del sujeto pasivo, regímenes especiales…) con su clave de VeriFactu.
- [`verifactu_claves.csv`](facturacion/verifactu_claves.csv) y [`verifactu_errores.csv`](facturacion/verifactu_errores.csv): listas de claves y códigos de error de VeriFactu.
- [`facturae_codigos.csv`](facturacion/facturae_codigos.csv): listas de códigos de Facturae.
- [`face_unidades.csv`](facturacion/face_unidades.csv): oficinas contables, órganos gestores y unidades tramitadoras de FACe.

## [fiscal/](fiscal/)

- [`tipos_impositivos_es.csv`](fiscal/tipos_impositivos_es.csv): tipos de IVA, IGIC e IPSI con su recargo y su periodo de vigencia.
- [`canon_digital_es.csv`](fiscal/canon_digital_es.csv) y [`canon_digital_reglas_es.csv`](fiscal/canon_digital_reglas_es.csv): importes del canon digital por equipo y reglas de aplicación.
- [`gravamenes_producto_es.csv`](fiscal/gravamenes_producto_es.csv): impuesto sobre los envases de plástico no reutilizables.

## [lugares/](lugares/)

- [`estaciones_tren_es.csv`](lugares/estaciones_tren_es.csv): estaciones de Renfe con código ADIF, municipio, servicios y coordenadas.
- [`aeropuertos_es.csv`](lugares/aeropuertos_es.csv): aeropuertos, aeródromos y helipuertos con códigos OACI e IATA, municipio, altitud y coordenadas.
- [`puertos_es.csv`](lugares/puertos_es.csv): puertos con municipio, UN/LOCODE, si son de interés general y coordenadas.
- [`unlocode_es.csv`](lugares/unlocode_es.csv): códigos UN/LOCODE de España con su municipio y coordenadas.
- [`hospitales_es.csv`](lugares/hospitales_es.csv): hospitales del Catálogo Nacional de Hospitales.
- [`centros_salud_es.csv`](lugares/centros_salud_es.csv): centros de salud y consultorios de atención primaria.
- [`centros_educativos_es.csv`](lugares/centros_educativos_es.csv): centros educativos no universitarios.
- [`universidades_es.csv`](lugares/universidades_es.csv): universidades con su código RUCT.
- [`estaciones_meteo_es.csv`](lugares/estaciones_meteo_es.csv): estaciones meteorológicas de AEMET con indicativo, altitud y coordenadas.
- [`playas_es.csv`](lugares/playas_es.csv): playas de AEMET con municipio y coordenadas.

## [email/](email/)

- [`dominios_desechables.csv`](email/dominios_desechables.csv): dominios de correo temporal o desechable.

## [pagos/](pagos/)

- [`redsys_codigos.csv`](pagos/redsys_codigos.csv): códigos de respuesta y errores de Redsys en seis idiomas.
- [`iso20022_codigos.csv`](pagos/iso20022_codigos.csv): códigos externos de ISO 20022 usados en SEPA (motivos de devolución, propósito, estados…).
- [`norma43_conceptos.csv`](pagos/norma43_conceptos.csv): conceptos comunes de los extractos bancarios en Norma 43.

## [telecomunicaciones/](telecomunicaciones/)

- [`numeracion_asignada_es.csv`](telecomunicaciones/numeracion_asignada_es.csv): bloques de numeración telefónica con el operador al que se asignaron.
- [`operadores_telecom_es.csv`](telecomunicaciones/operadores_telecom_es.csv): operadores de telecomunicaciones registrados en la CNMC (solo personas jurídicas).
- [`mnc_es.csv`](telecomunicaciones/mnc_es.csv): códigos de red móvil (MCC y MNC).

## Cómo funciona

Cada CSV sale de un script de [`scripts/`](scripts/) que descarga su fuente oficial, la procesa y la valida. Si el formato de la fuente cambia o algo no cuadra (códigos que no existen, totales que no suman, filas repetidas…), el script falla con un mensaje y no escribe nada, para que nunca entre un dato dudoso sin revisarlo.

- **Ficheros nuevos:** cada script escribe directamente su CSV.
- **Columnas de ficheros existentes:** los scripts que amplían un CSV, como los que añaden la superficie de Eurostat a `municipios_es.csv`, dejan esas columnas en `build/` (fuera del repo), y [`scripts/unir_columnas.py`](scripts/unir_columnas.py) las une por su código con un orden de columnas fijo.
- **Datos tomados de normas:** los tipos de IVA, el canon digital o las menciones de factura van escritos en el script junto con la frase literal de la norma que los respalda, y el script comprueba esa frase contra el texto vigente del BOE.

### Acciones de GitHub

| Acción | Cuándo | Qué hace |
|---|---|---|
| [Festivos del BOE](.github/workflows/festivos.yml) | Lunes de octubre a enero | Busca la resolución de fiestas laborales del año siguiente y abre un PR. |
| [Fiestas locales](.github/workflows/festivos_locales.yml) | Días 1 y 15 de cada mes | Descarga las fiestas locales de los portales autonómicos y abre un PR. |
| [Actualización de los datos](.github/workflows/actualizacion.yml) | Día 3 de cada mes | Ejecuta [`scripts/actualizar_datos.py`](scripts/actualizar_datos.py), que regenera todos los datos y une las columnas, y abre un PR con un informe de los pasos que fallan, las entidades nuevas del Banco de España y los ficheros cambiados. |
| [Vigilancia de normas](.github/workflows/vigilancia_normas.yml) | Lunes | Ejecuta [`scripts/vigilancia_normas.py`](scripts/vigilancia_normas.py) y abre un issue si el BOE cambia algo de lo que dependen los datos, por ejemplo un tipo nuevo del IGIC. |

Los PR no se fusionan solos: hay que revisar el diff. Algunas fuentes no responden desde GitHub (los portales de fiestas locales de Asturias, Castilla y León y Galicia, y los boletines de Ceuta); en ese caso se conservan sus datos anteriores y el PR lo indica.

### Ejecutar en local

Hace falta Python 3.10 o posterior con las librerías de [`scripts/requirements.txt`](scripts/requirements.txt), `pdftotext` (poppler-utils) y, para las banderas, Node.js. Desde la raíz del repo:

```sh
pip install -r scripts/requirements.txt
npm ci --prefix scripts/banderas
python3 scripts/actualizar_datos.py        # todo
python3 scripts/territorio/zonas_horarias.py  # o un script suelto
python3 scripts/unir_columnas.py           # tras un script que deja columnas en build/
python3 scripts/festivos_locales/festivos_locales.py --ccaa 03,07,12
```

Los scripts no necesitan argumentos.

## Licencia

- Los scripts tienen licencia [MIT](LICENSE).
- La selección, la limpieza y las correcciones de los datos tienen licencia [CC BY 4.0](LICENSES/CC-BY-4.0.txt): se pueden reutilizar citando este repositorio.
- Los datos de terceros conservan la licencia de su fuente, indicada en [FUENTES.md](FUENTES.md); las que exigen incluir su texto están en [`LICENSES/`](LICENSES/). Hay que tener en cuenta sobre todo:
  - las banderas y los escudos, que llevan la licencia de cada fichero de Wikimedia Commons;
  - las fiestas locales de Galicia (CC BY-SA 4.0) y de la Región de Murcia (no comercial en 2026);
  - los datos del Banco de España, que se pueden reproducir sin alterarlos y citando la fuente.
