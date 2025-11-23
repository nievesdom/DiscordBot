# core/firebase_storage.py
from typing import Dict
from core.firebase_client import db

# Colecciones y documentos
SETTINGS_COLLECTION = "settings"
SETTINGS_DOC = "global"

PROPIEDADES_COLLECTION = "propiedades"
PROPIEDADES_DOC = "global"

def cargar_settings() -> Dict:
    doc = db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_settings(settings: Dict) -> None:
    db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).set(settings)

def cargar_propiedades() -> Dict:
    doc = db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_propiedades(propiedades: Dict) -> None:
    db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).set(propiedades)
