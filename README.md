# protocol-core-dist

Envoltura de **distribución** del núcleo `protocol-core` v0.1.0 (Camino P-1,
acta del 9-Oct-2026). Aporta **un solo** ejecutable: `protocol-audit`.

El núcleo sellado no se toca. Este repositorio **copia** el núcleo byte a byte
(ver `VENDOR.md`) y le añade el ejecutable y la puerta que vigila la copia.

## Qué hace

Audita un árbol de archivos contra su manifiesto sellado:

1. lee el manifiesto (`<sha256>  <ruta>`, filas ordenadas en colación C);
2. mide el árbol con `protocol.metrics.manifest` (el núcleo sellado);
3. compara fila por fila y reporta las diferencias por `stderr`;
4. imprime **una sola línea** por `stdout`.

## La línea del contrato

```
AUDIT=<OK|ROJO> RUTAS=<n> SHA256_AGREGADO=<64 hex> MANIFIESTO=<ruta> RC=<0|1>
```

- `RUTAS` cuenta las rutas **medidas**, después de la exclusión.
- `SHA256_AGREGADO` es `sha256` sobre el cuerpo entero del manifiesto
  (etiqueta, dos espacios, ruta UTF-8, salto de línea; en orden C). **No** es el
  árbol: es el manifiesto. Por eso una fila alterada lo deja igual y un
  contenido alterado sí lo mueve.
- `MANIFIESTO` es la ruta del manifiesto tal como se pasó.
- La línea **no lleva hora**: es determinista byte a byte, y así se puede sellar.
- La prosa va **sólo** a `stderr`: telemetría, desglose de divergencias y
  defectos de invocación.

## Códigos de salida

| `RC` | Significado | `stdout` |
| ---- | ----------- | -------- |
| `0`  | el árbol coincide con el manifiesto (`AUDIT=OK`) | la línea |
| `1`  | el árbol **no** coincide (`AUDIT=ROJO`) | la línea |
| `2`  | defecto de invocación: no hubo medición | **vacío** |

`RC=2` no imprime línea a propósito: `RUTAS=0` sería un cero sin base. El `RC`
de la línea siempre es igual al código de salida del proceso.

## Uso

Como módulo, sin instalar nada:

```
PYTHONPATH=src python3 -B -m protocol_audit --raiz ARBOL --manifiesto ARBOL/SHA256SUMS
```

Como ejecutable de consola, tras instalar el paquete:

```
protocol-audit --raiz ARBOL --manifiesto ARBOL/SHA256SUMS
```

Opciones: `--raiz` (obligatoria), `--manifiesto` (obligatoria), `--excluir`
(repetible). `--excluir` enumera **nombres de slug**, uno por uno, y nunca por
subcadena: `--excluir sub` quita el componente `sub`, y `SHA256SUMS` no puede
matar `SHA256SUMS.bak`.

## Qué NO hace

- **No escribe** en el árbol auditado. Cero escrituras, ni `__pycache__`
  (la corrida declarada usa `-B`).
- **No toca** `~/protocol-core`; no lo importa por ruta, no lo instala, no lo
  re-sella.
- **No** descarga nada ni abre red: `dependencies = []` y sólo biblioteca
  estándar.
- **No** certifica la **corrección** del contenido de las filas: certifica que
  la fila **está** y **cuadra**. Un manifiesto con las etiquetas cambiadas de
  fila a fila da rojo; un manifiesto firmado por quien no debe, daría verde.
  Ese juicio no es del ejecutable, es de quien tiene la llave.
- **No** hereda la fecha cierta del sello: la copia no es el sello.

## Puertas

```
python3 -B -m unittest discover -s tests -v
```

- `tests/test_cli.py` — un positivo y sus negativos. Incluye el control
  obligatorio: un objeto alterado a mano **debe** dar `AUDIT=ROJO` y `RC=1`.
  Sin ese control, el verde no valdría.
- `tests/test_vendor.py` — la puerta de la copia: sha256 de cada pieza heredada
  y, si existe `~/protocol-core`, el cotejo vivo y la corrida de la suite
  sellada **contra la copia**.

Motor de pruebas: **uno solo**, la biblioteca estándar (`unittest`). Dos
motores para la misma suite miden dos veces el mismo objeto.
