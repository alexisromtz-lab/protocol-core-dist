"""protocol_audit — envoltura de distribución del núcleo `protocol-core` v0.1.0.

Esta distribución **no** re-implementa nada del protocolo: importa la copia
sellada que vive en `protocol_audit._vendor.protocol` (byte a byte idéntica a
las piezas selladas; la identidad se comprueba en `tests/test_vendor.py`) y sólo
añade el ejecutable `protocol-audit` y su `pyproject.toml`.

El núcleo sellado vive intacto y congelado en `protocol-core` (etiqueta
`v0.1.0`, commit `2290b6d`): este repositorio no lo modifica ni lo instala.
"""

from .cli import main

__version__ = "0.1.0"
__all__ = ["__version__", "main"]
