# Fuentes

## Bancos

- **Datos de registro de las entidades** (NIF, LEI, tipo, bajas y sucesoras, históricos, entidades de pago): [Registro de Entidades](https://www.bde.es/f/webbe/SGE/regis/ficheros/es/Registro_Entidades.xlsx) del Banco de España, con datos a 22 de octubre de 2026. Fuente: Banco de España. Según su [aviso legal](https://www.bde.es/wbe/es/pie/aviso-legal/), se reproduce sin alterar, así que los nombres y los motivos de baja van tal como los publica, erratas incluidas. El cambio de código de Openbank (de 0224 a 0073) sale de la resolución [BOE-A-2026-11394](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-11394).
- **BIC de las entidades añadidas en octubre de 2026 y de Open Bank:** [fichero de relaciones BIC-LEI](https://www.gleif.org/en/lei-data/lei-mapping/download-bic-to-lei-relationship-files) de GLEIF y SWIFT (septiembre de 2026, CC0), cruzado por el LEI del registro del Banco de España, de la lista de entidades del BCE o de la [API de GLEIF](https://api.gleif.org/). Las sucursales de entidades extranjeras sin BIC español llevan el de la sede central de su matriz, que se reconoce por el país (posiciones 5 y 6 del BIC). Las filiales sin BIC propio, como las financieras de consumo o de leasing, lo llevan vacío.
- **Estructura del IBAN:** IBAN Registry de SWIFT.

## Direcciones

- **Comunidades, provincias, municipios e islas:** [relación de municipios, provincias, comunidades autónomas y sus códigos](https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736177031&menu=ultiDatos&idp=1254734710990) del INE, a 1 de enero de 2026.
- **Códigos postales:** [Callejero del Censo Electoral](https://www.ine.es/ss/Satellite?L=es_ES&c=Page&cid=1259952026632&p=1259952026632&pagename=ProductosYServicios%2FPYSLayout) del INE. Los nombres de municipio están alineados con la relación de 2026.
- **Población:** cifras oficiales del Padrón a 1 de enero de 2025 del INE (Real Decreto 1117/2025), fichero `pobmun25.xlsx` de [pobmun.zip](https://www.ine.es/pob_xls/pobmun.zip).
- **NUTS:** clasificación [NUTS 2024](https://ec.europa.eu/eurostat/web/nuts/overview) de Eurostat, contrastada municipio a municipio con su lista LAU 2025.
- **Superficie, grado de urbanización, costa, ciudad y área urbana funcional de los municipios:** [lista LAU 2025](https://ec.europa.eu/eurostat/documents/345175/501971/EU-27-LAU-2025-NUTS-2024.xlsx) de Eurostat. `degurba` vale 1 (ciudad), 2 (pueblos y suburbios) o 3 (rural); `coastal` vale 1 si el municipio linda con la costa o tiene al menos la mitad de su superficie a menos de 10 km de ella; `city_*` y `fua_*` son la ciudad y el área urbana funcional según las [definiciones de Eurostat](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Glossary:Degree_of_urbanisation). Eurostat avisa de que la superficie la aportan los Estados y no la valida.
- **Partidos judiciales:** [Censo Judicial](https://datos.gob.es/catalogo/e05228601-censo-judicial) del Ministerio de Justicia, actualizado a 25 de marzo de 2026. Origen de los datos: Ministerio de Justicia. El código del partido es el código INE del municipio cabeza de partido.
- **Código DIR3 de los ayuntamientos:** `L01` seguido del código INE del municipio y su dígito de control, contrastado con las unidades de FACe (coincide en los 7.900 ayuntamientos que figuran en ella; el resto factura con unidades propias).
- **Entidades de población:** [Nomenclátor](https://www.ine.es/nomen_files/nacional/es/Nacional_2025.zip) del INE, con la población a 1 de enero de 2025. Los nombres van como los publica el INE, en mayúsculas y con el artículo detrás.
- **Secciones censales:** [seccionado](https://www.ine.es/prodyser/cartografia/seccionado_2026.zip) del INE a 1 de enero de 2026. El centroide y la superficie (geodésica, sobre el elipsoide GRS80) se calculan a partir de los recintos; en secciones con forma de anillo el centroide puede quedar fuera de la sección.
- **Coordenadas y altitud:**
  - Municipios: posición de la capital municipal en el [IGN](https://api-features.ign.es/collections/nuc/items) (núcleos y otras entidades de población). Los 27 municipios cuya capital no está marcada en el IGN conservan las coordenadas de [Wikidata](https://www.wikidata.org/) (CC0).
  - Entidades de población: las del IGN para los núcleos.
  - Comunidades y subdivisiones: Wikidata, por código INE o ISO 3166-2.
  - Provincias (capital) y países: [FacturaScripts](https://github.com/NeoRazorX/facturascripts), con los signos de Angola, Argentina y Kenia corregidos.
- **Tipos de vía:** [tabla de tipos de vía](https://www.ine.es/prodyser/callejero/TiposVia.csv) del callejero del INE, con sus sinónimos.
- **Matrículas provinciales:** anexo XVIII del [Reglamento General de Vehículos](https://www.boe.es/buscar/act.php?id=BOE-A-1999-1826) (Real Decreto 2822/1998). Los códigos anteriores (GE, PM, OR) salen de los Reales Decretos 567/1992, 1209/1997 y 1735/1998.
- **Prefijos telefónicos:** [Plan Nacional de Numeración Telefónica](https://www.boe.es/buscar/act.php?id=BOE-A-2004-21841) (Real Decreto 2296/2004) y las resoluciones de atribución publicadas en el BOE, contrastados con el registro de numeración de la CNMC.
- **Zona horaria:** [tz database](https://www.iana.org/time-zones) de IANA (versión 2026e).
- **Países:**
  - Códigos ISO 3166-1, nombres en español y regiones y subregiones (M49) de [Unicode CLDR](https://cldr.unicode.org/) 49.
  - Nombre oficial, capital y gentilicio: anexo A5 del [Libro de estilo interinstitucional](https://style-guide.europa.eu/o/opportal-service/isg?resource=es/annex-a5-list-countries-territories-currencies.html) de la UE (© Unión Europea).
  - Código de país del INE: lista de países del diccionario del [Censo de 2021](https://www.ine.es/ftp/microdatos/censopv/cen21/dr_CensoPersonas_2021.zip).
  - Prefijo del IVA: [VIES](https://ec.europa.eu/taxation_customs/vies/) de la Comisión Europea.
  - Divisa: la de curso legal según CLDR. Irlanda del Norte (XI), que no está en CLDR, lleva la del Reino Unido según la lista ISO 4217.
- **Subdivisiones de otros países:** nombres de FacturaScripts, con los códigos ISO 3166-2 validados contra [iso-codes](https://salsa.debian.org/iso-codes-team/iso-codes); los que no son válidos se dejan vacíos.
- **Banderas y escudos:** ficheros elegidos en Wikidata (propiedades P41 y P94) y alojados en [Wikimedia Commons](https://commons.wikimedia.org/). Cada imagen tiene su propia licencia y su autor, indicados en `simbolos_es.csv` y, para los países, en las columnas `flag_*` de `paises.csv`. Los SVG incrustados están optimizados sin cambiar el dibujo: se han comparado píxel a píxel con el original a 1.000 y 2.000 px (solo la bandera de las islas Georgias del Sur difiere en un píxel). Algunos territorios usan la bandera del Estado del que dependen.
- **Entidades locales:** [Base de Datos General de Entidades Locales](https://serviciostelematicosext.hacienda.gob.es/sgcief/InventarioBDGEL/Reports) (BDGEL), consulta de entidades vigentes del 27 de octubre de 2026. Origen de los datos: Ministerio de Hacienda. El primer bloque del código es la numeración de comunidades propia de BDGEL, que no coincide con la del INE.

## Calendario

- **Festivos:** resoluciones de la Dirección General de Trabajo con la relación de fiestas laborales de cada año ([2025](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-21316), [2026](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-21667) y [2027](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-21254)). Algunos años una comunidad tiene 13 fiestas porque una es recuperable (en 2025, Cataluña y la Comunitat Valenciana); el detalle está en las notas de la resolución, enlazada en la columna `boe_id`.
- **Fiestas locales:** portales de datos abiertos de cada comunidad, que publican las fiestas que fija cada ayuntamiento: [Andalucía](https://datos.juntadeandalucia.es/api/v0/work-calendar/all?format=csv), [Aragón](https://opendata.aragon.es/), [Asturias](https://descargas.asturias.es/asturias/opendata/CulturayOcio/calendario/dataset_calendario_festivos.csv), [Illes Balears](https://intranet.caib.es/opendatacataleg/), [Castilla y León](https://datosabiertos.jcyl.es/), [Cataluña](https://analisi.transparenciacatalunya.cat/resource/b4eh-r8up), [Extremadura](https://www.juntaex.es/), [Galicia](https://abertos.xunta.gal/), [Comunidad de Madrid](https://datos.comunidad.madrid/), [Región de Murcia](https://datosabiertos.carm.es/), [Navarra](https://datosabiertos.navarra.es/) y [País Vasco](https://opendata.euskadi.eus/). Las demás comunidades no las publican como datos abiertos. Cuando el portal solo da el nombre del municipio, se cruza con los del INE; el registro de la acción muestra los cruces y las filas descartadas. Una fila con `locality` vacía vale para todo el municipio; si una localidad tiene filas propias, sustituyen a las del municipio. En el País Vasco y Navarra se añaden las fiestas comunes a todo el territorio (San Prudencio en Álava, San Ignacio en Bizkaia y Gipuzkoa, San Francisco Javier en Navarra).
- **Cambios de hora:** [Real Decreto 236/2002](https://www.boe.es/buscar/act.php?id=BOE-A-2002-4221) y las órdenes que fijan las fechas de cada periodo (PRE/2211/2006, PRE/2767/2011, PRA/157/2017 y PCM/186/2022); de 1996 a 2001, las Directivas 94/21/CE y 97/44/CE. De 2027 en adelante todavía no hay orden en el BOE: las fechas salen de la [Comunicación de la Comisión C/2026/1660](http://data.europa.eu/eli/C/2026/1660/oj) y de las reglas del Real Decreto 236/2002.

## Catálogos

- **CNAE-2025:** [estructura](https://www.ine.es/daco/daco42/clasificaciones/cnae25/Estructura_CNAE2025.xlsx) y [correspondencia con la CNAE-2009](https://www.ine.es/daco/daco42/clasificaciones/cnae25/Correspondencia_CNAE09_CNAE25.xlsx) del INE; nombres según el [Real Decreto 10/2025](https://www.boe.es/buscar/act.php?id=BOE-A-2025-587).
- **CNO-11:** [estructura](https://www.ine.es/daco/daco42/clasificaciones/cno11_estructura.xls) y [correspondencia con la CIUO-08](https://www.ine.es/daco/daco42/clasificaciones/corr_cno11_ciuo08.xls) del INE; nombres según el anexo del [Real Decreto 1591/2010](https://www.boe.es/buscar/act.php?id=BOE-A-2010-19389).
- **CNED-2014:** estructura de [niveles de formación](https://www.ine.es/daco/daco42/clasificaciones/cned14/CNED14_A_estr.xls) y de [sectores de estudio](https://www.ine.es/daco/daco42/clasificaciones/cned14/CNED_F_estr.xlsx) del INE.
- **Tipos de documento de identidad:** lista L7 de la [Orden HAC/1177/2024](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-22138) (VeriFactu), contrastada con su XSD; tabla T-11 del Sistema RED de la [Seguridad Social](https://www.seg-social.es/descarga/214608) (edición de junio de 2016); letras K, L y M del NIF según los artículos 19 y 20 del [Real Decreto 1065/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-15984). Del NIE, el BOE ([Orden INT/2058/2008](https://www.boe.es/buscar/act.php?id=BOE-A-2008-12050)) solo nombra la X y dice que, agotada su serie, se sigue por orden alfabético; de ahí salen la Y y la Z.
- **Idiomas:** nombres en español y autónimos de Unicode CLDR 49 y códigos ISO 639-2 de la [Library of Congress](https://www.loc.gov/standards/iso639-2/). La cooficialidad sale del artículo 3 de la Constitución y de los Estatutos de Autonomía: País Vasco (art. 6), Navarra (art. 9, solo en la zona vascófona), Cataluña (art. 6, catalán y aranés), Illes Balears (art. 4), Comunitat Valenciana (art. 6) y Galicia (art. 5). El asturiano y el aragonés están protegidos, pero no son oficiales.
- **Formas jurídicas:** lista [ISO 20275](https://www.gleif.org/lei-data/code-lists/iso-20275-entity-legal-forms-code-list) de GLEIF (versión 1.6, CC0), con sus nombres tal cual. La letra del NIF sale de la [Orden EHA/451/2008](https://www.boe.es/buscar/act.php?id=BOE-A-2008-3580), modificada por la Orden HAP/5/2016, o de la ley propia de cada forma (por ejemplo, las SICAV, las SII y las sociedades de capital riesgo son sociedades anónimas, y las cooperativas de crédito son cooperativas). Se deja vacía cuando la Orden no da una letra inequívoca.
- **Letras del NIF:** texto literal de la Orden EHA/451/2008.
- **Unidades de medida:** recomendaciones 20 y 21 de la CEPE/ONU, en la [copia de la Comisión Europea](https://ec.europa.eu/digital-building-blocks/sites/display/DIGITAL/Registry+of+supporting+artefacts+to+implement+EN16931) para la factura electrónica EN 16931 (versión del 15 de noviembre de 2026, CC BY 4.0). La equivalencia con Facturae y el nombre en español salen del XSD de Facturae 3.2.2, solo cuando la correspondencia es inequívoca.
- **Divisas:** [lista oficial ISO 4217](https://www.six-group.com/en/products-services/financial-information/data-standards.html) de SIX, de las vigentes (septiembre de 2026) y de las históricas, con nombres, plurales, símbolos, países de curso legal y redondeo en efectivo de Unicode CLDR 49. Las divisas históricas sin nombre en español en CLDR llevan el nombre inglés de SIX (columna `name_lang`).
- **Numeración telefónica y matrículas especiales:** las mismas normas que los prefijos y las matrículas provinciales; cada fila cita su norma en la columna `regulation`. La numeración geográfica nómada se suprimió en 2026 ([BOE-A-2026-9431](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-9431)), así que sus bloques figuran como geográficos.

## Comercio exterior

- **Nomenclatura Combinada 2026:** [Eurostat](https://data.europa.eu/data/datasets/combined-nomenclature-2026) en EU Vocabularies (Reglamento de Ejecución (UE) 2025/1926), con las unidades suplementarias y los textos autoexplicativos en español. Se han corregido 34 caracteres dañados del original (lista en `scripts/comercio_exterior/nomenclatura_combinada.py`).
- **Intrastat:** anexos de la [Resolución de 24 de enero de 2022](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2022-1361) del Departamento de Aduanas e Impuestos Especiales y el Reglamento de Ejecución (UE) 2020/1197, en su versión consolidada.
- **Incoterms:** códigos y nombres del anexo V de la [resolución del DUA](https://www.boe.es/buscar/act.php?id=BOE-A-2014-7683) y del anexo III de la resolución de Intrastat, con dos erratas corregidas («a costado», «una vez descargas»). No se incluyen los textos de la Cámara de Comercio Internacional, que tienen derechos de autor.

## Contabilidad

- **Plan General Contable:** cuadro de cuentas del [Real Decreto 1514/2007](https://www.boe.es/buscar/act.php?id=BOE-A-2007-19884), texto consolidado. Se han corregido erratas del propio texto, como los espacios que faltan en «DETERIOROY» o «DONACIONESY».

## Email

- **Dominios desechables:** [disposable/disposable-email-domains](https://github.com/disposable/disposable-email-domains), en la copia que publica [Propaganistas/Laravel-Disposable-Email](https://github.com/Propaganistas/Laravel-Disposable-Email) (octubre de 2026).

## Facturación

- **VeriFactu:** [errores](https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tikeV1.0/cont/ws/errores.properties) y esquemas XSD de la AEAT, listas del anexo de la [Orden HAC/1177/2024](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2024-22138) y documento [Validaciones y errores](https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Validaciones_Errores_Veri-Factu.pdf) (versión 1.2.2) para los códigos de IGIC e IPSI. Los mensajes de error van tal cual los devuelve la AEAT, erratas incluidas.
- **Facturae:** [XSD de la versión 3.2.2](https://www.facturae.gob.es/content/dam/facturae/formato/versiones/Facturaev3_2_2.xml). Origen de los datos: Ministerio de Hacienda y Administraciones Públicas - Ministerio de Industria, Energía y Turismo.
- **Unidades de FACe:** [relación de oficinas contables, órganos gestores y unidades tramitadoras](https://proveedores.face.gob.es/api/v1/relations.csv) de FACe. Origen de los datos: Ministerio de Hacienda.
- **Menciones obligatorias:** [Reglamento de facturación](https://www.boe.es/buscar/act.php?id=BOE-A-2012-14696) (Real Decreto 1619/2012), [Ley del IVA](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740), [Reglamento del IVA](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28925) y Orden HAC/1177/2024, en su versión consolidada vigente a 27 de octubre de 2026. `scripts/facturacion/menciones_verificar.py` comprueba cada texto literal contra el BOE.

## Fiscal

- **Tipos de IVA, IGIC e IPSI:** textos consolidados del BOE de la [Ley del IVA](https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740); de la [Ley 20/1991](https://www.boe.es/buscar/act.php?id=BOE-A-1991-14463) y las leyes canarias del IGIC (Ley 4/2012 y [Decreto Legislativo 1/2025](https://www.boe.es/buscar/act.php?id=BOC-j-2025-90249)), y de la [Ley 8/1991](https://www.boe.es/buscar/act.php?id=BOE-A-1991-7645) (IPSI), más las normas que fijan tipos temporales, cada una citada en la columna `regulation`. Los tipos del IPSI salen de las ordenanzas fiscales publicadas en el BOCCE (Ceuta) y el BOME (Melilla). No se incluyen los tipos temporales de 2026 condicionados a la evolución del IPC, porque ninguna fuente oficial confirma si se han aplicado. Las filas están escritas en `scripts/fiscal/` con la frase de la norma que las respalda: el script falla si el BOE publica una versión de un artículo que ya no recoge un tipo vigente. Las ordenanzas del IPSI no tienen texto consolidado, así que sus cambios hay que revisarlos a mano.
- **Canon digital:** importes del anexo del [Real Decreto 209/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-7941) y, para los periodos anteriores, del Real Decreto-ley 12/2017; reglas del artículo 25 del [texto refundido de la Ley de Propiedad Intelectual](https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930) y del Real Decreto 1398/2018. El real decreto prevé revisar los importes antes del 1 de julio de 2026; a 28 de octubre de 2026 no se ha publicado la revisión.
- **Impuesto sobre los envases de plástico no reutilizables:** artículo 78 de la [Ley 7/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-5809) y artículo 11 de la [Ley Foral 14/2023](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2023-10923) de Navarra.

## Lugares

- **Estaciones de tren:** [listado de estaciones](https://ssl.renfe.com/ftransit/Fichero_estaciones/estaciones.csv) y GTFS de Cercanías y de Alta Velocidad, Larga y Media Distancia del [portal de datos abiertos de Renfe](https://data.renfe.com/) (CC BY 4.0), del 27 de octubre de 2026. Los servicios salen de los trenes que circulan en los GTFS.
- **Playas:** [códigos de playas](https://www.aemet.es/documentos/es/eltiempo/prediccion/playas/Playas_codigos.csv) de AEMET. Fuente: AEMET.
- **Estaciones meteorológicas:** inventario de AEMET de 2025 en la copia de [AnCode666/aemet-mcp](https://github.com/AnCode666/aemet-mcp), porque AEMET solo lo publica con clave de acceso. Se han reparado 231 nombres con la codificación dañada usando los de la web de AEMET. Fuente: AEMET.
- **Hospitales:** [Catálogo Nacional de Hospitales 2025](https://www.sanidad.gob.es/estadEstudios/estadisticas/sisInfSanSNS/ofertaRecursos/hospitales/docs/CNH_2025.xlsx) del Ministerio de Sanidad. No trae coordenadas.
- **Centros de salud y consultorios:** [listado mensual](https://regcesslm.sanidad.gob.es/recesAdminWeb/lm/GetExcelListadoMensual?tipoListado=C2) del Registro General de Centros, Servicios y Establecimientos Sanitarios (REGCESS) del Ministerio de Sanidad, tipos C2.3.1 y C2.3.2. No se incluyen los correos electrónicos.
- **Aeropuertos y puertos:** nodos de aeródromo y de puerto del [IGN](https://api-features.idee.es/) (CC BY 4.0). Los puertos de interés general son los del anexo I del [Real Decreto Legislativo 2/2011](https://www.boe.es/buscar/act.php?id=BOE-A-2011-16467). Los códigos OACI o IATA que el IGN repite o tiene mal (detectados al contrastar con [OurAirports](https://ourairports.com/), que no se usa como fuente) se dejan vacíos.
- **UN/LOCODE:** [lista de la CEPE/ONU](https://unlocode.unece.org/) del 23 de octubre de 2026 (CC BY 4.0). El municipio se asigna por nombre exacto, por entidad de población del INE o por coordenadas; se quitan las coordenadas que caen fuera de España o lejos de su municipio.
- **Centros educativos:** [Registro Estatal de Centros Docentes no Universitarios](https://www.educacion.gob.es/centros) del Ministerio de Educación.
- **Universidades:** [Registro de Universidades, Centros y Títulos](https://www.educacion.gob.es/ruct) (RUCT) del Ministerio de Educación.
- **Municipio de estaciones, aeropuertos y puertos:** calculado a partir de las coordenadas con los recintos municipales del IGN (CC BY 4.0).

## Pagos

- **Redsys:** catálogos de la [librería PHP oficial](https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/librerias-de-integracion/) (versión 2.0.1). En la columna en castellano se han corregido las faltas de ortografía del original (tildes y erratas como «competada» o «parémtro»); la lista completa está en `scripts/redsys_codigos.py`. Los demás idiomas se mantienen tal cual. El código `0000` agrupa los códigos del 0000 al 0099.
- **ISO 20022:** [External Code Sets](https://www.iso20022.org/sites/default/files/media/file/ExternalCodeSets_XLSX.zip) del segundo trimestre de 2026, publicados por SWIFT como autoridad de registro. Es una copia no oficial; la versión actualizada está en iso20022.org.
- **Norma 43:** conceptos comunes del [Cuaderno 43](https://www.cajamar.es/storage/documents/1733/cuaderno-43.pdf) de la AEB, la CECA y la UNACC (junio de 2012).

## Telecomunicaciones

- **Numeración asignada, operadores y MNC:** [ficheros de numeración](https://numeracionyoperadores.cnmc.es/bd-num.zip) y [registro de operadores](https://numeracionyoperadores.cnmc.es/rosce.zip) (ROSCE) de la [CNMC](https://numeracionyoperadores.cnmc.es/), del 28 de octubre de 2026. Origen de los datos: Comisión Nacional de los Mercados y la Competencia (CNMC). El NIF de cada operador sale del ROSCE cruzando por el nombre. Del ROSCE solo se publican personas jurídicas: se excluyen las personas físicas, las comunidades de bienes y las sociedades civiles, y no se incluyen domicilios.
- **Portabilidad:** `numeracion_asignada_es.csv` dice a qué operador asignó la CNMC cada bloque, no qué operador presta hoy servicio a un número concreto: un número portado conserva su bloque aunque cambie de operador. Para un número concreto, la única fuente oficial es la [consulta de portabilidad](https://numeracionyoperadores.cnmc.es/portabilidad/movil) de la CNMC, que es individual, tiene captcha y un límite diario, y no debe automatizarse.

## Licencias

- [FacturaScripts](LICENSES/LGPL-3.0-facturascripts.txt): LGPL-3.0.
- [Dominios desechables](LICENSES/MIT-disposable-email-domains.txt): MIT.
- [Unicode CLDR](LICENSES/Unicode-3.0-cldr.txt): licencia Unicode v3.
- [aemet-mcp](LICENSES/MIT-aemet-mcp.txt): MIT.
- INE, Eurostat, IGN, Renfe, Comisión Europea y CEPE/ONU: reutilización libre citando la fuente (CC BY 4.0).
- Ministerios de Hacienda, Justicia, Sanidad y Educación, AEAT, Seguridad Social, AEMET y CNMC: reutilización libre (Ley 37/2007) citando la fuente y la fecha de actualización.
- Banco de España: reproducción fiel, sin alterar los contenidos y citando la fuente.
- Libro de estilo interinstitucional: © Unión Europea, reproducción autorizada citando la fuente.
- Wikidata y GLEIF: CC0. IANA tz database: dominio público.
- Banderas y escudos: la licencia de cada fichero de Wikimedia Commons, indicada junto a él.
- ISO 20022: uso libre según su política de propiedad intelectual. ISO 639-2 de la Library of Congress: solo se toman los códigos.
- Fiestas locales: CC BY 4.0 o equivalente en cada portal autonómico, salvo Galicia (CC BY-SA 4.0, Xunta de Galicia) y la Región de Murcia, que publica las de 2026 con licencia no comercial.
- BOE y boletines autonómicos: los textos legales no están sujetos a derechos de autor.

## Nota sobre Python

Algunos SVG de `comunidades_es.csv` y `paises.csv` ocupan más de 128 KB, que es el límite por defecto del módulo `csv` de Python. Para leerlos hay que subir ese límite con `csv.field_size_limit(sys.maxsize)`.
