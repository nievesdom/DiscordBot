# Importamos Flask y la función send_from_directory para servir archivos estáticos
from flask import Flask, send_from_directory
import os
import threading

# Creamos la aplicación Flask
app = Flask(__name__)

# Definimos la carpeta donde se encuentran las imágenes
CARPETA_IMAGENES = os.path.join(os.getcwd(), "cartas")

# Ruta principal del servidor
@app.route("/")
def home():
    # Devuelve un mensaje simple para comprobar que el servidor funciona
    return "Servidor Flask funcionando."

# Ruta para servir imágenes desde la carpeta "cartas"
# Ejemplo: http://localhost:8080/cartas/imagen.png
@app.route("/cartas/<nombre>")
def servir_imagen(nombre):
    # Busca y devuelve el archivo solicitado dentro de la carpeta de imágenes
    return send_from_directory(CARPETA_IMAGENES, nombre)

# Función para iniciar el servidor Flask en un hilo separado
def iniciar_servidor():
    # Obtiene el puerto desde la variable de entorno PORT, o usa 8080 por defecto
    port = int(os.environ.get("PORT", 8080))
    print(f"Servidor Flask iniciado en http://localhost:{port}")
    # Ejecuta Flask en un hilo paralelo para no bloquear la ejecución principal
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

# Punto de entrada del script
if __name__ == "__main__":
    iniciar_servidor()
