"""__main__.py — el ejecutable por partida doble.

  * como módulo, sin instalar nada:  `python -m protocol_audit --raiz DIR --manifiesto RUTA`
  * como comando de consola, tras instalar la distribución:  `protocol-audit ...`

Los dos caminos llaman a la MISMA función: `protocol_audit.cli.main`. El punto
de entrada de consola que declara `pyproject.toml` apunta a este módulo, de modo
que la forma instalada y la forma en seco no pueden divergir sin que la puerta
`tests/test_cli.py` lo vea.
"""

from .cli import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
