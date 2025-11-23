# core/firebase_client.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def _init_app():
    # Leer el contenido del JSON desde la variable de entorno
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if not creds_json:
        raise RuntimeError("FIREBASE_CREDENTIALS_JSON no está definida en Render.")

    # Convertir el texto JSON en dict de Python
    data = json.loads(creds_json)

    # Crear credenciales a partir del dict
    cred = credentials.Certificate(data)

    # Inicializar la app una sola vez
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)

    return firestore.client()

# Cliente global de Firestore
db = _init_app()
