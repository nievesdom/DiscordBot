from typing import Dict
from core.firebase_client import db

# Colecciones y documentos
SETTINGS_COLLECTION = "settings"
SETTINGS_DOC = "global"

PROPIEDADES_COLLECTION = "propiedades"
PROPIEDADES_DOC = "global"

PACKS_COLLECTION = "packs"
PACKS_DOC = "global"

MAZOS_COLLECTION = "mazos"
MAZOS_DOC = "global"

# Datos sobre los servidores
def cargar_settings() -> Dict:
    doc = db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_settings(settings: Dict) -> None:
    # merge=True para no borrar otras claves
    db.collection(SETTINGS_COLLECTION).document(SETTINGS_DOC).set(settings, merge=True)

# Cartas en propiedad del usuario
def cargar_propiedades() -> Dict:
    doc = db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_propiedades(servidor_id: str, usuario_id: str, cartas: list) -> None:
    db.collection(PROPIEDADES_COLLECTION).document(PROPIEDADES_DOC).update({
        f"{servidor_id}.{usuario_id}": cartas
    })

# Packs
def cargar_packs() -> Dict:
    doc = db.collection(PACKS_COLLECTION).document(PACKS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_packs(packs: Dict) -> None:
    db.collection(PACKS_COLLECTION).document(PACKS_DOC).set(packs, merge=True)

# Backup de settings
def backup_settings(settings: Dict) -> None:
    import datetime
    timestamp = datetime.datetime.now().isoformat()
    db.collection("settings_backup").document(timestamp).set(settings)
    
# Mazos
def cargar_mazos() -> Dict:
    doc = db.collection(MAZOS_COLLECTION).document(MAZOS_DOC).get()
    return doc.to_dict() if doc.exists else {}

def guardar_mazos(mazos: Dict) -> None:
    db.collection(MAZOS_COLLECTION).document(MAZOS_DOC).set(mazos, merge=True)
