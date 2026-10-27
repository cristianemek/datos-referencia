# Datos de referencia

Datos de bancos, direcciones, contabilidad y email en CSV (UTF-8, separados por comas, con cabecera) para reutilizar en cualquier proyecto.

## bancos/

- `bancos_es.csv`: bancos españoles con código de entidad, BIC, nombre y logo SVG.
- `iban_paises.csv`: estructura del IBAN en los países SEPA (longitud y posición del código de banco).

## direcciones/

- `codigos_postales_es.csv`: códigos postales de España con provincia, municipio y localidad.
- `municipios_es.csv`: municipios de España con su código INE y coordenadas.
- `provincias_es.csv`: provincias de España con su código INE, código ISO 3166-2 y coordenadas de la capital.
- `paises.csv`: países ISO con nombre en español, prefijo telefónico, pertenencia a la UE y coordenadas.
- `subdivisiones.csv`: provincias, estados o regiones de 52 países, con código ISO 3166-2 y coordenadas cuando están verificados.

## contabilidad/

- `pgc_es.csv`: cuadro de cuentas del Plan General Contable, con nivel (1 grupo, 2 subgrupo, 3 cuenta, 4 y 5 subcuenta) y cuenta padre.

## email/

- `dominios_desechables.csv`: dominios de correo temporal o desechable, para rechazar registros con ellos.

## Fuentes

- Códigos postales y provincias: [Callejero del Censo Electoral del INE](https://www.ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259952026632&p=1259952026632&pagename=ProductosYServicios%2FPYSLayout).
- Coordenadas de municipios y de subdivisiones: [Wikidata](https://www.wikidata.org/) (CC0), por código INE y código ISO 3166-2.
- Países: códigos ISO 3166-1 y nombres en español de [Unicode CLDR](https://cldr.unicode.org/); coordenadas de [FacturaScripts](https://github.com/NeoRazorX/facturascripts).
- Códigos ISO 3166-2 y coordenadas de provincias, y nombres de subdivisiones: [FacturaScripts](https://github.com/NeoRazorX/facturascripts), con los códigos validados contra la lista ISO 3166-2 de [iso-codes](https://salsa.debian.org/iso-codes-team/iso-codes).
- Plan General Contable: [Real Decreto 1514/2007, texto consolidado del BOE](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19884) (actualizado por el Real Decreto 1/2021).
- Estructura del IBAN: IBAN Registry de SWIFT.
- Dominios desechables: [disposable/disposable-email-domains](https://github.com/disposable/disposable-email-domains), en la copia que publica [Propaganistas/Laravel-Disposable-Email](https://github.com/Propaganistas/Laravel-Disposable-Email) (octubre 2026).

Las licencias de los datos de terceros están en `LICENSES/`: LGPL-3.0 para lo que viene de FacturaScripts y MIT para los dominios desechables.
