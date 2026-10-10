# SPEC · Protocolo de Custodia Determinista y Reserva de Ranuras

**Versión** 0.1.0 · **Estado** ESQUEMA EN SECO — sin implementación, sin extracción de código
**Materia** A (Método y Arquitectura) · **Hora de la puerta** 09Z01Z11Z21Z.015293 (UTC)
**Entregable** `protocol-core/` · **Fuera de alcance** Materia B (corpus teórico) · Materia C (evidencia y bitácora)

**Regla de oro de este documento.** Ninguna cifra empírica viaja sin su comando, su universo declarado y su hora.
Las cifras de §1–§6 son **normativas**: exigencias dirigidas a toda implementación. Las empíricas viven en §7 y
allí se declara de cada una que es **testigo del prototipo**, nunca garantía del protocolo.

---

## §0 Puerta, alcance y orden de los actos

**0.1** El orden es **metro → reserva**. Este documento se fija **antes** de tocar, mover o refactorizar un solo
archivo del taller. La razón es operativa, no ceremonial: el código existente en la raíz y en `mesa/` es un testigo
de laboratorio **contaminado por supuestos locales** (dependencia del directorio temporal del sistema, flotantes de
`st_birthtime` de APFS, rutas absolutas, acoplamiento a scripts concretos). Si el inventario precede a la
especificación, **los vicios del prototipo dictan los tipos del protocolo**. Fijado el estándar en seco, es el
estándar el que decide qué código **califica** para Materia A y qué parte se desecha por ser andamiaje forense.

**0.2 Alcance.** Tipos y primitivas (§2) · invariantes (§3) · interfaz abstracta (§4) · matriz de pruebas (§5) ·
topología del subárbol limpio (§6) · procedencia empírica (§7) · deudas declaradas (§8).

**0.3 No-alcance.** La bitácora de adendas y actas (Materia C) **no se publica: se cita**. El corpus teórico
(Materia B) tiene contrato editorial propio. La licencia no se elige aquí: se declara en el repositorio, no en el
código. Este documento no contiene implementación.

**0.4 Criterio de admisión a `src/`.** Una función o script del taller entra al subárbol limpio **solo si**:
(a) satisface al menos un caso de §5; (b) no contiene rutas absolutas; (c) no depende del directorio temporal del
sistema ni de recursos fuera del namespace; (d) no depende de `st_birthtime`, del reloj local ni de la zona
horaria del proceso; (e) toda cifra que emita sale con la etiqueta de INV_TIME. Lo que no cumpla (a)–(e) se
**desecha**, aunque funcione.

**0.5 Regla de supervivencia del prototipo.** El árbol limpio es **agnóstico del sistema de archivos**. Todo lo
que en el taller se apoya en el volumen concreto de origen (resolución de `T0`, sensibilidad al caso, límites de
nombre, colación de orden) se **declara como parámetro del namespace** y se **certifica por sonda** en el volumen
de destino.

**0.6 Ficha del acto.** La **hora de la puerta** consignada en la cabecera es la del vuelo de calibración previo a
la escritura (`09Z01Z11Z21Z.015293`), no la del nacimiento: la puerta se abre antes, el objeto nace después.
`I` y `T0` se imprimen aquí porque los fija el sistema de archivos al crear el objeto y no cambian al escribir
(`INO 97278960` · `DEV 16777229` · `NLINK 1` · `MODE 0o100644` · `NACE 09Z01Z12Z05Z.024427`, medidos fuera y
después). Por **INV-6**, este documento **no** imprime su propia `H`, `B` ni `L`: lo que imprimiera describiría la
versión anterior de sí mismo. La ficha del acto se mide fuera, en el crudo de la partición posterior.

---

## §1 Universo de discurso y notación

**1.1** Sean: `N` un namespace; `FD_root` su descriptor de directorio raíz; `s` un slug; `S` una ranura;
`F` una ficha; `R` un recibo.

**1.2** `LF` := el byte `0x0A`. `|X|` := cardinal. `t_*` := instante en UTC.

**1.3 Unidad adjetiva obligatoria.** «archivo», «línea», «ocurrencia» y «byte» son **unidades distintas** y dan
números distintos sobre el mismo objeto. Publicar un conteo sin declarar su unidad produce una cifra que **no se
puede volver a medir**. La unidad se elige **antes** de ver la salida.

**1.4 Etiqueta de validez.** Toda magnitud de censo o estado viaja con
`(Universo, Unidad, Motor, T_UTC)` más `VENTANA` y `UMBRAL`. Sin esa tupla, la cifra no es cifra: es una
afirmación.

---

## §2 Tipos y primitivas abstractas

### 2.1 Slug — identificador unívoco atómico

Cadena canónica que satisface el *POSIX portable filename character set*.
Alfabeto: `A–Z a–z 0–9 . _ -`. Prohibido: `/`, `NUL`, `.`, `..`, prefijo `-`, byte fuera del alfabeto.
Longitud en bytes `≤ NAME_MAX(N)` — **parámetro del namespace**, no constante (255 es un valor típico, no una ley).
Forma canónica **NFC** obligatoria.

**2.1.1 El slug es la llave primaria.** No lo es el inodo (`I`): `I` solo es biyectivo con el slug si `K = 1`
(§2.3.6). Un enlace duro crea **dos nombres y un objeto**: el protocolo cuenta nombres y declara el objeto.

**2.1.2 El slug es opaco.** Ninguna parte del protocolo deriva ranura, fecha o clase del **texto** del slug.
Reservar el nombre no reserva el número.

**2.1.3 Invariancia de caso y de forma.** El conjunto de slugs de `N` debe ser **inyectivo bajo `casefold` y bajo
NFC**, o `N` debe **certificar por sonda** que es sensible al caso (§3, INV-9). Un volumen insensible al caso
convierte dos slugs que difieran solo en caso en **un solo nombre**: la exclusividad de INV_EXCL deja de proteger
sin que ninguna llamada falle.

### 2.2 Ranura — `S ∈ ℕ`

Ordinal de secuencia o clasificación temporal. **Proyección lógica no exclusiva**: dos slugs distintos pueden
coexistir bajo la misma ranura sin violar la integridad del sistema. La ranura **no es llave** y no confiere
unicidad. Su asignación es un acto declarado, no un efecto colateral de escribir un archivo.

### 2.3 Ficha — tupla de identidad `F = (H, B, L, P, I, T₀)`

Registro de seis dimensiones. Seis son obligatorias; tres extensiones declaradas (§2.3.7).

**2.3.1 `H` — hash del contenido.** `SHA-256` sobre el **flujo crudo de bytes**: sin traducción de fin de línea,
sin descarte de BOM, sin normalización Unicode, sin decodificación previa. Un truncamiento es un **prefijo de
anchura declarada** y viaja siempre con el nombre del algoritmo y la anchura (`sha256:16`). `H` es la única
identidad **portable** de la ficha.

**2.3.2 `B` — masa física.** `st_size` tomado del **mismo descriptor** desde el que se leyó el flujo. Exigencia:
`B == |flujo leído|`; la divergencia no es un error de cálculo: es **lectura rasgada** (§3, INV-8).

**2.3.3 `L` — saltos de línea físicos.** Número de bytes `0x0A`. Es un **conteo de un byte**, no un conteo de
líneas: la palabra «línea» no aparece en su definición.

**2.3.4 `P` — partición canónica.** Dos proyecciones, ambas obligatorias, ambas declaradas:

- `P_sep` := partición por separador (`split(LF)`), que **conserva el campo vacío final**.
- `P_lines` := partición que **descarta** el campo vacío final.

Leyes (verificadas en §7.1, siete casos, tolerancia cero):

```text
|P_sep|   = L + 1                                    (SIEMPRE, incluido el archivo vacío)
|P_lines| = 0                si |T| = 0
          = L                si |T| > 0 y el flujo termina en 0x0A   (fin = True)
          = L + 1            si |T| > 0 y el flujo no termina en 0x0A (fin = False)
```

**2.3.4.1 `fin` es derivado, no entrada.** `fin ⇔ |P_lines| = L` cuando `|T| > 0`. Ninguna implementación
recibe `fin` como parámetro: lo mide.
**2.3.4.2 Caso degenerado.** `|T| = 0` da `|P_sep| = 1` y `|P_lines| = 0`. La discrepancia es **correcta** y queda
declarada para que ninguna implementación la «arregle».
**2.3.4.3 Uso normativo.** La diferencia entre las dos proyecciones detecta **cierre limpio del flujo sin umbral**:
no hay margen que calibrar. Cualquier otra lectura de `P` (medir «líneas» sin decir cuál de las dos proyecciones)
es una cifra sin unidad.

**2.3.5 `I` — inodo.** Par `(D, i)` = `(st_dev, st_ino)`. Válido **dentro del volumen**. Imprimir `st_ino` sin `D`
no identifica nada entre volúmenes.

**2.3.6 `K` — enlaces.** `st_nlink`. Sin `K = 1`, `I` no es biyectivo con el slug.

**2.3.7 `T₀` — nacimiento. Campo OPCIONAL y no portable.** POSIX **no define** tiempo de nacimiento: `stat(2)`
expone `st_atime`, `st_mtime` y `st_ctime`, y **`st_ctime` es tiempo de cambio de inodo, no de creación**.
Fuentes admisibles: `st_birthtime` (macOS/BSD), `statx(STATX_BTIME)` (Linux ≥ 4.11). Sin fuente disponible,
`T₀ = ⊥`, y `⊥` es un **valor válido** que debe imprimirse como `⊥`: inventarlo es la falsificación más barata que
admite este protocolo.

**2.3.8 Extensiones declaradas.** `D` (`st_dev`), `M` (`st_mode`, incluido el efecto del `umask`), `K` (`st_nlink`).
Se declaran cuando el recibo las use; no son obligatorias.

**2.3.9 Ficha fuera de banda (INV-6).** La ficha de una pieza **no puede medirse dentro de la pieza**: lo impreso
describe la versión anterior del archivo (`x == x`). `H`, `B` y `L` se miden **fuera**, después de la escritura. `I`
y `T₀` sí pueden imprimirse dentro, porque los fija la reserva y no cambian al escribir.

### 2.4 Namespace — espacio de nombres confinado

Dominio de almacenamiento delimitado por `FD_root`. Reglas:
ninguna ruta dentro del namespace resuelve referencias fuera de su árbol; ninguna depende de variables de entorno
implícitas; ninguna usa `..`; ninguna abre por ruta absoluta.
El namespace **declara**: (a) si es sensible al caso (§2.1.3); (b) `NAME_MAX`; (c) su motor de nacimiento (§3,
INV-7); (d) si la sincronización de directorio está soportada (§3, INV_EXCL).

### 2.5 Recibo y manifiesto

**2.5.1 Recibo** `R = (s, H, B, L, I, T₀, H_prev)`. La **cadena de recibos** es lo que sostiene la fecha cierta:
el sistema de archivos no es un notario, y sus marcas de tiempo son **testigos**, no firmas.
**2.5.2 Manifiesto** = lista ordenada de `(H, slug)` de un namespace, con rutas **relativas**, autocerrado
(§3, INV_ISOL).

---

## §3 Invariantes (leyes de consistencia)

### INV_EXCL — Exclusividad en la apertura

**Ley.** Toda asignación de un slug nuevo se ejecuta atómicamente con `open(2)` y banderas
`O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC`. Si la entrada de directorio preexiste, la rutina colapsa de forma
determinista con `EEXIST`. Sin bloqueos colaborativos.

**3.a.1 La reserva no termina en `open`.** Un `open` con éxito deja el nombre reservado; no deja el contenido
custodiado. La operación completa es: `open` exclusivo → **una** escritura → `fsync(fd)` → `close` → sincronización
del directorio. Sin el sellado, el nombre puede sobrevivir sin el contenido (o al revés) ante una caída.
**3.a.2 Límite declarado.** La atomicidad de `O_EXCL` **no está garantizada por POSIX** en sistemas de archivos de
red (NFS y similares). Por eso INV_EXCL exige una **sonda de certificación por volumen** (T-01) ejecutada antes de
aceptar el namespace, y el certificado se registra en el recibo.
**3.a.3 Enlaces.** `O_EXCL` no sigue enlaces simbólicos: un nombre ocupado por un enlace ⇒ `EEXIST`. Es el
comportamiento correcto y se exige.
**3.a.4 Modo.** El modo efectivo es `m & ~umask`. Si el protocolo declara `M`, declara también el `umask` bajo el
que se midió; en caso contrario `M` no es reproducible.

### INV_SPLIT — Partición determinista

**Ley.** La relación entre `L` y las partes de partición está gobernada por las dos leyes de §2.3.4. **`fin` es un
derivado de la medición, no un dato de entrada.**

**3.b.1 Corrección medida.** La forma que este esquema recibió de origen —`split = nl + 1` si termina en salto,
`split = nl` si no— es la **inversa** de la identidad de la proyección que descarta el campo vacío final. El
control de §7.1 (siete casos, dos proyecciones) muestra que las leyes de §2.3.4 se cumplen **7/7 en ambas
proyecciones** y que la forma publicada **no** reproduce ninguna de las dos. Se registra la corrección; no se
hereda el error.
**3.b.2 Falsación.** Una implementación en la que las dos proyecciones devuelven siempre el mismo valor, o en la
que la partición colapsa a `L` con independencia del byte final, viola la ley.

### INV_SELF — Resta endógena de auto-conteo

**Ley.** Ningún evaluador audita un conjunto del cual su propia salida forma parte **sin aislar su huella**. Si el
descriptor `D_k` evalúa la frecuencia de una tupla de tokens `T` en el namespace `N`, el resultado neto válido
exige **una** de dos estrategias **excluyentes**:

```text
E (exclusión)  El universo declarado excluye el pie del instrumento.
               La exclusión se enumera POR SLUG DE UN CONJUNTO DECLARADO.
D (deducción)  M_neto = M_bruto(N) - M_self(D_k).
               Válida SOLO si M_self está CONGELADO (el instrumento no escribe
               en el universo mientras mide).
```

**3.c.1 Prohibición de doble descuento.** Aplicar E y D a la vez descuenta dos veces el mismo pie.
**3.c.2 Prohibición de exclusión por subcadena.** Excluir «todo lo que lleve X en la ruta» mata archivos ajenos:
la misma subcadena aparece en nombres de objetos distintos. La exclusión es un **conjunto enumerado**.
**3.c.3 No convergencia.** Si el pie no está congelado, la resta no converge y la cifra crece con el acto de
medirla. En ese caso el resultado es `Indeterminado`, **no** un número.
**3.c.4 Caducidad.** Un censo en un universo vivo **caduca al escribirse**: su hora es parte de la cifra. El
corolario operativo del taller —un `+1` por contención no es un `+1` por escritura— se registra aquí como
advertencia, no como ley.

### INV_ISOL — Aislamiento de manifiestos

**Ley.** La validez criptográfica de un manifiesto depende de rutas **relativas confinadas** al subdirectorio
contenedor. Un manifiesto **jamás incluye su propio hash** y es inmune a escrituras en namespaces colindantes o
superiores.

**3.d.1 Instantánea previa.** La lista de slugs se **captura antes** de hashear. Sin captura previa, el manifiesto
puede ser internamente consistente y **no describir ningún instante**: manifiesto rasgado.
**3.d.2 Orden determinista.** Ordenación **byte a byte**, con colación `C`. El orden por colación local hace que
dos máquinas produzcan manifiestos distintos del mismo contenido.
**3.d.3 Autocierre.** El manifiesto excluye su propio hash **y** cualquier fichero de sumas preexistente.
**3.d.4 Declaración.** El manifiesto declara su algoritmo y su anchura. Un fichero de sumas sin algoritmo es un
número sin unidad.

### INV_TIME — Validez temporal acoplada

**Ley.** Ninguna magnitud de censo o estado es válida sin declarar la tupla
`(Universo, Unidad, Motor, T_UTC)`, más `VENTANA` y `UMBRAL`. No existen estados de reposo declarados por decreto
retrospectivo.

**3.e.1 Reposo — cota, no diferencia (corrección medida).** La forma recibida —«reposo ⇔ `Δ(mtime) = 0` dentro de
una ventana»— es **más débil que la ley**. La igualdad de diferencias la satisface un archivo cuyo `mtime` es
**posterior** a la hora de corte, y también un archivo re-sellado en bloque durante la medición. Ley correcta:

```text
reposo(N, t_corte, ventana)  ⇔  ∀ e ∈ N : mtime(e) ≤ t_corte
```

medido con el **mismo instrumento**, con la ventana declarada **antes** de medir. Una medición que descubre
llegadas **no** tiene reposo: tiene movimiento, y se declara.
**3.e.2 Llegada — conjunto, no marca de tiempo.** El motor de llegada es la **diferencia de conjuntos de slugs**
entre dos censos. `mtime` no es motor de llegada: un re-sello lo mueve sin nacimiento.
**3.e.3 Nacimiento.** `T₀` sería el motor de nacimiento, pero **no es portable** (INV-7). Por tanto el motor de
nacimiento **no puede ser el sistema de archivos**: es la **cadena de recibos**.
**3.e.4 Reloj etiquetado.** Las etiquetas van en UTC. Una `Z` literal sobre una hora local es una **mentira con
forma de etiqueta**, y una ventana que se elige **después** de ver la salida no vale más que la nada.

### INV-6 — Ficha fuera de banda (extensión declarada)

Ninguna pieza imprime su propia `H`, `B` o `L`; lo que imprime describe su versión anterior. Sí imprime `I` y `T₀`
cuando la reserva los fijó. La ficha del acto se **mide fuera**, después de la escritura.

### INV-7 — Portabilidad de `T₀` (extensión declarada)

Escalera declarada: `st_birthtime` (macOS/BSD) · `statx(STATX_BTIME)` (Linux ≥ 4.11) · `⊥`. Reglas: `⊥` es válido
y se imprime como `⊥`; `T₀` **no ordena** la cadena de recibos; `T₀` **no es llave**; el reloj local no es motor;
la conversión a etiquetas de microsegundos **redondea** y esa anchura se declara (los flotantes de nacimiento de
APFS son una fuente conocida de cifras no reproducibles si no se fija la anchura).

### INV-8 — Lectura no rasgada (extensión declarada)

Se abre por descriptor, se lee, y se hace `fstat` **sobre el mismo descriptor**. Se exige `st_size == |flujo|`. El
hash se calcula sobre **el flujo leído**, nunca reabriendo la ruta. Si `st_size` discrepa, el objeto se movió
durante la medición: **se declara**, no se reintenta en silencio hasta que salga un número redondo.

### INV-9 — Inyectividad de caso y de forma (extensión declarada)

El conjunto de slugs de un namespace es inyectivo bajo `casefold` **y** bajo NFC, o el namespace está **certificado
por sonda** como sensible al caso. Sin esta condición, INV_EXCL no protege: dos slugs que difieran solo en caso (o
solo en forma de normalización) son **un solo nombre**. Ver §7.3: el volumen de origen es **insensible al caso**.

---

## §4 Interfaz abstracta

Contratos, no código. `→` separa entradas de salida; `|` separa resultados alternativos.

```text
reserve(N, s, M, m) -> Handle | Err
  pre   s ∈ alfabeto(N) ; |s|_bytes ≤ NAME_MAX(N) ; inyectividad de caso/forma (§2.1.3)
  post  el nombre s existe; M está íntegro en él; fd sincronizado; directorio sincronizado
        o declarado ⊥; I y T₀ quedan fijados y son estables a partir de aquí
  err   EEXIST | ENAMETOOLONG | EACCES | EXDEV | EISDIR | ENOTSUP | ENOSPC

ficha(N, s) -> F                    # FUERA DE BANDA
  pre   s existe y no es enlace simbólico
  post  H sobre flujo crudo; B = st_size del mismo fd; L = count(0x0A);
        (P_sep, P_lines, fin); I = (D, i); T₀ = t | ⊥
  err   ENOENT | ELOOP
  nota  T₀ ausente NO es error

partition(flujo, enc) -> (P_sep, P_lines, L, fin, vacio)
  post  leyes de §2.3.4 ; fin derivado, nunca recibido
  err   error de decodificación declarado (no se sustituye por U+FFFD en silencio)

manifest(FD_root, E) -> Manifiesto
  pre   E capturado antes de hashear; E enumera slugs; E excluye el manifiesto y todo fichero de sumas
  post  rutas relativas; orden byte a byte (colación C); algoritmo y anchura declarados
  err   EACCES | ELOOP | ENAMETOOLONG

census(N, ctx) -> Etiqueta
  post  (valor, Universo, Unidad, Motor, VENTANA, UMBRAL, T_UTC) — tupla completa o no hay resultado

resta(m_bruto, m_self, congelado) -> entero | Indeterminado
  pre   estrategia declarada (E o D, nunca ambas); si E, la exclusión es conjunto enumerado
        si D, congelado = True y m_self enumerado
  err   Indeterminado (pie no congelado)

reposo(N, t_corte, ventana) -> bool
  pre   ventana declarada ANTES de medir
  post  ∀ e ∈ N : mtime(e) ≤ t_corte

attest(F, prev) -> Recibo
  post  H_prev = prev.H ; la cadena, no el sistema de archivos, es el orden

verify(R, N) -> Ok | Divergencia(campo, esperado, medido)

sonda_excl(N) -> Certificado(atomico: bool)        # T-01 sobre el volumen real
sonda_caso(N) -> Certificado(sensible_al_caso: bool)   # INV-9
```

---

## §5 Matriz de pruebas y falsación

Estado de la columna final: **ESQUEMA** = especificada y no corrida sobre la implementación (no existe aún);
**SONDA** = corrida sobre el volumen de origen, vale para ese volumen y solo para él.

| Test ID | Caso de prueba | Condición de entrada | Comportamiento esperado | Falsación / fallo | Estado |
|---|---|---|---|---|---|
| **T-01** | Carrera de reserva atómica | Dos procesos concurrentes intentan abrir el mismo slug bajo `O_CREAT\|O_EXCL`. | Proceso A obtiene descriptor válido (`FD > 0`); proceso B colapsa con `EEXIST`. | Escritura intercalada, sobreescritura silenciosa o **ambos procesos con éxito**. | SONDA (§7.2) |
| **T-02** | Discriminación de salto terminal | Archivo de prueba con y sin terminador `0x0A`, y archivo vacío. | Con terminador: `\|P_lines\| = L`. Sin terminador: `\|P_lines\| = L + 1`. Vacío: `\|P_lines\| = 0`, `\|P_sep\| = 1`. En todo caso `\|P_sep\| = L + 1`. | Colapso de las dos proyecciones al mismo valor, o `P` independiente del byte final. | SONDA (§7.1) |
| **T-03** | Endogeneidad del observador | Evaluador que busca un token `X` que él mismo contiene en su cuerpo o en sus parámetros. | El reporte imprime el par discriminado `(Total, C_self)`, declara **una** estrategia (E o D) y verifica `Total − C_self` solo bajo D congelado. | Reportar únicamente `Total`, inflando el censo en `+C_self`; o aplicar E y D a la vez; o excluir por subcadena. | ESQUEMA |
| **T-04** | Inmunidad de namespace | Se ejecuta una mutación en la raíz de trabajo mientras se valida una mesa sellada. | El manifiesto relativo devuelve OK sin alterar hashes, marcas de tiempo ni inodos de la mesa; el orden es byte a byte. | El validador reporta fallo de suma por contaminación de ruta, o el manifiesto cambia de orden entre máquinas. | ESQUEMA |
| **T-05** | Caducidad de censo en vuelo | Medición de cardinalidad de directorio con inserción concurrente de descriptor. | El sistema detecta el incremento de entradas y **rechaza** la aserción de reposo. | Aceptación de reposo nominal frente a un `mtime` posterior a la hora de corte. | ESQUEMA |
| **T-06** | Ausencia portátil de nacimiento | Sistema de archivos sin tiempo de nacimiento. | Ficha válida con `T₀ = ⊥`; `H`, `B`, `L`, `I` intactos. | Error o excepción por falta de `T₀`; `T₀` inventado; `T₀` usado como llave de orden. | ESQUEMA |
| **T-07** | Enlace duro: dos nombres, un objeto | Un inodo con `K = 2` alcanzable por dos slugs. | La ficha declara `K`; el sistema cuenta **nombres** y no pretende que `I` sea llave. | Declarar dos objetos distintos con la misma `I` sin declarar `K`. | ESQUEMA |
| **T-08** | Equivalencia y divergencia de las estrategias de INV_SELF | El mismo universo medido con E y con D. | Ambas dan el mismo neto; D solo con pie congelado; con pie no congelado, `Indeterminado`. | Deducir un pie no enumerado; excluir por subcadena; aplicar las dos estrategias. | ESQUEMA |
| **T-09** | Inyectividad de caso y forma | Dos slugs que difieren solo en caso, y dos que difieren solo en forma de normalización. | El segundo `reserve` **no** ocurre: `EEXIST` (volumen insensible) o conjunto no admisible (sensible). | Ambos `reserve` con éxito ⇒ un solo nombre para dos objetos. | ESQUEMA (§7.3 prueba el riesgo) |
| **T-10** | Lectura rasgada | Escritura concurrente durante la medición de la ficha. | `st_size` del mismo descriptor `== |flujo leído|`; en caso contrario, divergencia declarada. | Ficha devuelta sin comparar `st_size` contra el flujo, o hash calculado reabriendo la ruta. | ESQUEMA |
| **T-11** | Durabilidad de la reserva | `reserve` + caída simulada antes y después del sellado del directorio. | Después del sellado, nombre y contenido sobreviven juntos. | Nombre sin contenido, o contenido sin nombre, tras el sellado. | **DEUDA** (§8.2: no ejecutable sin control de caída) |

---

## §6 Estructura del subárbol limpio (Repo A)

```text
protocol-core/
├── SPEC.md               # Especificación formal del protocolo (RFC / Whitepaper)
├── pyproject.toml        # Configuración estándar empaquetable
├── src/
│   └── protocol/
│       ├── __init__.py
│       ├── types.py      # Definición de Slug, Ficha, Ranura y Contexto
│       ├── atomic.py     # Wrapper de bajo nivel sobre os.open con O_CREAT|O_EXCL
│       ├── metrics.py    # Medidor de Ficha, líneas, splits puros y terminaciones
│       └── audit.py      # Verificador de invariantes y deducción de auto-conteo
└── tests/
    ├── test_atomic.py    # Concurrencia y colisión determinista (T-01)
    ├── test_metrics.py   # Propiedades de partición y terminación (T-02)
    └── test_audit.py     # Aislamiento y deducción endógena (T-03, T-04, T-05)
```

**6.1** El subárbol **no contiene bitácora**: ninguna adenda, acta ni crudo del taller. Materia C se cita, no se
copia.
**6.2** `pyproject.toml` sin rutas absolutas: la instalación no puede depender de la máquina de origen.
**6.3** Las versiones del árbol (`src/`) y de sus pruebas (`tests/`) se declaran en el paquete; la del documento es
la de la cabecera.
**6.4** La licencia se declara en el repositorio (no en el código) y es **independiente** de las de Materia B y
Materia C.

---

## §7 Procedencia empírica

Convenciones de este apéndice: `$ROOT` = raíz del espacio de trabajo medida; `$TMP` = directorio temporal del
sistema. Los comandos se citan **normalizados**: ninguna ruta absoluta entra al documento (regla 6.2 aplicada al
propio texto), y las rutas se sustituyen por las variables declaradas.
Etiqueta común de los censos: `UNIVERSO DECLARADO … | UNIDAD … | VENTANA … | UMBRAL presencia ≥ 1 | MOTOR python3 -B | RELOJ UTC`.

### 7.1 Control de INV_SPLIT — dos proyecciones, siete casos

```sh
cd $ROOT && TZ=UTC python3 -u -B - <<'PY' 2>&1 | tee $TMP/spec_dry_pre_01.txt
# siete casos: '', 'a', 'a\n', 'a\nb', 'a\nb\n', '\n', 'a\n\n'
# imprime L, |P_sep|, |P_lines|, fin, vacio, y la ley 0 / L / L+1
PY
```

Medido a `09Z01Z11Z21Z.015293`–`09Z01Z11Z21Z.018081` (UTC):
`|P_sep| = L + 1` en **7/7** casos · `|P_lines|` según la ley de tres ramas en **7/7** casos.
La forma recibida (`nl + 1` si termina en salto) **no** reproduce ninguna de las dos proyecciones: queda corregida
en §2.3.4 y §3.b.1.

### 7.2 Sonda T-01 — exclusividad de la apertura, volumen de origen

Mismo comando de §7.1. `open` con `O_CREAT|O_EXCL|O_WRONLY` dos veces sobre el mismo slug:
primera = `OK` · segunda = `EEXIST`. Certifica el volumen de origen (§3.a.2); **no** certifica ningún otro volumen.

### 7.3 Sonda INV-9 — sensibilidad al caso del volumen de origen

Mismo comando. Se toma un nombre existente, se le invierte el caso de su primer carácter, se comprueba que la
variante **no** figura en el listado exacto del directorio y se pregunta por su existencia:
`en listado exacto = False` · `os.path.exists = True` ⇒ **el volumen es INSENSIBLE al caso**.
Consecuencia medida: en un volumen así, dos slugs que difieran solo en caso son **un solo nombre**. Es la razón de
INV-9 y del caso T-09.

### 7.4 Sonda INV-7 — disponibilidad de nacimiento

Mismo comando, sobre `ADENDA_62_*` de Materia C como testigo: `st_birthtime` **presente**,
`T₀ = 08Z23Z51Z45Z.358483` · `st_ctime = st_mtime = 08Z23Z51Z45Z.358671` · `st_ino = 97262421` ·
`st_dev = 16777229` · `st_nlink = 1` · `st_mode = 0o100644`.
Lectura: `c_time` y `m_time` coinciden aquí **porque la escritura fue única**; no son nacimiento, y en cuanto algo
re-escriba el archivo dejarán de coincidir entre sí (Materia C lo tiene medido). El nacimiento viene de
`st_birthtime` y es **el único campo no portable** de la ficha.

### 7.5 Testigos del prototipo citados en este esquema

Estas cifras **no** son garantías del protocolo: son observaciones de Materia C que **motivaron** cada ley. Viajan
con su procedencia.

| Observación citada | Ley que motiva | Procedencia |
|---|---|---|
| El instrumento que se cuenta a sí mismo no converge (el recuento de su propio nombre crece al escribirlo). | INV_SELF §3.c.3 | Familia de dictámenes de Materia C sobre auto-conteo |
| Excluir por subcadena de ruta mató archivos ajenos al patrón. | INV_SELF §3.c.2 | Medición de filtros de ruta en el registro |
| Llegadas de terceros durante una medición de reposo; y re-sellado de `mtime` en bloque, por delante del reloj. | INV_TIME §3.e.1–§3.e.2 | Censos de movimiento del registro |
| Una pieza que imprime su propia identidad describe su versión anterior. | INV-6 | Doctrina `x == x` del registro |
| Un fallo de escritura no reporta cuánto escribió: el éxito del instrumento es del acto, no del objeto. | INV-8 · T-10 | Casos de duplicación silenciosa del registro |

**7.5.1 Regla de exportación.** Cualquier cifra de Materia C que se cite en un documento público debe venir con su
comando y su hora. Un número sin comando **no se exporta**.

### 7.6 Efecto del acto sobre el universo de origen

Crear `protocol-core/` dentro de la raíz medida **mueve el universo** que Materia C cuenta:
`PRE` a `09Z01Z11Z21Z.015293` → `entradas 253 · dirs 8 · ficheros 245 · .md 241 · .txt 2 · otros 2`.
La partición posterior se mide en el crudo `$TMP/spec_dry_post_01.txt`. Se **declara el movimiento** en lugar de
perseguirlo: la cifra previa era verdadera hasta el instante de crear el directorio, y en ese instante dejó de
serlo. El árbol limpio no vuelve a escribirse desde el taller.

---

## §8 Deudas declaradas

**8.1** Atomicidad de `O_EXCL` en sistemas de archivos de red: **no certificada**. Requiere sonda por volumen
(T-01) y certificado en el recibo.
**8.2** Durabilidad (T-11): el sellado del directorio depende del sistema —`fsync` sobre descriptor de directorio
donde esté soportado; sellado completo del fichero donde la plataforma lo exija— y en ausencia de soporte se
declara `⊥`. La prueba de caída **no es ejecutable** en este espacio de usuario: deuda abierta.
**8.3** `NAME_MAX` y soporte de `statx`: parámetros del namespace, no constantes del protocolo.
**8.4** `M` (modo) solo es reproducible si se declara el `umask` de la medición.
**8.5** El protocolo **no** adopta ninguna costumbre del prototipo que dependa del volumen de origen: rutas
absolutas, directorio temporal, `st_birthtime`, reloj local, colación local y campos semánticos dentro del slug
quedan **fuera**.
**8.6** Materia B y Materia C tienen dueño de estado y licencia propios; este documento **no las contiene** y no
las sustituye.
