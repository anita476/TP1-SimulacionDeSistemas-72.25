# TP1 — Búsqueda Eficiente de Partículas Vecinas

Simulación de Sistemas — 72.25 — ITBA

Implementación del **Cell Index Method** para detectar, en un área cuadrada de lado `L`
con `N` partículas de radio no nulo, cuáles distan menos de `rc` **borde a borde**.

## Reproducir todo, en orden

Desde la raíz del repositorio. En Windows nativo, agregar `.exe` al ejecutable y
correr desde la *Developer Command Prompt for VS 2022*.

**1.** Dependencias del sistema (Linux / WSL; omitir si ya están):

```bash
sudo apt install -y build-essential cmake git python3-matplotlib
```

**2.** Compilar:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

**3.** Generar 1000 partículas con paredes, buscar vecinas con el CIM y verificar
que ninguna se solapa:

```bash
./build/CIM-TP1 -N 1000 -L 20 --rc 1.0 -M 13 --seed 42 --method cim --verify
```

**4.** Lo mismo con condiciones periódicas de contorno. Va a archivos aparte para
no pisar la configuración con paredes, que los pasos 6 a 8 vuelven a usar:

```bash
./build/CIM-TP1 -N 1000 -L 20 --rc 1.0 -M 13 --seed 42 --method cim --periodic --verify --static-out data/static_pbc.txt --dynamic-out data/dynamic_pbc.txt --neighbors-out data/neighbors_pbc.txt
```

**5.** Figura del punto 1: una partícula resaltada y sus vecinas:

```bash
python3 python/visualize.py --particle 30 --rc 1.0 --neighbors data/neighbors.txt --out figures/vecinas.png
```
Puede utilizarse la versión interactiva. Hacer clic para seleccionar una partícula o utilizar **n,p**.

```bash
 python3 python/visualize.py --particle 30 --rc 1.0 --neighbors data/neighbors_pbc.txt --interactive --periodic
```

>`--periodic` sirve para visualizar el caso con condiciones de contorno de mejor manera)

**6.** Correr la fuerza bruta sobre **la misma** configuración, leyéndola de disco:

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 --method brute --neighbors-out data/nb_brute.txt
```

**7.** Y el CIM sobre esa misma configuración:

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 -M 13 --method cim --neighbors-out data/nb_cim.txt
```

**8.** Comparar ambas listas. Tiene que imprimir `IDENTICAS`:

```bash
python3 python/compare_neighbors.py data/nb_brute.txt data/nb_cim.txt
```

**9.** Comprobar que un `M` mayor al máximo da error (exit code 1):

```bash
./build/CIM-TP1 -N 1000 -L 20 --rc 1.0 -M 14 --method cim
```

**10.** Trazar el barrido de un caso chico y animarlo:

```bash
./build/CIM-TP1 -N 40 -L 20 --rc 2.0 --seed 7 -M 5 --method cim --trace data/trace.txt
```

```bash
python3 python/animate_cim.py --trace data/trace.txt --out figures/cim.gif --fps 6
```

**11.** Punto 3, barrido de `M` para dos valores de `N`:

```bash
python3 python/benchmark.py --part 3 --repeat 1000
```

**12.** Graficarlo. Imprime el `M` óptimo, que hace falta en el paso siguiente:

```bash
python3 python/plot_m.py
```

**13.** Punto 4, barrido de `N` con ese `M` óptimo, en los dos regímenes de densidad:

```bash
python3 python/benchmark.py --part 4 --M 13 --repeat 1000
```

**14.** Graficar las dos curvas superpuestas:

```bash
python3 python/plot_n.py
```

Al terminar, en `figures/` quedan `vecinas.png`, `cim.gif`, `tiempo_vs_M.png` y
`tiempo_vs_N.png`.

## Estructura

```
.
├── src/                    simulador (C++17)
│   ├── particle.hpp        struct Particle {x, y, r}
│   ├── geometry.hpp        mínima imagen + criterio de distancia borde a borde
│   ├── cell_grid.hpp       grilla uniforme de M x M celdas
│   ├── generator.hpp/.cpp  generación de partículas no superpuestas
│   ├── neighbors.hpp/.cpp  fuerza bruta y Cell Index Method
│   ├── io.hpp/.cpp         lectura y escritura de los archivos de la cátedra
│   └── main.cpp            CLI y escritura de archivos
├── python/                 análisis y visualización
│   ├── requirements.txt
│   ├── visualize.py           figura de partículas y vecinas
│   ├── animate_cim.py         animación paso a paso del barrido del CIM
│   ├── compare_neighbors.py   valida el CIM contra la fuerza bruta
│   ├── benchmark.py           barridos de M y de N (puntos 3 y 4)
│   ├── plot_m.py              tiempo en función de M
│   ├── plot_n.py              tiempo en función de N
│   └── bench_common.py        carga de los CSV y estadística compartida
├── data/                   archivos generados (fuera de git)
├── figures/                figuras generadas (fuera de git)
└── CMakeLists.txt
```


## Requisitos

- Compilador C++17 y CMake ≥ 3.16
  - Linux / WSL: `sudo apt install build-essential cmake git`
  - Windows nativo: Visual Studio Build Tools 2022, desde la *Developer Command Prompt*
- Python 3 con `pip install -r python/requirements.txt`

CMake baja [argparse](https://github.com/p-ranav/argparse) automáticamente, así que
hace falta red la primera vez.

## Compilar

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

El ejecutable queda en `build/CIM-TP1` (`build/CIM-TP1.exe` en Windows nativo).


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
| `--method` | búsqueda de vecinas: `cim`, `brute` o `none` | `cim` |
| `--input-static` / `--input-dynamic` | leer la configuración en vez de generarla | — |
| `--seed` | semilla del generador | 42 |
| `--attempts` | intentos por partícula antes de fallar | 20000 |
| `--verify` | chequeo O(N²) de que no hay solapamientos | off |
| `--static-out` / `--dynamic-out` / `--neighbors-out` | archivos de salida | `data/…` |
| `--trace` | traza del barrido del CIM para `animate_cim.py` | — |

`--method none` genera las partículas y no busca vecinas: sirve para medir sólo la
generación. `--method brute` es O(N²), así que con `N` grande conviene dejar el
default `cim`: para N=10⁶ la fuerza bruta tarda unos 200 s y el CIM menos de uno.

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

## Tamaño de la grilla

El criterio `L/M > rc` del apunte vale para partículas puntuales. Como acá las
partículas tienen radio y se archivan en la celda de su **centro**, el alcance
efectivo entre centros es `rc + r_i + r_j`, de modo que:

```
L/M >= rc + 2·r_max     =>     M <= L / (rc + 2·r_max)
```

Con `L=20`, `rc=1` y `r_max=0.26` da **M ≤ 13**. Pasarse de ahí pierde en
silencio los pares cuyos centros quedan a dos celdas pero cuyos bordes siguen
dentro de `rc`, así que el programa lo rechaza con un error. `r_max` se toma de
las partículas reales, no del parámetro `--rmax`.

Códigos de salida: `0` ok, `1` error de parámetros o densidad inalcanzable,
`2` la verificación encontró un solapamiento.

## Cell Index Method

```bash
./build/CIM-TP1 -N 1000 -L 20 --rc 1.0 -M 13 --method cim
```

Cada celda se toma como foco una sola vez. Dentro del foco se recorren los pares
propios (posiciones `i < j` dentro de la misma celda) y después se abren **cuatro** de las
ocho celdas vecinas:

```
SE (+1, -1)   E (+1, 0)   NE (+1, +1)   N (0, +1)
```

Es el *half-shell*, y es exactamente el conjunto que se muestra en clase y en Allen &
Tildesley p. 152.

## Animar el barrido

```bash
./build/CIM-TP1 -N 40 -L 20 --rc 2.0 --seed 7 -M 5 --method cim --trace data/trace.txt
python python/animate_cim.py --trace data/trace.txt --out figures/cim.gif --fps 6
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
python3 python/benchmark.py --part 3 && python3 python/plot_m.py
```

Barre `M` de 1 hasta el máximo, para dos valores de `N` (uno intermedio y el más
alto que la geometría admite), cronometrando la búsqueda `--repeat` veces por
punto. `plot_m.py` grafica promedio con desvío estándar e imprime el `M` óptimo.


```bash
python3 python/benchmark.py --part 4 --M 13 && python3 python/plot_n.py
```

Barre `N` con ese `M`: **densidad libre** (`L=20` fijo) y **densidad fija**
(`L ∝ √N`), superpuestas en la misma figura.


## Bibliografía

- Allen, M. P. & Tildesley, D. J., *Computer Simulation of Liquids*, Oxford, 1989.
  - §5.3.2 «Cell structures and linked lists», pp. 149–152 — el método completo.
  - p. 150 — el criterio `l = L/M` mayor al radio de corte, y `N_c = N/M²`.
  - p. 151 — costo `9·N·N_c`, o `4.5·N·N_c` aprovechando la tercera ley.
  - p. 152 — el half-shell, y la advertencia de que para `N` chico el costo de
    armar las listas no compensa.
  - §5.3.1, pp. 147–149 — listas de Verlet, la alternativa que no usamos.
  - §1.5.2 y programa F.01 — condiciones periódicas e imagen mínima.
  - programa F.18 — evitar la raíz cuadrada, que es lo que hace `within_cutoff`.
  - programa F.20 — implementación de referencia del método de celdas.
- Quentrec, B. & Brot, C., «New method for searching for neighbours in molecular
  dynamics computations», *J. Comput. Phys.* **13**(3), 430–432, 1973 — el método
  original de celdas.
- Hockney, R. W. & Eastwood, J. W., *Computer Simulation Using Particles*, 1981,
  cap. 8 — listas enlazadas.
- Teórica 1 de la cátedra, láminas 19–28 — planteo del CIM y consigna del TP.
