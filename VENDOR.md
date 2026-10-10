# Procedencia de la copia

Sin este documento, la copia es una afirmación. Con él, es una afirmación
**medible**.

## Origen

| Campo | Valor |
| ----- | ----- |
| Repositorio | `~/protocol-core` (`git@github.com:alexisromtz-lab/protocol-core.git`) |
| Rama | `main` |
| Etiqueta | `v0.1.0` |
| Commit | `2290b6d` |
| Estado del árbol | `git status --porcelain` vacío al copiar |
| Método de copia | `cp -p` (bytes y marcas de tiempo) |

El árbol de origen quedó **intacto**: la distribución vive fuera, en este
repositorio, y no escribe en el núcleo.

## Las ocho piezas copiadas

`sha256` completo, medido sobre la **copia** y sobre el **origen** (coinciden):

| Ruta en este repositorio | Ruta en el origen | `sha256` |
| ------------------------ | ----------------- | -------- |
| `LICENSE` | `LICENSE` | `0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0` |
| `LICENSE_SPEC_CC-BY-4.0.txt` | `LICENSE_SPEC_CC-BY-4.0.txt` | `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411` |
| `SPEC.md` | `SPEC.md` | `9565f56832e7071612a337c0ec6e1efc134253cabbdfae797100472399397ec8` |
| `src/protocol_audit/_vendor/protocol/__init__.py` | `src/protocol/__init__.py` | `ffd3d4a2cfcbec73bd38e40fc000019a3bc179abaf83cc8c630e83552d1876ca` |
| `src/protocol_audit/_vendor/protocol/atomic.py` | `src/protocol/atomic.py` | `f683048ede5e0d484ead274260c7e78bfd13a339ec0a4951832d0bf142d672de` |
| `src/protocol_audit/_vendor/protocol/audit.py` | `src/protocol/audit.py` | `2e5126ae125dd0e946bbfd4971134faecda5a191faeb9fcd1df4f8a4086fad46` |
| `src/protocol_audit/_vendor/protocol/metrics.py` | `src/protocol/metrics.py` | `b0ffe59125d335352eeea25bc90e6765807bab67fc59f58d7c44f4dff062a767` |
| `src/protocol_audit/_vendor/protocol/types.py` | `src/protocol/types.py` | `2c7d13f85a4bce17e5e87cb9dc81266e819d27ad00427851bcc66e72aa685074` |

No se copió `pyproject.toml` del núcleo: este repositorio tiene el suyo. No se
copiaron `README.md`, `NOTICE` ni `CITATION.cff`: ver «Lo que la copia no
hereda».

## Por qué el paquete anidado conserva el nombre `protocol`

El núcleo declara cuatro archivos bajo `src/protocol/`. Copiarlos a
`src/protocol/` en este repositorio instalaría un **segundo** paquete de nivel
superior llamado `protocol`, que colisionaría con el del núcleo en cualquier
entorno donde ambos convivieran. Por eso la copia vive en
`src/protocol_audit/_vendor/protocol/`: anidada, el nombre `protocol` no sale a
la superficie del entorno, y `protocol_audit.cli` la importa de forma relativa
(`from ._vendor.protocol import metrics`). El desvío es deliberado y está
declarado aquí.

## Cómo se vigila la copia

```
python3 -B -m unittest discover -s tests -v
```

`tests/test_vendor.py` sostiene la tabla de arriba en código y además:

1. comprueba que el árbol del vendor **no tiene piezas de más** (una pieza
   suelta dentro del vendor es una copia que nadie vigila). El vendor tiene
   **una** pieza escrita por nosotros — `_vendor/__init__.py`, que lo vuelve
   paquete y declara por qué la copia conserva el nombre `protocol`; no es
   heredada, así que no lleva sello de origen, y se vigila **por su sha256** en
   la segunda tabla (`PROPIAS`): no se deja suelta la pieza que no se copió;
2. comprueba que el ejecutable consume **esta** copia, y no otro `protocol` que
   ande por el sistema;
3. coteja contra `~/protocol-core` cuando el árbol existe (prueba omitida si no);
4. corre la **suite sellada** (26 pruebas, cardinal de v0.1.0) contra la copia:
   copia los tests del origen a un directorio temporal y los ejecuta con
   `PYTHONPATH` apuntando al vendor. Los tests sellados resuelven su paquete
   por `__file__`; sin un `src` hermano, el import cae en el `PYTHONPATH`, o sea
   en la copia. Se comprueba aparte que el import cae ahí de verdad, porque una
   suite que corre contra el original no diría nada de la copia.

## Lo que la copia no hereda

- **La fecha cierta.** El sello de v0.1.0 vale para el árbol sellado, no para
  esta copia. Copiar no sella.
- **El campo `license`.** El `pyproject.toml` sellado no declara campo de
  licencia y este tampoco: elegir la expresión que la resume es un acto del
  dueño del sello, no de la envoltura. Se declara la ausencia; no se improvisa
  el campo.

## Coste declarado del Camino P-1

Dos copias del mismo código pueden divergir. El costo **no** se cierra
prometiendo cuidado: se cierra con la tabla de `sha256` de arriba y su puerta.
Si el núcleo avanza a v0.2.0, esta copia queda marcada como anterior por su
propia puerta hasta que alguien la actualice **declarándolo**.
