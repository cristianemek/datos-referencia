# Fuentes

## Direcciones

- **Comunidades, provincias, municipios e islas:** [relación de municipios, provincias, comunidades autónomas y sus códigos](https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177031&menu=ultiDatos&idp=1254734710990) del INE, a 1 de enero de 2026.
- **Códigos postales:** [Callejero del Censo Electoral](https://www.ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259952026632&p=1259952026632&pagename=ProductosYServicios%2FPYSLayout) del INE. Los nombres de municipio están alineados con la relación de 2026.
- **Población:** cifras oficiales del Padrón a 1 de enero de 2025 del INE (Real Decreto 1117/2025), fichero `pobmun25.xlsx` de [pobmun.zip](https://www.ine.es/pob_xls/pobmun.zip).
- **NUTS:** clasificación [NUTS 2024](https://ec.europa.eu/eurostat/web/nuts/overview) de Eurostat, contrastada municipio a municipio con su lista LAU 2025.
- **Tipos de vía:** [tabla de tipos de vía](https://www.ine.es/prodyser/callejero/TiposVia.csv) del callejero del INE, con sus sinónimos.
- **Matrículas provinciales:** anexo XVIII del [Reglamento General de Vehículos](https://www.boe.es/buscar/act.php?id=BOE-A-1999-1826) (Real Decreto 2822/1998). Los códigos anteriores (GE, PM, OR) salen de los Reales Decretos 567/1992, 1209/1997 y 1735/1998.
- **Prefijos telefónicos:** [Plan Nacional de Numeración Telefónica](https://www.boe.es/buscar/act.php?id=BOE-A-2004-21841) (Real Decreto 2296/2004) y las resoluciones de atribución publicadas en el BOE, contrastados con el registro de numeración de la CNMC.
- **Coordenadas:** las de comunidades, municipios y subdivisiones salen de [Wikidata](https://www.wikidata.org/) (CC0), por código INE o ISO 3166-2. Las de provincias (capital) y países salen de [FacturaScripts](https://github.com/NeoRazorX/facturascripts), con los signos de Angola, Argentina y Kenia corregidos.
- **Países:** códigos ISO 3166-1 y nombres en español de [Unicode CLDR](https://cldr.unicode.org/).
- **Subdivisiones de otros países:** nombres de FacturaScripts, con los códigos ISO 3166-2 validados contra [iso-codes](https://salsa.debian.org/iso-codes-team/iso-codes); los que no son válidos se dejan vacíos.
- **Banderas y escudos:** ficheros elegidos en Wikidata (propiedades P41 y P94) y alojados en [Wikimedia Commons](https://commons.wikimedia.org/). Cada imagen tiene su propia licencia y su autor, indicados en `simbolos_es.csv`. Los SVG de `comunidades_es.csv` están optimizados sin cambiar el dibujo: se han comparado píxel a píxel con el original.
- **Estructura del IBAN:** IBAN Registry de SWIFT.

## Calendario

- **Festivos:** resoluciones de la Dirección General de Trabajo con la relación de fiestas laborales de cada año ([2026](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667) y [2027](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-21254)). Las fiestas locales de cada municipio no se publican en el BOE y no están incluidas.

## Catálogos

- **CNAE-2025:** [estructura](https://www.ine.es/daco/daco42/clasificaciones/cnae25/Estructura_CNAE2025.xlsx) y [correspondencia con la CNAE-2009](https://www.ine.es/daco/daco42/clasificaciones/cnae25/Correspondencia_CNAE09_CNAE25.xlsx) del INE; nombres según el [Real Decreto 10/2025](https://www.boe.es/buscar/act.php?id=BOE-A-2025-587).
- **Divisas:** [lista oficial ISO 4217](https://www.six-group.com/en/products-services/financial-information/data-standards.html) de SIX (septiembre de 2026), con nombres y símbolos en español de Unicode CLDR 49.
- **Numeración telefónica y matrículas especiales:** las mismas normas que los prefijos y las matrículas provinciales; cada fila cita su norma en la columna `regulation`.

## Contabilidad

- **Plan General Contable:** cuadro de cuentas del [Real Decreto 1514/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19884), texto consolidado. Se han corregido erratas del propio texto, como los espacios que faltan en «DETERIOROY» o «DONACIONESY».

## Email

- **Dominios desechables:** [disposable/disposable-email-domains](https://github.com/disposable/disposable-email-domains), en la copia que publica [Propaganistas/Laravel-Disposable-Email](https://github.com/Propaganistas/Laravel-Disposable-Email) (octubre de 2026).

## Pagos

- **Redsys:** catálogos de la [librería PHP oficial](https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/librerias-de-integracion/) (versión 2.0.1). En la columna en castellano se han corregido las faltas de ortografía del original (tildes y erratas como «competada» o «parémtro»); la lista completa está en `scripts/redsys_codigos.py`. Los demás idiomas se mantienen tal cual. El código `0000` agrupa los códigos del 0000 al 0099.

## Licencias

- [FacturaScripts](LICENSES/LGPL-3.0-facturascripts.txt): LGPL-3.0.
- [Dominios desechables](LICENSES/MIT-disposable-email-domains.txt): MIT.
- [Unicode CLDR](LICENSES/Unicode-3.0-cldr.txt): licencia Unicode v3.
- INE y Eurostat: reutilización libre citando la fuente (CC BY 4.0).
- Wikidata: CC0.
- BOE: los textos legales no están sujetos a derechos de autor.

## Nota sobre Python

Algunos escudos de `comunidades_es.csv` ocupan más de 128 KB, que es el límite por defecto del módulo `csv` de Python. Para leerlo hay que subirlo con `csv.field_size_limit(sys.maxsize)`.
