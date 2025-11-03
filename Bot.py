import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging
from discord.ext import tasks, commands
import aiohttp
import random
import re
from urllib.parse import unquote
import json
from bs4 import BeautifulSoup

# Cargar las variables desde .env (el token del bot).
# Esto se hace para mantenerlo seguro y que no esté en el código, donde cualquiera pueda acceder
load_dotenv()
token = os.getenv("DISCORD_TOKEN")

# Activar los intents necesarios
intents = discord.Intents.default()
intents.message_content = True #Permite leer mensajes
intents.members = True #Permite acceder a la lista de miembros
intents.presences = True #Permite saber si un usuario está conectado

# Crear la conexión a Discord con los intents
client = discord.Client(intents=intents)
client = commands.Bot(command_prefix='y!', intents=intents, help_command=None)

# Cartas mostradas: mensaje_id -> nombre
cartas_mostradas = {}

# Archivo de propiedades, donde se guardan las cartas y sus propietarios
DATA_FILE = "propiedades.json"


# Cargar propiedades
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        propiedades = json.load(f)
else:
    propiedades = {}

def guardar_propiedades():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(propiedades, f, ensure_ascii=False, indent=2)



# Vista interactiva con botones para navegar entre cartas
class Navegador(discord.ui.View):
    def __init__(self, ctx, ids, datos):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.ids = ids # Lista de IDs de cartas del usuario
        self.datos = datos # Diccionario con info de cada carta
        self.orden = "original" # Estado del orden actual ("original" o "alfabetico")
        self.i = 0 # Índice de la carta actual
        self.msg = None # Mensaje que contiene el embed

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

    # Devuelve la lista ordenada según el estado actual (alfabético o por fecha)
    def lista(self):
        if self.orden == "alfabetico":
            return sorted(self.ids, key=lambda cid: self.datos.get(str(cid), {}).get("nombre", "").lower())
        return self.ids

    # Crea el embed y adjunta la imagen si existe
    def mostrar(self):
        lista_actual = self.lista()
        carta_id = str(lista_actual[self.i])
        carta = self.datos.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")

        embed = discord.Embed(title=nombre, color=color)
        embed.set_footer(text=f"Carta {self.i + 1} de {len(lista_actual)}")

        if imagen and os.path.exists(imagen):
            archivo = discord.File(imagen, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
            return embed, archivo
        else:
            embed.description = "⚠️ Imagen no encontrada."
            return embed, None

    # Actualiza el mensaje con la carta actual
    async def actualizar(self):
        lista_actual = self.lista()
        if self.i >= len(lista_actual):
            self.i = 0
        embed, archivo = self.mostrar()
        if archivo:
            await self.msg.edit(embed=embed, attachments=[archivo], view=self)
        else:
            await self.msg.edit(embed=embed, view=self)

    # Botón para ir a la carta anterior
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para ir a la carta siguiente
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para cambiar el orden de visualización
    @discord.ui.button(label="📆 Orden: por fecha", style=discord.ButtonStyle.primary, custom_id="orden")
    async def cambiar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Alternar entre modos
        self.orden = "alfabetico" if self.orden == "original" else "original"
        self.i = 0  # Reiniciar índice

        # Actualizar etiqueta del botón con emoji y texto
        nuevo_label = "🔤 Orden: alfabético" if self.orden == "alfabetico" else "📆 Orden: por fecha"
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "orden":
                item.label = nuevo_label

        await self.actualizar()
        await interaction.response.defer()


# Vista con botón para reclamar la carta
class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=60) # El botón expira tras 1 minuto
        self.carta_id = carta_id # ID de la carta mostrada
        self.embed = embed # Embed que se actualizará al reclamar
        self.imagen_ruta = imagen_ruta # Ruta de la imagen local
        self.reclamada = False # Estado de la carta (si ya fue reclamada)

    # Botón para reclamar la carta
    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Si ya fue reclamada, no permitir la interacción
        if self.reclamada:
            await interaction.response.send_message("Esta carta ya ha sido reclamada.", ephemeral=True)
            return

        usuario_id = str(interaction.user.id)
        servidor_id = str(interaction.guild.id)

        # Cargar archivo de cartas
        ruta_json = os.path.join("cartas", "cartas.json")
        if not os.path.exists(ruta_json):
            await interaction.response.send_message("No se encontró el archivo de cartas.", ephemeral=True)
            return

        with open(ruta_json, "r", encoding="utf-8") as f:
            cartas_guardadas = json.load(f)

        # Buscar la carta por ID
        carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
        if carta_info is None:
            await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
            return

        # Inicializar propiedades si no existen
        if servidor_id not in propiedades:
            propiedades[servidor_id] = {}
        if usuario_id not in propiedades[servidor_id]:
            propiedades[servidor_id][usuario_id] = []

        # Verificar si la carta ya fue reclamada por alguien
        for persona in propiedades[servidor_id]:
            if self.carta_id in propiedades[servidor_id][persona]:
                await interaction.response.send_message("Esa carta ya tiene dueño.", ephemeral=True)
                return

        # Asignar carta al usuario
        propiedades[servidor_id][usuario_id].append(self.carta_id)
        guardar_propiedades()

        # 🖤 Actualizar el embed: cambiar color a negro y mostrar quién la reclamó
        self.embed.color = discord.Color.dark_theme()
        self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
        self.reclamada = True
        self.clear_items()  # Eliminar el botón

        # Crear archivo nuevo si la imagen existe
        archivo = discord.File(self.imagen_ruta, filename="carta.png") if self.imagen_ruta and os.path.exists(self.imagen_ruta) else None

        # Editar el mensaje original con el nuevo embed y sin botón
        await interaction.message.edit(embed=self.embed, attachments=[archivo] if archivo else None, view=self)

        # Confirmación al usuario
        await interaction.response.send_message(f"{interaction.user.mention} ha obtenido **{carta_info['nombre']}**")
        

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



#Registrar eventos
@client.event


# --------- INICIO --------
async def on_ready():
    print(f'Iniciada sesión como {client.user}')
    # Cargar cartas al iniciar
    
    

# --------- COMANDOS ---------

@client.command(help="Saluda al usuario")
async def hola(ctx):
    await ctx.send(f"¡Hola, {ctx.author.mention}!")


@client.command(help="Cuenta hasta un número introducido por el usuario")
async def contar(ctx, numero: int):
    async def contar_mensaje(mensaje, numero):
        for i in range(1, numero + 1):
            await asyncio.sleep(1)
            await mensaje.edit(content=f"Contando... {i}")

    # Enviar mensaje inicial
    mensaje = await ctx.send("Contando... 0")

    # Ejecutar la cuenta en segundo plano para poder usar otros comandos mientras
    asyncio.create_task(contar_mensaje(mensaje, numero))


# Repite lo que escriba el usuario y borra el mensaje original
@client.command(help="Repite lo que escriba el usuario")
async def decir(ctx, *, arg):
    await ctx.send(arg)
    await ctx.message.delete()
  
    
@client.command(help="Muestra todos los comandos")
async def ayuda(ctx):
    #Obtener la lista de comandos y ordenarlos alfabéticamente
    comandos = sorted(client.commands, key=lambda c: c.name)
    
    mensajes = []
    mensaje = ""
    for comando in comandos:
        #comando.name es el nombre y comando.help la descripción
        if comando.help:
            linea = f"y!{comando.name} - {comando.help}"
        else:
            linea = f"y!{comando.name}"
        
        #Verificar límite de 2000 caracteres por mensaje. Si ocupa más, lo dividirá en varios
        if len(mensaje) + len(linea) + 1 > 2000:
            mensajes.append(mensaje)
            mensaje = ""
        mensaje += linea + "\n"
    if mensaje:
        mensajes.append(mensaje)
    
    #Enviar los mensajes al canal
    for m in mensajes:
        await ctx.send(m)


@client.command(help="Busca un término en la wiki de Yakuza")
async def wiki(ctx, *, termino: str):
    # Cambia los espacios por +
    termino_enc = termino.replace(' ', '+')
    # Usa la API de Yakuza Fandom para buscar resultados dentro de la wiki
    api_url = f"https://yakuza.fandom.com/api.php?action=query&list=search&srsearch={termino_enc}&format=json"
    # Espera a obtener un resultado
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            data = await resp.json()
    # Si encuentra un resultado, manda un enlace
    if data["query"]["search"]:
        mejor = data["query"]["search"][0]["title"]
        enlace = f"https://yakuza.fandom.com/wiki/{mejor.replace(' ', '_')}"
        await ctx.send(f"Aquí tienes el resultado más relevante para tu búsqueda: \n{enlace}")
    # Si no encuentra un resultado, lo comunica
    else:
        await ctx.send("Lo siento, no he encontrado nada.")
        
        
@client.command(help="Devuelve un personaje aleatorio")
async def personaje(ctx):
    url = "https://yakuza.fandom.com/api.php"
    parametros = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Characters",
        "cmlimit": "500",
        "format": "json"
    }
    personajes = []
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(url, params=parametros) as resp:
                data = await resp.json()
                # Filtrar solo artículos y no subcategorías (ns == 0)
                personajes += [item["title"] for item in data["query"]["categorymembers"] if item["ns"] == 0]
                if "continue" in data:
                    parametros.update(data["continue"])
                else:
                    break
    elegido = random.choice(personajes)
    enlace = f"https://yakuza.fandom.com/wiki/{elegido.replace(' ', '_')}"
    await ctx.send(enlace)

    
# Comando para sacar una carta aleatoria
@client.command(help="Saca una carta aleatoria de RGGO")
async def carta(ctx):
    # Verificar que el archivo de cartas existe
    ruta_json = os.path.join("cartas", "cartas.json")
    if not os.path.exists(ruta_json):
        await ctx.send("No se ha encontrado el archivo de cartas.")
        return

    # Cargar cartas desde el archivo
    with open(ruta_json, "r", encoding="utf-8") as f:
        cartas_guardadas = json.load(f)

    if not cartas_guardadas:
        await ctx.send("No hay cartas guardadas en el archivo.")
        return

    # Elegir una carta aleatoria
    elegida = random.choice(cartas_guardadas)

    # Colores por rareza
    colores = {
        "UR": 0x8841f2,
        "KSR": 0xabfbff,
        "SSR": 0x57ffae,
        "SR": 0xfcb63d,
        "R": 0xfc3d3d,
        "N": 0x8c8c8c
    }

    rareza = elegida.get("rareza", "N")
    color = colores.get(rareza, 0x8c8c8c)

    # Crear el embed con color por rareza
    embed = discord.Embed(title=elegida["nombre"], color=color)

    # Cargar imagen si existe
    ruta_img = elegida["imagen"]
    archivo = None
    if os.path.exists(ruta_img):
        archivo = discord.File(ruta_img, filename="carta.png")
        embed.set_image(url="attachment://carta.png")
    else:
        embed.description = "⚠️ Imagen no encontrada en la carpeta local."

    # Crear vista con botón, pasando solo la ruta de imagen
    vista = ReclamarCarta(elegida["id"], embed, ruta_img)

    # Enviar mensaje con embed y botón
    if archivo:
        await ctx.send(file=archivo, embed=embed, view=vista)
    else:
        await ctx.send(embed=embed, view=vista)

  
  
@client.command(help="Busca cartas de RGGO")
async def buscar(ctx, *, palabra):
    servidor_id = str(ctx.guild.id)

    # Carga el archivo de cartas desde la carpeta
    ruta_json = os.path.join("cartas", "cartas.json")
    if not os.path.exists(ruta_json):
        await ctx.send("No se encontró el archivo de cartas.")
        return

    with open(ruta_json, "r", encoding="utf-8") as f:
        cartas_guardadas = json.load(f)

    # Busca las cartas cuyo nombre contenga la palabra introducida
    coincidencias = [c for c in cartas_guardadas if palabra.lower() in c["nombre"].lower()]
    coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

    if not coincidencias:
        await ctx.send(f"No se encontraron cartas que contengan '{palabra}'.")
        return

    # Determinar qué cartas ya tienen propietario en este servidor
    cartas_con_dueño = set()
    if servidor_id in propiedades:
        for usuario in propiedades[servidor_id]:
            for carta_id in propiedades[servidor_id][usuario]:
                cartas_con_dueño.add(str(carta_id))

    # Genera el mensaje con formato
    mensaje = "```diff\n"  # El bloque diff permite usar texto rojo
    for c in coincidencias:
        if str(c["id"]) in cartas_con_dueño:
            mensaje += f"- {c['nombre']}\n"  # Rojo: carta con propietario
        else:
            mensaje += f"+ {c['nombre']}\n"  # Verde: carta libre
    mensaje += "```"

    # Limita el mensaje si es demasiado largo para Discord
    if len(mensaje) > 2000:
        mensaje = mensaje[:1990] + "\n```..."

    await ctx.send(f"Se han encontrado {len(coincidencias)} cartas que contienen '{palabra}':\n{mensaje}")
    
    
@client.command(help="Muestra la colección de cartas de un usuario. Si no se menciona a nadie, se mostrará la carta del autor del mensaje.")
async def coleccion(ctx):
    try:
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # Verificar si el usuario tiene cartas registradas
        if servidor_id not in propiedades or usuario_id not in propiedades[servidor_id]:
            await ctx.send(f"{ctx.author.mention}, no tienes ninguna carta todavía.")
            return

        cartas_ids = propiedades[servidor_id][usuario_id]
        if not cartas_ids:
            await ctx.send(f"{ctx.author.mention}, no tienes ninguna carta todavía.")
            return

        # Cargar el archivo de cartas para traducir ids a nombres
        ruta_json = os.path.join("cartas", "cartas.json")
        cartas_map = {}
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, "r", encoding="utf-8") as f:
                    cartas_guardadas = json.load(f)
                for c in cartas_guardadas:
                    cartas_map[str(c.get("id"))] = c.get("nombre")
            except Exception as e:
                print("Error al cargar cartas.json:", e)

        # Construir lista de nombres
        lista_mostrar = []
        for cid in cartas_ids:
            nombre = cartas_map.get(str(cid), f"ID {cid} (no encontrada)")
            lista_mostrar.append(nombre)

        # Ordenar alfabéticamente
        lista_mostrar = sorted(lista_mostrar, key=lambda s: s.lower())

        # Generar mensaje
        texto = f"{ctx.author.mention}, estas son tus cartas ({len(lista_mostrar)}):\n" + "\n".join(lista_mostrar)

        # Dividir si excede 2000 caracteres
        if len(texto) <= 2000:
            await ctx.send(texto)
        else:
            partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
            for parte in partes:
                await ctx.send(parte)

    except Exception as e:
        print("Error en comando coleccion:", e)
        await ctx.send("Ha ocurrido un error al intentar mostrar tu colección.")
        


@client.command(help="Actualiza el archivo cartas.json con las imágenes nuevas de la carpeta cartas")
async def actualizar_cartas(ctx):
    carpeta = "cartas"
    archivo_json = os.path.join(carpeta, "cartas.json")

    os.makedirs(carpeta, exist_ok=True)

    # Cargar cartas ya guardadas (si existe el archivo)
    if os.path.exists(archivo_json):
        with open(archivo_json, "r", encoding="utf-8") as f:
            try:
                cartas_existentes = json.load(f)
            except json.JSONDecodeError:
                cartas_existentes = []
    else:
        cartas_existentes = []

    nombres_existentes = {c["nombre"] for c in cartas_existentes}
    imagenes = [f for f in os.listdir(carpeta) if f.lower().endswith(".png")]

    rarezas = ["UR", "KSR", "SSR", "SR", "R", "N"]
    max_id = max((c.get("id", 0) for c in cartas_existentes), default=0)

    nuevas = 0
    for imagen in imagenes:
        nombre = imagen.replace(".png", "")
        if nombre in nombres_existentes:
            continue  # Ya registrada

        # Determinar rareza
        rareza = next((r for r in rarezas if nombre.startswith(r + " ")), "N")

        # Asignar nuevo id
        max_id += 1

        nueva_carta = {
            "id": max_id,
            "nombre": nombre,
            "rareza": rareza,
            "imagen": os.path.join(carpeta, imagen)
        }

        cartas_existentes.append(nueva_carta)
        nuevas += 1

        print(f"[*] Añadida: {nombre} (ID {max_id}, Rareza {rareza})")

    # Guardar los cambios
    try:
        with open(archivo_json, "w", encoding="utf-8") as f:
            json.dump(cartas_existentes, f, ensure_ascii=False, indent=2)
        print("[OK] Archivo cartas.json actualizado correctamente.")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar el archivo JSON: {e}")

    await ctx.send(f"Se han añadido {nuevas} cartas nuevas al archivo cartas.json.")
    
    

# Muestra la colección del usuario de forma visual
@client.command(help="Muestra la colección de cartas de forma visual")
async def album(ctx, mencionado: discord.Member = None):
    try:
        # Si se menciona a alguien, usamos su ID; si no, usamos el del autor del comando
        objetivo = mencionado or ctx.author
        servidor = str(ctx.guild.id)
        usuario = str(objetivo.id)

        # Verificar si el usuario tiene cartas
        if servidor not in propiedades or usuario not in propiedades[servidor]:
            await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
            return

        ids = propiedades[servidor][usuario]
        if not ids:
            await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
            return

        # Cargar archivo de cartas
        ruta = os.path.join("cartas", "cartas.json")
        if not os.path.exists(ruta):
            await ctx.send("No se ha encontrado el archivo de cartas.")
            return

        with open(ruta, "r", encoding="utf-8") as f:
            cartas = json.load(f)

        datos = {str(c["id"]): c for c in cartas}

        # Crear vista y mostrar primera carta
        vista = Navegador(ctx, ids, datos)
        embed, archivo = vista.mostrar()

        if archivo:
            vista.msg = await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            vista.msg = await ctx.send(embed=embed, view=vista)

    except Exception as e:
        print("Error en coleccion_visual:", e)
        await ctx.send("Ha ocurrido un error al intentar mostrar tu colección visual.")

    
# Registrar logging y conectar con token del bot
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
client.run(token, log_handler=handler, log_level=logging.DEBUG)
