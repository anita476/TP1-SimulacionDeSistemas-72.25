# Uso de cada herramienta

El CLI del simulador y los scripts de análisis, uno por uno. Para el pipeline
completo en orden, ver el [README](../README.md).

## Generar partículas

```bash
./build/CIM-TP1 -N 1000 -L 20 --seed 42 --verify
```

Escribe `data/static.txt` y `data/dynamic.txt`, y reporta por `stderr` el tiempo, la
grilla usada, los intentos por partícula y la fracción de empaquetamiento.

| opción | descripción | default |
|---|---|---|
| `-N` | cantidad de partículas | 1000 |
| `-L` | lado del área | 20 |
| `--rmin` / `--rmax` | rango de radios | 0.23 / 0.26 |
| `-M` | celdas por lado; `0` usa el máximo permitido | 0 |
| `--periodic` | condiciones periódicas de contorno | paredes |
| `--rc` | radio de interacción | 1.0 |
| `--method` | búsqueda de vecinas: `cim`, `cim-ll`, `brute` o `none` | `cim` |
| `--input-static` / `--input-dynamic` | leer la configuración en vez de generarla | — |
| `--seed` | semilla del generador | 42 |
| `--attempts` | intentos por partícula antes de fallar | 20000 |
| `--verify` | chequeo O(N²) de que no hay solapamientos | off |
| `--static-out` / `--dynamic-out` / `--neighbors-out` | archivos de salida | `data/…` |
| `--trace` | traza del barrido del CIM para `animate_cim.py` | — |

`--method none` genera las partículas y no busca vecinas: sirve para medir sólo la
generación. `--method brute` es O(N²), así que con `N` grande conviene dejar el
default `cim`: para N=10⁶ la fuerza bruta tarda unos 200 s y el CIM menos de uno.
`--method cim-ll` es el mismo CIM con las celdas guardadas como listas enlazadas
([Dos estructuras de celdas](metodo.md#dos-estructuras-de-celdas)).

Con `cim` o `cim-ll`, además del tiempo total el programa reporta por `stderr` en qué se
fue: cuánto costó armar la grilla, cuánto barrerla, cuántos bytes ocupa la estructura,
cuántos bloques del heap tiene y cuántas distancias midió.

```
cim:    rc=1 | 0.000472208 s | 7948 pairs | 15.896 neighbours/particle
  build 3.7917e-05 s | sweep 0.000427375 s | 9336 B in 170 bloques vivos | 23897 distance tests
cim-ll: rc=1 | 0.000411125 s | 7948 pairs | 15.896 neighbours/particle
  build 1.875e-06 s  | sweep 0.000410334 s | 4676 B in 2 bloques vivos   | 23897 distance tests
```

El archivo de vecinas tiene una línea por partícula:

```
0: 83 159 316 318
1: 10 15 45 131 271 301 370
```

## Usar una configuración existente

En vez de generar, el programa puede leer las posiciones y los radios de disco,
que es como el enunciado plantea el input del CIM. `N` y `L` salen de los
archivos, así que `-N` y `-L` se ignoran.

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 -M 13
```

## Validación contra la fuerza bruta

```bash
python3 python/validate_m.py -N 1000 --seeds 1 2 3
```

Genera una configuración, calcula la lista de referencia con `--method brute` y después
corre **las dos estructuras** con **cada** `M` de 1 al máximo sobre esos mismos archivos.
Para cada `M` compara conjunto contra conjunto, así que el orden dentro de cada línea no
importa, y además verifica que no haya vecinas repetidas, ni auto-vecindad, ni pares
asimétricos (`j ∈ vecinas(i)` ⟺ `i ∈ vecinas(j)`). Cierra comprobando que
`M = m_max + 1` es rechazado. Corre paredes y contorno periódico salvo que se pase
`--periodic` o `--walls`, y las dos estructuras salvo que se pase `--methods`.

`compare_neighbors.py` hace la misma comparación pero entre dos archivos ya generados,
que es lo que usan los pasos 6 a 8 del README.

## Animar el barrido

```bash
./build/CIM-TP1 -N 40 -L 20 --rc 2.0 --seed 7 -M 5 --method cim --trace data/trace.txt
python python/animate_cim.py --trace data/trace.txt --out images/cim.gif --fps 6 --stride 5
```

`--trace` escribe una línea por decisión del barrido (celda foco, celda del
half-shell abierta, y el veredicto de cada par medido). `animate_cim.py` sólo
reproduce ese archivo.

`--stride` submuestrea los pares y `--max-frames` acota el total.

## Visualizar

```bash
python python/visualize.py --particle 42 --neighbors data/neighbors.txt --rc 1.0
```

Dibuja todas las partículas a escala real, la elegida en rojo y sus vecinas en azul,
más el anillo punteado a `r_i + rc` (todo lo que lo toca es vecina). Con `--periodic`
agrega la imagen mínima de las vecinas que interactúan cruzando el borde.

Sin `--neighbors` dibuja sólo las posiciones. Con `--index-base 1` lee listas de
vecinas numeradas desde 1 en lugar de desde 0.

## Estudio paramétrico (puntos 3 y 4)

```bash
python3 python/benchmark.py --part 3 --repeat 1000 && python3 python/plot_m.py
```

Barre `M` de 1 hasta el máximo, para dos valores de `N` (uno intermedio y el más
alto que la geometría admite) y para las dos estructuras de celdas, cronometrando la
búsqueda `--repeat` veces por punto. `plot_m.py` grafica promedio con desvío estándar
e imprime el `M` óptimo de cada una.

Las estructuras van en el bucle **más interno**, para que se midan una al lado de la
otra con el mismo estado de máquina: si una corriera entera y después la otra, la
comparación se llevaría puesta cualquier deriva térmica o de carga entre las dos mitades.
Con `--methods` se puede medir una sola.

El `M` óptimo **no** sale del mínimo pelado: la cola de la curva es una meseta y cuál
`M` gana ahí cambia con el ruido. La decisión se queda con el **mayor `M` que empata
con el mínimo a 2 σ** del error de la media, así el elegido no depende de dónde cayó
el argmin dentro de la meseta.

`plot_m.py` cierra con una línea en el formato que espera el punto 4, con el óptimo de
cada estructura, que es lo que `run_all.sh` extrae y pasa sin intervención:

```
-> usar --M cim=13 cim-ll=13 en el punto 4
```

```bash
python3 python/benchmark.py --part 4 --M cim=13 cim-ll=13 --repeat 1000 && python3 python/plot_n.py
```

`--M` acepta un solo número, que vale para todas las estructuras, o uno por estructura.
Cada una corre en **su** óptimo: medirlas en un `M` compartido dejaría a una fuera de su
mejor grilla, que es justo la diferencia que el punto 3 podría encontrar.

Barre `N` con ese `M`: **densidad libre** (`L=20` fijo) y **densidad fija**
(`L ∝ √N`), superpuestas en la misma figura. En la curva de densidad fija `L` crece,
y lo que se mantiene es el **tamaño de celda** óptimo (`M_n ≈ M·L_n/L`), no el número
`M`: dejar `M=13` con `L=58` daría celdas de 4.5 y el barrido dejaría de ser el que se
optimizó en el punto 3.

Ambos ejes van en escala logarítmica cuando los datos abarcan dos órdenes de magnitud
o más, que es el caso de las dos figuras.

## Comparar las dos estructuras

```bash
python3 python/plot_compare.py --csv data/bench_p3.csv --x M --out images/comparacion_vs_M.png
python3 python/plot_compare.py --csv data/bench_p4.csv --x N --tag "densidad fija" --out images/comparacion_vs_N.png
```

No mide nada nuevo: lee los mismos CSV que dejaron los barridos y los mira por el lado
del armado, el barrido, la memoria y los bloques vivos, en vez del tiempo
total. Con `--x M` y varios `N` mezclados las curvas se pisan, así que se queda con el
`N` más grande salvo que se pase `--N`.

Cada fila del CSV lleva, además del tiempo total:

| columna | qué es |
|---|---|
| `build_seconds` | armar la grilla: reservarla y archivar las `N` partículas |
| `sweep_seconds` | el barrido de celda foco y half-shell |
| `grid_bytes` | bytes que ocupa la estructura de celdas, sin las listas de salida |
| `grid_live_blocks` | bloques del heap que la estructura tiene, una vez armada |
| `pair_tests` | distancias medidas; igual para las dos estructuras |

`seconds - (build_seconds + sweep_seconds)` no es holgura: es lo que cuesta reservar las
listas de salida, que las dos estructuras pagan igual, más destruir la grilla, que no:
son un `free()` por celda no vacía contra dos.
