# Caché global de cartas, depecado
cartas_cache = []

# Este comando sirve para actualizar la lista de cartas y descargar sus imágenes desde la wiki (depecado)
@client.command(help="Guarda en local todas las cartas y sus datos")
async def guardar(ctx):
    # Busca cartas y las guarda en cache
    cargar_cartas()
    if not cartas_cache:
        await ctx.send("No hay cartas en cache para guardar.")
        return

    # Comprueba si existen la carpeta y el archivo donde se guardan las cartas
    carpeta = "cartas"
    os.makedirs(carpeta, exist_ok=True)
    archivo_json = os.path.join(carpeta, "cartas.json")
    datos_guardados = []

    rarezas = ["UR", "KSR", "SSR", "SR", "R", "N"]

    async with aiohttp.ClientSession() as session:
        for idx, carta in enumerate(cartas_cache, start=1):
            # Comprueba si la imagen de la carta ya está guardada en la carpeta
            nombre_archivo = re.sub(r'[\\/*?:"<>|]', "", carta["nombre"]) + ".png"
            ruta = os.path.join(carpeta, nombre_archivo)

            # Descargar imagen solo si no la tiene ya
            if not os.path.exists(ruta):
                async with session.get(carta["url"]) as resp:
                    if resp.status == 200:
                        contenido = await resp.read()
                        await asyncio.to_thread(lambda: open(ruta, "wb").write(contenido))

            # Determinar rareza según prefijo del nombre
            rareza = next((r for r in rarezas if carta["nombre"].startswith(r + " ")), "N")

            # Guardar info en JSON con id y rareza
            datos_guardados.append({
                "id": idx,
                "nombre": carta["nombre"],
                "rareza": rareza,
                "imagen": os.path.relpath(ruta)
            })

    # Guardar archivo JSON
    await asyncio.to_thread(lambda: open(archivo_json, "w", encoding="utf-8").write(
        json.dumps(datos_guardados, ensure_ascii=False, indent=2)
    ))

    await ctx.send(f"Se han actualizado {len(cartas_cache)} cartas")
    
    # Cargar cartas desde la wiki, DEPECADO
async def cargar_cartas():
    global cartas_cache
    print("Cargando cartas RGGO...")

    base_url = "https://yakuza.fandom.com/api.php"
    params = {
        "action": "query",
        "list": "allimages",
        "aiprefix": "RGGO_-_Card_-",
        "ailimit": "500",
        "format": "json"
    }

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(base_url, params=params) as resp:
                data = await resp.json()

            for img in data["query"]["allimages"]:
                # Formateo aplicado directamente aquí
                nombre = (
                    img["name"]
                    .replace("RGGO_-_Card_-_", "")  # quitar prefijo
                    .replace(".png", "")            # quitar extensión
                    .replace("_", " ")              # guiones bajos -> espacios
                    .strip()
                )
                url = img["url"]
                cartas_cache.append({"nombre": nombre, "url": url})

            print(f"Cartas acumuladas: {len(cartas_cache)}")

            if "continue" in data:
                params.update(data["continue"])
            else:
                break

