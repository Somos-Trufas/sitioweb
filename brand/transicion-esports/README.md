# Transición esports — Somos Trufas

Stinger de **1,000 s exacto** (60 frames a 60 fps), 1920×1080 (16:9), con canal alpha.

| Archivo | Uso |
|---|---|
| `transicion-somos-trufas-1080p60.webm` | El stinger. VP9 con alpha, 3,2 MB. Para OBS / vMix / Streamlabs. |
| `transicion-somos-trufas-DEMO-1080p60.mp4` | Vista previa de 2 s: escena A → transición → escena B. |

El master **ProRes 4444 con alpha** (~98 MB) no se versiona por peso. Se regenera
con `src/encode.py` y es el que conviene pasarle a un editor de video.

## Punto de corte

La pantalla queda **100 % cubierta entre 0,175 s y 0,775 s**. El cambio de escena
tiene que caer dentro de esa ventana o se verá el corte.

- **OBS** → Transiciones → *Stinger* → archivo `.webm` → **Punto de transición: 500 ms**

Eso deja 325 ms de margen antes y 275 ms después.

## Anatomía

| Tiempo | Qué pasa |
|---|---|
| 0,00–0,10 s | Esquirlas diagonales cruzan la pantalla de derecha a izquierda |
| 0,00–0,34 s | Tres bandas a 18° barren en cascada: amarillo → naranja → marrón |
| 0,24–0,40 s | La mascota entra con sobre-escala, giro y desenfoque de movimiento |
| 0,29–0,45 s | El logotipo *TRUFAS* se revela con un barrido desde detrás de la mascota |
| **0,385 s** | Impacto: destello, onda de choque, ráfaga radial y aberración cromática |
| 0,40–0,60 s | Sostenido sobre el lockup oficial |
| 0,60–0,96 s | Las bandas salen hacia la izquierda en cascada y revelan la escena nueva |

El logo acompaña la salida con parallax (34 % de la velocidad de la banda) y se
recorta contra el borde de la banda marrón, no se desvanece.

## Marca

Todo sale del *Manual de Identidad TRUFAS* (agosto 2025):

| Color | Hex |
|---|---|
| Mikado Yellow | `#FFC621` |
| Liver | `#583F37` |
| Acento | `#FF9A21` |
| Fondo | `#452B22` |

El logotipo *TRUFAS* y el lockup de `src/assets/` **se extrajeron del propio manual**
(página 7, versión negativa) desmultiplicando el alpha sobre el panel sólido. Son la
curva original dibujada a mano, no una recreación con tipografía — la display de marca
es Dharma Gothic M, que es comercial y no reproduce esas terminaciones redondeadas.

La mascota se usa a todo color: su contorno amarillo es justamente lo que la hace
legible sobre el fondo oscuro.

## Regenerar

```bash
pip install pillow numpy        # requiere además ffmpeg
cd src
python3 render.py               # 60 PNG RGBA en out/frames  (~90 s)
python3 encode.py               # webm + mov + mp4 demo, y verifica el alpha
```

`SS=3` es el supersampling por defecto; `SS=1 python3 render.py` acelera las pruebas
a costa del antialiasing en las diagonales.

Las escenas de la demo usan Bebas Neue y Poppins (ambas OFL, no versionadas); si no
están, cae a la tipografía por defecto sin romper nada.

### Nota sobre el alpha en WebM

ffmpeg guarda el alpha de WebM en un stream aparte y **el decoder nativo lo ignora**.
Para comprobarlo hay que pedir el decoder explícitamente:

```bash
ffmpeg -c:v libvpx-vp9 -i transicion-somos-trufas-1080p60.webm -vframes 1 -pix_fmt rgba chk.png
```

Sin `-c:v libvpx-vp9` el frame sale opaco y parece que el alpha se perdió. No es así.
