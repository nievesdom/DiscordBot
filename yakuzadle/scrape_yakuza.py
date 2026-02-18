import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
import os
import re
from io import BytesIO

# -----------------------------
# Firestore
# -----------------------------
db = firestore.Client()

# -----------------------------
# Utilidades
# -----------------------------

def clean_text(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()

def extract_list(section):
    """Extrae listas <li> o texto simple."""
    if section is None:
        return None
    lis = section.find_all("li")
    if lis:
        return [clean_text(li.get_text()) for li in lis]
    return [clean_text(section.get_text())]

def get_section(soup, key):
    """Busca un bloque con data-source="key"."""
    return soup.find("div", {"data-source": key})

# -----------------------------
# Descarga imágenes del panel superior
# -----------------------------

def download_images(soup, personaje):
    img_folder = "img_yakuzadle"
    os.makedirs(img_folder, exist_ok=True)

    # Todas las imágenes del infobox superior
    infobox = soup.find("aside", {"class": "portable-infobox"})
    if not infobox:
        print("⚠ No se encontró infobox para imágenes")
        return

    images = infobox.find_all("img")

    for img in images:
        url = img.get("src")
        if not url:
            continue

        # Nombre del juego: viene en el atributo alt
        game = img.get("alt") or "Unknown"
        game = re.sub(r"[^A-Za-z0-9]+", "", game)

        filename = f"{personaje}_{game}.png"
        filepath = os.path.join(img_folder, filename)

        try:
            img_data = requests.get(url).content
            with open(filepath, "wb") as f:
                f.write(img_data)
            print(f"📥 Imagen descargada: {filename}")
        except Exception as e:
            print(f"❌ Error descargando {url}: {e}")

# -----------------------------
# Scraping principal
# -----------------------------

def scrape_personaje(nombre):
    url_name = nombre.replace(" ", "_")
    url = f"https://yakuza.fandom.com/wiki/{url_name}"

    print(f"\n🔎 Procesando: {nombre} → {url}")

    r = requests.get(url)
    if r.status_code != 200:
        print(f"❌ No se pudo acceder a la página de {nombre}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    # Extraer datos
    data = {
        "name": nombre,
        "aliases": extract_list(get_section(soup, "aliases")),
        "nicknames": extract_list(get_section(soup, "nicknames")),
        "arena_names": extract_list(get_section(soup, "arena_names")),
        "date_of_birth": clean_text(get_section(soup, "date_of_birth").get_text()) if get_section(soup, "date_of_birth") else None,
        "place_of_birth": clean_text(get_section(soup, "place_of_birth").get_text()) if get_section(soup, "place_of_birth") else None,
        "nationality": clean_text(get_section(soup, "nationality").get_text()) if get_section(soup, "nationality") else None,
        "height": clean_text(get_section(soup, "height").get_text()) if get_section(soup, "height") else None,
        "blood_type": clean_text(get_section(soup, "blood_type").get_text()) if get_section(soup, "blood_type") else None,
        "affiliation": extract_list(get_section(soup, "affiliation")),
        "appears_in": extract_list(get_section(soup, "appears_in")),
    }

    # Guardar en Firestore (crea o actualiza)
    db.collection("personajes").document(nombre).set(data, merge=True)
    print(f"✔ Guardado/actualizado en Firestore: {nombre}")

    # Descargar imágenes
    download_images(soup, nombre.replace(" ", ""))

# -----------------------------
# Main
# -----------------------------

def main():
    with open("personajes.txt", "r", encoding="utf-8") as f:
        personajes = [line.strip() for line in f if line.strip()]

    for p in personajes:
        scrape_personaje(p)

if __name__ == "__main__":
    main()
