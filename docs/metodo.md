# El método

Implementación del Cell Index Method en este código: el criterio de tamaño de
grilla, el barrido half-shell y las dos estructuras de celdas.

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
quedarían vecinas repetidas. Con `M=1` es peor: los cuatro desplazamientos vuelven a la
celda foco. El half-shell sólo es una enumeración válida mientras `d` y `−d` sean celdas
distintas módulo `M`, y eso pide `M ≥ 3`.

La fuerza bruta no es un parche para ese caso: es la respuesta exacta. El criterio de
tamaño de celda obliga a `L/M ≥ rc + 2·r_max`, así que con `M ≤ 2` el alcance de una
partícula cubre todo el rango de mínima imagen y **ninguna** pareja de celdas se puede
descartar. Medir todos los pares es en lo que degenera el barrido, no una aproximación.

Lo que sí cambia es el CSV: esas filas salen etiquetadas `method=cim` pero con
`build_seconds` y `sweep_seconds` en `0` (no se armó ninguna grilla) y `pair_tests` en
`N(N−1)/2`, que es la firma de la fuerza bruta. Los barridos del punto 3 corren con
paredes, así que no aparecen; si alguna vez se corre `benchmark.py --part 3 --periodic`,
los puntos `M=1` y `M=2` son esos y no miden el CIM.

## Dos estructuras de celdas

El barrido de arriba no dice nada sobre **cómo** cada celda guarda las partículas que le
tocaron, y ahí hay dos opciones implementadas:

| | `--method cim` | `--method cim-ll` |
|---|---|---|
| clase | `CellGrid` | `LinkedCellGrid` |
| una celda es | un `std::vector<int>` | una cadena de índices |
| memoria | `M²` cabeceras de 24 B + la reserva de cada celda | `(M² + N)` enteros, planos |
| armado | `N` `push_back`, con duplicación de capacidad | `N` escrituras, sin reasignar nunca |
| bloques vivos | uno por celda no vacía, más el array externo | **dos**, siempre |

La segunda es la de Allen & Tildesley (§5.3.2, pp. 149-151), que la llaman `HEAD` y
`LIST`:

```
head_[c] = id de la primera partícula de la celda c, o -1 si está vacía
next_[i] = id de la siguiente partícula de la celda de i, o -1 si es la última
```

Insertar es empujar al frente de la cadena, dos escrituras y ninguna reserva:

```cpp
next_[id] = head_[c];   // la vieja cabeza pasa a ser el sucesor de id
head_[c]  = id;         // y id pasa a ser la nueva cabeza
```

`clear()` sólo resetea `HEAD`. Cada `insert` pisa su propio `next_[id]` con la cabeza
actual de su celda, así que ninguna cadena puede alcanzar una posición sobrante de un
armado anterior; limpiar `LIST` también sería `O(N)` de puro desperdicio.

**El barrido es uno solo.** `cim_sweep` es un template sobre el tipo de grilla, y las dos
estructuras entregan un rango por celda, así que el mismo código recorre las dos. El
`i < j` de los pares propios pasa a ser "arrancar desde el sucesor de `it`", que sobre un
vector es lo mismo de antes y sobre una cadena es el recorrido natural. Como el código es
el mismo, una diferencia de tiempo entre las dos sólo puede venir de la estructura.

**Sale en distinto orden.** Como se inserta al frente, cada celda se recorre en orden
descendente de id, así que las vecinas de cada partícula salen en otro orden que con
`cim`. No cambia cuáles son, porque la relación es simétrica y todas las comparaciones
del proyecto son entre conjuntos, pero un `diff` pelado entre `nb_cim.txt` y
`nb_cimll.txt` marca diferencias que no existen.

**Instrumentación.** `--trace` y el contador de distancias son argumentos de template y
no flags, así que `if constexpr` los saca de la instanciación que usan las corridas
cronometradas y no pueden inflar una medición.

Lo mismo vale para la memoria. Contarla obliga a recorrer las `M²` celdas, que en
`CellGrid` es un barrido entero del arreglo de celdas y en `LinkedCellGrid` no cuesta
nada: dejarlo adentro del reloj le cobraría a una estructura lo que no le cobra a la
otra, y justo en la dirección de la conclusión. Por eso `cim_untimed_stats` corre el
barrido una vez más, aparte, y de ahí salen las tres columnas que son cuentas y no
tiempos: `pair_tests`, `grid_bytes` y `grid_live_blocks`. Ninguna corrida cronometrada
las paga.


## Bibliografía

- Allen, M. P. & Tildesley, D. J., *Computer Simulation of Liquids*, Oxford, 1989.
  - §5.3.2 «Cell structures and linked lists», pp. 149–152 — el método completo.
- Teórica 1 de la cátedra, láminas 19–28 — planteo del CIM y consigna del TP.
