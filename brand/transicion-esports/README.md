# Transiciones esports — Somos Trufas

Tres stingers de **1,000 s exacto** (60 frames a 60 fps), 1920×1080 (16:9), en
WebM VP9 **con canal alpha**. Listos para OBS / vMix / Streamlabs.

| Archivo | Estilo | Para qué |
|---|---|---|
| `transicion-barrido-1080p60.webm` | Bandas diagonales | Transición general entre escenas |
| `transicion-iris-1080p60.webm` | Iris de mascota | Transición general, alternativa a la anterior |
| `transicion-replay-1080p60.webm` | Replay | Entrar (y salir) de una repetición |

## Punto de corte

Cada transición tapa la pantalla por completo durante una ventana. El cambio de
escena tiene que caer dentro o se verá el corte.

| Estilo | Ventana 100 % opaca | Punto de transición |
|---|---|---|
| Barrido | 0,175 – 0,775 s | **500 ms** |
| Iris | 0,208 – 0,692 s | **500 ms** |
| Replay | 0,208 – 0,692 s | **500 ms** |

En **OBS**: Transiciones → *Stinger* → el `.webm` → Punto de transición 500 ms.

## Los tres estilos

**Barrido** — Tres bandas a 18° cruzan de derecha a izquierda, la mascota golpea
en el centro con sobre-escala y desenfoque, el logotipo *TRUFAS* se revela desde
detrás de ella, y las bandas salen en cascada por la izquierda. El logo acompaña
la salida con parallax y se recorta contra el borde de la banda.

**Iris** — La silueta de la propia mascota crece desde un punto en el centro
hasta tragarse la pantalla, y después se abre como un agujero con la misma forma
para revelar la escena nueva. El mecanismo es radial en vez de lineal: es lo que
lo diferencia del barrido aunque comparta paleta y lockup. Las tres capas de
color entran escalonadas, así que la silueta deja un reborde amarillo y naranja
al crecer. A tamaño grande la silueta lee como una forma orgánica más que como
la mascota; se reconoce durante los primeros seis o siete frames.

**Replay** — Dos mitades convergen sobre la diagonal de marca y se juntan sobre
el rótulo *REPLAY*, con estética de cinta: líneas de barrido, chevrones de
rebobinado, saltos horizontales de imagen y un barrido de luz. Después se separan
para dejar ver la repetición. El filo brillante del corte se apaga al juntarse
las mitades —si no, la línea parte el rótulo por la mitad— y vuelve al separarse.

## Marca

Del *Manual de Identidad TRUFAS* (agosto 2025):

| Color | Hex |
|---|---|
| Mikado Yellow | `#FFC621` |
| Liver | `#583F37` |
| Acento | `#FF9A21` |
| Fondo | `#452B22` |

El logotipo *TRUFAS* y el lockup de `src/assets/` se extrajeron del propio manual
(página 7, versión negativa) desmultiplicando el alpha sobre el panel sólido: son
la curva original dibujada a mano, no una recreación tipográfica.

El rótulo *REPLAY* va en **Dharma Gothic M Heavy**, la display del manual.

Es una tipografía **comercial**, así que el `.ttf` no se versiona: subirlo al
repositorio sería redistribuirla. Está en el Drive de la organización
(`Branding Público / Fonts / Dharma Gothic M`); para regenerar el replay con la
tipografía real hay que copiar `DharmaGothicM-Heavy.ttf` a `src/fonts/`. Si
falta, el render cae en Bebas Neue —el sustituto libre habitual, sí incluido— y
avisa de cuál está usando:

    [replay] Replay  (rotulo en DharmaGothicM-Heavy.ttf)

Ver `src/fonts/README.md`.

## Regenerar

```bash
pip install pillow numpy        # requiere además ffmpeg
cd src
python3 build.py                # los tres  (~5 min)
python3 build.py replay         # solo uno
python3 build.py iris --preview 10,24,36
```

`build.py` comprueba en cada render que la ventana opaca contiene el punto de
corte y que el alpha sobrevivió a la codificación.

`SS=3` es el supersampling por defecto; `SS=1 python3 build.py` acelera las
pruebas a costa del antialiasing en las diagonales.

### Estructura

    src/common.py    paleta, easing, geometría, assets, pipeline y codificación
    src/sweep.py     estilo 1
    src/iris.py      estilo 2
    src/replay.py    estilo 3
    src/build.py     CLI

Un estilo es un módulo que expone `NAME`, `TITLE`, `CUT_POINT` y
`frame(f) -> RGBA`. Añadir uno nuevo es escribir ese módulo y sumarlo a `STYLES`.

### Nota sobre el alpha en WebM

ffmpeg guarda el alpha de WebM en un stream aparte y **el decoder nativo lo
ignora**. Para comprobarlo hay que pedir el decoder explícitamente:

```bash
ffmpeg -c:v libvpx-vp9 -i transicion-replay-1080p60.webm -vframes 1 -pix_fmt rgba chk.png
```

Sin `-c:v libvpx-vp9` el frame sale opaco y parece que el alpha se perdió.
