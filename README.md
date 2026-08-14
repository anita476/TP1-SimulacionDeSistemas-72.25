# TP1 — Búsqueda Eficiente de Partículas Vecinas

Simulación de Sistemas — 72.25 — ITBA

Implementación del **Cell Index Method** para detectar, en un área cuadrada de lado `L`
con `N` partículas de radio no nulo, cuáles distan menos de `rc` **borde a borde**.

La grilla de celdas está implementada de **dos maneras**, con el mismo barrido por
encima: un `std::vector` por celda (`--method cim`) y las listas enlazadas `HEAD`/`LIST`
de Allen & Tildesley (`--method cim-ll`). Resultan en exactamente las mismas vecinas; la diferencia está documentada en [docs/metodo.md](docs/metodo.md#dos-estructuras-de-celdas).

Este README se usa para correr el proyecto. El resto está en `docs/`:

- [docs/resultados.md](docs/resultados.md) — las figuras y qué dicen
- [docs/metodo.md](docs/metodo.md) — tamaño de grilla, half-shell, las dos estructuras de celdas y bibliografía
- [docs/uso.md](docs/uso.md) — cada herramienta por separado: el CLI del simulador y los scripts de análisis

## Requisitos

- Compilador C++17 y CMake ≥ 3.16
  - Linux / WSL: `sudo apt install build-essential cmake git`
  - Windows nativo: Visual Studio Build Tools 2022, desde la *Developer Command Prompt*
- Python 3 con `pip install -r python/requirements.txt`

CMake baja [argparse](https://github.com/p-ranav/argparse) automáticamente, así que
hace falta red la primera vez.

## Reproducir todo, de una

```bash
./run_all.sh
```

Compila, genera la configuración de referencia, saca la figura del punto 1 y el gif,
valida contra la fuerza bruta, mide los puntos 3 y 4 y deja las ocho figuras en
`images/`. Los barridos cronometran **1000 búsquedas por punto**, con las
dos estructuras.

El script acepta como argumento el visor interactivo:

```bash
./run_all.sh interactivo
```

El orden no es arbitrario: hay una dependencia de datos que el script resuelve solo, el
`M` óptimo, que sale del texto que imprime `plot_m.py` y entra como argumento del punto
4, uno por estructura. Los pasos independientes no corren en paralelo pues los puntos 3 y 4 miden tiempos con el fin de no ensuciar la medición.

## Reproducir todo, paso a paso

Lo mismo que hace `run_all.sh`, para correr a mano. Desde la raíz del repositorio. En
Windows nativo, agregar `.exe` al ejecutable y correr desde la *Developer Command Prompt
for VS 2022*.

**1.** Dependencias del sistema (Linux / WSL; omitir si ya están):

```bash
sudo apt install -y build-essential cmake git python3-matplotlib
```

**2.** Compilar:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

El ejecutable queda en `build/CIM-TP1` (`build/CIM-TP1.exe` en Windows nativo).

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
Puede utilizarse la versión interactiva. Hacer clic para seleccionar una partícula o utilizar **n,p**.

```bash
python3 python/visualize.py --particle 30 --rc 1.0 --periodic --interactive --static data/static_pbc.txt --dynamic data/dynamic_pbc.txt --neighbors data/neighbors_pbc.txt
```

> `--periodic` dibuja las réplicas por wrap-around, que es lo que hace legible el caso
> con contorno periódico.
>
> **Los tres archivos van juntos.** `--static` y `--dynamic` apuntan por defecto a la
> configuración con paredes, así que pasar sólo `--neighbors data/neighbors_pbc.txt`
> dibuja las posiciones del paso 3 con las vecinas del paso 4. No son la misma
> configuración: el generador rechaza por solapamiento **a través del borde** cuando se
> le pide `--periodic`, así que con la misma semilla acepta otras partículas (las 1000
> posiciones y 768 de los 1000 radios difieren). Lo que se ve entonces es una partícula
> unida a "vecinas" que están a 15 unidades en una caja de lado 20.

**6.** Correr la fuerza bruta sobre **la misma** configuración, leyéndola de disco:

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 --method brute --neighbors-out data/nb_brute.txt
```

**7.** Y el CIM sobre esa misma configuración:

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 -M 13 --method cim --neighbors-out data/nb_cim.txt
```

**7.bis** Y el CIM con listas enlazadas, sobre la misma configuración otra vez:

```bash
./build/CIM-TP1 --input-static data/static.txt --input-dynamic data/dynamic.txt --rc 1.0 -M 13 --method cim-ll --neighbors-out data/nb_cimll.txt
```

**8.** Comparar las listas contra la fuerza bruta. Las dos tienen que imprimir
`IDENTICAS`:

```bash
python3 python/compare_neighbors.py data/nb_brute.txt data/nb_cim.txt
python3 python/compare_neighbors.py data/nb_brute.txt data/nb_cimll.txt
```

> Las dos estructuras dan las mismas vecinas pero en **distinto orden** dentro de cada
> línea, porque la lista enlazada recorre cada celda en orden descendente de id. Un
> `diff` pelado entre los dos archivos marca diferencias que no existen;
> `compare_neighbors.py` compara conjuntos, que es lo que corresponde.

**8.bis** La validación que pide la cátedra: que **todo** `M > 1` dé exactamente las
mismas vecinas que la fuerza bruta (`M=1`), partícula por partícula, sin importar el
orden dentro de cada línea. Barre `M` de 1 al máximo, con las dos estructuras, con
paredes y con contorno periódico, sobre varias configuraciones. Tiene que terminar en
`VALIDACION OK`:

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

**11.** Punto 3, barrido de `M` para dos valores de `N`, con 1000 búsquedas
cronometradas por punto:

```bash
python3 python/benchmark.py --part 3 --repeat 1000
```

**12.** Graficarlo. Del mismo CSV salen dos figuras: la del punto 3, con una sola
estructura, y la del estudio extra, con las dos superpuestas. La segunda es la que
imprime el `M` óptimo que hace falta en el paso siguiente, porque el punto 4 toma uno
por estructura:

```bash
python3 python/plot_m.py --methods cim --out images/tiempo_vs_M.png
python3 python/plot_m.py --out images/tiempo_vs_M_con_ll.png
```

**13.** Punto 4, barrido de `N` con ese `M` óptimo, en los dos regímenes de densidad:

```bash
python3 python/benchmark.py --part 4 --M cim=13 cim-ll=13 --repeat 1000
```

**14.** Graficarlo, con el mismo criterio de dos figuras:

```bash
python3 python/plot_n.py --methods cim --out images/tiempo_vs_N.png
python3 python/plot_n.py --out images/tiempo_vs_N_con_ll.png
```

**15.** Comparar las dos estructuras de celdas, leyendo los CSV que ya quedaron:

```bash
python3 python/plot_compare.py --csv data/bench_p3.csv --x M --out images/comparacion_vs_M.png
python3 python/plot_compare.py --csv data/bench_p4.csv --x N --tag "densidad fija" --out images/comparacion_vs_N.png
```

Al terminar, en `images/` quedan las figuras que comenta
[docs/resultados.md](docs/resultados.md).

## Estructura

```
.
├── run_all.sh              corre el pipeline entero, de punta a punta
├── src/                        simulador (C++17)
│   ├── particle.hpp            struct Particle {x, y, r}
│   ├── geometry.hpp            mínima imagen + criterio de distancia borde a borde
│   ├── cell_grid.hpp           grilla de M x M celdas, un std::vector por celda
│   ├── linked_cell_grid.hpp    la misma grilla como HEAD/LIST de A&T
│   ├── generator.hpp/.cpp      generación de partículas no superpuestas
│   ├── neighbors.hpp/.cpp      fuerza bruta y Cell Index Method
│   ├── io.hpp/.cpp             lectura y escritura de los archivos de la cátedra
│   └── main.cpp                CLI y escritura de archivos
├── python/                     análisis y visualización
│   ├── requirements.txt
│   ├── visualize.py            figura de partículas y vecinas
│   ├── animate_cim.py          animación paso a paso del barrido del CIM
│   ├── compare_neighbors.py    compara dos listas de vecinas ya generadas
│   ├── validate_m.py           barre M de 1 al máximo contra la fuerza bruta
│   ├── benchmark.py            barridos de M y de N (puntos 3 y 4)
│   ├── plot_m.py               tiempo en función de M
│   ├── plot_n.py               tiempo en función de N
│   ├── plot_compare.py         armado, barrido, memoria y bloques de cada estructura
│   └── bench_common.py         carga de los CSV y estadística compartida
├── docs/                   informe: resultados, método y uso de cada herramienta
├── data/                   archivos generados (fuera de git)
├── images/                 figuras del informe (versionadas)
└── CMakeLists.txt
```
