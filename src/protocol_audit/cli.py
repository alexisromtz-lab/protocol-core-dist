"""cli.py — `protocol-audit`: cuenta y compara, en frío.

UNIVERSO DECLARADO: el árbol que `--raiz` nombra, menos el conjunto declarado
`E` de slugs (el nombre del manifiesto auditado, más lo que `--excluir`
enumere *uno por uno*). `E` se enumera por slug y nunca por subcadena: una
subcadena mata archivos ajenos (SPEC §3.c.2). MOTOR: biblioteca estándar de
Python (sin red, sin credenciales, sin dependencias de ejecución). RELOJ: el
CLI **no lee el reloj** — la línea del contrato no lleva sello de tiempo y dos
corridas sobre el mismo objeto dan los mismos bytes.

La línea que este CLI imprime en stdout es el contrato (Acta P-1, §2, cláusula
1). Su gramática, declarada en un solo sitio:

    AUDIT=<OK|ROJO> RUTAS=<n> SHA256_AGREGADO=<64hex> MANIFIESTO=<ruta> RC=<0|1>

Reglas que la línea cumple y que `tests/test_cli.py` exige:

  * stdout lleva **exactamente esa línea**: ASCII, terminada en LF, y nada más.
    Ni siquiera `--help` escribe en stdout: la ayuda va a stderr.
  * `RUTAS` = número de objetos **regulares** del árbol medido (el árbol menos
    `E`). El ancho declarado es el objeto, no su contenido.
  * `SHA256_AGREGADO` = sha256 del cuerpo canónico del manifiesto medido, esto
    es, de la concatenación `<hexdigest>  <ruta>\\n` de las entradas que el
    núcleo devuelve ya ordenadas byte a byte (colación C, SPEC §3.d.2). Es el
    mismo cuerpo que el formato `SHA256SUMS` escribe: el árbol entero leído
    como un solo documento.
  * `MANIFIESTO` = la ruta declarada, tal como se recibió.
  * `AUDIT=OK` ⇔ las filas ordenadas medidas son idénticas a las filas
    ordenadas declaradas (misma ruta, misma etiqueta). El orden del fichero no
    se adjudica: el CLI ordena las dos listas con el mismo metro antes de
    comparar.
  * `RC`: **0** medido y coincide · **1** medido y diverge · **2** NO medido
    (defecto de invocación, o defecto del objeto que impide medir: raíz
    inexistente, manifiesto ilegible o mal formado, nombre fuera del alfabeto
    §2.1, objeto que no es fichero regular ni directorio). En `RC=2` no se
    imprime línea: escribir `RUTAS=0` sobre algo que no se midió sería un cero
    sin base declarada. El `RC` de la línea y el del proceso coinciden siempre.

Un CLI **cuenta y compara**: certifica la **presencia** del objeto —que la fila
está y cuadra—, **no la corrección** de su contenido. No escribe una sola línea
en el árbol auditado, no abre la red y no sella nada.

Gate: `python3 -B -m unittest discover -s tests -v`, desde la raíz del repo.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from ._vendor.protocol import metrics as _metrics
from ._vendor.protocol.types import (
    ConjuntoDeclarado,
    ContratoViolado,
    FuenteT0,
    Manifiesto,
    Namespace,
    ProtocoloError,
    RutaRelativa,
    Slug,
)

__all__ = ["GRAMATICA", "NOMBRE_MAX_DECLARADO", "VERSION", "VOLUMEN_DECLARADO", "main"]

VERSION = "0.1.0"
GRAMATICA = "AUDIT=<OK|ROJO> RUTAS=<n> SHA256_AGREGADO=<64hex> MANIFIESTO=<ruta> RC=<0|1>"

# §2.1: el alfabeto de un slug no distingue aquí; se declaran los parámetros del
# namespace por lo que son —parámetros— aunque `manifest` no los lea.
NOMBRE_MAX_DECLARADO = 255
VOLUMEN_DECLARADO = "volumen-auditado"

_HEX = "0123456789abcdef"
_MOTIVO_EXCLUSION = (
    "el manifiesto auditado se excluye por slug, no por subcadena: una subcadena "
    "mata archivos ajenos (SPEC §3.c.2), y un manifiesto que se incluyera es "
    "irrepresentable (§3.d.3)"
)

_Filas = Tuple[Tuple[bytes, str], ...]


class _Defecto(Exception):
    """Defecto del objeto o de la invocación: no se midió, luego `RC=2`."""


def _prosa(texto: str) -> None:
    """La prosa del CLI —y sólo ella— vive en stderr (cláusula 2)."""

    sys.stderr.write(texto + "\n")


class _Analizador(argparse.ArgumentParser):
    """Nada escribe en stdout: ni la ayuda ni los errores de invocación."""

    def _print_message(self, message: str, file: object = None) -> None:  # noqa: D102
        if message:
            sys.stderr.write(message)


def _analizador() -> _Analizador:
    p = _Analizador(
        prog="protocol-audit",
        description=(
            "Cuenta y compara un árbol contra su manifiesto, en frío. "
            "stdout: " + GRAMATICA
        ),
    )
    p.add_argument("--raiz", required=True, metavar="DIR", help="árbol auditado")
    p.add_argument(
        "--manifiesto",
        required=True,
        metavar="RUTA",
        help="manifiesto de filas `<64hex>  <ruta>`, orden byte a byte",
    )
    p.add_argument(
        "--excluir",
        action="append",
        default=[],
        metavar="SLUG",
        help=(
            "slug enumerado a excluir de la medición; repetible. Se suma al "
            "nombre del manifiesto, que siempre se excluye"
        ),
    )
    return p


def _nombres_excluidos(manifiesto: str, excluir: Sequence[str]) -> List[str]:
    return sorted(set(excluir) | {os.path.basename(manifiesto)})


def _sin_blancos(etiqueta: str, valor: str) -> None:
    if valor == "" or any(c.isspace() for c in valor):
        raise _Defecto(
            "defecto de invocación: %s es vacío o lleva blancos, y los campos de "
            "la línea del contrato se separan por blancos" % etiqueta
        )


def _filas_del_manifiesto(ruta: str) -> _Filas:
    """Filas `(ruta_bytes, etiqueta_hex)` ordenadas byte a byte.

    El fichero se lee entero y se trocea a mano: una fila que no cumpla la forma
    se declara, no se salta. Un manifiesto con líneas que se saltan en silencio
    certificaría una ausencia que no midió.
    """

    try:
        with open(ruta, "rb") as fh:
            crudo = fh.read()
    except OSError as exc:
        raise _Defecto(
            "el manifiesto no se puede leer: %s: %s" % (ruta, exc.strerror or exc)
        ) from exc

    filas: List[Tuple[bytes, str]] = []
    for n, linea in enumerate(crudo.split(b"\n"), start=1):
        if linea == b"":
            continue
        if len(linea) < 67:
            raise _Defecto(
                "fila %d del manifiesto: demasiado corta para `<64hex>  <ruta>`" % n
            )
        if linea[64:66] != b"  ":
            raise _Defecto(
                "fila %d del manifiesto: faltan los dos espacios separadores" % n
            )
        try:
            etiqueta = linea[:64].decode("ascii")
        except UnicodeDecodeError as exc:
            raise _Defecto("fila %d del manifiesto: la etiqueta no es ASCII" % n) from exc
        if len(etiqueta) != 64 or any(c not in _HEX for c in etiqueta):
            raise _Defecto(
                "fila %d del manifiesto: la etiqueta no es sha256 en hexadecimal "
                "minúsculo" % n
            )
        try:
            ruta_rel = linea[66:].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _Defecto(
                "fila %d del manifiesto: la ruta no es UTF-8" % n
            ) from exc
        try:
            RutaRelativa(ruta_rel)
        except ContratoViolado as exc:
            raise _Defecto(
                "fila %d del manifiesto: la ruta no es admisible (§2.4): %s" % (n, exc)
            ) from exc
        filas.append((linea[66:], etiqueta))
    if not filas:
        raise _Defecto("el manifiesto no tiene filas: un conjunto vacío no declara nada")
    return tuple(sorted(filas, key=lambda par: par[0]))


def _medir(raiz: str, manifiesto: str, excluir: Sequence[str]) -> Manifiesto:
    """El manifiesto del árbol, medido por el núcleo sellado (no re-implementado)."""

    if not os.path.isdir(raiz):
        raise _Defecto("el árbol auditado no existe o no es un directorio: %s" % raiz)
    slugs: List[Slug] = []
    for nombre in _nombres_excluidos(manifiesto, excluir):
        try:
            slugs.append(Slug(nombre))
        except ContratoViolado as exc:
            raise _Defecto(
                "el slug a excluir no es admisible (§2.1): %r: %s" % (nombre, exc)
            ) from exc
    exclusion = ConjuntoDeclarado(slugs=tuple(slugs), motivo=_MOTIVO_EXCLUSION)
    fd = os.open(raiz, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        ns = Namespace(
            fd_root=fd,
            sensible_al_caso=True,
            nombre_max=NOMBRE_MAX_DECLARADO,
            motor_nacimiento=FuenteT0.BIRTHTIME,
            sincronizacion_directorio=None,
            volumen=VOLUMEN_DECLARADO,
        )
        return _metrics.manifest(ns, exclusion)
    finally:
        # El namespace no es dueño del descriptor: lo cierra quien lo abrió.
        os.close(fd)


def _filas_del_arbol(m: Manifiesto) -> _Filas:
    return tuple((e.ruta.clave_bytes, e.h.digest) for e in m.entradas)


def _agregado(m: Manifiesto) -> str:
    resumen = hashlib.sha256()
    for e in m.entradas:
        resumen.update(e.h.digest.encode("ascii"))
        resumen.update(b"  ")
        resumen.update(e.ruta.clave_bytes)
        resumen.update(b"\n")
    return resumen.hexdigest()


def _descomponer(declarado: _Filas, medido: _Filas) -> Dict[str, List[str]]:
    """La divergencia se descompone: sumar sus clases en una sola fila es el defecto."""

    d_declarado = dict(declarado)
    d_medido = dict(medido)
    solo_declarado = [r for r in d_declarado if r not in d_medido]
    solo_medido = [r for r in d_medido if r not in d_declarado]
    etiqueta_distinta = [
        r for r in d_medido if r in d_declarado and d_declarado[r] != d_medido[r]
    ]

    def texto(rutas: List[bytes]) -> List[str]:
        return sorted(r.decode("utf-8", "replace") for r in rutas)

    return {
        "solo_en_el_manifiesto": texto(solo_declarado),
        "solo_en_el_arbol": texto(solo_medido),
        "etiqueta_distinta": texto(etiqueta_distinta),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Devuelve el código de salida; no llama a `sys.exit` (la envuelve el punto de entrada)."""

    args = _analizador().parse_args(argv)
    try:
        _sin_blancos("--raiz", args.raiz)
        _sin_blancos("--manifiesto", args.manifiesto)
        declarado = _filas_del_manifiesto(args.manifiesto)
        medido = _medir(args.raiz, args.manifiesto, args.excluir)
    except _Defecto as exc:
        _prosa("protocol-audit: NO MEDIDO: %s" % exc)
        return 2
    except ProtocoloError as exc:
        _prosa("protocol-audit: NO MEDIDO: el árbol viola el protocolo: %s" % exc)
        return 2
    except OSError as exc:
        _prosa("protocol-audit: NO MEDIDO: %s" % (exc.strerror or exc))
        return 2

    filas = _filas_del_arbol(medido)
    agregado = _agregado(medido)
    coincide = filas == declarado
    rc = 0 if coincide else 1
    auditoria = "OK" if coincide else "ROJO"

    if not coincide:
        for clave, valores in sorted(_descomponer(declarado, filas).items()):
            muestra = ", ".join(valores[:8])
            if len(valores) > 8:
                muestra += ", ..."
            _prosa("protocol-audit: %s=%d [%s]" % (clave, len(valores), muestra))
    _prosa(
        "protocol-audit: %d filas medidas, %d declaradas, exclusion por slug [%s]"
        % (
            len(filas),
            len(declarado),
            ",".join(_nombres_excluidos(args.manifiesto, args.excluir)),
        )
    )

    # Única escritura en stdout, y la última: nada parcial puede precederla.
    sys.stdout.write(
        "AUDIT=%s RUTAS=%d SHA256_AGREGADO=%s MANIFIESTO=%s RC=%d\n"
        % (auditoria, len(filas), agregado, args.manifiesto, rc)
    )
    sys.stdout.flush()
    return rc
