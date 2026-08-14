#!/usr/bin/env bash
#
# Corre todo el pipeline del TP, en orden, con los numeros del informe:
#
#   1. compila
#   2. genera la configuracion de referencia (paredes y contorno periodico)
#   3. figura del punto 1 y gif del barrido
#   4. valida el CIM y las listas enlazadas contra la fuerza bruta
#   5. puntos 3 y 4: los dos barridos y sus figuras
#   6. vector por celda contra listas enlazadas
#
#   ./run_all.sh
#
# El orden no es arbitrario, hay tres dependencias reales:
#
#   config -> figuras, validar, comparar   (todas leen la MISMA configuracion)
#   trace  -> gif
#   bench3 -> plot_m -> bench4             (el M optimo sale de plot_m.py)
#
# La tercera es la unica en la que viaja un valor calculado entre pasos, y se
# extrae de la salida de plot_m.py en vez de copiarlo a mano.
#
# El visor interactivo va aparte porque abre una ventana y espera a que la
# cierren:  ./run_all.sh interactivo

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# ---------------------------------------------------------------- parametros
N=1000
L=20
RC=1.0
SEED=42
REPEAT=1000          # busquedas cronometradas por punto
SEEDS_VALID="1 2 3"  # configuraciones distintas para validate_m.py
PARTICLE=30          # particula resaltada en la figura del punto 1

# Caso chico de la animacion.
N_GIF=40
RC_GIF=2.0
M_GIF=5
SEED_GIF=7

EXE=./build/CIM-TP1
[[ -x "${EXE}.exe" ]] && EXE="${EXE}.exe"

# El venv del repo si existe, si no el python del sistema.
if [[ -x venv-sds/bin/python ]]; then PY=venv-sds/bin/python; else PY=python3; fi

step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }

# ---------------------------------------------------------------- interactivo
# Lo unico que este script acepta como argumento. Necesita la configuracion, asi
# que hay que haber corrido './run_all.sh' antes al menos una vez.
#
# Los tres archivos van juntos en cada llamada. --static y --dynamic apuntan por
# defecto a la configuracion con paredes, asi que pasar solo --neighbors del caso
# periodico dibujaria las posiciones de una configuracion con las vecinas de la
# otra: el generador rechaza por solapamiento a traves del borde cuando se le
# pide --periodic, asi que con la misma semilla acepta otras particulas.
if [[ ${1:-} == interactivo ]]; then
    [[ -f data/neighbors.txt && -f data/neighbors_pbc.txt ]] \
        || { echo "faltan las vecinas en data/: corre './run_all.sh' primero" >&2; exit 1; }

    step "Visor interactivo, con paredes  (clic para elegir particula, n/p para recorrer)"
    note "cerra la ventana para pasar al caso periodico"
    "$PY" python/visualize.py --particle "$PARTICLE" --rc "$RC" --interactive \
        --static data/static.txt \
        --dynamic data/dynamic.txt \
        --neighbors data/neighbors.txt

    step "Visor interactivo, contorno periodico  (dibuja las replicas por wrap-around)"
    note "cerra la ventana para terminar"
    "$PY" python/visualize.py --particle "$PARTICLE" --rc "$RC" --interactive --periodic \
        --static data/static_pbc.txt \
        --dynamic data/dynamic_pbc.txt \
        --neighbors data/neighbors_pbc.txt
    exit 0
fi

if [[ $# -gt 0 ]]; then
    echo "uso: ./run_all.sh [interactivo]" >&2
    exit 1
fi

mkdir -p data images

# ---------------------------------------------------------------- 1. compilar
step "Compilando"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j

# ------------------------------------------- 2. configuracion de referencia
# Todo lo que sigue (figuras, fuerza bruta, CIM, comparacion) lee ESTOS archivos.
step "Configuracion con paredes  (data/static.txt, data/dynamic.txt)"
"$EXE" -N "$N" -L "$L" --rc "$RC" -M 0 --seed "$SEED" --method cim --verify

step "Configuracion con contorno periodico  (archivos *_pbc)"
"$EXE" -N "$N" -L "$L" --rc "$RC" -M 0 --seed "$SEED" --method cim --periodic --verify \
    --static-out data/static_pbc.txt \
    --dynamic-out data/dynamic_pbc.txt \
    --neighbors-out data/neighbors_pbc.txt

# ------------------------------------------------- 3. figuras y animacion
step "Punto 1: particula $PARTICLE y sus vecinas -> images/vecinas.png"
"$PY" python/visualize.py --particle "$PARTICLE" --rc "$RC" \
    --neighbors data/neighbors.txt --out images/vecinas.png

step "Traza del barrido del CIM  (caso chico)"
"$EXE" -N "$N_GIF" -L "$L" --rc "$RC_GIF" --seed "$SEED_GIF" -M "$M_GIF" \
    --method cim --trace data/trace.txt \
    --static-out data/static_gif.txt --dynamic-out data/dynamic_gif.txt \
    --neighbors-out data/neighbors_gif.txt

step "Animacion -> images/cim.gif"
"$PY" python/animate_cim.py --trace data/trace.txt --out images/cim.gif --fps 6 --stride 5

# --------------------------------------------------------- 4. validacion
step "Fuerza bruta sobre la misma configuracion -> data/nb_brute.txt"
"$EXE" --input-static data/static.txt --input-dynamic data/dynamic.txt --rc "$RC" \
    --method brute --neighbors-out data/nb_brute.txt

step "CIM sobre la misma configuracion -> data/nb_cim.txt"
"$EXE" --input-static data/static.txt --input-dynamic data/dynamic.txt --rc "$RC" \
    -M 0 --method cim --neighbors-out data/nb_cim.txt

step "CIM con listas enlazadas sobre la misma configuracion -> data/nb_cimll.txt"
"$EXE" --input-static data/static.txt --input-dynamic data/dynamic.txt --rc "$RC" \
    -M 0 --method cim-ll --neighbors-out data/nb_cimll.txt

# Ojo: las dos estructuras dan las mismas vecinas pero en distinto orden dentro
# de cada linea, porque la lista enlazada recorre cada celda en orden descendente
# de id. Un 'diff' pelado marcaria diferencias que no existen;
# compare_neighbors.py compara conjuntos, que es lo que corresponde.
step "Comparando las tres listas  (tienen que decir IDENTICAS)"
"$PY" python/compare_neighbors.py data/nb_brute.txt data/nb_cim.txt
"$PY" python/compare_neighbors.py data/nb_brute.txt data/nb_cimll.txt

step "Barrido de M contra la fuerza bruta, las dos estructuras, paredes y periodico"
"$PY" python/validate_m.py -N "$N" --seeds $SEEDS_VALID

# m_max sale de la linea 'grid: M=.. (max ..)'. Se genera a un archivo aparte
# para no pisar la configuracion de referencia.
m_max=$("$EXE" -N "$N" -L "$L" --rc "$RC" --seed "$SEED" --method none \
            --static-out data/probe_s.txt --dynamic-out data/probe_d.txt 2>&1 >/dev/null \
        | sed -n 's/.*(max \([0-9]*\)).*/\1/p')
step "Un M mayor al maximo ($m_max) tiene que ser rechazado"
if "$EXE" -N "$N" -L "$L" --rc "$RC" -M "$((m_max + 1))" --method cim \
        --static-out data/probe_s.txt --dynamic-out data/probe_d.txt \
        --neighbors-out data/probe_n.txt >/dev/null 2>&1; then
    echo "FALLO: M=$((m_max + 1)) deberia haber dado error" >&2
    exit 1
fi
note "rechazado, como corresponde"

# --------------------------------------------- 5. puntos 3 y 4 (la parte larga)
# Encodear el gif de arriba satura los nucleos y deja el procesador caliente, asi
# que el gobernador le baja la frecuencia justo cuando esto empieza a medir. Eso
# infla los primeros puntos del barrido y no los ultimos, que sesga la curva en
# vez de solo ensancharla.
step "Enfriando 15s antes de medir"
sleep 15

step "Punto 3: tiempo en funcion de M  ($REPEAT busquedas por punto)"
"$PY" python/benchmark.py --part 3 --rc "$RC" --seed "$SEED" --repeat "$REPEAT"

step "Graficando el punto 3"
# Dos figuras del mismo CSV. La del punto 3 lleva una sola estructura: es la que
# pide la catedra, y las cuatro curvas de la otra tapan lo que se quiere leer.
# La segunda es el estudio extra, y es la que imprime el M optimo porque el
# punto 4 toma uno por estructura.
"$PY" python/plot_m.py --methods cim --out images/tiempo_vs_M.png >/dev/null
note "images/tiempo_vs_M.png        (punto 3, solo vector por celda)"

# plot_m.py cierra con '-> usar --M cim=13 cim-ll=13 en el punto 4', ya en el
# formato que espera benchmark.py. El tee deja la salida completa a la vista.
m_opt=$("$PY" python/plot_m.py --out images/tiempo_vs_M_con_ll.png | tee /dev/stderr \
        | sed -n 's/^-> usar --M \(.*\) en el punto 4$/\1/p')
[[ -n $m_opt ]] || { echo "no pude leer el M optimo de plot_m.py" >&2; exit 1; }
note "images/tiempo_vs_M_con_ll.png (las dos estructuras superpuestas)"
note "M optimo: $m_opt  (entra directo al punto 4)"

step "Punto 4: tiempo en funcion de N, con $m_opt"
# $m_opt va sin comillas a proposito: son varios argumentos, uno por metodo.
# shellcheck disable=SC2086
"$PY" python/benchmark.py --part 4 --M $m_opt --rc "$RC" --seed "$SEED" --repeat "$REPEAT"

step "Graficando el punto 4"
"$PY" python/plot_n.py --methods cim --out images/tiempo_vs_N.png
note "images/tiempo_vs_N.png        (punto 4, solo vector por celda)"
"$PY" python/plot_n.py --out images/tiempo_vs_N_con_ll.png >/dev/null
note "images/tiempo_vs_N_con_ll.png (las dos estructuras superpuestas)"

# ------------------------------------------- 6. vector contra listas enlazadas
# No vuelve a medir nada: lee los CSV de arriba y los mira por el lado del
# armado, la memoria y los pedidos al allocator en vez del tiempo total.
step "Comparacion en funcion de M -> images/comparacion_vs_M.png"
"$PY" python/plot_compare.py --csv data/bench_p3.csv --x M \
    --out images/comparacion_vs_M.png

step "Comparacion en funcion de N -> images/comparacion_vs_N.png"
"$PY" python/plot_compare.py --csv data/bench_p4.csv --x N --tag "densidad fija" \
    --out images/comparacion_vs_N.png

# ---------------------------------------------------------------------- listo
step "Listo"
note "images/vecinas.png            punto 1"
note "images/cim.gif                barrido del CIM"
note "images/tiempo_vs_M.png        punto 3, solo vector por celda"
note "images/tiempo_vs_N.png        punto 4, solo vector por celda"
note "images/tiempo_vs_M_con_ll.png punto 3 con las listas enlazadas superpuestas"
note "images/tiempo_vs_N_con_ll.png punto 4 con las listas enlazadas superpuestas"
note "images/comparacion_vs_M.png   vector contra listas enlazadas, en funcion de M"
note "images/comparacion_vs_N.png   vector contra listas enlazadas, en funcion de N"
echo
note "para explorar las vecinas a mano:  ./run_all.sh interactivo"
