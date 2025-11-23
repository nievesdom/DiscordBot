from typing import Dict
from core.firebase_client import db

# Colecciones y documentos
SETTINGS_COLLECTION = "settings"
SETTINGS_DOC = "global"

PROPIEDADES_COLLECTION = "propiedades"
PROPIEDADES_DOC = "global"

PACKS_COLLECTION = "packs"
PACKS_DOC = "global"

def cargar_settings() -> Dict:
    doc = db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_settings(settings: Dict) -> None:
    # ✅ merge=True para no borrar otras claves
    db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).set(settings, merge=True)

def cargar_propiedades() -> Dict:
    doc = db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_propiedades(propiedades: Dict) -> None:
    # ✅ merge=True para no borrar otras claves
    db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).set(propiedades, merge=True)

# 🔥 Nuevo: packs
def cargar_packs() -> Dict:
    doc = db.collection(PACKS_COLLECTION).document(PACKS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_packs(packs: Dict) -> None:
    # ✅ merge=True para no borrar otras claves
    db.collection(PACKS_COLLECTION).document(PACKS_DOC).set(packs, merge=True)

