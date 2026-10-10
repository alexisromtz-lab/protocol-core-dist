"""La puerta de la copia: la deriva es el coste declarado del Camino P-1.

UNIVERSO DECLARADO: el arbol de ESTE repositorio bajo `src/`, mas las ocho
piezas heredadas del nucleo sellado, mas (cuando existen) los arboles de origen
`~/protocol-core` para el cotejo vivo. MOTOR: `python3 -B -m unittest` y
`subprocess` con `sys.executable`. RELOJ: no se lee.

El Camino P-1 mueve el ejecutable FUERA del arbol sellado a cambio de mantener
DOS copias del mismo codigo. El riesgo no es teorico: basta un byte para que la
copia deje de ser el nucleo que dice ser. Por eso la tabla de abajo esta escrita
a mano —el sha256 completo, no el tamano— y la prueba enrojece si la copia se
mueve.

Orden de las tres capas, de la mas barata a la mas fuerte:
  1. `test_la_tabla_se_cumple`: siempre corre. Fija el sha256 de cada pieza
     heredada. Esta es la puerta que sobrevive aunque el boveda no este.
     A su lado, `test_las_piezas_propias_se_cumplen` fija las piezas que
     escribimos nosotros dentro del vendor (hoy una): no son copias, pero
     tampoco se dejan sueltas.
  2. `test_el_origen_coincide` (omitida si no hay origen): cotejo vivo contra
     `~/protocol-core`.
  3. `test_la_suite_sellada_pasa_contra_la_copia` (omitida si no hay origen):
     copia los tests sellados a un directorio temporal y los corre con
     `PYTHONPATH` apuntando a la copia. Los tests sellados resuelven el paquete
     por `__file__` (su `src` hermano); en un directorio sin `src`, el import
     cae en el `PYTHONPATH`, o sea en la copia. Asi la suite de 26 pruebas del
     nucleo v0.1.0 corre contra ESTE codigo y no contra el original.
     El cardinal declarado es 26 (medido al sellar v0.1.0); si la copia se
     moviera, la cifra o el rojo lo dirian.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.dirname(TESTS)
SRC = os.path.join(RAIZ_REPO, "src")
VENDOR = os.path.join(SRC, "protocol_audit", "_vendor")
ORIGEN = os.path.join(os.path.expanduser("~"), "protocol-core")
TIMEOUT = 300
CARDINAL_SUITE_SELLADA = 26

# Pieza heredada -> sha256 completo, medido sobre la copia byte a byte.
# Rutas relativas a la raiz de ESTE repositorio.
TABLA = {
    "LICENSE": "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0",
    "LICENSE_SPEC_CC-BY-4.0.txt": "9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411",
    "SPEC.md": "9565f56832e7071612a337c0ec6e1efc134253cabbdfae797100472399397ec8",
    "src/protocol_audit/_vendor/protocol/__init__.py": (
        "ffd3d4a2cfcbec73bd38e40fc000019a3bc179abaf83cc8c630e83552d1876ca"
    ),
    "src/protocol_audit/_vendor/protocol/atomic.py": (
        "f683048ede5e0d484ead274260c7e78bfd13a339ec0a4951832d0bf142d672de"
    ),
    "src/protocol_audit/_vendor/protocol/audit.py": (
        "2e5126ae125dd0e946bbfd4971134faecda5a191faeb9fcd1df4f8a4086fad46"
    ),
    "src/protocol_audit/_vendor/protocol/metrics.py": (
        "b0ffe59125d335352eeea25bc90e6765807bab67fc59f58d7c44f4dff062a767"
    ),
    "src/protocol_audit/_vendor/protocol/types.py": (
        "2c7d13f85a4bce17e5e87cb9dc81266e819d27ad00427851bcc66e72aa685074"
    ),
}

# Piezas ESCRITAS POR NOSOTROS dentro del vendor: no son copias del nucleo y
# por eso no llevan el sello de origen, pero tampoco pueden quedar sueltas — una
# pieza que nadie vigila es indistinguible de una copia que derivo. Solo hay una:
# el `__init__.py` que hace del vendor un paquete y declara por que la copia
# conserva el nombre `protocol` (colision evitada: `protocol_audit._vendor.protocol`
# no pisa a un `protocol` de nivel superior en el entorno del usuario).
PROPIAS = {
    "src/protocol_audit/_vendor/__init__.py": (
        "f6b08d3ed4629cf649b85748c5e528794e827d107ef4df2edd2bf1a4de3ca7e0"
    ),
}


def _sha256(ruta):
    with open(ruta, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _ambiente(extra_path):
    ambiente = dict(os.environ)
    previo = ambiente.get("PYTHONPATH", "")
    ambiente["PYTHONPATH"] = extra_path + ((os.pathsep + previo) if previo else "")
    return ambiente


class PuertaDeLaCopia(unittest.TestCase):
    def test_la_tabla_se_cumple(self):
        for rel, esperado in sorted(TABLA.items()):
            completo = os.path.join(RAIZ_REPO, rel)
            with self.subTest(pieza=rel):
                self.assertTrue(os.path.isfile(completo), "falta la pieza %s" % rel)
                self.assertEqual(_sha256(completo), esperado, "la copia derivo en %s" % rel)

    def test_las_piezas_propias_se_cumplen(self):
        """Nuestras piezas tampoco quedan sueltas: se vigilan por sha256."""
        for rel, esperado in sorted(PROPIAS.items()):
            completo = os.path.join(RAIZ_REPO, rel)
            with self.subTest(pieza=rel):
                self.assertTrue(os.path.isfile(completo), "falta la pieza %s" % rel)
                self.assertEqual(_sha256(completo), esperado, "derivo la pieza %s" % rel)

    def test_el_vendor_no_tiene_piezas_de_mas(self):
        """Una pieza suelta dentro del vendor es una copia que nadie vigila."""
        declaradas = {
            rel.split("_vendor/", 1)[1]
            for rel in list(TABLA) + list(PROPIAS)
            if "_vendor/" in rel
        }
        presentes = set()
        for base, _dirs, ficheros in os.walk(VENDOR):
            for nombre in ficheros:
                if nombre.endswith(".pyc"):
                    continue
                ruta = os.path.join(base, nombre)
                presentes.add(os.path.relpath(ruta, VENDOR))
        self.assertEqual(presentes, declaradas)

    def test_el_cli_consume_la_copia(self):
        """El ejecutable no puede estar midiendo otro `protocol` del sistema."""
        sys.path.insert(0, SRC)
        try:
            import protocol_audit.cli as cli
            import protocol_audit._vendor.protocol.metrics as copia
        finally:
            if sys.path and sys.path[0] == SRC:
                sys.path.pop(0)
        real = os.path.realpath(copia.__file__)
        self.assertTrue(
            real.startswith(os.path.realpath(VENDOR) + os.sep),
            "la copia no vive bajo el vendor: %s" % real,
        )
        self.assertEqual(os.path.realpath(cli._metrics.__file__), real)

    @unittest.skipUnless(os.path.isdir(ORIGEN), "no hay arbol de origen en %s" % ORIGEN)
    def test_el_origen_coincide(self):
        for rel, esperado in sorted(TABLA.items()):
            if "_vendor/" in rel:
                continue
            # Las piezas heredadas sin vendor viven en la raiz del origen.
            origen = os.path.join(ORIGEN, rel)
            if not os.path.isfile(origen):
                continue
            with self.subTest(pieza=rel):
                self.assertEqual(_sha256(origen), esperado, "el origen se movio: %s" % rel)
        for rel, esperado in sorted(TABLA.items()):
            if "_vendor/" not in rel:
                continue
            interno = rel.split("_vendor/", 1)[1]
            origen = os.path.join(ORIGEN, "src", interno)
            with self.subTest(pieza=interno):
                self.assertTrue(os.path.isfile(origen), "falta en el origen: %s" % origen)
                self.assertEqual(_sha256(origen), esperado, "la copia no es el origen: %s" % interno)

    @unittest.skipUnless(os.path.isdir(ORIGEN), "no hay arbol de origen en %s" % ORIGEN)
    def test_la_suite_sellada_pasa_contra_la_copia(self):
        origen_tests = os.path.join(ORIGEN, "tests")
        self.assertTrue(os.path.isdir(origen_tests), origen_tests)
        temporal = tempfile.mkdtemp(prefix="protocol-core-suite-")
        try:
            copiadas = 0
            for nombre in sorted(os.listdir(origen_tests)):
                if nombre.endswith(".py"):
                    shutil.copy2(os.path.join(origen_tests, nombre), os.path.join(temporal, nombre))
                    copiadas += 1
            self.assertGreater(copiadas, 0, "no se copio ninguna prueba sellada")
            corrida = subprocess.run(
                [sys.executable, "-B", "-m", "unittest", "discover", "-s", temporal, "-v"],
                capture_output=True,
                text=True,
                env=_ambiente(VENDOR),
                cwd=temporal,
                timeout=TIMEOUT,
            )
            print(corrida.stderr)
            self.assertEqual(corrida.returncode, 0, corrida.stderr)
            encontrado = re.search(r"Ran (\d+) tests", corrida.stderr)
            self.assertIsNotNone(encontrado, corrida.stderr)
            self.assertEqual(int(encontrado.group(1)), CARDINAL_SUITE_SELLADA)
        finally:
            shutil.rmtree(temporal, ignore_errors=True)

    @unittest.skipUnless(os.path.isdir(ORIGEN), "no hay arbol de origen en %s" % ORIGEN)
    def test_el_import_de_la_suite_apunta_al_vendor(self):
        """Bajo el mismo entorno de la suite funcional, `protocol` es la copia."""
        codigo = "import protocol, sys; sys.stdout.write(protocol.__file__)"
        corrida = subprocess.run(
            [sys.executable, "-B", "-c", codigo],
            capture_output=True,
            text=True,
            env=_ambiente(VENDOR),
            cwd=tempfile.gettempdir(),
            timeout=TIMEOUT,
        )
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        real = os.path.realpath(corrida.stdout.strip())
        self.assertTrue(
            real.startswith(os.path.realpath(VENDOR) + os.sep),
            "el import no cayo en la copia: %s" % real,
        )


if __name__ == "__main__":
    unittest.main()
