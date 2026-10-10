"""protocol.types — contratos inmutables de la Materia A.

Transcripción tipada de `protocol-core/SPEC.md` (Protocolo de Custodia
Determinista y Reserva de Ranuras): §1.3–§1.4 (unidad y etiqueta), §2.1–§2.5
(tipos y primitivas), las invariantes de §3 en su parte estructural, y los
errores POSIX de §4. Este módulo **no implementa ninguna operación**: declara
los contratos que las implementaciones (§6) deben satisfacer. La partición, el
manifiesto y el censo se ejecutan en `metrics` y `audit`.

Criterio de admisión de SPEC §0.4, verificado sobre este mismo archivo:
  (a) sostiene casos de §5: T-02 (leyes de partición), T-06 (T0 = ⊥ es valor
      válido), T-07 (K declarado; I no es llave), T-09 (forma canónica del slug);
  (b) cero rutas absolutas; `RutaRelativa` y `Namespace` las rechazan;
  (c) cero dependencia del directorio temporal del sistema ni de recursos fuera
      del namespace: no se importa `tempfile` ni nada semejante;
  (d) cero `st_birthtime`, cero reloj local, cero zona horaria: este módulo no
      importa ningún reloj, y `T0` transporta una etiqueta ya formada;
  (e) no emite cifras: la etiqueta de INV_TIME es `Contexto`, y sin ella
      `Etiqueta` no se construye.

Lecturas declaradas. Son declaraciones, no reparaciones silenciosas: `SPEC.md`
está fijado y no se edita desde aquí.
  - §2.3 dice «Seis son obligatorias» y §2.3.7 declara `T0` opcional. Se lee el
    cardinal de la tupla `F = (H, B, L, P, I, T0)` como lo que «seis» nombra, y
    la obligatoriedad se toma de §2.3.7 y del bloque `post` de §4: `T0 = ⊥` es
    un valor válido, no ausencia de dato.
  - `L`, `D` y `fin` **no** se almacenan. `|P_sep| = L + 1` es universal
    (§2.3.4), `D = i.dev` por definición de `I` (§2.3.5) y `fin` se deriva de la
    partición (§2.3.4.1). Almacenarlos admitiría un objeto internamente
    contradictorio: aquí eso es irrepresentable.
  - `fin` es `None` cuando el flujo es vacío: la equivalencia de §2.3.4.1 rige
    «cuando |T| > 0», y §2.3.4.2 declara el caso degenerado correcto, no
    corregible.
  - `L <= B` **no** se impone: depende de `enc`, que el tipo no conoce.
  - §3.a.2 exige registrar el certificado de INV_EXCL «en el recibo» y §2.5.1 no
    le da lugar en la tupla. Se tipa como extensión declarada del recibo, con el
    mismo estatuto que `D`, `M` y `K` tienen en §2.3.8.
  - El alfabeto de §2.1 es ASCII, luego la regla NFC queda subsumida por él. Se
    conserva —y se declara redundante— porque sólo mordería si el alfabeto se
    ensanchara.
  - Las pre-condiciones de §4 no tienen errno. Se tipan con `ContratoViolado`,
    que **no** entra en `MAPA_ERRNO`: no es un resultado del sistema operativo.

Trampa declarada. Una `Z` literal sobre una hora local es «una mentira con forma
de etiqueta» (SPEC §3.e.4). `Contexto` comprueba la **forma** de la etiqueta y
no su verdad: un chequeo que busca una forma no certifica la ausencia de las
otras, y el reloj etiquetado es disciplina del llamador.
"""

from __future__ import annotations

import errno as _errno
import unicodedata as _unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal, Mapping, Optional, Tuple, Type, Union

__all__ = [
    "ALFABETO",
    "ALGORITMO",
    "ANCHURA_COMPLETA",
    "BOTTOM",
    "CertificadoCaso",
    "CertificadoExclusividad",
    "ConjuntoDeclarado",
    "ContratoViolado",
    "Contexto",
    "Divergencia",
    "EEXIST",
    "EACCES",
    "EISDIR",
    "ELOOP",
    "ENAMETOOLONG",
    "ENOENT",
    "ENOSPC",
    "ENOTSUP",
    "EXDEV",
    "EntradaManifiesto",
    "ErrorDecodificacion",
    "EstrategiaSelf",
    "Etiqueta",
    "Ficha",
    "FuenteT0",
    "Hash",
    "Indeterminado",
    "Inodo",
    "LecturaRasgada",
    "MAPA_ERRNO",
    "Manifiesto",
    "Namespace",
    "OK",
    "Particion",
    "ProtocoloError",
    "Ranura",
    "Recibo",
    "Reserva",
    "ResultadoResta",
    "ResultadoVerificacion",
    "RutaRelativa",
    "Slug",
    "T0",
    "Unidad",
]


# ---------------------------------------------------------------------------
# §2.1 Alfabeto, forma canónica y algoritmo. Constantes declaradas, no leyes
# deducidas: `NAME_MAX` no vive aquí porque es parámetro del namespace (§2.1).
# ---------------------------------------------------------------------------

ALFABETO: Final[str] = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)
ALGORITMO: Final[str] = "sha256"
ANCHURA_COMPLETA: Final[int] = 64
BOTTOM: Final[str] = "⊥"
NUL: Final[str] = chr(0)
SEPARADOR: Final[str] = "/"
_HEX: Final[frozenset] = frozenset("0123456789abcdef")


def _entero_mayor_que_cero(valor: object, campo: str, minimo: int) -> None:
    if not isinstance(valor, int) or isinstance(valor, bool) or valor < minimo:
        raise ContratoViolado(
            "no es un entero admisible", campo=campo, valor=valor, minimo=minimo
        )


def _etiqueta_de_volumen(valor: object) -> None:
    """El volumen viaja como ETIQUETA legible, nunca como ruta (§0.4.b)."""

    if not isinstance(valor, str) or valor == "":
        raise ContratoViolado("la etiqueta del volumen no puede ser vacía")
    if valor.startswith(SEPARADOR):
        raise ContratoViolado("una ruta absoluta no puede etiquetar un volumen", etiqueta=valor)


# ---------------------------------------------------------------------------
# §4 Errores. El nombre de la clase ES el nombre del contrato: se conserva la
# mayúscula del errno y se declara la excepción a la convención de estilo.
# ---------------------------------------------------------------------------


class ProtocoloError(Exception):
    """Falla tipada del protocolo. Nunca se devuelve un centinela ambiguo."""

    errno_nombre: str = ""

    def __init__(self, mensaje: str = "", **campos: object) -> None:
        super().__init__(mensaje or self.errno_nombre)
        self.mensaje: str = mensaje
        self.campos: Mapping[str, object] = dict(campos)

    def __repr__(self) -> str:
        return "%s(%r, %r)" % (type(self).__name__, self.mensaje, self.campos)


class ContratoViolado(ProtocoloError):
    """Pre-condición de §4 incumplida. No es un resultado del sistema operativo."""


class EEXIST(ProtocoloError):  # noqa: N801 - el nombre es el contrato §4
    """El nombre ya existe. Resultado determinista de INV_EXCL (§3.a.3)."""

    errno_nombre = "EEXIST"


class ENAMETOOLONG(ProtocoloError):  # noqa: N801
    """El slug excede `NAME_MAX(N)`. Parámetro del namespace (§2.1, §8.3)."""

    errno_nombre = "ENAMETOOLONG"


class EXDEV(ProtocoloError):  # noqa: N801
    """Enlace duro o movimiento a través de la frontera de un volumen (§2.3.5)."""

    errno_nombre = "EXDEV"


class EACCES(ProtocoloError):  # noqa: N801
    errno_nombre = "EACCES"


class EISDIR(ProtocoloError):  # noqa: N801
    errno_nombre = "EISDIR"


class ENOTSUP(ProtocoloError):  # noqa: N801
    """Operación no soportada por el volumen (p. ej. sellado de directorio, §8.2)."""

    errno_nombre = "ENOTSUP"


class ENOSPC(ProtocoloError):  # noqa: N801
    errno_nombre = "ENOSPC"


class ENOENT(ProtocoloError):  # noqa: N801
    errno_nombre = "ENOENT"


class ELOOP(ProtocoloError):  # noqa: N801
    """Demasiados enlaces simbólicos: la ficha exige objeto directo (§4)."""

    errno_nombre = "ELOOP"


class ErrorDecodificacion(ProtocoloError):
    """§4 `partition`: el fallo de decodificación se declara; no se sustituye
    por U+FFFD en silencio."""


class LecturaRasgada(ProtocoloError):
    """`st_size` discrepa del flujo leído (INV-8). Se declara, no se reintenta
    hasta que salga un número redondo."""


MAPA_ERRNO: Final[Mapping[int, Type[ProtocoloError]]] = {
    _errno.EEXIST: EEXIST,
    _errno.ENAMETOOLONG: ENAMETOOLONG,
    _errno.EXDEV: EXDEV,
    _errno.EACCES: EACCES,
    _errno.EISDIR: EISDIR,
    _errno.ENOTSUP: ENOTSUP,
    _errno.ENOSPC: ENOSPC,
    _errno.ENOENT: ENOENT,
    _errno.ELOOP: ELOOP,
}


# ---------------------------------------------------------------------------
# Enumeraciones declaradas
# ---------------------------------------------------------------------------


class Unidad(Enum):
    """§1.3. Unidades distintas dan números distintos sobre el mismo objeto."""

    ARCHIVO = "archivo"
    LINEA = "línea"
    OCURRENCIA = "ocurrencia"
    BYTE = "byte"


class FuenteT0(Enum):
    """§2.3.7 · INV-7. Escalera declarada del nacimiento. `NINGUNA` da `⊥`."""

    BIRTHTIME = "st_birthtime"
    STATX_BTIME = "statx(STATX_BTIME)"
    NINGUNA = "ninguna"


class EstrategiaSelf(Enum):
    """§3. Mutuamente excluyentes: aplicar E y D a la vez descuenta dos veces."""

    E_EXCLUSION = "E"
    D_DEDUCCION = "D"


# ---------------------------------------------------------------------------
# §2.1 Slug — llave primaria del protocolo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Slug:
    """Identificador unívoco atómico (§2.1).

    Admisibilidad namespace-independiente: alfabeto, prohibiciones y forma
    canónica. La longitud contra `NAME_MAX(N)` la decide el `Namespace`, porque
    es parámetro suyo y no constante del protocolo.
    """

    texto: str

    def __post_init__(self) -> None:
        t = self.texto
        if not isinstance(t, str) or t == "":
            raise ContratoViolado("slug vacío o no textual", valor=t)
        if NUL in t:
            raise ContratoViolado("NUL prohibido (§2.1)", slug=t)
        if SEPARADOR in t:
            raise ContratoViolado("separador de ruta prohibido (§2.1)", slug=t)
        if t == "." or t == "..":
            raise ContratoViolado("componente de directorio prohibido (§2.1)", slug=t)
        if t.startswith("-"):
            raise ContratoViolado("prefijo '-' prohibido (§2.1)", slug=t)
        fuera = sorted({c for c in t if c not in ALFABETO})
        if fuera:
            raise ContratoViolado("byte fuera del alfabeto (§2.1)", slug=t, fuera=fuera)
        if _unicodedata.normalize("NFC", t) != t:
            raise ContratoViolado("forma no canónica NFC (§2.1)", slug=t)

    @property
    def longitud_bytes(self) -> int:
        return len(self.texto.encode("utf-8"))

    @property
    def clave_casefold(self) -> str:
        """Clave de inyectividad de caso (§2.1.3, INV-9)."""

        return self.texto.casefold()

    @property
    def clave_forma(self) -> str:
        """Clave de inyectividad de forma (§2.1.3, INV-9)."""

        return _unicodedata.normalize("NFC", self.texto)

    def __str__(self) -> str:
        return self.texto


@dataclass(frozen=True)
class Ranura:
    """§2.2. Proyección lógica NO exclusiva: no es llave y no confiere unicidad."""

    s: int

    def __post_init__(self) -> None:
        _entero_mayor_que_cero(self.s, "ranura", 0)


@dataclass(frozen=True)
class RutaRelativa:
    """§2.4 y §2.5.2. Ruta confinada al namespace, compuesta de slugs.

    Rechaza rutas absolutas y todo componente `..`. Al exigir que cada
    componente sea un `Slug`, hereda alfabeto y forma canónica: no hay una
    segunda definición de nombre en el protocolo.
    """

    texto: str

    def __post_init__(self) -> None:
        t = self.texto
        if not isinstance(t, str) or t == "":
            raise ContratoViolado("ruta vacía o no textual", valor=t)
        if NUL in t:
            raise ContratoViolado("NUL prohibido en ruta", ruta=t)
        if t.startswith(SEPARADOR):
            raise ContratoViolado("ruta absoluta prohibida (§2.4)", ruta=t)
        partes = t.split(SEPARADOR)
        if any(p == "" for p in partes):
            raise ContratoViolado("componente vacío en ruta (§2.4)", ruta=t)
        if any(p == ".." for p in partes):
            raise ContratoViolado("componente '..' prohibido (§2.4)", ruta=t)
        for p in partes:
            try:
                Slug(p)
            except ContratoViolado as exc:
                raise ContratoViolado(
                    "componente no admisible como slug", ruta=t, componente=p, causa=str(exc)
                ) from exc

    @property
    def partes(self) -> Tuple[Slug, ...]:
        return tuple(Slug(p) for p in self.texto.split(SEPARADOR))

    @property
    def clave_bytes(self) -> bytes:
        """Clave de orden byte a byte, colación C (§3.d.2)."""

        return self.texto.encode("utf-8")

    def __str__(self) -> str:
        return self.texto


# ---------------------------------------------------------------------------
# §2.3 Dimensiones de la ficha
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hash:
    """§2.3.1. Identidad portable. Viaja siempre con algoritmo y anchura."""

    algoritmo: str
    digest: str
    anchura: Optional[int] = None

    def __post_init__(self) -> None:
        if self.algoritmo != ALGORITMO:
            raise ContratoViolado("algoritmo no declarado en §2.3.1", algoritmo=self.algoritmo)
        esperada = ANCHURA_COMPLETA if self.anchura is None else self.anchura
        if not isinstance(esperada, int) or isinstance(esperada, bool):
            raise ContratoViolado("anchura no entera", anchura=self.anchura)
        if esperada < 1 or esperada > ANCHURA_COMPLETA:
            raise ContratoViolado("anchura fuera de rango", anchura=self.anchura)
        if not isinstance(self.digest, str):
            raise ContratoViolado("digest no textual", digest=self.digest)
        if len(self.digest) != esperada:
            raise ContratoViolado(
                "el digest no tiene la anchura declarada",
                anchura=self.anchura,
                longitud=len(self.digest),
            )
        if any(c not in _HEX for c in self.digest):
            raise ContratoViolado("digest no hexadecimal en minúsculas", digest=self.digest)

    @property
    def etiqueta(self) -> str:
        return "%s:%d" % (self.algoritmo, self.anchura or ANCHURA_COMPLETA)

    @property
    def truncado(self) -> bool:
        return self.anchura is not None and self.anchura < ANCHURA_COMPLETA


@dataclass(frozen=True)
class Inodo:
    """§2.3.5. `I = (D, i)`. Válido dentro del volumen: `st_ino` sin `D` no
    identifica nada entre volúmenes."""

    dev: int
    ino: int

    def __post_init__(self) -> None:
        _entero_mayor_que_cero(self.dev, "dev", 0)
        _entero_mayor_que_cero(self.ino, "ino", 0)


@dataclass(frozen=True)
class T0:
    """§2.3.7 · INV-7. Nacimiento: campo opcional y no portable.

    `⊥` es valor válido y se imprime como `⊥`. Inventarlo es la falsificación
    más barata que admite este protocolo. `T0` no ordena la cadena de recibos y
    no es llave. La anchura de redondeo se declara porque los flotantes de
    nacimiento son fuente conocida de cifras no reproducibles.
    """

    fuente: FuenteT0
    etiqueta: Optional[str] = None
    redondeo_us: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.fuente, FuenteT0):
            raise ContratoViolado("fuente de nacimiento no declarada", fuente=self.fuente)
        nulo = self.fuente is FuenteT0.NINGUNA
        if nulo != (self.etiqueta is None):
            raise ContratoViolado(
                "⊥ y etiqueta se excluyen: sin fuente no hay valor, con fuente hay valor",
                fuente=self.fuente,
                etiqueta=self.etiqueta,
            )
        if not nulo:
            if not isinstance(self.etiqueta, str) or self.etiqueta == "":
                raise ContratoViolado("etiqueta de nacimiento vacía")
            if "Z" not in self.etiqueta:
                raise ContratoViolado(
                    "la etiqueta no declara UTC (§3.e.4); su verdad no la comprueba un tipo",
                    etiqueta=self.etiqueta,
                )
        if self.redondeo_us is not None:
            _entero_mayor_que_cero(self.redondeo_us, "redondeo_us", 0)

    @staticmethod
    def nulo() -> T0:
        return T0(FuenteT0.NINGUNA)

    @property
    def es_nulo(self) -> bool:
        return self.fuente is FuenteT0.NINGUNA

    def __str__(self) -> str:
        return BOTTOM if self.es_nulo else str(self.etiqueta)


@dataclass(frozen=True)
class Particion:
    """§2.3.4. Dos proyecciones, ambas obligatorias, ambas declaradas.

    `P_sep` conserva el campo vacío final; `P_lines` lo descarta. La segunda es
    función de la primera, así que una partición internamente contradictoria es
    irrepresentable: la ley de tres ramas no se comprueba después, no puede
    dejar de cumplirse. `fin` se deriva y jamás se recibe (§2.3.4.1).
    """

    p_sep: Tuple[str, ...]
    p_lines: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.p_sep, tuple) or len(self.p_sep) < 1:
            raise ContratoViolado("|P_sep| = L + 1 es siempre >= 1 (§2.3.4)")
        if any(not isinstance(x, str) for x in self.p_sep):
            raise ContratoViolado("los campos de P_sep no son textuales")
        if not isinstance(self.p_lines, tuple):
            raise ContratoViolado("P_lines no es tupla")
        esperada = self.esperada(self.p_sep)
        if self.p_lines != esperada:
            raise ContratoViolado(
                "P_lines no es la proyección que descarta el campo vacío final",
                p_lines=self.p_lines,
                esperada=esperada,
            )

    @staticmethod
    def esperada(p_sep: Tuple[str, ...]) -> Tuple[str, ...]:
        return p_sep[:-1] if p_sep[-1] == "" else p_sep

    @property
    def l(self) -> int:
        return len(self.p_sep) - 1

    @property
    def vacio(self) -> bool:
        return len(self.p_sep) == 1 and self.p_sep[0] == ""

    @property
    def fin(self) -> Optional[bool]:
        if self.vacio:
            return None
        return self.p_sep[-1] == ""


@dataclass(frozen=True)
class Ficha:
    """§2.3. `F = (H, B, L, P, I, T0)` más extensiones declaradas (§2.3.8).

    `L` y `D` se exponen como propiedades y no como campos: son funciones de `P`
    y de `I`, y almacenarlos admitiría un objeto contradictorio. `B` contra el
    flujo leído lo exige INV-8 en la operación; aquí sólo se fija lo que el tipo
    puede decidir sin el flujo: `B = 0` sii flujo vacío.
    """

    h: Hash
    b: int
    p: Particion
    i: Inodo
    t0: Optional[T0] = None
    m: Optional[int] = None
    k: Optional[int] = None

    def __post_init__(self) -> None:
        for campo, valor in (("h", self.h), ("p", self.p), ("i", self.i)):
            if valor is None:
                raise ContratoViolado("dimensión obligatoria ausente", campo=campo)
        _entero_mayor_que_cero(self.b, "b", 0)
        if (self.b == 0) != self.p.vacio:
            raise ContratoViolado(
                "B y la partición discrepan: B = 0 sii flujo vacío (§2.3.2, §2.3.4.2)",
                b=self.b,
                vacio=self.p.vacio,
            )
        if self.t0 is not None and not isinstance(self.t0, T0):
            raise ContratoViolado("T0 mal tipado", t0=self.t0)
        if self.m is not None:
            _entero_mayor_que_cero(self.m, "m", 0)
            if self.m > 0o7777:
                raise ContratoViolado("modo fuera de rango", modo=self.m)
        if self.k is not None:
            _entero_mayor_que_cero(self.k, "k", 1)

    @property
    def l(self) -> int:
        """§2.3.3. Conteo del byte 0x0A. No es un conteo de líneas."""

        return self.p.l

    @property
    def fin(self) -> Optional[bool]:
        return self.p.fin

    @property
    def vacio(self) -> bool:
        return self.p.vacio

    @property
    def d(self) -> int:
        return self.i.dev

    @property
    def nacimiento(self) -> str:
        """Impresión declarada de `T0`: `⊥` cuando no hay fuente (§2.3.7)."""

        return str(self.t0) if self.t0 is not None else BOTTOM


# ---------------------------------------------------------------------------
# §3.d · §2.5.2 Conjunto enumerado y manifiesto
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConjuntoDeclarado:
    """§3.c.2. La exclusión se enumera por slug, de un conjunto declarado.

    Excluir «todo lo que lleve X en la ruta» mata archivos ajenos: la misma
    subcadena aparece en nombres de objetos distintos. Una subcadena no es un
    conjunto y no se admite aquí.
    """

    slugs: Tuple[Slug, ...]
    motivo: str

    def __post_init__(self) -> None:
        if not isinstance(self.slugs, tuple):
            raise ContratoViolado("el conjunto declarado no es tupla de slugs")
        if any(not isinstance(s, Slug) for s in self.slugs):
            raise ContratoViolado("el conjunto declarado admite sólo Slug, no subcadenas")
        if not isinstance(self.motivo, str) or self.motivo == "":
            raise ContratoViolado("el conjunto declarado exige motivo declarado")
        claves = [s.texto for s in self.slugs]
        if len(set(claves)) != len(claves):
            raise ContratoViolado("el conjunto declarado repite slugs", repetidos=len(claves) - len(set(claves)))

    def contiene(self, slug: Slug) -> bool:
        return slug in self.slugs


@dataclass(frozen=True)
class EntradaManifiesto:
    """Par `(H, slug)` de §2.5.2, con la ruta relativa confinada."""

    ruta: RutaRelativa
    h: Hash


@dataclass(frozen=True)
class Manifiesto:
    """§2.5.2 · INV_ISOL. Lista ordenada, de rutas relativas, autocerrada.

    No tiene campo para su propio hash: un manifiesto que se incluyera es
    irrepresentable, no «desaconsejado» (§3.d.3). El orden se exige byte a byte
    con colación C, de modo que dos máquinas ordenen igual el mismo contenido.
    """

    entradas: Tuple[EntradaManifiesto, ...]
    algoritmo: str
    anchura: Optional[int]
    exclusion: ConjuntoDeclarado
    orden: str = "C"

    def __post_init__(self) -> None:
        if not isinstance(self.entradas, tuple):
            raise ContratoViolado("las entradas del manifiesto no son tupla")
        if self.algoritmo != ALGORITMO:
            raise ContratoViolado("algoritmo de manifiesto no declarado (§3.d.4)", algoritmo=self.algoritmo)
        if self.orden != "C":
            raise ContratoViolado("orden no declarado como colación C (§3.d.2)", orden=self.orden)
        if not isinstance(self.exclusion, ConjuntoDeclarado):
            raise ContratoViolado("el manifiesto exige la exclusión enumerada (§3.d.3)")
        claves = [e.ruta.clave_bytes for e in self.entradas]
        if any(claves[i] > claves[i + 1] for i in range(len(claves) - 1)):
            raise ContratoViolado("las entradas no están en orden byte a byte (§3.d.2)")
        if len(set(claves)) != len(claves):
            raise ContratoViolado("el manifiesto repite rutas")
        for e in self.entradas:
            if not isinstance(e, EntradaManifiesto):
                raise ContratoViolado("entrada de manifiesto mal tipada")
            if e.h.algoritmo != self.algoritmo or e.h.anchura != self.anchura:
                raise ContratoViolado(
                    "una entrada declara algoritmo o anchura distintos de los del manifiesto",
                    ruta=str(e.ruta),
                    etiqueta=e.h.etiqueta,
                )

    @property
    def rutas(self) -> Tuple[RutaRelativa, ...]:
        return tuple(e.ruta for e in self.entradas)


# ---------------------------------------------------------------------------
# §2.5.1 Recibo — la cadena es el motor de nacimiento
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CertificadoExclusividad:
    """§3.a.2. La atomicidad de `O_EXCL` no está garantizada por POSIX en
    sistemas de archivos de red. El certificado vale para UN volumen."""

    atomico: bool
    volumen: str
    motivo: str

    def __post_init__(self) -> None:
        if not isinstance(self.atomico, bool):
            raise ContratoViolado("el certificado declara un booleano, no una impresión")
        _etiqueta_de_volumen(self.volumen)
        if not isinstance(self.motivo, str) or self.motivo == "":
            raise ContratoViolado("el certificado exige motivo declarado")


@dataclass(frozen=True)
class CertificadoCaso:
    """INV-9. Un volumen insensible al caso convierte dos slugs en un nombre."""

    sensible_al_caso: bool
    volumen: str
    motivo: str

    def __post_init__(self) -> None:
        if not isinstance(self.sensible_al_caso, bool):
            raise ContratoViolado("el certificado declara un booleano, no una impresión")
        _etiqueta_de_volumen(self.volumen)
        if not isinstance(self.motivo, str) or self.motivo == "":
            raise ContratoViolado("el certificado exige motivo declarado")


@dataclass(frozen=True)
class Recibo:
    """§2.5.1. `R = (s, H, B, L, I, T0, H_prev)`.

    Las seis dimensiones de la ficha se exponen por delegación: el recibo no
    almacena una segunda copia que podría contradecir a la primera. `H_prev`
    nulo marca el origen de la cadena. El sistema de archivos no es un notario:
    sus marcas son testigos, no firmas.
    """

    slug: Slug
    ficha: Ficha
    h_prev: Optional[Hash] = None
    certificado: Optional[CertificadoExclusividad] = None

    def __post_init__(self) -> None:
        if not isinstance(self.slug, Slug) or not isinstance(self.ficha, Ficha):
            raise ContratoViolado("el recibo exige slug y ficha tipados")
        if self.h_prev is not None and not isinstance(self.h_prev, Hash):
            raise ContratoViolado("H_prev mal tipado", h_prev=self.h_prev)
        if self.certificado is not None and not isinstance(self.certificado, CertificadoExclusividad):
            raise ContratoViolado("certificado de exclusividad mal tipado")

    @property
    def h(self) -> Hash:
        return self.ficha.h

    @property
    def b(self) -> int:
        return self.ficha.b

    @property
    def l(self) -> int:
        return self.ficha.l

    @property
    def p(self) -> Particion:
        return self.ficha.p

    @property
    def i(self) -> Inodo:
        return self.ficha.i

    @property
    def t0(self) -> Optional[T0]:
        return self.ficha.t0

    @property
    def es_origen(self) -> bool:
        return self.h_prev is None


# ---------------------------------------------------------------------------
# §2.4 Namespace · §4 Reserva
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Namespace:
    """§2.4. Dominio delimitado por `FD_root`, que declara sus cuatro
    parámetros: sensibilidad al caso, `NAME_MAX`, motor de nacimiento y soporte
    de sincronización de directorio.

    El namespace **no es dueño** del descriptor: no lo cierra. `volumen` es una
    etiqueta legible, nunca una ruta: una ruta absoluta aquí reintroduce la
    dependencia de la máquina de origen (§0.4.b, §6.2).
    """

    fd_root: int
    sensible_al_caso: bool
    nombre_max: int
    motor_nacimiento: FuenteT0
    sincronizacion_directorio: Optional[bool]
    volumen: str

    def __post_init__(self) -> None:
        _entero_mayor_que_cero(self.fd_root, "fd_root", 0)
        if not isinstance(self.sensible_al_caso, bool):
            raise ContratoViolado("la sensibilidad al caso se declara, no se supone")
        _entero_mayor_que_cero(self.nombre_max, "nombre_max", 1)
        if not isinstance(self.motor_nacimiento, FuenteT0):
            raise ContratoViolado("motor de nacimiento no declarado (§2.4.c)")
        if self.sincronizacion_directorio is not None and not isinstance(
            self.sincronizacion_directorio, bool
        ):
            raise ContratoViolado("el soporte de sellado se declara true, false o ⊥")
        _etiqueta_de_volumen(self.volumen)

    def admite(self, slug: Slug) -> bool:
        """§2.1. La longitud se mide en BYTES, con la unidad declarada."""

        return slug.longitud_bytes <= self.nombre_max

    @property
    def sella_directorio(self) -> Optional[bool]:
        return self.sincronizacion_directorio


@dataclass(frozen=True)
class Reserva:
    """§4 `reserve` → `Handle`. Estado posterior del acto, no un descriptor vivo.

    INV_EXCL (§3.a.1) no termina en `open`: `open` exclusivo, UNA escritura,
    `fsync`, `close` y sincronización del directorio —o `⊥` declarado donde no
    haya soporte (§8.2). `sellado = False` describe una reserva incompleta y no
    es un estado final admisible.
    """

    slug: Slug
    i: Inodo
    t0: Optional[T0] = None
    sellado: bool = False
    sincronizacion_directorio: Optional[bool] = None

    def __post_init__(self) -> None:
        if not isinstance(self.slug, Slug) or not isinstance(self.i, Inodo):
            raise ContratoViolado("la reserva exige slug e inodo tipados")
        if not isinstance(self.sellado, bool):
            raise ContratoViolado("el sellado se declara con un booleano")
        if self.sincronizacion_directorio is not None and not isinstance(
            self.sincronizacion_directorio, bool
        ):
            raise ContratoViolado("sincronización de directorio: true, false o ⊥")

    @property
    def completa(self) -> bool:
        return self.sellado


# ---------------------------------------------------------------------------
# §1.4 Etiqueta de validez · §4 resultados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Contexto:
    """§1.4. `(Universo, Unidad, Motor, T_UTC)` más `VENTANA` y `UMBRAL`.

    Sin esta tupla una cifra no es cifra: es una afirmación. La ventana y el
    umbral se declaran antes de ver la salida.
    """

    universo: str
    unidad: Unidad
    motor: str
    t_utc: str
    ventana: str
    umbral: str

    def __post_init__(self) -> None:
        for campo, valor in (
            ("universo", self.universo),
            ("motor", self.motor),
            ("ventana", self.ventana),
            ("umbral", self.umbral),
        ):
            if not isinstance(valor, str) or valor == "":
                raise ContratoViolado("la etiqueta de validez exige sus seis campos", campo=campo)
        if not isinstance(self.unidad, Unidad):
            raise ContratoViolado("la unidad se elige antes de ver la salida (§1.3)", unidad=self.unidad)
        if not isinstance(self.t_utc, str) or self.t_utc == "":
            raise ContratoViolado("T_UTC ausente")
        if "Z" not in self.t_utc:
            raise ContratoViolado(
                "la etiqueta no declara UTC (§3.e.4); su verdad no la comprueba un tipo",
                t_utc=self.t_utc,
            )


@dataclass(frozen=True)
class Etiqueta:
    """§4 `census`. La tupla completa o no hay resultado."""

    valor: int
    contexto: Contexto

    def __post_init__(self) -> None:
        if not isinstance(self.contexto, Contexto):
            raise ContratoViolado("una etiqueta sin contexto no es una cifra")
        _entero_mayor_que_cero(self.valor, "valor", 0)


@dataclass(frozen=True)
class Divergencia:
    """§4 `verify` → `Ok | Divergencia(campo, esperado, medido)`."""

    campo: str
    esperado: object
    medido: object

    def __post_init__(self) -> None:
        if not isinstance(self.campo, str) or self.campo == "":
            raise ContratoViolado("la divergencia nombra el campo que diverge")


@dataclass(frozen=True)
class Indeterminado:
    """§3.c.3. Si el pie no está congelado la resta no converge y el resultado es
    `Indeterminado`, **no** un número. Tratarlo como cero es el defecto que esta
    clase existe para impedir."""

    razon: str

    def __post_init__(self) -> None:
        if not isinstance(self.razon, str) or self.razon == "":
            raise ContratoViolado("Indeterminado exige razón declarada")


OK: Final = True

ResultadoVerificacion = Union[Literal[True], Divergencia]
ResultadoResta = Union[int, Indeterminado]
