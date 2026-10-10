"""atomic.py — la primera capa funcional de Materia A (§3.a · §4).

Entrada/salida del protocolo: reserva exclusiva, sellado y dos sondas
empíricas. Todo lo demás —medir la ficha, contar el pie, deducir el
auto-conteo— vive en `metrics.py` y `audit.py`, y no se adelanta aquí.

Mapa de nombres declarado. El encargo nominaba entidades que `types.py` —ya
ratificado— no tiene. La correspondencia se declara; no se renombra en
silencio y no se inventa ningún tipo que SPEC.md no tenga:

    encargo            types.py (real)             razón
    ----------------   -------------------------  ---------------------------
    Handle             Reserva                    estado posterior al acto
    Certificado        CertificadoExclusividad    T-01 (§3.a.2)
                       CertificadoCaso            T-09 (INV-9)
    Error              ProtocoloError             base tipada
                       ContratoViolado            pre-condición §4, sin errno
    ErrnoEEXIST        EEXIST                     MAPA_ERRNO[errno.EEXIST]

Lecturas declaradas — siete, y ninguna se hace pasar por el texto de SPEC.md:

  1. §3.a.1 exige UNA escritura. `os.write` se llama una sola vez y su
     resultado se compara con el contenido. Un `write` corto NO se reintenta:
     §7.5 tiene medido que «un fallo de escritura no reporta cuánto escribió»,
     y reintentar convertiría el fallo en una segunda escritura. El objeto
     queda con el nombre ocupado: se declara, no se repara.
  2. `types.py` no tiene clase para la divergencia de ESCRITURA (su
     `LecturaRasgada` describe la lectura, INV-8). Se usa la base
     `ProtocoloError` con campos declarados, en vez de acuñar un tipo que
     SPEC.md no tiene.
  3. `⊥` se emite como `T0.nulo()`, no como `None`: `None` no declara por qué
     no hay valor.
  4. §0.4(d) prohíbe «depender» de `st_birthtime`. La escalera de INV-7 se
     LEE y no se exige: sin el campo, `T0` es `⊥` y no cambia ningún camino.
     El peldaño `statx(STATX_BTIME)` se declara NO IMPLEMENTADO —la
     biblioteca estándar no lo expone sin dependencias— y no se simula.
  5. `time` se añade al conjunto admitido de importaciones como lectura
     declarada: la etiqueta de `T₀` exige un reloj UTC y `time.gmtime` es el
     único de la biblioteca estándar —UTC e independiente de `TZ`. Lo
     prohibido por §0.4(d) son el reloj local y la zona del proceso:
     `localtime`, `timezone`, `altzone` y `tzset` no aparecen aquí.
  6. El modo efectivo `m & ~umask` (§3.a.4) no se calcula aquí. `Reserva` no
     tiene ranura para el modo (§2.3.8), y leer la `umask` exige cambiar el
     estado del proceso (`os.umask` es leer-y-fijar): una escritura global
     para una lectura. `modo` se pasa a `open`; el efectivo lo mide la ficha.
  7. `sincronizacion_directorio` sólo toma `True` o `⊥` —nunca `False`: un
     volumen que no sella se declara `⊥` (§4 post, §8.2), y `False` afirmaría
     que el volumen contestó cuando no contestó.

INV-6: este módulo no imprime su propia identidad ni cifra alguna. Devuelve
objetos tipados; imprimirlos es de quien los recibe.
"""

from __future__ import annotations

import errno as _errno
import os as _os
import time as _time
from typing import Final, Optional

from .types import (
    CertificadoCaso,
    CertificadoExclusividad,
    ContratoViolado,
    EEXIST,
    ENAMETOOLONG,
    ENOTSUP,
    FuenteT0,
    Inodo,
    MAPA_ERRNO,
    Namespace,
    ProtocoloError,
    Reserva,
    Slug,
    T0,
)

__all__ = [
    "BANDERAS_RESERVA",
    "SLUG_SONDA_CASO_MAYOR",
    "SLUG_SONDA_CASO_MENOR",
    "SLUG_SONDA_EXCL",
    "reserve",
    "sonda_caso",
    "sonda_excl",
]


# ---------------------------------------------------------------------------
# Declaración de plataforma. §8.3: lo que es parámetro no se supone.
# ---------------------------------------------------------------------------

_O_CLOEXEC: Final[Optional[int]] = getattr(_os, "O_CLOEXEC", None)
_O_DIRECTORY: Final[int] = getattr(_os, "O_DIRECTORY", 0)
_CLOEXEC_AUSENTE: Final[bool] = _O_CLOEXEC is None

#: §3.a.1. La máscara exacta de INV_EXCL, sin añadidos ni omisiones.
BANDERAS_RESERVA: Final[int] = (
    _os.O_CREAT | _os.O_EXCL | _os.O_WRONLY | (_O_CLOEXEC or 0)
)

#: Errores que significan «este volumen no sella directorios» (§8.2).
_ERRNOS_SIN_SELLADO: Final[frozenset] = frozenset(
    {
        _errno.EINVAL,
        _errno.ENOTSUP,
        getattr(_errno, "EOPNOTSUPP", _errno.ENOTSUP),
        _errno.EBADF,
        _errno.EACCES,
        _errno.EPERM,
        _errno.EROFS,
    }
)

#: Nombres de sonda declarados. Son SLUGS (§2.1), no rutas: ningún nombre de
#: este módulo lleva separador, ni prefijo `-`, ni componente de directorio.
SLUG_SONDA_EXCL: Final[Slug] = Slug(".protocolo-sonda-excl")
SLUG_SONDA_CASO_MENOR: Final[Slug] = Slug(".protocolo-sonda-caso-a")
SLUG_SONDA_CASO_MAYOR: Final[Slug] = Slug(".protocolo-sonda-caso-A")

#: Anchura declarada del redondeo de `T₀` a microsegundos (§2.3.7 · INV-7).
REDONDEO_US: Final[int] = 1


# ---------------------------------------------------------------------------
# Utilidades de declaración
# ---------------------------------------------------------------------------


def _exigir_namespace(namespace: object) -> Namespace:
    if not isinstance(namespace, Namespace):
        raise ContratoViolado(
            "la operación exige un Namespace (§2.4)",
            tipo=type(namespace).__name__,
        )
    return namespace


def _exigir_dir_fd() -> None:
    """El confinamiento al descriptor raíz es la única resolución admitida."""

    for funcion, nombre in (
        (_os.open, "os.open"),
        (_os.stat, "os.stat"),
        (_os.unlink, "os.unlink"),
    ):
        if funcion not in _os.supports_dir_fd:
            raise ENOTSUP(
                "el motor no admite dir_fd: la ruta no se puede confinar al "
                "descriptor raíz (§2.4 · §0.4.c)",
                funcion=nombre,
            )


def _etiqueta_utc(t: float) -> str:
    """Etiqueta UTC en la forma del taller: díaZ horaZ minZ segZ.micro.

    `time.gmtime` es UTC y no consulta `TZ`. La anchura del redondeo viaja en
    `T0.redondeo_us` porque los flotantes de nacimiento son fuente conocida de
    cifras no reproducibles (§2.3.7).
    """

    g = _time.gmtime(t)
    micro = int(round((t % 1.0) * 1e6))
    if micro >= 1000000:
        micro = 999999
    return "%02dZ%02dZ%02dZ%02dZ.%06d" % (g.tm_mday, g.tm_hour, g.tm_min, g.tm_sec, micro)


def _t0_de_stat(st: object) -> T0:
    """Escalera INV-7 leída, nunca exigida. Sin fuente disponible: `⊥`."""

    nace = getattr(st, "st_birthtime", None)
    if nace is None:
        return T0.nulo()
    return T0(FuenteT0.BIRTHTIME, _etiqueta_utc(float(nace)), redondeo_us=REDONDEO_US)


def _error_tipado(exc: BaseException) -> ProtocoloError:
    """Traduce un `OSError` a la clase tipada del contrato (§4 err).

    La clase mapeada conserva su nombre de errno; un errno no listado en
    `MAPA_ERRNO` no se disfraza de otra cosa: sale la base con el número y la
    clase del sistema declarados. El mensaje se arma con `strerror` y jamás con
    el nombre del objeto, para que ninguna ruta entre por el texto del error
    (§0.4.b).
    """

    numero = getattr(exc, "errno", None)
    mensaje = getattr(exc, "strerror", None) or str(exc)
    clase = MAPA_ERRNO.get(numero) if isinstance(numero, int) else None
    if clase is not None:
        return clase(mensaje, errno_numero=numero)
    return ProtocoloError(
        mensaje,
        errno_numero=numero,
        clase_de_os=type(exc).__name__,
    )


# ---------------------------------------------------------------------------
# §3.a INV_EXCL — la reserva
# ---------------------------------------------------------------------------


def _abrir_exclusivo(namespace: Namespace, slug: Slug, modo: int) -> int:
    """§3.a. `open` exclusivo y nada más. La ruta se resuelve contra FD_root."""

    if _CLOEXEC_AUSENTE:
        raise ENOTSUP(
            "O_CLOEXEC no existe en esta plataforma: no se abre un descriptor "
            "que se heredaría (§3.a.1)"
        )
    _exigir_dir_fd()
    try:
        return _os.open(
            slug.texto, BANDERAS_RESERVA, modo, dir_fd=namespace.fd_root
        )
    except OSError as exc:
        raise _error_tipado(exc) from exc


def _sellar_directorio(namespace: Namespace) -> Optional[bool]:
    """§3.a.1. Sincroniza el directorio, o declara `⊥`. Nunca declara `False`."""

    if namespace.sincronizacion_directorio is False:
        return None
    _exigir_dir_fd()
    fd = -1
    try:
        fd = _os.open(".", _os.O_RDONLY | _O_DIRECTORY, dir_fd=namespace.fd_root)
        _os.fsync(fd)
        return True
    except OSError as exc:
        numero = getattr(exc, "errno", None)
        if numero in _ERRNOS_SIN_SELLADO:
            return None
        raise _error_tipado(exc) from exc
    finally:
        if fd >= 0:
            try:
                _os.close(fd)
            except OSError:
                # El sellado ya se decidió; un fallo al cerrar el descriptor
                # del directorio no lo cambia y no se convierte en el error
                # visible. Se declara aquí en lugar de callarse.
                pass


def _cerrar_sin_ruido(fd: Optional[int]) -> None:
    """Cierra un descriptor de sonda. Un fallo al cerrar no altera el certificado."""

    if fd is None:
        return
    try:
        _os.close(fd)
    except OSError:
        pass


def _borrar_si_existe(namespace: Namespace, slug: Slug) -> None:
    """Limpieza declarada del objeto de prueba. No se traga otros errores."""

    try:
        _os.unlink(slug.texto, dir_fd=namespace.fd_root)
    except OSError as exc:
        if getattr(exc, "errno", None) == _errno.ENOENT:
            return
        raise _error_tipado(exc) from exc


def reserve(
    namespace: Namespace,
    slug: Slug,
    contenido: bytes,
    modo: int = 0o644,
) -> Reserva:
    """§4 `reserve` — reserva exclusiva, íntegra y sellada.

    Pre (§4): `slug` pertenece al alfabeto y a la forma canónica —lo garantiza
    el propio `Slug`—, cabe en `NAME_MAX(N)` y es inyectivo bajo caso y forma
    en el volumen declarado (§2.1.3).

    Post (§4): el nombre existe, `contenido` está íntegro en él, el descriptor
    quedó sincronizado, el directorio quedó sincronizado o declarado `⊥`, y `I`
    y `T₀` quedan fijados. Falla de forma determinista con `EEXIST` si el
    nombre estaba ocupado.
    """

    ns = _exigir_namespace(namespace)
    if not isinstance(slug, Slug):
        raise ContratoViolado("la reserva exige un Slug (§2.1)", valor=slug)
    if not isinstance(contenido, bytes):
        raise ContratoViolado("el contenido se reserva como bytes", valor=type(contenido).__name__)
    if not isinstance(modo, int) or isinstance(modo, bool) or modo < 0 or modo > 0o7777:
        raise ContratoViolado("modo fuera de rango", modo=modo)

    if not ns.admite(slug):
        raise ENAMETOOLONG(
            "el slug excede NAME_MAX del namespace (§2.1 · §8.3)",
            nombre_max=ns.nombre_max,
            bytes_slug=slug.longitud_bytes,
        )

    # §2.1.3. La forma canónica ya es inyectiva por construcción (`Slug` exige
    # NFC y el alfabeto ASCII la subsume). La inyectividad de CASO sólo se
    # puede pre-decidir desde la declaración del volumen: si el volumen no
    # distingue caso, dos slugs que sólo difieran en caso son un solo nombre y
    # la exclusividad de INV_EXCL deja de proteger sin que ninguna llamada
    # falle.
    if ns.sensible_al_caso is False and slug.clave_casefold != slug.texto:
        raise ContratoViolado(
            "el volumen está declarado insensible al caso y este slug no es "
            "inyectivo bajo casefold (§2.1.3 · INV-9)",
            slug=slug.texto,
            clave_casefold=slug.clave_casefold,
            certificar_con="sonda_caso",
        )

    fd = _abrir_exclusivo(ns, slug, modo)
    fallo: Optional[BaseException] = None
    i: Optional[Inodo] = None
    t0: Optional[T0] = None
    try:
        escrito = _os.write(fd, contenido)
        if escrito != len(contenido):
            raise ProtocoloError(
                "escritura rasgada: los bytes escritos no son los del contenido "
                "(§3.a.1 exige UNA escritura: no se reintenta)",
                escrito=escrito,
                esperado=len(contenido),
                nombre_ocupado=True,
            )
        st = _os.fstat(fd)
        if st.st_size != len(contenido):
            raise ProtocoloError(
                "st_size discrepa del contenido escrito (§2.3.2 · INV-8, sobre "
                "el mismo descriptor)",
                st_size=st.st_size,
                esperado=len(contenido),
                nombre_ocupado=True,
            )
        i = Inodo(st.st_dev, st.st_ino)
        t0 = _t0_de_stat(st)
        _os.fsync(fd)
    except BaseException as exc:
        fallo = exc
    try:
        _os.close(fd)
    except OSError as exc:
        if fallo is None:
            fallo = _error_tipado(exc)
    if fallo is not None:
        raise fallo

    assert i is not None and t0 is not None
    return Reserva(
        slug=slug,
        i=i,
        t0=t0,
        sellado=True,
        sincronizacion_directorio=_sellar_directorio(ns),
    )


# ---------------------------------------------------------------------------
# §5 T-01 · §5 T-09 — las dos sondas sobre el volumen real
# ---------------------------------------------------------------------------


def sonda_excl(namespace: Namespace) -> CertificadoExclusividad:
    """§5 T-01. ¿Colapsa `O_EXCL` con `EEXIST` en este volumen?

    Dos aperturas exclusivas consecutivas sobre el mismo nombre de sonda: la
    primera debe tener éxito, la segunda debe colapsar. El certificado vale
    para UN volumen y sólo para él (§3.a.2), y se emite con el nombre de sonda
    ya borrado.

    Si el nombre de sonda ya estaba ocupado, la sonda no corrió y por eso NO
    emite certificado: un booleano aquí sería una figura sin medición. Falla
    con `EEXIST` y lo declara. La durabilidad de la sonda no se certifica: la
    sonda mide atomicidad, no sellado.
    """

    ns = _exigir_namespace(namespace)
    slug = SLUG_SONDA_EXCL
    if not ns.admite(slug):
        raise ENAMETOOLONG(
            "el slug de sonda excede NAME_MAX del namespace",
            nombre_max=ns.nombre_max,
            bytes_slug=slug.longitud_bytes,
        )

    try:
        primero = _abrir_exclusivo(ns, slug, 0o600)
    except EEXIST as exc:
        raise EEXIST(
            "el nombre de sonda ya estaba ocupado: la sonda de atomicidad no "
            "corrió y no emite certificado (§5 T-01)",
            slug=slug.texto,
        ) from exc

    segundo: Optional[int] = None
    colapsa = False
    try:
        try:
            segundo = _abrir_exclusivo(ns, slug, 0o600)
        except EEXIST:
            colapsa = True
        return CertificadoExclusividad(
            atomico=colapsa,
            volumen=ns.volumen,
            motivo=(
                "la segunda apertura exclusiva sobre %r colapsó con EEXIST "
                "dejando viva la primera" % slug.texto
                if colapsa
                else "la segunda apertura exclusiva sobre %r tuvo éxito: dos "
                "objetos con un solo nombre (§5 T-01, falsación)" % slug.texto
            ),
        )
    finally:
        _cerrar_sin_ruido(primero)
        _cerrar_sin_ruido(segundo)
        _borrar_si_existe(ns, slug)


def sonda_caso(namespace: Namespace) -> CertificadoCaso:
    """§5 T-09 · INV-9. ¿Distingue el volumen mayúsculas de minúsculas?

    Crea el nombre de sonda en minúsculas y consulta existencia con el MISMO
    nombre en mayúsculas mediante llamada de sistema (`stat`), sin pasar por el
    listado del directorio: un listado devuelve el nombre real y mide la
    colación del motor, no la del volumen.

    Un volumen insensible convierte dos slugs que difieran sólo en caso en un
    único nombre: la exclusividad de INV_EXCL deja de proteger sin que ninguna
    llamada falle. El certificado vale para UN volumen y sólo para él, y se
    emite con el nombre de sonda ya borrado.
    """

    ns = _exigir_namespace(namespace)
    menor = SLUG_SONDA_CASO_MENOR
    mayor = SLUG_SONDA_CASO_MAYOR
    for slug in (menor, mayor):
        if not ns.admite(slug):
            raise ENAMETOOLONG(
                "el slug de sonda excede NAME_MAX del namespace",
                nombre_max=ns.nombre_max,
                bytes_slug=slug.longitud_bytes,
            )
    _exigir_dir_fd()

    try:
        creado: Optional[int] = _abrir_exclusivo(ns, menor, 0o600)
    except EEXIST as exc:
        raise EEXIST(
            "el nombre de sonda ya estaba ocupado: la sonda de caso no corrió y "
            "no emite certificado (INV-9)",
            slug=menor.texto,
        ) from exc

    try:
        try:
            _os.stat(mayor.texto, dir_fd=ns.fd_root, follow_symlinks=False)
            insensible = True
        except OSError as exc:
            if getattr(exc, "errno", None) == _errno.ENOENT:
                insensible = False
            else:
                raise _error_tipado(exc) from exc
        return CertificadoCaso(
            sensible_al_caso=not insensible,
            volumen=ns.volumen,
            motivo=(
                "stat sobre %r halló el objeto creado como %r: el volumen NO "
                "distingue caso" % (mayor.texto, menor.texto)
                if insensible
                else "stat sobre %r no halló el objeto creado como %r: el "
                "volumen distingue caso" % (mayor.texto, menor.texto)
            ),
        )
    finally:
        _cerrar_sin_ruido(creado)
        _borrar_si_existe(ns, menor)
        _borrar_si_existe(ns, mayor)
