# Datos de referencia

Datos de bancos, direcciones, contabilidad y email en CSV (UTF-8, separados por comas, con cabecera) para reutilizar en cualquier proyecto.

## bancos/

- `bancos_es.csv`: bancos españoles con código de entidad, BIC, nombre y logo SVG.
- `iban_paises.csv`: estructura del IBAN en los países SEPA (longitud y posición del código de banco).

## direcciones/

- `codigos_postales_es.csv`: códigos postales de España con provincia, municipio y localidad.
- `comunidades_es.csv`: comunidades y ciudades autónomas con su código INE, código ISO 3166-2, coordenadas, y bandera y escudo en SVG (los originales de Wikimedia Commons, optimizados sin cambiar el dibujo; licencia y autor en `simbolos_es.csv`). Algunos escudos pasan de 128 KB: en Python hay que subir el límite con `csv.field_size_limit(sys.maxsize)`.
- `provincias_es.csv`: provincias de España con su código INE, comunidad autónoma, código ISO 3166-2 y coordenadas de la capital.
- `municipios_es.csv`: municipios de España con su código INE, dígito de control, isla (Baleares y Canarias) y coordenadas.
- `simbolos_es.csv`: enlaces a la bandera y el escudo de comunidades, provincias y municipios en Wikimedia Commons, con su licencia y autor.
- `paises.csv`: países ISO con nombre en español, prefijo telefónico, pertenencia a la UE y coordenadas.
- `subdivisiones.csv`: provincias, estados o regiones de 52 países, con código ISO 3166-2 y coordenadas cuando están verificados.

## contabilidad/

- `pgc_es.csv`: cuadro de cuentas del Plan General Contable, con nivel (1 grupo, 2 subgrupo, 3 cuenta, 4 y 5 subcuenta) y cuenta padre.

## email/

- `dominios_desechables.csv`: dominios de correo temporal o desechable, para rechazar registros con ellos.

## Fuentes

- Códigos postales: [Callejero del Censo Electoral del INE](https://www.ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259952026632&p=1259952026632&pagename=ProductosYServicios%2FPYSLayout).
- Comunidades, provincias, municipios e islas: [relación de municipios, provincias, comunidades autónomas y sus códigos del INE](https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177031&menu=ultiDatos&idp=1254734710990) (1 de enero de 2026).
- Coordenadas de comunidades, municipios y subdivisiones, y banderas y escudos: [Wikidata](https://www.wikidata.org/) (CC0), por código INE y código ISO 3166-2. Las imágenes están en [Wikimedia Commons](https://commons.wikimedia.org/), cada una con la licencia que indica `simbolos_es.csv`.
- Países: códigos ISO 3166-1 y nombres en español de [Unicode CLDR](https://cldr.unicode.org/); coordenadas de [FacturaScripts](https://github.com/NeoRazorX/facturascripts).
- Códigos ISO 3166-2 y coordenadas de provincias, y nombres de subdivisiones: [FacturaScripts](https://github.com/NeoRazorX/facturascripts), con los códigos validados contra la lista ISO 3166-2 de [iso-codes](https://salsa.debian.org/iso-codes-team/iso-codes).
- Plan General Contable: [Real Decreto 1514/2007, texto consolidado del BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19884) (actualizado por el Real Decreto 1/2021).
- Estructura del IBAN: IBAN Registry de SWIFT.
- Dominios desechables: [disposable/disposable-email-domains](https://github.com/disposable/disposable-email-domains), en la copia que publica [Propaganistas/Laravel-Disposable-Email](https://github.com/Propaganistas/Laravel-Disposable-Email) (octubre 2026).

Las licencias de los datos de terceros están en `LICENSES/`: LGPL-3.0 para lo que viene de FacturaScripts y MIT para los dominios desechables.
