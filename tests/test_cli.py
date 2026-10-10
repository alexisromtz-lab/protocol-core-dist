"""La puerta del ejecutable: un positivo y sus negativos.

UNIVERSO DECLARADO: el arbol que cada prueba construye en un directorio
temporal, mas el manifiesto que la propia prueba escribe dentro de ese arbol.
MOTOR: `python3 -B -m unittest` sobre `subprocess` con `sys.executable` (el
mismo interprete que corre la suite) y `PYTHONPATH` apuntando a `src/`.
RELOJ: no se lee; ninguna cifra de este archivo es una hora.

El metro de la expectativa se construye AQUI, con `hashlib`, escribiendo los
campos del contrato del CLI por un camino distinto del que usa el CLI. Si la
expectativa saliera del mismo codigo que la medicion, la prueba mediria al
instrumento con el instrumento.

Gate verde no vale sin su control. Las pruebas `test_control_*` entregan un
objeto alterado a mano y EXIGEN `AUDIT=ROJO` con `RC=1`; sin ellas, el verde de
`test_arbol_intacto_*` no distingue «mide bien» de «dice OK siempre».

Trampa de metro que estas pruebas evitan: nunca se verifica a traves de una
tuberia. Se capturan `returncode` y `stdout` en el mismo acto y se comparan
despues (una tuberia pierde el codigo de salida, que es la mitad del contrato).
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.dirname(TESTS)
SRC = os.path.join(RAIZ_REPO, "src")

# El contrato del CLI: la linea de stdout lleva estos campos, en este orden.
CONTRATO = ("AUDIT", "RUTAS", "SHA256_AGREGADO", "MANIFIESTO", "RC")
NOMBRE_MANIFIESTO = "SHA256SUMS"
TIMEOUT = 120

CONTENIDOS = {
    "a.txt": b"alfa\n",
    "sub/b.bin": b"\x00\x01beta\xff",
    "z.txt": b"zeta",
}


def _escribir(raiz, contenidos):
    for ruta, datos in contenidos.items():
        destino = os.path.join(raiz, ruta)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as fh:
            fh.write(datos)


def _cuerpo(contenidos):
    """El cuerpo del manifiesto segun el contrato: filas ordenadas en C.

    `sha256(contenido)`, dos espacios, ruta UTF-8, salto de linea. El orden es
    por los bytes UTF-8 de la ruta (colacion C), no por el orden del dict.
    """
    filas = [(hashlib.sha256(datos).hexdigest(), ruta) for ruta, datos in contenidos.items()]
    filas.sort(key=lambda par: par[1].encode("utf-8"))
    return "".join("%s  %s\n" % (h, ruta) for h, ruta in filas)


def _agregado(contenidos):
    """El agregado del contrato: sha256 sobre el cuerpo entero."""
    return hashlib.sha256(_cuerpo(contenidos).encode("utf-8")).hexdigest()


def _campos(linea):
    """Trocea la linea por campos `CLAVE=valor`. Devuelve la lista de pares."""
    pares = []
    for trozo in linea.rstrip("\n").split(" "):
        if trozo == "":
            continue
        clave, _, valor = trozo.partition("=")
        pares.append((clave, valor))
    return pares


def _retrato(raiz):
    """Retrato del arbol: ruta relativa -> (bytes, mtime_ns, sha256 o None)."""
    fuera = {}
    for base, dirs, ficheros in os.walk(raiz, followlinks=False):
        for nombre in list(dirs):
            completo = os.path.join(base, nombre)
            rel = os.path.relpath(completo, raiz)
            fuera[rel] = ("dir", None, None)
        for nombre in ficheros:
            completo = os.path.join(base, nombre)
            rel = os.path.relpath(completo, raiz)
            info = os.lstat(completo)
            if os.path.islink(completo) or not os.path.isfile(completo):
                fuera[rel] = ("otro", info.st_size, None)
                continue
            with open(completo, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            fuera[rel] = ("ficha", info.st_size, digest)
    return fuera


class PuertaDelCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="protocol-audit-")
        self.raiz = os.path.join(self.tmp, "arbol")
        os.makedirs(self.raiz)
        _escribir(self.raiz, CONTENIDOS)
        self.manifiesto = os.path.join(self.raiz, NOMBRE_MANIFIESTO)
        with open(self.manifiesto, "w", encoding="utf-8") as fh:
            fh.write(_cuerpo(CONTENIDOS))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- instrumento de invocacion ------------------------------------------

    def _correr(self, extra=(), entorno=None, raiz=None, manifiesto=None, cwd=None):
        ambiente = dict(os.environ)
        previo = ambiente.get("PYTHONPATH", "")
        ambiente["PYTHONPATH"] = SRC + ((os.pathsep + previo) if previo else "")
        if entorno:
            ambiente.update(entorno)
        orden = [
            sys.executable,
            "-B",
            "-m",
            "protocol_audit",
            "--raiz",
            self.raiz if raiz is None else raiz,
            "--manifiesto",
            self.manifiesto if manifiesto is None else manifiesto,
        ]
        orden.extend(extra)
        return subprocess.run(
            orden,
            capture_output=True,
            text=True,
            env=ambiente,
            cwd=self.tmp if cwd is None else cwd,
            timeout=TIMEOUT,
        )

    def _linea_ok(self):
        corrida = self._correr()
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        self.assertEqual(corrida.stdout.count("\n"), 1, corrida.stdout)
        return corrida

    def _escribir_manifiesto(self, texto):
        with open(self.manifiesto, "w", encoding="utf-8") as fh:
            fh.write(texto)

    # --- el positivo ---------------------------------------------------------

    def test_arbol_intacto_imprime_una_sola_linea_ok(self):
        corrida = self._linea_ok()
        pares = _campos(corrida.stdout)
        self.assertEqual([clave for clave, _ in pares], list(CONTRATO), corrida.stdout)
        campos = dict(pares)
        self.assertEqual(campos["AUDIT"], "OK")
        self.assertEqual(campos["RC"], "0")
        # Cuatro fichas en disco (tres + el manifiesto) y TRES rutas medidas: la
        # cifra prueba que el manifiesto quedo fuera por nombre.
        self.assertEqual(len(os.listdir(self.raiz)), 4, sorted(os.listdir(self.raiz)))
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS)))
        self.assertEqual(campos["MANIFIESTO"], self.manifiesto)
        self.assertEqual(campos["SHA256_AGREGADO"], _agregado(CONTENIDOS))
        self.assertTrue(corrida.stdout.endswith("\n"), repr(corrida.stdout))

    def test_prosa_solo_en_stderr_y_la_linea_es_una_sola(self):
        corrida = self._correr()
        self.assertEqual(corrida.returncode, 0)
        self.assertTrue(corrida.stderr.strip(), "el CLI no dijo nada por stderr")
        self.assertEqual(corrida.stdout.count("\n"), 1)
        self.assertNotIn("AUDIT", corrida.stderr, "el contrato de stdout se filtro a stderr")

    # --- los controles obligatorios (negativos) -----------------------------

    def test_control_fila_alterada_da_rojo_sin_mover_el_agregado(self):
        """El control que hace valer el verde: el arbol no se toca, la fila si."""
        agregado_ok = _agregado(CONTENIDOS)
        lineas = _cuerpo(CONTENIDOS).rstrip("\n").split("\n")
        etiqueta, ruta = lineas[0][:64], lineas[0][66:]
        primera = etiqueta[0]
        alterada = ("0" if primera != "0" else "1") + etiqueta[1:]
        lineas[0] = "%s  %s" % (alterada, ruta)
        self._escribir_manifiesto("\n".join(lineas) + "\n")

        corro = _retrato(self.raiz)
        corrida = self._correr()
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 1, corrida.stderr)
        self.assertEqual(campos["AUDIT"], "ROJO")
        self.assertEqual(campos["RC"], "1")
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS)))
        # El objeto medido no se movio: el agregado del manifiesto es el mismo,
        # lo que cambio fue el arbol que la fila declara.
        self.assertEqual(campos["SHA256_AGREGADO"], agregado_ok)
        self.assertEqual(len(campos["SHA256_AGREGADO"]), 64)
        # Cero escrituras: ni siquiera el acto de auditar deja huella.
        self.assertEqual(_retrato(self.raiz), corro)

    def test_control_contenido_alterado_da_rojo_y_mueve_el_agregado(self):
        agregado_ok = _agregado(CONTENIDOS)
        with open(os.path.join(self.raiz, "a.txt"), "wb") as fh:
            fh.write(b"alfa!\n")
        corrida = self._correr()
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 1, corrida.stderr)
        self.assertEqual(campos["AUDIT"], "ROJO")
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS)))
        self.assertNotEqual(campos["SHA256_AGREGADO"], agregado_ok)

    def test_ruta_de_mas_en_el_arbol_da_rojo(self):
        with open(os.path.join(self.raiz, "nuevo.txt"), "wb") as fh:
            fh.write(b"nuevo\n")
        corrida = self._correr()
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 1, corrida.stderr)
        self.assertEqual(campos["AUDIT"], "ROJO")
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS) + 1))

    def test_ruta_de_menos_en_el_arbol_da_rojo(self):
        os.remove(os.path.join(self.raiz, "z.txt"))
        corrida = self._correr()
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 1, corrida.stderr)
        self.assertEqual(campos["AUDIT"], "ROJO")
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS) - 1))

    # --- defectos de invocacion: RC=2 y stdout VACIO ------------------------

    def _exigir_dos(self, corrida):
        self.assertEqual(corrida.returncode, 2, (corrida.returncode, corrida.stdout, corrida.stderr))
        # Sin medicion no hay linea: `RUTAS=0` seria un cero sin base.
        self.assertEqual(corrida.stdout, "")
        self.assertTrue(corrida.stderr.strip(), "un defecto mudo no es un defecto declarado")

    def test_manifiesto_ausente(self):
        self._exigir_dos(self._correr(manifiesto=os.path.join(self.tmp, "no-existe")))

    def test_raiz_ausente(self):
        self._exigir_dos(self._correr(raiz=os.path.join(self.tmp, "no-existe")))

    def test_raiz_que_no_es_directorio(self):
        self._exigir_dos(self._correr(raiz=os.path.join(self.raiz, "a.txt")))

    def test_manifiesto_corto(self):
        self._escribir_manifiesto("deadbeef  a.txt\n")
        self._exigir_dos(self._correr())

    def test_manifiesto_sin_los_dos_espacios(self):
        etiqueta = hashlib.sha256(CONTENIDOS["a.txt"]).hexdigest()
        self._escribir_manifiesto("%s a.txt\n" % etiqueta)
        self._exigir_dos(self._correr())

    def test_manifiesto_con_etiqueta_no_hexadecimal(self):
        etiqueta = hashlib.sha256(CONTENIDOS["a.txt"]).hexdigest()
        self._escribir_manifiesto("%sg  a.txt\n" % etiqueta[:63])
        self._exigir_dos(self._correr())

    def test_manifiesto_vacio(self):
        self._escribir_manifiesto("")
        self._exigir_dos(self._correr())

    def test_manifiesto_con_ruta_fuera_del_alfabeto_de_slug(self):
        etiqueta = hashlib.sha256(CONTENIDOS["a.txt"]).hexdigest()
        self._escribir_manifiesto("%s  con espacio.txt\n" % etiqueta)
        self._exigir_dos(self._correr())

    def test_argumento_obligatorio_faltante(self):
        ambiente = dict(os.environ)
        ambiente["PYTHONPATH"] = SRC
        corrida = subprocess.run(
            [sys.executable, "-B", "-m", "protocol_audit"],
            capture_output=True,
            text=True,
            env=ambiente,
            cwd=self.tmp,
            timeout=TIMEOUT,
        )
        self._exigir_dos(corrida)

    def test_ayuda_va_a_stderr_y_no_toca_stdout(self):
        ambiente = dict(os.environ)
        ambiente["PYTHONPATH"] = SRC
        corrida = subprocess.run(
            [sys.executable, "-B", "-m", "protocol_audit", "--help"],
            capture_output=True,
            text=True,
            env=ambiente,
            cwd=self.tmp,
            timeout=TIMEOUT,
        )
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        self.assertEqual(corrida.stdout, "", "la ayuda uso stdout, que es del contrato")
        self.assertIn("--raiz", corrida.stderr)

    # --- las reglas de la gramatica ----------------------------------------

    def test_objeto_no_regular_no_se_salta_en_silencio(self):
        """Un objeto que el metro no puede fichar no se ignora: se declara."""
        fifo = os.path.join(self.raiz, "cola")
        try:
            os.mkfifo(fifo)
        except (AttributeError, OSError) as exc:
            self.skipTest("este sistema no permite mkfifo: %s" % exc)
        self._exigir_dos(self._correr())

    def test_excluir_no_mata_por_subcadena(self):
        """`E` se enumera por slug: `SHA256SUMS` no puede matar `SHA256SUMS.bak`."""
        contenidos = dict(CONTENIDOS)
        contenidos["SHA256SUMS.bak"] = b"copia\n"
        _escribir(self.raiz, {"SHA256SUMS.bak": b"copia\n"})
        self._escribir_manifiesto(_cuerpo(contenidos))
        corrida = self._correr()
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        self.assertEqual(campos["RUTAS"], str(len(CONTENIDOS) + 1))
        self.assertEqual(campos["SHA256_AGREGADO"], _agregado(contenidos))

    def test_excluir_componente_lo_quita_del_arbol_y_del_manifiesto(self):
        contenidos = {r: d for r, d in CONTENIDOS.items() if not r.startswith("sub/")}
        self._escribir_manifiesto(_cuerpo(contenidos))
        corrida = self._correr(extra=["--excluir", "sub"])
        campos = dict(_campos(corrida.stdout))
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        self.assertEqual(campos["RUTAS"], str(len(contenidos)))
        self.assertEqual(campos["SHA256_AGREGADO"], _agregado(contenidos))

    # --- el determinismo y la ausencia de escritura -------------------------

    def test_dos_locales_dan_los_mismos_bytes(self):
        primera = self._linea_ok().stdout
        for locale in ("C", "POSIX", "en_US.UTF-8"):
            corrida = self._correr(entorno={"LC_ALL": locale, "LANG": locale})
            self.assertEqual(corrida.returncode, 0, corrida.stderr)
            self.assertEqual(corrida.stdout, primera, "el locale movio la linea")

    def test_la_linea_no_lleva_hora(self):
        """Determinismo byte a byte: repetida, la linea es identica.

        No se busca una hora por subcadena: el agregado es hexadecimal y podria
        contener cualquier digito por azar. Lo que decide es que la linea no
        tenga campos fuera del contrato y que dos corridas den los mismos bytes.
        """
        primera = self._linea_ok().stdout
        segunda = self._linea_ok().stdout
        self.assertEqual(primera, segunda)
        claves = {clave for clave, _ in _campos(primera)}
        self.assertEqual(claves, set(CONTRATO))

    def test_cero_escrituras_en_el_arbol_auditado(self):
        antes = _retrato(self.raiz)
        corrida = self._correr()
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        despues = _retrato(self.raiz)
        self.assertEqual(sorted(antes), sorted(despues))
        self.assertEqual(antes, despues)
        # `-B` significa que ni el interprete dejo `__pycache__` en el arbol.
        self.assertNotIn("__pycache__", " ".join(despues))

    def test_sin_red(self):
        """Aislamiento fisico: el ejecutable importa el nucleo y nada mas."""
        ambiente = dict(os.environ)
        ambiente["PYTHONPATH"] = SRC
        ambiente["no_proxy"] = "*"
        codigo = (
            "import sys;"
            "import protocol_audit.cli as c;"
            "mods = sorted(m for m in sys.modules if m.split('.')[0] in {'socket','ssl','urllib','http','ftplib'});"
            "sys.stderr.write(','.join(mods))"
        )
        corrida = subprocess.run(
            [sys.executable, "-B", "-c", codigo],
            capture_output=True,
            text=True,
            env=ambiente,
            cwd=self.tmp,
            timeout=TIMEOUT,
        )
        self.assertEqual(corrida.returncode, 0, corrida.stderr)
        self.assertEqual(corrida.stderr.strip(), "", "el CLI carga modulos de red")


if __name__ == "__main__":
    unittest.main()
