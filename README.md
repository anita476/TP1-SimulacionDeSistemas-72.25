# TP1 — Búsqueda Eficiente de Partículas Vecinas

Simulación de Sistemas — 72.25 — ITBA

Implementación del **Cell Index Method** para detectar, en un área cuadrada de lado `L`
con `N` partículas de radio no nulo, cuáles distan menos de `rc` **borde a borde**.

## Estructura

```
.
├── src/                    simulador (C++17)
│   ├── particle.hpp        struct Particle {x, y, r}
│   ├── geometry.hpp        mínima imagen + criterio de distancia borde a borde
│   ├── cell_grid.hpp       grilla uniforme de M x M celdas
│   ├── generator.hpp/.cpp  generación de partículas no superpuestas
│   └── main.cpp            CLI y escritura de archivos
├── python/                 análisis y visualización
│   ├── requirements.txt
│   └── visualize.py        figura de partículas y vecinas
├── data/                   archivos generados (fuera de git)
├── figures/                figuras generadas (fuera de git)
└── CMakeLists.txt
```

`data/` y `figures/` están enteras en el `.gitignore` y no se versionan: las crean
el simulador y el visualizador la primera vez que escriben en ellas.

La separación es la que pide la cátedra: **simulación → archivos → análisis**. El
simulador no grafica; el visualizador no simula.

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

> **No compartas `build/` entre WSL y Windows.** El `CMakeCache.txt` guarda rutas
> absolutas (`/mnt/c/...` contra `C:/...`) y CMake se niega a reusarlo. Si cambiás
> de entorno, borrá la carpeta: `rm -rf build`.

## Generar partículas

```bash
./build/CIM-TP1 -N 1000 -L 20 --seed 42 --verify
```

Verificado que Windows (MSVC) y Linux (libstdc++) producen la **misma**
configuración para la misma semilla.

Escribe `data/static.txt` y `data/dynamic.txt`, y reporta por `stderr` el tiempo, la
grilla usada, los intentos por partícula y la fracción de empaquetamiento.

| opción | descripción | default |
|---|---|---|
| `-N` | cantidad de partículas | 1000 |
| `-L` | lado del área | 20 |
| `--rmin` / `--rmax` | rango de radios | 0.23 / 0.26 |
| `--periodic` | condiciones periódicas de contorno | paredes |
| `--rc` | radio de interacción | 1.0 |
| `--method` | búsqueda de vecinas: `brute` o `none` | `brute` |
| `--seed` | semilla del generador | 42 |
| `--attempts` | intentos por partícula antes de fallar | 20000 |
| `--verify` | chequeo O(N²) de que no hay solapamientos | off |
| `--static-out` / `--dynamic-out` / `--neighbors-out` | archivos de salida | `data/…` |

`--method none` genera las partículas y no busca vecinas: sirve para medir sólo la
generación, y es obligatorio si `N` es grande, porque la fuerza bruta es O(N²).

El archivo de vecinas tiene una línea por partícula:

```
0: 83 159 316 318
1: 10 15 45 131 271 301 370
```

Códigos de salida: `0` ok, `1` error de parámetros o densidad inalcanzable,
`2` la verificación encontró un solapamiento.

## Visualizar

```bash
python python/visualize.py --particle 42 --neighbors data/neighbors.txt --rc 1.0
```

Dibuja todas las partículas a escala real, la elegida en rojo y sus vecinas en azul,
más el anillo punteado a `r_i + rc` (todo lo que lo toca es vecina). Con `--periodic`
agrega la imagen mínima de las vecinas que interactúan cruzando el borde.

Sin `--neighbors` dibuja sólo las posiciones. Con `--index-base 1` lee listas de
vecinas numeradas desde 1 en lugar de desde 0.

## Estado

| Punto del enunciado | Estado |
|---|---|
| 1 — generación aleatoria no superpuesta | listo |
| 1 — figura de partículas y vecinas | listo |
| 1 — fuerza bruta | listo |
| 1 — salida de lista de vecinas y tiempo | listo |
| 1 — Cell Index Method (paredes y periódico) | pendiente |
| 1 — error si `M > L/(rc + 2·r_max)` | pendiente |
| 3 — tiempo en función de M | pendiente |
| 4 — tiempo en función de N | pendiente |
