import requests
from bs4 import BeautifulSoup
from google.cloud import firestore
from google.oauth2 import service_account
import os
import re
import urllib.parse

# -----------------------------
# Firestore
# -----------------------------
credentials = service_account.Credentials.from_service_account_file(
    "credentials.json"
)

db = firestore.Client(
    credentials=credentials,
    project="yamaibot"
)

# -----------------------------
# Headers
# -----------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# -----------------------------
# Limpieza
# -----------------------------

def clean_text(text):
    if not text:
        return None
    return re.sub(r"\s+", " ", text).strip()

def remove_refs(text):
    return re.sub(r"\[[^\]]*\]", "", text)

def clean_parentheses(text, field=None):
    def repl(m):
        content = m.group(1)
        if "formerly" in content.lower():
            return f"({content})"
        if field == "height":
            return f"({content})"
        return ""
    return re.sub(r"\((.*?)\)", repl, text)

def clean_scalar(section, field=None):
    if section is None:
        return "Unknown"

    local = BeautifulSoup(str(section), "html.parser")

    for sup in local.find_all("sup"):
        sup.decompose()

    h = local.find(["h1", "h2", "h3", "h4"])
    if h:
        h.decompose()

    text = local.get_text(" ", strip=True)
    text = remove_refs(text)
    text = clean_parentheses(text, field)
    text = clean_text(text)

    if not text or text in ("-", "—"):
        return "Unknown"
    return text

def clean_list_item(text):
    text = remove_refs(text)
    text = clean_parentheses(text)
    text = clean_text(text)
    if not text or text in ("-", "—"):
        return None
    return text

def extract_list(section):
    if section is None:
        return None

    lis = section.find_all("li")
    if lis:
        items = []
        for li in lis:
            val = clean_list_item(li.get_text())
            if val:
                items.append(val)
        return items or None

    val = clean_list_item(section.get_text())
    return [val] if val else None

def extract_affiliations(section):
    if section is None:
        return None

    lis = section.find_all("li")
    if not lis:
        val = clean_list_item(section.get_text())
        return [val] if val else None

    afiliaciones = []

    for li in lis:
        raw = li.get_text(" ", strip=True)
        raw = remove_refs(raw)

        parts = re.split(r"\)\s+", raw)

        for p in parts:
            p = p.strip()
            if not p:
                continue

            if "(formerly" in p and not p.endswith(")"):
                p = p + ")"

            val = clean_list_item(p)
            if val and val not in afiliaciones:
                afiliaciones.append(val)

    return afiliaciones or None

def get_section(soup, key):
    return soup.find("div", {"data-source": key})

# -----------------------------
# Fighting Style (data-source="fighting_styles")
# -----------------------------

def extract_fighting_style(soup):
    section = get_section(soup, "fighting_styles")
    if section is None:
        return None

    lis = section.find_all("li")
    styles = []

    for li in lis:
        text = li.get_text(" ", strip=True)
        text = remove_refs(text)
        text = clean_text(text)
        if text and text not in styles:
            styles.append(text)

    return styles or None

# -----------------------------
# Normalización de appears_in (separar juegos)
# -----------------------------

def normalize_appears_in(items):
    if not items:
        return None

    final = []

    for item in items:
        if not item:
            continue

        # 1. Separar por "/"
        parts = item.split("/")

        for p in parts:
            p = p.replace("_", " ")

            # 2. Separar por " and "
            if " and " in p:
                sub = p.split(" and ")
                for s in sub:
                    s = clean_text(s)
                    if s and s not in final:
                        final.append(s)
            else:
                p = clean_text(p)
                if p and p not in final:
                    final.append(p)

    return final or None

# -----------------------------
# Nombre japonés
# -----------------------------

def get_japanese_name(soup):
    infobox = soup.find("aside", {"class": "portable-infobox"})
    if not infobox:
        return "Unknown"

    jp = infobox.find("span", {"lang": "ja"})
    if jp:
        val = clean_list_item(jp.get_text())
        return val or "Unknown"

    text = infobox.get_text(separator="\n")
    for line in text.split("\n"):
        if re.search(r"[\u3040-\u30FF\u4E00-\u9FFF]", line):
            val = clean_list_item(line)
            return val or "Unknown"

    return "Unknown"

# -----------------------------
# 1. Buscar título real
# -----------------------------

def buscar_titulo(nombre):
    termino = urllib.parse.quote(nombre)
    api_url = (
        f"https://yakuza.fandom.com/api.php?"
        f"action=query&list=search&srsearch={termino}&format=json"
    )

    r = requests.get(api_url, headers=HEADERS)
    data = r.json()

    if not data["query"]["search"]:
        print(f"❌ No se encontró ninguna página para: {nombre}")
        return None

    return data["query"]["search"][0]["title"]

# -----------------------------
# 2. Obtener HTML real con action=parse
# -----------------------------

def obtener_html(titulo):
    api_url = (
        f"https://yakuza.fandom.com/api.php?"
        f"action=parse&page={urllib.parse.quote(titulo)}&format=json"
    )

    r = requests.get(api_url, headers=HEADERS)
    data = r.json()

    if "parse" not in data:
        return None

    return data["parse"]["text"]["*"]

# -----------------------------
# 3. Descargar imágenes
# -----------------------------

def download_images(soup, personaje):
    img_folder = "img_yakuzadle"
    os.makedirs(img_folder, exist_ok=True)

    infobox = soup.find("aside", {"class": "portable-infobox"})
    if not infobox:
        print("⚠ No se encontró infobox para imágenes")
        return

    images = infobox.find_all("img")

    for img in images:
        url = img.get("src")
        if not url:
            continue

        game = img.get("alt") or "Unknown"
        game = re.sub(r"[^A-Za-z0-9]+", "", game)

        filename = f"{personaje}_{game}.png"
        filepath = os.path.join(img_folder, filename)

        if os.path.exists(filepath):
            continue

        try:
            img_data = requests.get(url, headers=HEADERS).content
            with open(filepath, "wb") as f:
                f.write(img_data)
            print(f"📥 Imagen descargada: {filename}")
        except Exception as e:
            print(f"❌ Error descargando {url}: {e}")

# -----------------------------
# 4. Scraping principal
# -----------------------------

def scrape_personaje(nombre):
    print(f"\n🔎 Buscando página para: {nombre}")

    titulo = buscar_titulo(nombre)
    if not titulo:
        return

    print(f"➡ Página encontrada: {titulo}")

    html = obtener_html(titulo)
    if not html:
        print(f"❌ No se pudo obtener el HTML de {titulo}")
        return

    soup = BeautifulSoup(html, "html.parser")

    appears_raw = extract_list(get_section(soup, "appears_in"))
    appears_clean = normalize_appears_in(appears_raw)

    data = {
        "name": nombre,
        "japanese_name": get_japanese_name(soup),
        "aliases": extract_list(get_section(soup, "aliases")),
        "nicknames": extract_list(get_section(soup, "nicknames")),
        "arena_names": extract_list(get_section(soup, "arena_names")),
        "date_of_birth": clean_scalar(get_section(soup, "date_of_birth")),
        "place_of_birth": clean_scalar(get_section(soup, "place_of_birth")),
        "nationality": clean_scalar(get_section(soup, "nationality")),
        "height": clean_scalar(get_section(soup, "height"), field="height"),
        "blood_type": clean_scalar(get_section(soup, "blood_type")),
        "affiliation": extract_affiliations(get_section(soup, "affiliation")),
        "appears_in": appears_clean,
        "fighting_style": extract_fighting_style(soup),
    }

    db.collection("personajes").document(nombre).set(data, merge=True)
    print(f"✔ Guardado/actualizado en Firestore: {nombre}")

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
