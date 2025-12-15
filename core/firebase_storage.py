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


INVENTARIO_COLLECTION = "inventario"

def agregar_cartas_inventario(server_id: str, user_id: str, nuevas_cartas: list[str]) -> None:
    """
    Añade cartas al inventario del usuario en inventario/{server_id}.
    Crea el documento si no existe. No reescribe todo el documento.
    """
    server_ref = db.collection(INVENTARIO_COLLECTION).document(server_id)

    doc = server_ref.get()
    data = doc.to_dict() or {}

    cartas_usuario = data.get(user_id, [])

    # Simplemente añadimos (permitiendo duplicados si quieres múltiples copias)
    cartas_actualizadas = cartas_usuario + nuevas_cartas

    server_ref.set(
        {user_id: cartas_actualizadas},
        merge=True
    )
    
def quitar_cartas_inventario(server_id: str, user_id: str, cartas_a_quitar: list[str]) -> bool:
    """
    Quita UNA copia por cada ID en cartas_a_quitar del inventario del usuario.
    Devuelve True si se modificó algo, False si no había cartas que quitar.
    """
    server_ref = db.collection(INVENTARIO_COLLECTION).document(server_id)

    doc = server_ref.get()
    data = doc.to_dict() or {}

    cartas_usuario = data.get(user_id, [])

    if not cartas_usuario:
        return False

    # Trabajamos con strings normalizadas
    cartas_usuario = [str(c) for c in cartas_usuario]
    objetivos = [str(c) for c in cartas_a_quitar]

    changed = False

    for objetivo in objetivos:
        if objetivo in cartas_usuario:
            cartas_usuario.remove(objetivo)  # quita solo UNA copia
            changed = True

    if not changed:
        return False

    # Actualizar solo el campo del usuario
    server_ref.set(
        {user_id: cartas_usuario},
        merge=True
    )
    return True

def cargar_inventario_usuario(server_id: str, user_id: str) -> list[str]:
    """
    Devuelve la lista de cartas del usuario.
    Si no existe el servidor o el usuario, devuelve [].
    """
    doc = db.collection(INVENTARIO_COLLECTION).document(server_id).get()
    data = doc.to_dict() or {}
    return data.get(user_id, [])

    