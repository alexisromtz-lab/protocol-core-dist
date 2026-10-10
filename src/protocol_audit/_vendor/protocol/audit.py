"""audit.py — la tercera capa funcional de Materia A (§3.c · §3.e · §4 · §6).

Reparto declarado entre las tres capas de `src/protocol`. `metrics.py` MIDE
objetos: abre descriptores, lee flujos, sella fichas. `atomic.py` EJECUTA el
acto: reserva, sella, sonda. Este módulo **deduce y verifica**: cuenta, resta el
pie del instrumento, declara el reposo y reconstruye un recibo. No mide fichas
nuevas —para `verify` llama a `metrics.ficha`—, no imprime y **no escribe nada
en disco**: las cuatro operaciones de aquí abajo son de lectura o puras.

El encargo nombra cuatro contratos (§4) y la orden de la sesión añade el cuarto
parámetro de `resta`. Las firmas se conservan tal como el contrato las declara:

    census(namespace: Namespace, ctx: Contexto) -> Etiqueta
    resta(m_bruto: int, m_self: int | None, congelado: bool,
          estrategia: EstrategiaSelf) -> ResultadoResta
    reposo(namespace: Namespace, t_corte: datetime, ventana: timedelta) -> bool
    verify(recibo: Recibo, namespace: Namespace) -> ResultadoVerificacion

Lecturas declaradas. Ninguna se hace pasar por el texto de SPEC.md:

  1. El censo NO descuenta su propio pie. Cuenta lo que hay. El descuento es de
     `resta`, que es otra operación con otra pregunta (§3.c): mezclarlas haría
     que el censo tuviera que saber quién lo llama, y un instrumento que se
     descuenta a sí mismo por defecto se cuenta una vez de menos sin decirlo.
  2. La unidad declarada decide la agregación (§1.3): `ARCHIVO` cuenta objetos
     regulares, `BYTE` suma `st_size` **medido sobre el descriptor abierto**
     —contra el flujo leído, INV-8—, `LINEA` suma el conteo del byte 0x0A de
     cada flujo (§2.3.3: no es un conteo de líneas). `OCURRENCIA` exige el
     patrón declarado; `Contexto` no tiene campo donde llevarlo ⇒ se eleva
     `ContratoViolado`. Un cero sería aquí el defecto que este módulo existe
     para impedir: la unidad no medida no vale cero, no vale.
  3. Los elementos del universo son los OBJETOS REGULARES; los directorios se
     atraviesan (misma convención que `manifest`, §2.5.2). Cualquier otro tipo
     —FIFO, enlace, dispositivo— se declara `ELOOP`: un recorrido que cuelga no
     es una medición, y abrir un FIFO para leerlo cuelga.
  4. La llegada es CONJUNTO, no marca (§3.e.2). Cada operación de este módulo
     encierra su medición entre **dos partidas de rutas relativas**; si el
     conjunto no es el mismo, el universo se movió y no hay cifra ni aserción:
     se eleva `ContratoViolado` en vez de devolver un número de un objeto que
     cambió mientras se contaba. «La cifra de un universo que se mueve no es una
     cifra» se cumple aquí por construcción, no por disciplina del llamador.
  5. `reposo` sí lee `mtime` de TODO objeto del subárbol, **directorios
     incluidos**: un directorio cuyo `mtime` excede el corte declara que su
     lista de nombres cambió después del corte, y eso es exactamente lo que un
     reposo no admite. Es lo único que ve un borrado seguido de un alta, que
     deja el conjunto de rutas idéntico. El objeto RAÍZ del namespace es el
     primero de esos directorios y no es hijo de ningún otro: se lee con
     `fstat` sobre `fd_root` —sin construir ninguna ruta (§0.4.b)— porque el
     recorrido visita a los hijos, y sin esa lectura la ley quedaría sin cubrir
     el único objeto que ninguna lista enumera. El censo, en cambio, agrega sólo
     objetos regulares. Son dos declaraciones distintas y se declaran aquí.
  6. La ley de `reposo` es la cota superior estricta de §3.e.1 — para todo
     objeto del subárbol, `mtime ≤ t_corte` — y **no** la igualdad `Δ(mtime) = 0`
     dentro de una ventana. La igualdad la satisface un re-sello en bloque: dos
     objetos escritos en el mismo instante tienen la misma marca y el delta es
     cero sin que haya reposo.
  7. La ventana se declara ANTES de medir (§1.4 · §3.e.1) y se comprueba CONTRA
     la observación: si el recorrido tarda más que la ventana declarada, la
     aserción no cubre ese intervalo y se eleva. El transcurrido se mide con
     `time.monotonic()`: es una DURACIÓN, no una fecha, no lleva zona y no
     consulta el reloj de pared. Este módulo no lee el reloj: el corte llega
     formado desde el llamador (§0.4.d).
  8. El corte se exige en UTC estricto (`tzinfo` presente y `utcoffset() == 0`):
     sin zona, el mismo número es otro instante según el proceso, y una aserción
     de reposo sobre un instante que depende de `TZ` no es reproducible
     (§3.e.4 · §0.4.d). La comparación usa `datetime.timestamp()`, que sobre un
     instante consciente de su zona no consulta la variable de entorno.
  9. La estrategia de auto-conteo se declara como la enumeración
     `EstrategiaSelf`, nunca como la letra suelta «E» o «D»: una letra es un
     rótulo y no viaja con su declaración (misma frontera que el sufijo frente a
     la marca de género).
 10. Los tres colapsos de `resta` a `Indeterminado` son declaraciones, no
     errores de entrada (§3.c.3): pie no congelado bajo D, doble descuento bajo
     E, y neto negativo. Un denominador negativo se imprime y no enrojece nada,
     así que no se devuelve. `Indeterminado` no es cero y no se suma.
 11. `verify` re-mide con **la anchura que el recibo declara** (`h.anchura`), no
     con la anchura completa: el truncamiento viaja con su anchura (§2.3.1), y
     medir a 64 un recibo sellado a 16 produciría una divergencia fabricada por
     el metro.
 12. La verificación compara en el orden declarado `(h, b, l, p, i, t0)` y
     devuelve la PRIMERA divergencia. No acumula una lista: el contrato devuelve
     `Ok | Divergencia(campo, esperado, medido)`, y una reparación que se
     presentara como reconciliación sería el defecto que `Divergencia` impide.
 13. `verify` NO adjudica la cadena ni el certificado: `H_prev` y el certificado
     de exclusividad no viven en el objeto —viven en el libro mayor— y el
     sistema de archivos no es notario. Se verifica lo que el objeto puede
     desmentir; por eso tocar el `mtime` de un objeto no produce divergencia
     (medido en la suite) y no tener el objeto no es una divergencia: es el
     error tipado de `ficha` (§4 err), que sale tal cual.
 14. Reutilización, no copia: de `atomic.py` se importan `_exigir_namespace`,
     `_exigir_dir_fd`, `_error_tipado` y `_cerrar_sin_ruido`; de `metrics.py`,
     `_stat_de_entrada`, `_abrir_directorio`, `_abrir_lectura`,
     `_medir_descriptor`, `_slug_de_entrada` y `ficha`. La forma de la etiqueta
     UTC vive una sola vez, en `atomic.py`, y este módulo no la re-escribe.
     Ninguna definición de este archivo duplica una que ya exista: si esas
     capas dejan de exponer lo que aquí se usa, esta capa rompe ruidoso al
     importar, que es la forma correcta de romper.
 15. Este módulo no imprime. El crudo de una corrida es de la suite
     (`tests/test_audit.py`) y de quien la invoca; `Indeterminado.razon` y
     `Divergencia` llevan su declaración como VALOR, no como salida.
 16. La RAÍZ se lee en los DOS extremos de la ventana —al abrirla, junto a la
     primera partida de rutas, y al cerrarla, junto a la segunda—. Un alta
     seguida de una baja dentro del intervalo deja el conjunto de rutas
     idéntico y mueve, en cambio, la lista de nombres de la raíz; y como una
     marca puede ser re-sellada hacia atrás (caso ya pagado en el taller), una
     sola lectura no cubre el intervalo que la aserción declara. Son dos
     instantes del MISMO objeto, no dos objetos: la ley de §3.e.1 se cumple por
     la cota, no por el número de lecturas, y ninguna de las dos puede convertir
     en reposo un movimiento que la otra vio.
"""

from __future__ import annotations

import os as _os
import stat as _stat
import time as _time
from datetime import datetime as _datetime, timedelta as _timedelta
from typing import Final, List, Optional, Tuple

from . import atomic as _at
from . import metrics as _me
from .types import (
    OK,
    ContratoViolado,
    Contexto,
    Divergencia,
    ELOOP,
    Etiqueta,
    EstrategiaSelf,
    Indeterminado,
    Namespace,
    Recibo,
    ResultadoResta,
    ResultadoVerificacion,
    SEPARADOR,
    Unidad,
)

__all__ = ["census", "resta", "reposo", "verify"]


#: §2.3.3. El byte que la unidad `LINEA` cuenta. No es «la línea».
_LF: Final[int] = 0x0A

#: §2.5.1. El orden declarado de la comparación de `verify`. La primera
#: divergencia que se devuelve es la primera de esta tupla, no la primera que
#: el sistema de archivos ocurra en reportar.
_CAMPOS_DEL_RECIBO: Final[Tuple[str, ...]] = ("h", "b", "l", "p", "i", "t0")

#: Unidades que este censo sabe agregar. `OCURRENCIA` falta a propósito: exige
#: el patrón declarado y el contexto no tiene dónde llevarlo (§1.4).
_UNIDADES_DEL_CENSO: Final[frozenset] = frozenset(
    {Unidad.ARCHIVO, Unidad.BYTE, Unidad.LINEA}
)


# ---------------------------------------------------------------------------
# Utilidades de declaración
# ---------------------------------------------------------------------------


def _exigir_contexto(ctx: object) -> Contexto:
    """La etiqueta de validez llega completa o no hay cifra (§1.4).

    El tipo ya exige los seis campos y que `t_utc` declare UTC; lo que el tipo
    NO puede exigir es que el universo sea una etiqueta legible y no una ruta:
    eso se mide aquí, porque una ruta absoluta en la etiqueta mete el directorio
    real en el texto del resultado (§0.4.b).
    """

    if not isinstance(ctx, Contexto):
        raise ContratoViolado(
            "el censo exige la etiqueta de validez completa (§1.4)",
            tipo=type(ctx).__name__,
        )
    if SEPARADOR in ctx.universo:
        raise ContratoViolado(
            "el universo viaja como etiqueta legible, nunca como ruta (§0.4.b)",
            universo=ctx.universo,
        )
    return ctx


def _partida_de_rutas(
    fd_dir: int, partes: Tuple[str, ...] = ()
) -> Tuple[Tuple[str, ...], ...]:
    """§3.e.2. El motor de llegada: el CONJUNTO de rutas relativas.

    Enumera nombres y desciende por directorios reales. No discrimina tipos ni
    lee marcas: es la partida contra la que se compara la segunda, y la barrera
    de tipo vive en el recorrido que va en medio (lectura 4). Las rutas son
    relativas siempre: ninguna ruta absoluta se hornea ni se acumula (§0.4.b).
    """

    _at._exigir_dir_fd()
    try:
        nombres = _os.listdir(fd_dir)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc
    salida: List[Tuple[str, ...]] = []
    for nombre in sorted(nombres):
        _me._slug_de_entrada(nombre)
        st = _me._stat_de_entrada(fd_dir, nombre)
        ruta = partes + (nombre,)
        salida.append(ruta)
        if _stat.S_ISDIR(st.st_mode):
            fd_hijo = _me._abrir_directorio(fd_dir, nombre)
            try:
                salida.extend(_partida_de_rutas(fd_hijo, ruta))
            finally:
                _at._cerrar_sin_ruido(fd_hijo)
    return tuple(salida)


def _exigir_sin_movimiento(
    antes: Tuple[Tuple[str, ...], ...], despues: Tuple[Tuple[str, ...], ...]
) -> None:
    """El universo que se movió no entrega cifra: entrega movimiento (§3.e.2).

    Se declaran los cardinales y las dos diferencias, no las rutas: la
    declaración de un movimiento nombra cuántas entradas llegaron y cuántas se
    fueron, que es lo que decide si una cifra puede publicarse.
    """

    if antes == despues:
        return
    previas = set(antes)
    nuevas = set(despues)
    raise ContratoViolado(
        "el universo se movió durante la medición: llegadas o partidas de "
        "entradas (§3.e.2 · T-05). Una cifra de un universo que se mueve no es "
        "una cifra, y una aserción de reposo sobre él no es una aserción",
        entradas_antes=len(antes),
        entradas_despues=len(despues),
        llegadas=len(nuevas - previas),
        partidas=len(previas - nuevas),
    )


def _recorrer(fd_dir: int, partes: Tuple[str, ...], visita) -> None:
    """Recorrido confinado al descriptor raíz; ninguna ruta absoluta entra.

    Aplica la barrera de tipo (§lectura 3) y llama a `visita` para TODO objeto
    —directorios incluidos—, antes de descender. El orden es el de la colación
    byte a byte de los nombres, para que dos corridas del mismo árbol visiten en
    el mismo orden.
    """

    _at._exigir_dir_fd()
    try:
        nombres = _os.listdir(fd_dir)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc
    for nombre in sorted(nombres):
        slug = _me._slug_de_entrada(nombre)
        st = _me._stat_de_entrada(fd_dir, nombre)
        ruta = partes + (nombre,)
        visita(ruta, fd_dir, nombre, st)
        if _stat.S_ISDIR(st.st_mode):
            fd_hijo = _me._abrir_directorio(fd_dir, nombre)
            try:
                _recorrer(fd_hijo, ruta, visita)
            finally:
                _at._cerrar_sin_ruido(fd_hijo)
        elif not _stat.S_ISREG(st.st_mode):
            raise ELOOP(
                "el recorrido no sigue enlaces ni abre objetos que no son "
                "archivos: un objeto que no es regular se declara, no se mide "
                "(§2.4 · §3.d.1)",
                slug=slug.texto,
            )


# ---------------------------------------------------------------------------
# §4 census — contar sin descontarse (§1.3 · §3.e.2)
# ---------------------------------------------------------------------------


def census(namespace: Namespace, ctx: Contexto) -> Etiqueta:
    """§4. Cuenta el universo en la unidad declarada y devuelve la etiqueta.

    La tupla `(Universo, Unidad, Motor, T_UTC)` más `VENTANA` y `UMBRAL` viaja
    **dentro** del resultado: el objeto `Etiqueta` no tiene constructor que
    admita un valor sin contexto, de modo que una cifra sin etiqueta de validez
    es irrepresentable y no «desaconsejada».

    El censo no descuenta el pie del instrumento (§lectura 1) y no devuelve
    cifra si el universo se movió mientras contaba (§lectura 4).
    """

    ns = _at._exigir_namespace(namespace)
    etiqueta = _exigir_contexto(ctx)
    unidad = etiqueta.unidad
    if unidad not in _UNIDADES_DEL_CENSO:
        raise ContratoViolado(
            "el censo no cuenta esa unidad: exige el patrón declarado y el "
            "contexto no tiene dónde llevarlo (§1.3 · §1.4). No se devuelve "
            "cero: la unidad no medida no vale cero, no vale",
            unidad=getattr(unidad, "value", str(unidad)),
            unidades_admitidas=tuple(sorted(u.value for u in _UNIDADES_DEL_CENSO)),
        )

    antes = _partida_de_rutas(ns.fd_root)
    total = 0

    def _visita(
        ruta: Tuple[str, ...], fd_padre: int, nombre: str, st: object
    ) -> None:
        nonlocal total
        if _stat.S_ISDIR(st.st_mode):
            return
        if unidad is Unidad.ARCHIVO:
            total += 1
            return
        fd = _me._abrir_lectura(fd_padre, nombre)
        try:
            flujo, st_flujo = _me._medir_descriptor(fd)
        finally:
            _at._cerrar_sin_ruido(fd)
        if unidad is Unidad.BYTE:
            total += st_flujo.st_size
        else:
            total += flujo.count(_LF)

    _recorrer(ns.fd_root, (), _visita)
    despues = _partida_de_rutas(ns.fd_root)
    _exigir_sin_movimiento(antes, despues)
    return Etiqueta(valor=total, contexto=etiqueta)


# ---------------------------------------------------------------------------
# §3.c INV_SELF — la resta del pie del instrumento
# ---------------------------------------------------------------------------


def resta(
    m_bruto: int,
    m_self: Optional[int],
    congelado: bool,
    estrategia: EstrategiaSelf,
) -> ResultadoResta:
    """§3.c · §4. Descuenta el pie del instrumento, o declara que no converge.

    Las dos estrategias son mutuamente excluyentes (§3.c.1). Bajo `E_EXCLUSION`
    el universo ya excluye el pie por enumeración de un conjunto declarado, de
    modo que restar además `m_self` es el **doble descuento** y devuelve
    `Indeterminado`. Bajo `D_DEDUCCION` el descuento es aritmético y sólo vale
    si el pie está **congelado** (§3.c.3): sin congelamiento el pie puede haber
    crecido entre la medición y la resta, y la resta no converge.
    """

    if not isinstance(congelado, bool):
        raise ContratoViolado(
            "el congelamiento del pie se declara con un booleano, no con una "
            "impresión (§3.c.3)",
            congelado=congelado,
        )
    if not isinstance(estrategia, EstrategiaSelf):
        raise ContratoViolado(
            "la resta exige la estrategia declarada entre E y D: son mutuamente "
            "excluyentes (§3.c.1) y una letra suelta no viaja con su "
            "declaración (lectura 9)",
            estrategia=estrategia,
        )
    if not isinstance(m_bruto, int) or isinstance(m_bruto, bool) or m_bruto < 0:
        raise ContratoViolado(
            "m_bruto no es un conteo admisible (§1.3)", m_bruto=m_bruto
        )
    if m_self is not None and (
        not isinstance(m_self, int) or isinstance(m_self, bool) or m_self < 0
    ):
        raise ContratoViolado(
            "m_self no es un conteo admisible (§1.3)", m_self=m_self
        )

    if estrategia is EstrategiaSelf.E_EXCLUSION:
        if m_self:
            return Indeterminado(
                "doble descuento: la estrategia E ya excluye el pie del universo "
                "por enumeración del conjunto declarado, y restar además m_self "
                "lo descontaría dos veces (§3.c.1 · §3.c.2)"
            )
        return m_bruto

    if m_self is None:
        return Indeterminado(
            "la estrategia D exige m_self enumerado: sin el pie contado no hay "
            "deducción, y suponerlo cero sería el pie no declarado (§3.c.3)"
        )
    if not congelado:
        return Indeterminado(
            "el pie no está congelado: puede haber crecido entre la medición y "
            "la resta, la resta no converge y no se devuelve un número (§3.c.3)"
        )
    if m_self > m_bruto:
        return Indeterminado(
            "el pie excede al bruto: la resta arrojaría un neto negativo, y un "
            "denominador negativo se imprime sin enrojecer nada (§3.c.3 · D23)"
        )
    return m_bruto - m_self


# ---------------------------------------------------------------------------
# §3.e INV_TIME — el reposo del universo
# ---------------------------------------------------------------------------


def reposo(
    namespace: Namespace, t_corte: _datetime, ventana: _timedelta
) -> bool:
    """§3.e · §4. ¿Estaba el universo quieto en el corte?

    Devuelve `True` si y sólo si **todo** objeto del subárbol —directorios
    incluidos, la raíz del namespace entre ellos (§lectura 5)— tiene
    `mtime ≤ t_corte` y el objetivo se observó dentro de la ventana declarada.
    Devuelve `False` cuando **hay objeto
    posterior al corte**: eso es un hecho del objeto, y el reposo no se sostiene.

    Eleva en los dos casos en que **no hubo medición**, que no son lo mismo que
    «no hay reposo»: el universo se movió durante el recorrido (§lectura 4) y la
    observación excedió la ventana declarada (§lectura 7). `False` dice que el
    objeto no está quieto; la excepción dice que la pregunta no llegó a
    responderse.
    """

    ns = _at._exigir_namespace(namespace)
    if not isinstance(t_corte, _datetime):
        raise ContratoViolado(
            "el corte es un instante formado por el llamador, no una impresión "
            "(§3.e.4 · §0.4.d)",
            t_corte=type(t_corte).__name__,
        )
    if t_corte.tzinfo is None or t_corte.utcoffset() != _timedelta(0):
        raise ContratoViolado(
            "el corte se declara en UTC estricto: sin zona, el mismo número es "
            "otro instante según el proceso (§3.e.4 · §0.4.d)",
            t_corte=t_corte.isoformat(),
        )
    if not isinstance(ventana, _timedelta):
        raise ContratoViolado(
            "la ventana se declara antes de medir (§1.4 · §3.e.1)",
            ventana=ventana,
        )
    if ventana <= _timedelta(0):
        raise ContratoViolado(
            "una ventana no positiva no acota ninguna observación (§3.e.1)",
            ventana=str(ventana),
        )

    corte = t_corte.timestamp()
    arranque = _time.monotonic()
    antes = _partida_de_rutas(ns.fd_root)
    posteriores: List[int] = []

    # La RAÍZ no es hija de nadie: `_recorrer` visita a los hijos, así que el
    # primer directorio del subárbol se lee aquí, entre las dos partidas.
    # `fstat` sobre el descriptor no construye ninguna ruta (§0.4.b).
    if _os.fstat(ns.fd_root).st_mtime > corte:
        posteriores.append(1)

    def _visita(
        ruta: Tuple[str, ...], fd_padre: int, nombre: str, st: object
    ) -> None:
        if st.st_mtime > corte:
            posteriores.append(1)

    _recorrer(ns.fd_root, (), _visita)
    # La raíz se marca al cerrar la ventana (§lectura 16): las dos partidas de
    # rutas no ven el alta que llegó y se fue entre ellas, y la lista de nombres
    # de la raíz sí.
    try:
        st_raiz = _os.fstat(ns.fd_root)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc
    if st_raiz.st_mtime > corte:
        posteriores.append(1)
    despues = _partida_de_rutas(ns.fd_root)
    transcurrido = _time.monotonic() - arranque

    _exigir_sin_movimiento(antes, despues)
    if transcurrido > ventana.total_seconds():
        raise ContratoViolado(
            "la observación excedió la ventana declarada antes de medir: la "
            "aserción no cubre ese intervalo y no se publica como reposo "
            "(§3.e.1 · lectura 7)",
            ventana=str(ventana),
            transcurrido="%.6f" % transcurrido,
        )
    return not posteriores


# ---------------------------------------------------------------------------
# §2.5.1 Recibo — la verificación contra el objeto
# ---------------------------------------------------------------------------


def verify(recibo: Recibo, namespace: Namespace) -> ResultadoVerificacion:
    """§2.5.1 · §4. Reconstruye la ficha del slug citado y compara campo a campo.

    La medición va **fuera de banda**: quien verifica no es el que escribió, y
    el recibo se contrasta contra el objeto, no contra otra copia del recibo.
    Se devuelve `OK` (`True`) sólo si los seis campos declarados coinciden; en
    cuanto uno diverge se devuelve la primera `Divergencia` del orden declarado
    (§lectura 12), sin seguir mirando y sin reconciliar nada.

    No adjudica `H_prev` ni el certificado: la cadena y el certificado de
    exclusividad no viven en el objeto (§lectura 13).
    """

    ns = _at._exigir_namespace(namespace)
    if not isinstance(recibo, Recibo):
        raise ContratoViolado(
            "la verificación exige un Recibo sellado (§2.5.1)",
            valor=type(recibo).__name__,
        )

    medida = _me.ficha(ns, recibo.slug, anchura=recibo.h.anchura)
    pares = (
        ("h", recibo.h, medida.h),
        ("b", recibo.b, medida.b),
        ("l", recibo.l, medida.l),
        ("p", recibo.p.p_sep, medida.p.p_sep),
        ("i", recibo.i, medida.i),
        ("t0", recibo.t0, medida.t0),
    )
    declarado = [campo for campo, _, _ in pares]
    if tuple(declarado) != _CAMPOS_DEL_RECIBO:  # pragma: no cover - invariante
        raise ContratoViolado(
            "el orden de comparación no es el declarado (lectura 12)",
            declarado=tuple(declarado),
            esperado=_CAMPOS_DEL_RECIBO,
        )
    for campo, esperado, medido in pares:
        if esperado != medido:
            return Divergencia(campo=campo, esperado=esperado, medido=medido)
    return OK
