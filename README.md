# Datos de referencia

Datos de España en CSV (UTF-8, separados por comas y con cabecera) para reutilizar en cualquier proyecto. Los códigos van como texto para conservar los ceros a la izquierda.

## bancos/

- `bancos_es.csv`: bancos con código de entidad, BIC, nombre y logo en SVG.
- `iban_paises.csv`: estructura del IBAN en los países SEPA.

## direcciones/

- `comunidades_es.csv`: comunidades y ciudades autónomas con código INE, ISO 3166-2, NUTS, coordenadas, bandera y escudo en SVG.
- `provincias_es.csv`: provincias con código INE, comunidad, ISO 3166-2, matrícula, prefijos telefónicos y coordenadas de la capital.
- `municipios_es.csv`: municipios con código INE, dígito de control, isla, NUTS3, población y coordenadas.
- `codigos_postales_es.csv`: códigos postales con su municipio y localidad.
- `tipos_via.csv`: tipos de vía con su abreviatura y sus sinónimos.
- `entidades_locales_es.csv`: ayuntamientos, diputaciones, cabildos, comarcas, mancomunidades y entidades locales menores.
- `nuts_es.csv`: regiones NUTS de España.
- `simbolos_es.csv`: enlaces a la bandera y el escudo de comunidades, provincias y municipios en Wikimedia Commons.
- `paises.csv`: países con códigos ISO, nombre en español, prefijo telefónico, pertenencia a la UE y coordenadas.
- `subdivisiones.csv`: provincias, estados o regiones de 52 países.

## calendario/

- `festivos_es.csv`: fiestas laborales nacionales, autonómicas e insulares de cada año.

## catalogos/

- `cnae_2025.csv`: actividades económicas (CNAE-2025) con su equivalencia en la CNAE-2009.
- `divisas.csv`: divisas ISO 4217 con nombre y símbolo en español.
- `numeracion_telefonica_es.csv`: tipos de número de teléfono no geográficos.
- `matriculas_especiales_es.csv`: matrículas especiales (diplomáticas, militares, cuerpos de seguridad…).

## contabilidad/

- `pgc_es.csv`: cuadro de cuentas del Plan General Contable.

## lugares/

- `estaciones_tren_es.csv`: estaciones de Renfe con código ADIF, municipio, servicios y coordenadas.
- `estaciones_meteo_es.csv`: estaciones meteorológicas de AEMET con indicativo, altitud y coordenadas.
- `playas_es.csv`: playas de AEMET con municipio y coordenadas.

## email/

- `dominios_desechables.csv`: dominios de correo temporal o desechable.

## pagos/

- `redsys_codigos.csv`: códigos de respuesta y errores de Redsys en seis idiomas.

## Actualización

- `scripts/festivos_boe.py` añade los festivos de un año a partir de la resolución del BOE. Una acción de GitHub lo ejecuta los lunes de octubre a enero y abre un PR cuando hay datos nuevos.
- `scripts/redsys_codigos.py` regenera los códigos de Redsys a partir de su librería oficial.

El origen de cada dato está en [FUENTES.md](FUENTES.md) y las licencias de terceros, en `LICENSES/`.
