"""_vendor — la copia del núcleo sellado que esta distribución hereda.

Contiene `protocol/`, copia **byte a byte** de las piezas selladas de
`protocol-core` v0.1.0 (commit `2290b6d`). Aquí no se edita código: la deriva es
el coste declarado del Camino P-1 (dos copias del mismo código) y lo cierra la
puerta `tests/test_vendor.py`, que compara cada pieza contra la tabla de
`VENDOR.md`.

El nombre de paquete se conserva (`protocol`) porque los módulos sellados se
importan entre sí con rutas relativas; lo que se elige aquí es la **ubicación**,
anidada bajo `protocol_audit`, para que instalar esta distribución no pueda
colisionar con una instalación de `protocol-core` en el mismo entorno.
"""
