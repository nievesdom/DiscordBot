import discord
from discord.ext import commands
import os
import json
import random
from urllib.parse import quote

# Para tener comandos que solo pueda usar el creador del bot (yo)
OWNER_ID = 182920174276575232

def es_dueno(ctx):
    return ctx.author.id == OWNER_ID

# Importar funciones y datos compartidos desde módulos core y views
from core.propiedades import propiedades, guardar_propiedades, obtener_cartas_usuario
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador import Navegador
from views.reclamar import ReclamarCarta

class Cartas(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot


    @commands.command(help="Saca una carta aleatoria de RGGO", extras={"categoria": "Cartas 🃏"})
    async def carta(self, ctx):
        cartas = cargar_cartas() # Cargar todas las cartas
        if not cartas:
            await ctx.send("No hay cartas guardadas en el archivo.")
            return

        elegida = random.choice(cartas) # Elegir una al azar

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

        # Crear el embed con el nombre y color
        embed = discord.Embed(title=elegida["nombre"], color=color)
        ruta_img = elegida["imagen"]
        archivo = None

        # Comprobar si existe una URL en el campo imagen y usarla
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description = "⚠️ Imagen no encontrada o sin URL válida."


    @commands.command(help="Muestra la colección de cartas de forma visual. Si no se menciona a nadie, se mostrará la colección del autor del mensaje.", extras={"categoria": "Cartas 🃏"})
    async def album(self, ctx, mencionado: discord.Member = None):
        try:
            # Si se menciona a alguien, se muestra la colección de ese usuario, si no la del autor del mensaje
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            cartas_ids = obtener_cartas_usuario(servidor_id, usuario_id)
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return

            cartas_info = cartas_por_id() # Diccionario de cartas por ID
            vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
            embed, archivo = vista.mostrar()

            # Borrar el mensaje del comando si el bot tiene permisos
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass

            # Enviar el mensaje con el album
            if archivo:
                vista.msg = await ctx.send(file=archivo, embed=embed, view=vista)
            else:
                vista.msg = await ctx.send(embed=embed, view=vista)

        except Exception as e:
            print(f"[ERROR] en comando album: {type(e).__name__} - {e}")
            await ctx.send("Ha ocurrido un error al intentar mostrar el álbum.")


    @commands.command(help="Muestra la colección de cartas en modo texto", extras={"categoria": "Cartas 🃏"})
    async def coleccion(self, ctx, mencionado: discord.Member = None):
        try:
            # Si se menciona a alguien, se muestra la colección de ese usuario, si no la del autor del mensaje
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            # Comprueba si el usuario tiene cartas
            cartas_ids = obtener_cartas_usuario(servidor_id, usuario_id)
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return

            cartas_info = cartas_por_id()
            nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
            nombres = sorted(nombres, key=lambda s: s.lower())

            texto = f"{ctx.author.mention}, estas son tus cartas ({len(nombres)}):\n" + "\n".join(nombres)

            # Si el mensaje tiene más de 2000 caracteres, lo divide en varios
            if len(texto) <= 2000:
                await ctx.send(texto)
            else:
                partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
            print(f"[ERROR] en comando coleccion: {type(e).__name__} - {e}")
            await ctx.send("Ha ocurrido un error al intentar mostrar tu colección.")


    @commands.command(help="Busca cartas de RGGO. Introduce el término a buscar detrás del comando.", extras={"categoria": "Cartas 🃏"})
    async def buscar(self, ctx, *, palabra = None):
        # Se debe introducir una
        if palabra == None:
            await ctx.send(f"Introduce un término tras el comando para buscar cartas que lo contengan. Ej: y!buscar Yamai")
            return
        servidor_id = str(ctx.guild.id)
        cartas = cargar_cartas()
        
        # Filtrar cartas que contengan la palabra
        coincidencias = [c for c in cartas if palabra.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await ctx.send(f"No se encontraron cartas que contengan '{palabra}'.")
            return

        # Determinar qué cartas ya tienen dueño
        cartas_con_dueño = set()
        if servidor_id in propiedades:
            for usuario in propiedades[servidor_id]:
                for carta_id in propiedades[servidor_id][usuario]:
                    cartas_con_dueño.add(str(carta_id))

        # Generar mensaje con formato diff.
        # Rojo: con dueño. Verde: libre
        mensaje = "```diff\n"
        for c in coincidencias:
            if str(c["id"]) in cartas_con_dueño:
                mensaje += f"- {c['nombre']}\n"
            else:
                mensaje += f"+ {c['nombre']}\n"
        mensaje += "```"

        bloques = [mensaje[i:i+1900] for i in range(0, len(mensaje), 1900)]
        for b in bloques:
            await ctx.send(f"\n{b}\n")

        await ctx.send(f"Se han encontrado {len(coincidencias)} cartas que contienen '{palabra}':\n{mensaje}")

    #@commands.command(help="Muestra la carta introducida", extras={"categoria": "Cartas 🃏"})
    #async def carta(self, ctx):


    # Actualiza el archivo cartas.json con las imágenes nuevas. Restringido, solo para el creador
    @commands.command(help=None)
    async def actualizar_img(self, ctx):
        # Carga el JSON existente
        with open("cartas/cartas.json", "r", encoding="utf-8") as f:
            cartas = json.load(f)

        # Cambia esta URL base según tu entorno
        # En local: usa localhost
        # En Render: cambia por la URL pública (por ejemplo, https://discordbot.onrender.com)
        BASE_URL = "https://discordbot-n4ts.onrender.com/cartas/"

        # Actualiza cada ruta de imagen
        for carta in cartas:
            nombre_archivo = os.path.basename(carta["imagen"]).replace("\\", "/")
            carta["imagen"] = BASE_URL + quote(nombre_archivo)

        # Guarda el nuevo archivo
        with open("cartas/cartas.json", "w", encoding="utf-8") as f:
            json.dump(cartas, f, ensure_ascii=False, indent=2)

        print("Rutas actualizadas correctamente.")



    # Actualiza el archivo cartas.json con las imágenes nuevas. Restringido, solo para el creador
    @commands.command(help=None)
    @commands.check(es_dueno)
    async def actualizar_cartas(self, ctx):
        carpeta = "cartas"
        archivo_json = os.path.join(carpeta, "cartas.json")
        os.makedirs(carpeta, exist_ok=True)

        # Cargar cartas existentes
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

        # Comprueba uno a uno si la carta ya está en el archivo
        nuevas = 0
        for imagen in imagenes:
            nombre = imagen.replace(".png", "")
            if nombre in nombres_existentes:
                continue

            rareza = next((r for r in rarezas if nombre.startswith(r + " ")), "N")
            max_id += 1

            # Si no lo está, la añade al final
            nueva_carta = {
                "id": max_id,
                "nombre": nombre,
                "rareza": rareza,
                "imagen": os.path.join(carpeta, imagen)
            }

            cartas_existentes.append(nueva_carta)
            nuevas += 1
            print(f"[*] Añadida: {nombre} (ID {max_id}, Rareza {rareza})")

        # Guardar el archivo actualizado
        try:
            with open(archivo_json, "w", encoding="utf-8") as f:
                json.dump(cartas_existentes, f, ensure_ascii=False, indent=2)
            print("[OK] Archivo cartas.json actualizado correctamente.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el archivo JSON: {e}")

        await ctx.send(f"Se han añadido {nuevas} cartas nuevas al archivo cartas.json.")
        
    # Depura errores si alguien más intenta usar el comando actualizar_cartas
    @actualizar_cartas.error
    async def actualizar_cartas_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("🚫 Este comando solo puede usarlo el creador del bot.")


async def setup(bot):
    await bot.add_cog(Cartas(bot))

