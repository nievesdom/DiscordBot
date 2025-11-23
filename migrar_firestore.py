import json
from core.firebase_client import db  # usa tu inicialización de Firebase

# Rutas a tus JSON locales
SETTINGS_FILE = "settings.json"
PROPIEDADES_FILE = "propiedades.json"

def migrar_settings():
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    db.collection("settings").document("global").set(data)
    print("[OK] Settings migrados a Firestore.")

def migrar_propiedades():
    with open(PROPIEDADES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    db.collection("propiedades").document("global").set(data)
    print("[OK] Propiedades migradas a Firestore.")

if __name__ == "__main__":
    migrar_settings()
    migrar_propiedades()
