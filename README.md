# Proyecto-Matem-ticas-Avanzadas
Aplicación web para el procesamiento de imágenes en el dominio de la frecuencia (FFT) implementando filtros Pasa-Bajas y Pasa-Altas con Python (Flask) y NumPy

Integrantes del equipo:
Montoya Rodriguez Issac.
Rodriguez Leal Marco Cesar.
Orozco Barrientos Ana Raquel.


Proyecto de Matemáticas Avanzadas:
Aplicación web en Python (Flask) para el procesamiento de imágenes
en el dominio de la frecuencia, enfocada en la aplicación de
filtros Pasa-bajas y Pasa-altas.


REQUISITOS PREVIOS

1. Python 3.10 o superior.
   - Verificar instalación escribiendo en terminal: python --version
2. Visual Studio Code (VS Code).


ESTRUCTURA DEL PROYECTO

fft_web/
 app.py          <-- Lógica del servidor (Python/Flask/NumPy)
 README.txt      <-- Este archivo

 templates/
  index.html  <-- Interfaz de usuario (HTML)

 static/
  style.css   <-- Estilos visuales
  app.js      <-- Lógica del cliente (JavaScript)


INSTALACIÓN Y EJECUCIÓN (MÉTODO SIMPLE)


PASO 1: ABRIR EL PROYECTO
1. Abrir Visual Studio Code.
2. Ir a: File → Open Folder...
3. Seleccionar la carpeta principal "fft_web".

PASO 2: ABRIR LA TERMINAL
Presionar: Ctrl + Ñ  
(O ir al menú: Terminal → New Terminal)

PASO 3: INSTALAR LIBRERÍAS
Escribe el siguiente comando en la terminal y presiona Enter para descargar
las herramientas necesarias (Flask, NumPy y Pillow):

    pip install Flask numpy Pillow

PASO 4: EJECUTAR LA APLICACIÓN
Para iniciar el servidor, ejecuta:

    python app.py

Si todo es correcto, verás un mensaje como:
"Running on http://127.0.0.1:5000"

PASO 5: USAR LA APLICACIÓN
1. No cierres la terminal.
2. Abre tu navegador (Chrome/Edge).
3. Entra a: http://127.0.0.1:5000


GUÍA DE USO

1. Carga una imagen (PNG o JPG). Se convertirá a escala de grises automáticamente.
2. Selecciona el TIPO DE FILTRO:
   - Pasa-bajas: Para suavizar la imagen y eliminar ruido.
   - Pasa-altas: Para detectar bordes y detalles finos.
   - Comparar ambos: Para ver los efectos lado a lado.
3. Ajusta el RADIO DE CORTE:
   - Radio pequeño: Mayor efecto de filtrado.
   - Radio grande: Menor efecto (pasan más frecuencias).
4. Presiona "PROCESAR FILTRO".


SOLUCIÓN DE PROBLEMAS COMUNES

A) Error "pip no se reconoce como un comando":
   - Causa: Python no se agregó al PATH al instalarse.
   - Solución: Intenta usar "py -m pip install ..." o reinstala Python marcando "Add to PATH".

B) El navegador dice "No se puede acceder a este sitio":
   - Causa: El servidor no está corriendo o cerraste la terminal.
   - Solución: Vuelve a la terminal y ejecuta de nuevo "python app.py".


DETENER EL SERVIDOR

Para apagar la aplicación, ve a la terminal donde corre el servidor
y presiona: Ctrl + C

Link de la presentación
https://www.canva.com/design/DAG9ybQQlTE/zttzULgW8jJiLSaBF7RljQ/edit?utm_content=DAG9ybQQlTE&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton
