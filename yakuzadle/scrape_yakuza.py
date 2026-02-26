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

def remove_wp(text):
    if not text:
        return text
    text = re.sub(r"\s*WP\b", "", text)
    text = re.sub(r"\(\s*WP\s*\)", "", text)
    return clean_text(text)

def clean_parentheses(text, field=None):
    def repl(m):
        content = m.group(1).strip()
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
    text = remove_wp(text)
    text = clean_parentheses(text, field)
    text = clean_text(text)

    if not text or text in ("-", "—"):
        return "Unknown"
    return text

def strip_field_name(text, field_name):
    if not text:
        return text
    pattern = rf"^{field_name}\s*[:\-–]?\s*"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    return text

def clean_list_item(text, field_name=None):
    text = remove_refs(text)
    text = remove_wp(text)
    if field_name:
        text = strip_field_name(text, field_name)
    text = clean_parentheses(text)
    text = clean_text(text)
    if not text or text in ("-", "—"):
        return None
    return text

# -----------------------------
# APPEARS IN — FILTRO ANTES DE LIMPIAR
# -----------------------------

APPEARS_EXCLUDE = [
    "mentioned only",
    "mentioned",
    "flashback",
    "dlc"
]

def extract_list(section, field_name=None):
    if section is None:
        return None

    lis = section.find_all("li")
    items = []

    for li in lis:
        raw = li.get_text(" ", strip=True)
        raw_low = raw.lower()

        # FILTRO ANTES DE LIMPIAR PARÉNTESIS
        if any(tag in raw_low for tag in APPEARS_EXCLUDE):
            continue

        val = clean_list_item(raw, field_name)
        if val:
            items.append(val)

    if items:
        return items

    # Caso sin <li>
    raw = section.get_text(" ", strip=True)
    raw_low = raw.lower()

    if any(tag in raw_low for tag in APPEARS_EXCLUDE):
        return None

    val = clean_list_item(raw, field_name)
    return [val] if val else None

# -----------------------------
# Affiliations
# -----------------------------

def extract_affiliations(section):
    if section is None:
        return None

    afiliaciones = []
    lis = section.find_all("li")

    for li in lis:
        a = li.find("a", recursive=False)
        if a:
            text = a.get_text(strip=True)
        else:
            direct = li.find(text=True, recursive=False)
            text = direct.strip() if direct else ""

        text = remove_refs(text)
        text = remove_wp(text)
        text = strip_field_name(text, "Affiliation")
        text = clean_text(text)

        if not text or text.lower() == "(formerly)":
            continue

        if text not in afiliaciones:
            afiliaciones.append(text)

    return afiliaciones or None

def get_section(soup, key):
    return soup.find("div", {"data-source": key})

# -----------------------------
# Fighting Style
# -----------------------------

def extract_fighting_style(soup):
    section = get_section(soup, "fighting_styles")
    if section is None:
        return None

    lis = section.find_all("li")
    styles = []

    for li in lis:
        raw = li.get_text(" ", strip=True)
        raw = remove_refs(raw)
        raw = remove_wp(raw)
        raw = strip_field_name(raw, "Fighting Style")

        parts = [clean_text(p) for p in raw.split("+")]

        parentheses = []
        for p in parts:
            m = re.search(r"\((.*?)\)", p)
            parentheses.append(m.group(1).strip() if m else None)

        for i in range(len(parts) - 2, -1, -1):
            if parentheses[i] is None and parentheses[i + 1] is not None:
                parentheses[i] = parentheses[i + 1]

        for p, par in zip(parts, parentheses):
            p = re.sub(r"\(.*?\)", "", p).strip()
            if par:
                p = f"{p} ({par})"
            if p:
                p = p[0].upper() + p[1:]
            if p and p not in styles:
                styles.append(p)

    return styles or None

# -----------------------------
# Occupation
# -----------------------------

def extract_occupation(soup):
    for key in ["occupations", "occupation"]:
        section = get_section(soup, key)
        if section:
            lis = section.find_all("li")
            occs = []
            for li in lis:
                text = clean_list_item(li.get_text(), "Occupation")
                if text and text not in occs:
                    occs.append(text)
            if occs:
                return occs

    section = get_section(soup, "associations")
    if section:
        lis = section.find_all("li")
        occs = []
        for li in lis:
            text = li.get_text(" ", strip=True)
            text = remove_refs(text)
            text = remove_wp(text)
            if text.lower().startswith("occupation"):
                parts = re.split(r"[:\-–]", text, maxsplit=1)
                if len(parts) == 2:
                    occ = clean_text(parts[1])
                    if occ and occ not in occs:
                        occs.append(occ)
        if occs:
            return occs

    return None

# -----------------------------
# Nationality + Heritage
# -----------------------------

def normalize_ethnic_field(value):
    if not value or value == "Unknown":
        return None
    parts = [clean_text(p) for p in value.split("/") if clean_text(p)]
    return parts if parts else None

def extract_nationality_and_heritage(soup):
    nat_raw = clean_scalar(get_section(soup, "nationality"))
    her_raw = clean_scalar(get_section(soup, "heritage"))

    nat_list = normalize_ethnic_field(nat_raw)
    her_list = normalize_ethnic_field(her_raw)

    if not nat_list and not her_list:
        return None

    combined = []
    if nat_list:
        combined.extend(nat_list)
    if her_list:
        combined.extend(her_list)

    final = []
    for x in combined:
        if x not in final:
            final.append(x)

    return final or None

# -----------------------------
# Appears In — normalización final
# -----------------------------

def normalize_appears_in(items):
    if not items:
        return None

    final = []

    for item in items:
        parts = item.split("/")
        for p in parts:
            p = clean_text(p.replace("_", " "))
            if p and p not in final:
                final.append(p)

    return final or None

# -----------------------------
# Actors
# -----------------------------

def extract_actors(soup):
    actors = {}

    for div in soup.find_all("div", {"data-source": True}):
        key = div["data-source"]
        if not key.endswith("voiced_by"):
            continue

        lang = div.find("h3")
        if not lang:
            continue

        lang_name = clean_text(lang.get_text())
        actors[lang_name] = []

        value = div.find("div", class_="pi-data-value")
        if not value:
            continue

        lis = value.find_all("li")
        if lis:
            for li in lis:
                text = li.get_text()
                text = remove_refs(text)
                text = remove_wp(text)
                text = clean_text(text)
                if text:
                    actors[lang_name].append(text)
        else:
            text = value.get_text()
            text = remove_refs(text)
            text = remove_wp(text)
            text = clean_text(text)
            if text:
                actors[lang_name].append(text)

    return actors or None

# -----------------------------
# Japanese Name
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
# Buscar título real
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
# Obtener HTML
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
# Descargar imágenes
# -----------------------------

def download_images(soup, personaje):
    img_folder = "img_yakuzadle"
    os.makedirs(img_folder, exist_ok=True)

    infobox = soup.find("aside", {"class": "portable-infobox"})
    if not infobox:
        print("⚠ No se encontró infobox para imágenes")
        return []

    images = infobox.find_all("img")
    saved = []

    for img in images:
        url = img.get("src")
        if not url:
            continue

        game = img.get("alt") or "Unknown"
        game = re.sub(r"[^A-Za-z0-9]+", "", game)

        filename = f"{personaje}_{game}.png"
        filepath = os.path.join(img_folder, filename)

        if not os.path.exists(filepath):
            try:
                img_data = requests.get(url, headers=HEADERS).content
                with open(filepath, "wb") as f:
                    f.write(img_data)
                print(f"📥 Imagen descargada: {filename}")
            except Exception as e:
                print(f"❌ Error descargando {url}: {e}")

        saved.append(filename)

    return saved

# -----------------------------
# EXTRAER YEAR OF BIRTH
# -----------------------------

def extract_year_of_birth(soup):
    section = get_section(soup, "year_of_birth")
    if section is None:
        return None

    raw = clean_scalar(section)
    if not raw or raw == "Unknown":
        return None

    raw = remove_refs(raw)

    raw = re.sub(r"^\s*c\.\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^\s*ca\.\s*", "", raw, flags=re.IGNORECASE)

    m = re.match(r"(\d{4})(?:\s*/\s*(\d{4}))?", raw)
    if m:
        if m.group(2):
            return f"{m.group(1)}/{m.group(2)}"
        return m.group(1)

    return None

# -----------------------------
# Scraping principal
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

    appears_raw = extract_list(get_section(soup, "appears_in"), "Appears In")
    appears_clean = normalize_appears_in(appears_raw)

    nationality_final = extract_nationality_and_heritage(soup)

    images = download_images(soup, nombre.replace(" ", ""))

    dob = clean_scalar(get_section(soup, "date_of_birth"))

    if not dob or dob == "Unknown":
        yob = extract_year_of_birth(soup)
        if yob:
            dob = yob

    data = {
        "name": nombre,
        "japanese_name": get_japanese_name(soup),
        "aliases": extract_list(get_section(soup, "aliases"), "Aliases"),
        "nicknames": extract_list(get_section(soup, "nicknames"), "Nicknames"),
        "arena_names": extract_list(get_section(soup, "arena_names"), "Arena Names"),
        "date_of_birth": dob,
        "place_of_birth": clean_scalar(get_section(soup, "place_of_birth")),
        "nationality": nationality_final,
        "height": clean_scalar(get_section(soup, "height"), field="height"),
        "blood_type": clean_scalar(get_section(soup, "blood_type")),
        "affiliation": extract_affiliations(get_section(soup, "affiliation")),
        "appears_in": appears_clean,
        "fighting_style": extract_fighting_style(soup),
        "occupation": extract_occupation(soup),
        "actors": extract_actors(soup),
        "images": images,
    }

    db.collection("personajes").document(nombre).set(data, merge=True)
    print(f"✔ Guardado/actualizado en Firestore: {nombre}")

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
