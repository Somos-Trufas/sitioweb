# Fuentes

## Incluidas

- `BebasNeue-Regular.ttf` — respaldo libre para el rótulo REPLAY.
- `Poppins-Bold.ttf` — tipografía secundaria del manual de marca.

Ambas bajo SIL Open Font License 1.1, que permite redistribuirlas.

## No incluida: Dharma Gothic M

La display del manual de marca es **Dharma Gothic M** (Flat-it). Es una
tipografía **comercial**, así que el `.ttf` no se versiona aquí: subirlo al
repositorio sería redistribuirla, y eso no lo cubre la licencia de escritorio.

Somos Trufas tiene la familia en Drive:

    Mi unidad / Somos Trufas / Directiva / Branding Público / Fonts / Dharma Gothic M

Para renderizar con la tipografía real, copia **`DharmaGothicM-Heavy.ttf`** a
esta carpeta. `src/replay.py` la detecta sola y lo indica al arrancar:

    [replay] Replay  (rotulo en DharmaGothicM-Heavy.ttf)

Si no está, cae en Bebas Neue y avisa igual. El resto de la transición no
cambia; solo el rótulo.

Los `.ttf` de Dharma están en `.gitignore`, así que no hay riesgo de subirlos
por accidente.
