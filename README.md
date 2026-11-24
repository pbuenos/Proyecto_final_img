# Analizador de hojas

Aplicacion web para analizar fotos de hojas y una interfaz de linea de comandos para procesar imagenes locales. Usa Pillow para abrir/guardar archivos y OpenCV/NumPy para segmentar y medir.

## Requisitos

- Python 3.10 o superior
- Pillow, OpenCV, NumPy, FastAPI y Uvicorn (instalables desde `requirements.txt`)

## Instalacion y uso web

Desde la carpeta `tp-final-analizador-hojas`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --web
```

Abrir <http://127.0.0.1:8000>. La documentacion de la API esta en <http://127.0.0.1:8000/docs>. Para cambiar el puerto, usar `python main.py --web --port 8765`.

## Uso por consola

En modo consola, la ruta de imagen es obligatoria. Se pueden indicar varias:

```powershell
python main.py fotos\hoja1.jpg fotos\hoja2.png
python main.py fotos\hoja1.jpg --salida resultados --hue-min 25 --hue-max 100 --kernel-size 5
python main.py --help
```

Cada imagen procesada por CLI genera una subcarpeta en `resultados/`, con archivos como `hoja1_mascara_hsv.png`, `hoja1_mascara_limpia.png`, `hoja1_contorno.png` y `hoja1_hoja_aislada.png`. En la web, las etapas se devuelven como vistas previas descargables (maximo 640 px por lado); el servidor no intenta guardarlas en disco, porque el almacenamiento de una funcion serverless no es persistente.

## Tecnicas y efecto

1. **Conversion RGB a HSV y mascara por color:** separar tono, saturacion y brillo permite seleccionar los tonos verdes mediante rangos ajustables. Los valores iniciales sirven como punto de partida, no como detector universal.
2. **Apertura y cierre morfologicos:** la apertura elimina manchas pequenas y el cierre rellena huecos pequenos; el kernel controla la intensidad de ambas operaciones.
3. **Contornos externos:** se elige la region mayor que supera un area minima. Se dibujan su contorno y caja delimitadora.
4. **Medicion geometrica:** se calculan area del contorno, perimetro, ancho, alto y proporcion ancho/alto. Son medidas en pixeles, no dimensiones fisicas.

Pillow se ocupa de decodificar, orientar segun EXIF, convertir a RGB y escribir los PNG. OpenCV realiza la conversion HSV, umbralizacion, morfologia y analisis de contornos.

## Limitaciones y pruebas recomendadas

El analisis inicial esta pensado para una hoja verde sobre un fondo simple que contraste y con iluminacion pareja. Un fondo verde puede confundirse con la hoja, y una hoja amarilla o seca puede quedar fuera del rango. Ajusta los controles HSV y compara las etapas; no interpretes pixeles como centimetros sin incluir una referencia de escala en la foto.

El proyecto incluye una imagen sintetica en `samples/` para verificar el flujo de forma reproducible. Para la presentacion, agreguen fotos propias de hojas con distintos fondos y comparen resultados. El CLI guarda las imagenes completas en `results/`; en la web, cada etapa puede descargarse desde el navegador.

## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Publicar en Vercel

El proyecto incluye `.python-version` (Python 3.12) y `pyproject.toml` con la entrada FastAPI `backend.app.main:app`. Vercel detecta FastAPI y sirve los archivos estaticos del frontend desde `frontend/`.

1. Importa el repositorio `Proyecto_final_img` desde GitHub. Esta carpeta ya es la raiz del proyecto, asi que deja **Root Directory** en `./`; si la subis a otro repo dentro de una subcarpeta, selecciona esa carpeta como raiz.
2. En Vercel, importa ese repositorio y deja que detecte el proyecto Python/FastAPI. No hace falta configurar un comando de build ni variables secretas.
3. Despues del deploy, abre la URL y carga desde tu computadora `samples/hoja_sintetica.png`; luego prueba con fotos reales.

La interfaz web limita las imagenes a 10 MB en total y 25 megapixeles por foto, y devuelve vistas previas comprimidas para no depender de escribir archivos en el disco efimero de Vercel. El modo CLI sigue guardando resultados de resolucion completa en la computadora local; no se ejecuta en Vercel.

## Integrantes

- Completar con los nombres del equipo.
