"""metrics.py — la segunda capa funcional de Materia A (§2.3 · §4).

Medidor de ficha, de líneas y de terminaciones. Este módulo **mide objetos**:

    partition(flujo, enc)   las dos proyecciones de `P` y la ley de tres
                            ramas (§2.3.4) — splits puros y terminaciones;
    ficha(N, s)             las seis dimensiones de `F`, medidas FUERA DE
                            BANDA (INV-6 · §2.3.9);
    manifest(N, E)          el manifiesto relativo, ordenado y autocerrado
                            de un namespace (§4 · §2.5.2);
    attest(s, F, prev)      el recibo de la cadena: `R = (s, H, B, L, I, T0,
                            H_prev)` (§2.5.1).

Reparto declarado. `census`, `resta`, `reposo` y `verify` —también de §4— NO
viven aquí, y la razón no es de gusto: §6 asigna `metrics.py` a la MEDICIÓN
(«Medidor de Ficha, líneas, splits puros y terminaciones») y `audit.py` a la
«verificación de invariantes y deducción de auto-conteo», y §5 coloca T-03,
T-04 y T-05 en `test_audit.py`. Escribirlos aquí sería dos manos sobre el mismo
objeto. Este módulo **no cuenta, no resta, no verifica y no imprime**
(§2.3.9 · INV-6): devuelve objetos tipados; imprimirlos es de quien los recibe.

Lecturas declaradas. Ninguna se hace pasar por el texto de SPEC.md:

  1. `partition` devuelve `Particion` y no una tupla de cinco. `L`, `fin` y
     `vacio` son propiedades derivadas de `P_sep` (§2.3.3, §2.3.4.1) y
     almacenarlas admitiría un objeto internamente contradictorio —la doctrina
     con la que `types.py` ya está ratificado—. Los cinco componentes que §4
     nombra son alcanzables desde el objeto devuelto: `p_sep`, `p_lines`, `l`,
     `fin`, `vacio`.
  2. Gate de unidad de `L`. §2.3.3 declara `L` como CONTEO DE BYTES `0x0A`;
     `Particion.l` es `len(P_sep) − 1`. Coinciden sólo si `enc` es transparente
     al byte `0x0A` (utf-8 lo es; una codificación de dos bytes puede llevar un
     `0x0A` dentro de otra unidad). El módulo mide las dos cifras y, si
     divergen, lo **declara**: no devuelve una partición cuyo `L` sería una
     cifra sin unidad (§2.3.4: `|P_sep| = L + 1` SIEMPRE).
  3. `ficha` recibe el `Namespace` —tipo ya ratificado— y no un `FD_root`
     suelto: el confinamiento al descriptor raíz es del namespace (§2.4), y la
     resolución por ruta absoluta es exactamente lo que §0.4(b) prohíbe.
  4. `ficha` añade `enc` y `anchura` como parámetros declarados. §2.3.4 exige
     la codificación declarada y §2.3.1 exige que el truncamiento viaje con su
     anchura; ninguna de las dos se deduce del flujo. Los valores por defecto
     (`utf-8`, anchura completa) se declaran aquí y no se adivinan allá.
  5. Reutilización y no copia de `atomic.py`. `_exigir_namespace`,
     `_exigir_dir_fd`, `_error_tipado`, `_t0_de_stat` y `_cerrar_sin_ruido` ya
     existen y son correctos; volver a escribirlos aquí crearía una segunda
     definición del mismo objeto, que es el defecto que §1.3 nombra. Se
     importan. Si `atomic.py` deja de exponerlos, este módulo **rompe ruidoso
     al importar** y no en silencio.
  6. La escalera de INV-7 se lee, nunca se exige: `st_birthtime` del mismo
     descriptor si está, `⊥` si no (§2.3.7). El peldaño `statx(STATX_BTIME)`
     sigue declarado NO IMPLEMENTADO —la biblioteca estándar no lo expone sin
     dependencias— y no se simula.
  7. `manifest` exige `E` como parámetro, SIN valor por defecto: §4 pre manda
     que `E` se capture ANTES de hashear y que enumere slugs. Un defecto sería
     un `E` elegido después de ver el listado. `E` es una afirmación del
     llamador sobre su propio subárbol; esta capa la registra y no la adjudica
     —no escribe el manifiesto y no conoce su nombre—.
  8. El manifiesto **no** particiona: §2.5.2 declara el par `(H, slug)`.
     Particionar exigiría una codificación, y la codificación es del objeto,
     no del manifiesto. `M` y `K` tampoco entran: no están en el par.
  9. Recorrido. Entran como entradas los objetos regulares; los directorios se
     atraviesan; cualquier otra cosa —enlace simbólico, FIFO, socket, nodo—
     se declara con `ELOOP`, el mismo errno que §4 da a `ficha` para un objeto
     que no es directo. Un FIFO no se abre en lectura: `open` bloquea sin
     escritor, y una medición que cuelga no es una medición.
 10. Un componente fuera del alfabeto se declara y no se salta: `Slug` y
     `RutaRelativa` no pueden representarlo, y un conjunto declarado de slugs
     no puede nombrarlo (§3.c.2: una subcadena no es un conjunto; un conjunto
     de slugs no alcanza a un no-slug).
 11. La exclusión se prueba contra CADA componente del recorrido: un slug de
     `E` que nombra un directorio toma su subárbol entero. §3.d.3 enumera
     slugs, no subárboles, así que esta lectura se declara en lugar de
     suponerse.
 12. `attest` recibe el slug explícitamente. §4 nombra `attest(F, prev)`, pero
     `R = (s, …)` (§2.5.1) lo exige y `F` no lo lleva (§2.3). Deducirlo de una
     ruta reabriría la dependencia de la máquina de origen (§0.4.b).
 13. Este módulo **no importa ningún reloj**. Los instantes entran ya formados
     —la etiqueta de `T0`— o como segundos absolutos del llamador. La forma de
     la etiqueta UTC vive una sola vez, en `atomic.py`, y no se reescribe.
 14. `B` se compara contra el flujo leído DEL MISMO descriptor (§2.3.2 · T-10)
     y el `H` se calcula sobre el flujo ya leído: nunca se reabre la ruta para
     hashear. `st_ctime` **no** es nacimiento (§2.3.7) y no se lee aquí.
 15. Dos barreras distintas, y ninguna sustituye a la otra. El TIPO se
     comprueba sobre el nombre sin seguirlo, **antes** de abrir: `open` en
     lectura de un FIFO bloquea sin escritor y una medición que cuelga no es
     una medición. `O_NOFOLLOW` no cubre ese caso —un FIFO no es un enlace—:
     cubre el enlace intercambiado entre la comprobación y la apertura. Lo que
     exceda a las dos lo declara `LecturaRasgada` al comparar `B`.

INV-6: este módulo no imprime su propia identidad ni cifra alguna. La ficha de
una pieza no se mide dentro de la pieza: `ficha` abre el objeto después de la
escritura y mide fuera de banda.
"""

from __future__ import annotations

import hashlib as _hashlib
import os as _os
import stat as _stat
from typing import Final, List, Optional, Tuple

from . import atomic as _at
from .types import (
    ALGORITMO,
    ANCHURA_COMPLETA,
    CertificadoExclusividad,
    ConjuntoDeclarado,
    ContratoViolado,
    ELOOP,
    ENOTSUP,
    EntradaManifiesto,
    ErrorDecodificacion,
    Ficha,
    Hash,
    Inodo,
    LecturaRasgada,
    Manifiesto,
    Namespace,
    Particion,
    Recibo,
    RutaRelativa,
    SEPARADOR,
    Slug,
)

__all__ = [
    "BANDERAS_LECTURA",
    "BLOQUE_LECTURA",
    "attest",
    "ficha",
    "manifest",
    "partition",
]


# ---------------------------------------------------------------------------
# Declaración de plataforma. §8.3: lo que es parámetro no se supone.
# ---------------------------------------------------------------------------

_O_NOFOLLOW: Final[Optional[int]] = getattr(_os, "O_NOFOLLOW", None)
_O_CLOEXEC: Final[Optional[int]] = getattr(_os, "O_CLOEXEC", None)

#: §4 `ficha` pre: el objeto es directo y no un enlace. Se lee con
#: `O_NOFOLLOW` —no se sigue el enlace y no se descubre después— y con
#: `O_CLOEXEC`, que no hereda el descriptor. Sin las dos, la capa no mide.
BANDERAS_LECTURA: Final[Optional[int]] = (
    None
    if (_O_NOFOLLOW is None or _O_CLOEXEC is None)
    else _os.O_RDONLY | _O_NOFOLLOW | _O_CLOEXEC
)

#: Anchura del bloque de lectura. **No es un umbral**: el flujo se lee completo
#: y el bucle sólo termina en el fin real del descriptor.
BLOQUE_LECTURA: Final[int] = 1 << 20

#: §2.3.3. El byte cuyo conteo es `L`. Va nombrado, no dentro de un literal.
_LF: Final[int] = 0x0A


# ---------------------------------------------------------------------------
# Utilidades de lectura. Ninguna construye una ruta: todo se resuelve contra
# un descriptor (confinamiento de §2.4 · §0.4.c).
# ---------------------------------------------------------------------------


def _exigir_lectura_directa() -> int:
    """Devuelve la máscara de lectura, o falla declarando qué falta (§4 err)."""

    if BANDERAS_LECTURA is None:
        raise ENOTSUP(
            "O_NOFOLLOW u O_CLOEXEC no existen en esta plataforma: la ficha "
            "exige objeto directo (err ELOOP) y un descriptor que no se herede; "
            "no se mide a medias para descubrirlo después (§4 · §8.3)",
            o_nofollow=_O_NOFOLLOW is not None,
            o_cloexec=_O_CLOEXEC is not None,
        )
    _at._exigir_dir_fd()
    return BANDERAS_LECTURA


def _abrir_lectura(fd_padre: int, nombre: str) -> int:
    """Abre el objeto confinado al descriptor padre. Ni una ruta absoluta."""

    banderas = _exigir_lectura_directa()
    try:
        return _os.open(nombre, banderas, dir_fd=fd_padre)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc


def _stat_de_entrada(fd_padre: int, nombre: str) -> object:
    """`st` del objeto NOMBRADO, sin seguirlo. Una sola definición (§1.3).

    `follow_symlinks=False` es el `lstat` de la entrada: no se atraviesa el
    enlace para descubrir después que lo era.
    """

    _at._exigir_dir_fd()
    try:
        return _os.stat(nombre, dir_fd=fd_padre, follow_symlinks=False)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc


def _abrir_directorio(fd_padre: int, nombre: str) -> int:
    """Abre un subdirectorio confinado al descriptor padre (§2.4)."""

    _at._exigir_dir_fd()
    banderas = _os.O_RDONLY | getattr(_os, "O_DIRECTORY", 0) | (_O_CLOEXEC or 0)
    try:
        return _os.open(nombre, banderas, dir_fd=fd_padre)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc


def _leer_descriptor(fd: int) -> bytes:
    """Lee el flujo completo del descriptor. `os.read` puede devolver menos."""

    trozos: List[bytes] = []
    try:
        while True:
            trozo = _os.read(fd, BLOQUE_LECTURA)
            if not trozo:
                break
            trozos.append(trozo)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc
    return b"".join(trozos)


def _medir_descriptor(fd: int) -> Tuple[bytes, object]:
    """Lee el flujo y toma el `st` del MISMO descriptor (§2.3.2 · T-10).

    Si `st_size` no coincide con el flujo leído, la lectura se rasgó: se
    declara (INV-8) y no se devuelve ficha. Un fallo de lectura no reporta
    cuánto escribió (§7.5); reintentar hasta que salga un número redondo es el
    defecto que `LecturaRasgada` existe para impedir.
    """

    flujo = _leer_descriptor(fd)
    try:
        st = _os.fstat(fd)
    except OSError as exc:
        raise _at._error_tipado(exc) from exc
    if st.st_size != len(flujo):
        raise LecturaRasgada(
            "B no coincide con el flujo leído del mismo descriptor (INV-8 · "
            "T-10): la ficha no se devuelve con una lectura rasgada",
            b=st.st_size,
            leidos=len(flujo),
        )
    return flujo, st


def _hash_de_flujo(flujo: bytes, anchura: Optional[int]) -> Hash:
    """§2.3.1. `SHA-256` sobre el flujo CRUDO: sin traducción de fin de línea,
    sin descartar BOM, sin normalizar. El truncamiento viaja declarado."""

    if anchura is not None:
        if not isinstance(anchura, int) or isinstance(anchura, bool):
            raise ContratoViolado("anchura de truncamiento no entera (§2.3.1)", anchura=anchura)
        if anchura < 1 or anchura > ANCHURA_COMPLETA:
            raise ContratoViolado("anchura de truncamiento fuera de rango (§2.3.1)", anchura=anchura)
    completo = _hashlib.sha256(flujo).hexdigest()
    return Hash(ALGORITMO, completo if anchura is None else completo[:anchura], anchura)


def _slug_de_entrada(nombre: str) -> Slug:
    """Un componente del namespace que no es slug se declara, no se salta."""

    try:
        return Slug(nombre)
    except ContratoViolado as exc:
        raise ContratoViolado(
            "una entrada del namespace no es admisible como slug: no se puede "
            "representar como ruta relativa ni nombrar con un conjunto "
            "declarado de slugs (§2.1 · §3.c.2)",
            componente=nombre,
            causa=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# §2.3.4 · §4 partition — dos proyecciones y la ley de tres ramas
# ---------------------------------------------------------------------------


def partition(flujo: bytes, enc: str = "utf-8") -> Particion:
    """§4 `partition` — las dos proyecciones de `P`, ambas obligatorias.

    `P_sep := split(LF)` **conservando** el campo vacío final; `P_lines :=` la
    misma proyección **descartándolo**. La segunda es función de la primera, de
    modo que una partición internamente contradictoria no se comprueba después:
    no puede construirse (§2.3.4).

    Ley de tres ramas, verificada en §7.1 sobre siete casos con tolerancia
    cero (`''`, `'a'`, `'a\\n'`, `'a\\nb'`, `'a\\nb\\n'`, `'\\n'`, `'a\\n\\n'`):

        |P_sep|   = L + 1                                SIEMPRE
        |P_lines| = 0        si |T| = 0
                  = L        si |T| > 0 y el flujo termina en `0x0A`
                  = L + 1    si |T| > 0 y no termina en `0x0A`

    `fin` **no es una entrada**: se deriva (§2.3.4.1), y en el caso degenerado
    `|T| = 0` vale `⊥` — `|P_sep| = 1` y `|P_lines| = 0` discrepan, y §2.3.4.2
    declara esa discrepancia correcta para que ninguna implementación la
    «arregle».

    La codificación se declara porque no se adivina. Un flujo que no decodifica
    produce `ErrorDecodificacion`: **no** se sustituye por `U+FFFD` (§4 err).
    """

    if not isinstance(flujo, bytes):
        raise ContratoViolado(
            "la partición opera sobre bytes, no sobre texto (§2.3.1)",
            valor=type(flujo).__name__,
        )
    if not isinstance(enc, str) or enc == "":
        raise ContratoViolado("la partición exige la codificación declarada (§2.3.4)", enc=enc)
    try:
        texto = flujo.decode(enc)
    except (UnicodeDecodeError, LookupError) as exc:
        raise ErrorDecodificacion(
            "el flujo no decodifica con la codificación declarada; no se "
            "sustituye por U+FFFD en silencio (§4 err)",
            enc=enc,
            causa=type(exc).__name__,
        ) from exc

    p_sep = tuple(texto.split("\n"))
    particion = Particion(p_sep, Particion.esperada(p_sep))

    saltos = flujo.count(_LF)
    if saltos != particion.l:
        raise ContratoViolado(
            "el conteo del byte 0x0A no coincide con |P_sep| − 1: con esta "
            "codificación `L` y la partición serían dos cifras del mismo "
            "objeto, y §2.3.4 declara la ley SIEMPRE (§2.3.3)",
            byte_0x0A=saltos,
            l=particion.l,
            enc=enc,
        )
    return particion


# ---------------------------------------------------------------------------
# §2.3 · §4 ficha — las seis dimensiones, medidas FUERA DE BANDA (INV-6)
# ---------------------------------------------------------------------------


def _ficha_del_descriptor(fd: int, enc: str, anchura: Optional[int]) -> Ficha:
    """Arma `F` desde un descriptor abierto y leído.

    `H`, `B` y `L` salen del flujo y del `st` del MISMO descriptor; `P` del
    flujo; `I`, `M` y `K` del `st`; `T0` de la escalera leída (§2.3.7).
    """

    flujo, st = _medir_descriptor(fd)
    return Ficha(
        h=_hash_de_flujo(flujo, anchura),
        b=st.st_size,
        p=partition(flujo, enc),
        i=Inodo(st.st_dev, st.st_ino),
        t0=_at._t0_de_stat(st),
        m=st.st_mode & 0o7777,
        k=st.st_nlink,
    )


def ficha(
    namespace: Namespace,
    slug: Slug,
    enc: str = "utf-8",
    anchura: Optional[int] = None,
) -> Ficha:
    """§4 `ficha` — **FUERA DE BANDA** (§2.3.9 · INV-6).

    Pre (§4): `slug` existe en el namespace y **no** es un enlace simbólico.
    Post (§4): `H` sobre el flujo crudo; `B = st_size` del mismo descriptor;
    `L = count(0x0A)`; `(P_sep, P_lines, fin)`; `I = (D, i)`; `T0 = t` o `⊥`.
    Falla con `ENOENT | ELOOP`; **la ausencia de `T0` no es un error**.

    INV-6. La ficha de una pieza no se mide dentro de la pieza: lo que la
    pieza imprime describe su versión anterior. Aquí se abre el objeto y se
    mide desde fuera; por eso `H` y `B` son legibles aunque el archivo siga
    creciendo —si creció entre la lectura y el `fstat`, `LecturaRasgada` lo
    declara en vez de fabricar una cifra—.

    `M` se mide del modo efectivo (incluye la `umask` de la medición): §8.4
    advierte que sólo es reproducible si esa `umask` se declara. Se mide; no se
    declara reproducible.
    """

    ns = _at._exigir_namespace(namespace)
    if not isinstance(slug, Slug):
        raise ContratoViolado("la ficha exige un Slug (§2.1)", valor=slug)

    st = _stat_de_entrada(ns.fd_root, slug.texto)
    if not _stat.S_ISREG(st.st_mode):
        raise ELOOP(
            "el objeto nombrado no es un objeto regular: no es enlace seguible "
            "ni se abre. Un FIFO en lectura bloquea sin escritor (§4 err ELOOP)",
            slug=str(slug),
            tipo=oct(st.st_mode & 0o170000),
        )

    fd = _abrir_lectura(ns.fd_root, slug.texto)
    try:
        return _ficha_del_descriptor(fd, enc, anchura)
    finally:
        _at._cerrar_sin_ruido(fd)


# ---------------------------------------------------------------------------
# §4 manifest · §2.5.2 — el manifiesto relativo, ordenado y autocerrado
# ---------------------------------------------------------------------------


def manifest(
    namespace: Namespace,
    exclusion: ConjuntoDeclarado,
    anchura: Optional[int] = None,
) -> Manifiesto:
    """§4 `manifest` — rutas relativas, orden byte a byte, autocerrado.

    Pre (§4): `E` capturado **antes** de hashear, enumerando slugs, y excluyendo
    el propio manifiesto y todo fichero de sumas. `E` es una afirmación del
    llamador sobre su subárbol: esta capa la registra, no la adjudica —no
    escribe el manifiesto y no conoce su nombre—.

    Post (§4): rutas relativas, orden byte a byte con colación C, algoritmo y
    anchura declarados. El manifiesto **no tiene campo para su propio hash**:
    incluirse es irrepresentable, no «desaconsejado» (§3.d.3).

    El recorrido se resuelve contra descriptores, nunca contra una ruta
    acumulada: ninguna ruta absoluta entra —ni siquiera transitoriamente— a la
    medición (§0.4.b, §0.4.c).
    """

    ns = _at._exigir_namespace(namespace)
    if not isinstance(exclusion, ConjuntoDeclarado):
        raise ContratoViolado(
            "el manifiesto exige `E` como CONJUNTO DECLARADO de slugs, capturado "
            "antes de hashear (§4 pre · §3.c.2 · §3.d.3)",
            tipo=type(exclusion).__name__,
        )

    entradas: List[EntradaManifiesto] = []

    def _recorrer(fd_dir: int, partes: Tuple[str, ...]) -> None:
        _at._exigir_dir_fd()
        try:
            nombres = _os.listdir(fd_dir)
        except OSError as exc:
            raise _at._error_tipado(exc) from exc
        for nombre in sorted(nombres):
            if exclusion.contiene(_slug_de_entrada(nombre)):
                continue
            st = _stat_de_entrada(fd_dir, nombre)
            ruta = RutaRelativa(SEPARADOR.join(partes + (nombre,)))
            if _stat.S_ISDIR(st.st_mode):
                fd_hijo = _abrir_directorio(fd_dir, nombre)
                try:
                    _recorrer(fd_hijo, partes + (nombre,))
                finally:
                    _at._cerrar_sin_ruido(fd_hijo)
                continue
            if not _stat.S_ISREG(st.st_mode):
                raise ELOOP(
                    "la entrada no es un objeto regular ni un directorio: no se "
                    "sigue y no se salta en silencio (§4 err ELOOP). Un FIFO no "
                    "se abre en lectura: `open` bloquea sin escritor y una "
                    "medición que cuelga no es una medición",
                    ruta=str(ruta),
                    tipo=oct(st.st_mode & 0o170000),
                )
            fd_obj = _abrir_lectura(fd_dir, nombre)
            try:
                flujo, _ = _medir_descriptor(fd_obj)
            finally:
                _at._cerrar_sin_ruido(fd_obj)
            entradas.append(EntradaManifiesto(ruta, _hash_de_flujo(flujo, anchura)))

    _recorrer(ns.fd_root, ())
    entradas.sort(key=lambda e: e.ruta.clave_bytes)
    return Manifiesto(
        entradas=tuple(entradas),
        algoritmo=ALGORITMO,
        anchura=anchura,
        exclusion=exclusion,
        orden="C",
    )


# ---------------------------------------------------------------------------
# §2.5.1 · §4 attest — el recibo: la cadena, no el sistema de archivos
# ---------------------------------------------------------------------------


def attest(
    slug: Slug,
    f: Ficha,
    prev: Optional[Recibo] = None,
    certificado: Optional[CertificadoExclusividad] = None,
) -> Recibo:
    """§4 `attest` — `R = (s, H, B, L, I, T0, H_prev)`.

    Post (§4): `H_prev = prev.H`. **La cadena, no el sistema de archivos, es
    el orden**: el recibo no se ordena por `mtime` —que no es motor de llegada—
    ni por `T0`, que no es portable (§2.3.7) y no es llave. Sin `prev`, el
    recibo es el origen de su cadena.

    El slug entra explícito: §4 nombra `attest(F, prev)`, pero `R` lo exige y
    `F` no lo lleva (§2.3). Deducirlo de una ruta reabriría la dependencia de
    la máquina de origen (§0.4.b).

    `certificado` es la extensión declarada que §3.a.2 exige registrar en el
    recibo y para la que `R` no tiene lugar en la tupla; su estatuto es el de
    `D`, `M` y `K` en §2.3.8. El certificado vale para UN volumen: viaja con
    su etiqueta, no con una ruta (§0.4.b).
    """

    if not isinstance(slug, Slug):
        raise ContratoViolado("el recibo exige un Slug (§2.1)", valor=slug)
    if not isinstance(f, Ficha):
        raise ContratoViolado("el recibo exige una Ficha medida (§2.3)", valor=type(f).__name__)
    if prev is not None and not isinstance(prev, Recibo):
        raise ContratoViolado(
            "el eslabón anterior es un Recibo o ⊥: la cadena no se ordena por el "
            "sistema de archivos (§2.5.1)",
            valor=type(prev).__name__,
        )
    if certificado is not None and not isinstance(certificado, CertificadoExclusividad):
        raise ContratoViolado(
            "el certificado de exclusividad es de §3.a.2 o ⊥",
            valor=type(certificado).__name__,
        )

    return Recibo(
        slug=slug,
        ficha=f,
        h_prev=None if prev is None else prev.ficha.h,
        certificado=certificado,
    )
