# Datos de referencia

Datos de bancos, direcciones y email en CSV (UTF-8, separados por comas, con cabecera) para reutilizar en cualquier proyecto.

## bancos/

- `bancos_es.csv`: bancos españoles con código de entidad, BIC, nombre y logo SVG.
- `iban_paises.csv`: estructura del IBAN en los países SEPA (longitud y posición del código de banco).

## direcciones/

- `codigos_postales_es.csv`: códigos postales de España con provincia, municipio y localidad.
- `provincias_es.csv`: provincias de España con su código INE.
- `paises.csv`: países ISO con nombre en español, prefijo telefónico y pertenencia a la UE.

## email/

- `dominios_desechables.csv`: dominios de correo temporal o desechable, para rechazar registros con ellos.

## Fuentes

- Códigos postales y provincias: [Callejero del Censo Electoral del INE](https://www.ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259952026632&p=1259952026632&pagename=ProductosYServicios%2FPYSLayout).
- Países: códigos ISO 3166-1 y nombres en español de [Unicode CLDR](https://cldr.unicode.org/).
- Estructura del IBAN: IBAN Registry de SWIFT.
- Dominios desechables: [disposable/disposable-email-domains](https://github.com/disposable/disposable-email-domains), en la copia que publica [Propaganistas/Laravel-Disposable-Email](https://github.com/Propaganistas/Laravel-Disposable-Email) (octubre 2026). Licencia MIT, en `email/LICENSE`.
