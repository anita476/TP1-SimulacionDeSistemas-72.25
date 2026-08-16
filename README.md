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
python3 python/visualize.py --particle 30 --rc 1.0 --neighbors data/neighbors.txt --out images/vecinas.png
```
**5.bis** La misma figura con contorno periódico. La partícula 591 cae en una esquina, así
que sus vecinas quedan repartidas en las **cuatro esquinas** de la caja. Hay que pasarle
los tres archivos periódicos: si se dejan los defaults, se mezclan posiciones con paredes
y lista de vecinas periódica.

```bash
python3 python/visualize.py --static data/static_pbc.txt --dynamic data/dynamic_pbc.txt --neighbors data/neighbors_pbc.txt --particle 591 --rc 1.0 --periodic --out images/vecinas_pbc.png
```

Puede utilizarse la versión interactiva. Hacer clic para seleccionar una partícula o utilizar **n,p**.

```bash
python3 python/visualize.py --static data/static_pbc.txt --dynamic data/dynamic_pbc.txt --neighbors data/neighbors_pbc.txt --particle 591 --rc 1.0 --periodic --interactive
```

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

**8.bis** La validación que pide la cátedra: que **todo** `M > 1` dé exactamente las
mismas vecinas que la fuerza bruta (`M=1`), partícula por partícula, sin importar el
orden dentro de cada línea. Barre `M` de 1 al máximo, con paredes y con contorno
periódico, sobre varias configuraciones. Tiene que terminar en `VALIDACION OK`:

```bash
python3 python/validate_m.py -N 1000 --seeds 1 2 3
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
python3 python/animate_cim.py --trace data/trace.txt --out images/cim.gif --fps 6 --stride 5
```

**10.bis** Lo mismo con contorno periódico. Sirve para ver que ahí el half-shell **nunca
descarta celdas**: las que se salen por un borde reaparecen por el opuesto.

```bash
./build/CIM-TP1 -N 40 -L 20 --rc 2.0 --seed 7 -M 5 --method cim --periodic --trace data/trace_pbc.txt
```

```bash
python3 python/animate_cim.py --trace data/trace_pbc.txt --out images/cim_pbc.gif --fps 6 --stride 5
```

**11.** Punto 3, barrido de `M` para dos valores de `N`. Son 1000 búsquedas por punto,
repartidas en 20 vueltas del barrido completo: la dispersión **entre vueltas** es lo que
mide la incerteza real, porque las búsquedas de una misma vuelta comparten el estado de
la máquina y subestiman el error:

```bash
python3 python/benchmark.py --part 3 --repeat 50
```

**12.** Graficarlo. Imprime el `M` óptimo, que hace falta en el paso siguiente:

```bash
python3 python/plot_m.py
```

**13.** Punto 4, barrido de `N` con ese `M` óptimo, en los dos regímenes de densidad:

```bash
python3 python/benchmark.py --part 4 --M 13 --repeat 50
```

**14.** Graficar las dos curvas superpuestas:

```bash
python3 python/plot_n.py
```

Al terminar, en `images/` quedan `vecinas.png`, `cim.gif`, `tiempo_vs_M.png` y
`tiempo_vs_N.png`, que son las que se muestran acá abajo.

## Resultados

### Punto 1 — vecinas de una partícula

Todas las partículas a escala real, la elegida en rojo y sus vecinas en azul. El anillo
punteado está a `r_i + rc` del centro: todo lo que lo toca con su **borde** es vecina.

![Vecinas de la partícula 30](images/vecinas.png)

### Punto 1 — vecinas con contorno periódico

La misma idea sobre el toroide. La partícula 591 está en la esquina superior derecha y
tiene 15 vecinas, **11 de ellas a través del borde**: aparecen en las otras tres esquinas
de la caja, porque para el sistema periódico las cuatro esquinas son el mismo lugar.

Los discos claros alrededor de la elegida son las **imágenes mínimas**: dónde cae cada
vecina cuando se la trae por el camino corto, que es la distancia que realmente se mide.

![Vecinas de la partícula 591 con contorno periódico](images/vecinas_pbc.png)

### El barrido del CIM, paso a paso

Celda foco en amarillo, celdas del half-shell en celeste, y cada par medido en verde si
cae dentro de `rc` o rojo si no. `N=40`, `L=20`, `rc=2`, `M=5`.

![Animación del barrido del CIM](images/cim.gif)

### El barrido con contorno periódico

Mismos parámetros, pero sobre el toroide. La diferencia se ve en las celdas del borde:
con paredes el half-shell descarta las vecinas que caen fuera de la grilla, mientras que
acá **las cuatro se abren siempre**, envolviendo hacia el lado opuesto.

![Animación del barrido del CIM con contorno periódico](images/cim_pbc.gif)

### Punto 3 — tiempo en función de M

`L=20`, `rc=1`, paredes, 1000 búsquedas por punto (20 vueltas × 50). `M=1` es la fuerza
bruta. El tiempo cae hasta que la curva entra en una meseta; el óptimo es `M=13`, el
máximo que permite el criterio `L/M ≥ rc + 2·r_max`, y es unas **4x más rápido** que el
peor `M`.

![Tiempo de búsqueda en función de M](images/tiempo_vs_M.png)

### Punto 4 — tiempo en función de N

Con `M=13`, los dos regímenes superpuestos. A **densidad fija** (`L ∝ √N`) el CIM escala
lineal, `t ~ N^1.01`, que es la propiedad que lo justifica; a **densidad libre** (`L=20`)
la densidad crece con `N` y el exponente sube a `t ~ N^1.51`, porque cada celda acumula
cada vez más partículas.

![Tiempo de búsqueda en función de N](images/tiempo_vs_N.png)

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
│   ├── compare_neighbors.py   compara dos listas de vecinas ya generadas
│   ├── validate_m.py          barre M de 1 al máximo contra la fuerza bruta
│   ├── benchmark.py           barridos de M y de N (puntos 3 y 4)
│   ├── plot_m.py              tiempo en función de M
│   ├── plot_n.py              tiempo en función de N
│   └── bench_common.py        carga de los CSV y estadística compartida
├── data/                   archivos generados (fuera de git)
├── images/                 figuras del informe (versionadas)
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

**Excepción, `M < 3` con contorno periódico.** Ahí la grilla es tan chica que el
half-shell se muerde la cola: con `M=2`, los desplazamientos `(+1,+1)` y `(+1,-1)`
caen en la **misma** celda módulo 2, así que el mismo par se mediría dos veces y
quedarían vecinas repetidas. Con esa grilla toda celda es vecina de toda celda, o sea
que el barrido degenera en medir todos los pares igual, de modo que el programa usa
directamente la fuerza bruta y lo avisa por `stderr`. El resultado es el mismo; lo que
cambia es que esos dos puntos del punto 3 no miden el CIM.

## Validación contra la fuerza bruta

```bash
python3 python/validate_m.py -N 1000 --seeds 1 2 3
```

Genera una configuración, calcula la lista de referencia con `--method brute` y después
corre el CIM con **cada** `M` de 1 al máximo sobre esos mismos archivos. Para cada `M`
compara conjunto contra conjunto, así que el orden dentro de cada línea no importa, y
además verifica que no haya vecinas repetidas, ni auto-vecindad, ni pares asimétricos
(`j ∈ vecinas(i)` ⟺ `i ∈ vecinas(j)`). Cierra comprobando que `M = m_max + 1` es
rechazado. Corre paredes y contorno periódico salvo que se pase `--periodic` o
`--walls`.

`compare_neighbors.py` hace la misma comparación pero entre dos archivos ya generados,
que es lo que usan los pasos 6 a 8 de arriba.

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
python3 python/benchmark.py --part 3 --repeat 50 && python3 python/plot_m.py
```

Barre `M` de 1 hasta el máximo, para dos valores de `N` (uno intermedio y el más
alto que la geometría admite), cronometrando la búsqueda `--repeat` veces por
punto. `plot_m.py` grafica promedio
con desvío estándar e imprime el `M` óptimo.

El `M` óptimo **no** sale del mínimo pelado: la cola de la curva es una meseta y cuál
`M` gana ahí cambia de vuelta en vuelta. La decisión usa la dispersión **entre vueltas**
y se queda con el **mayor `M` que empata con el mínimo a 2 σ**.

Hacen falta bastantes vueltas para que el resultado sea estable. Con 5 vueltas, `N=535`
daba una meseta ancha (`M ∈ {9,11,12,13}`) y el argmin caía en `M=12` **por ruido**; con
20 vueltas la meseta se cierra en `{12,13}` y el mínimo es `M=13`, igual que para
`N=1071`, que ahí sí es un mínimo neto sin empate. De ahí sale el `--M 13` del punto 4.
Moraleja: hay que leer la meseta, no el argmin.

```bash
python3 python/benchmark.py --part 4 --M 13 --repeat 50 && python3 python/plot_n.py
```

Barre `N` con ese `M`: **densidad libre** (`L=20` fijo) y **densidad fija**
(`L ∝ √N`), superpuestas en la misma figura. En la curva de densidad fija `L` crece,
y lo que se mantiene es el **tamaño de celda** óptimo (`M_n ≈ M·L_n/L`), no el número
`M`: dejar `M=13` con `L=58` daría celdas de 4.5 y el barrido dejaría de ser el que se
optimizó en el punto 3.

Ambos ejes van en escala logarítmica cuando los datos abarcan dos órdenes de magnitud
o más, que es el caso de las dos figuras.


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
