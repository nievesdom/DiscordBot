from flask import Flask, send_from_directory
import os
import threading

app = Flask(__name__)

CARPETA_IMAGENES = os.path.join(os.getcwd(), "cartas")

@app.route("/")
def home():
    return "Servidor Flask funcionando."

@app.route("/cartas/<nombre>")
def servir_imagen(nombre):
    return send_from_directory(CARPETA_IMAGENES, nombre)

def iniciar_servidor():
    port = int(os.environ.get("PORT", 8080))
    print(f"Servidor Flask iniciado en http://localhost:{port}")
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

if __name__ == "__main__":
    iniciar_servidor()
    input("Presiona ENTER para detener el servidor...\n")
