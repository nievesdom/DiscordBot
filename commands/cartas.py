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

# Importar funciones desde módulos core y views
from core.gist_propiedades import cargar_propiedades, guardar_propiedades, obtener_cartas_usuario  # NUEVO
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
        cartas = cargar_cartas()  # Cargar todas las cartas
        if not cartas:
            await ctx.send("No hay cartas guardadas en el archivo.")
            return

        elegida = random.choice(cartas)  # Elegir una al azar

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

        # Crear el embed
        embed = discord.Embed(title=elegida["nombre"], color=color)
        ruta_img = elegida["imagen"]
        archivo = None

        # Comprobar si la ruta es URL (Render) o local
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        elif os.path.exists(ruta_img):
            archivo = discord.File(ruta_img, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
        else:
            embed.description = "⚠️ Imagen no encontrada."

        # Crear vista con botón para reclamar
        vista = ReclamarCarta(elegida["id"], embed, ruta_img)

        # Enviar mensaje con embed y botón
        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)


    @commands.command(help="Muestra la colección de cartas de forma visual. Si no se menciona a nadie, se mostrará la colección del autor del mensaje.", extras={"categoria": "Cartas 🃏"})
    async def album(self, ctx, mencionado: discord.Member = None):
        try:
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)
    
            cartas_ids = obtener_cartas_usuario(servidor_id, usuario_id)
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return
    
            cartas_info = cartas_por_id()  # Diccionario de cartas por ID
    
            vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
            embed, archivo = vista.mostrar()
    
            # Borrar el mensaje del comando si el bot tiene permisos
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass
                
            # Enviar el mensaje con el álbum
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
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            cartas_ids = obtener_cartas_usuario(servidor_id, usuario_id)
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return

            cartas_info = cartas_por_id()
            nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
            nombres = sorted(nombres, key=lambda s: s.lower())

            texto = f"{ctx.author.mention}, estas son tus cartas ({len(nombres)}):\n" + "\n".join(nombres)

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
    async def buscar(self, ctx, *, palabra=None):
        if palabra is None:
            await ctx.send("Introduce un término tras el comando para buscar cartas. Ejemplo: y!buscar Yamai")
            return

        servidor_id = str(ctx.guild.id)
        cartas = cargar_cartas()

        coincidencias = [c for c in cartas if palabra.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await ctx.send(f"No se encontraron cartas que contengan '{palabra}'.")
            return

        # Cargar propiedades en tiempo real desde el Gist
        propiedades = cargar_propiedades()  # NUEVO

        # Determinar qué cartas ya tienen dueño
        cartas_con_dueño = set()
        if servidor_id in propiedades:
            for usuario in propiedades[servidor_id]:
                for carta_id in propiedades[servidor_id][usuario]:
                    cartas_con_dueño.add(str(carta_id))

        # Mostrar resultados con formato diff
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

        await ctx.send(f"Se han encontrado {len(coincidencias)} cartas que contienen '{palabra}'.")
    

    # Solo para el dueño del bot: actualiza rutas de imágenes con URL de Render
    @commands.command(help=None)
    @commands.check(es_dueno)
    async def actualizar_img(self, ctx):
        with open("cartas/cartas.json", "r", encoding="utf-8") as f:
            cartas = json.load(f)

        BASE_URL = "https://discordbot-n4ts.onrender.com/cartas/"

        for carta in cartas:
            nombre_archivo = f"{carta['nombre']}.png"
            nombre_codificado = quote(nombre_archivo)
            carta["imagen"] = BASE_URL + nombre_codificado

        with open("cartas/cartas.json", "w", encoding="utf-8") as f:
            json.dump(cartas, f, ensure_ascii=False, indent=2)

        await ctx.send("✅ Rutas de imágenes actualizadas correctamente.")


    @commands.command(help=None)
    @commands.check(es_dueno)
    async def actualizar_cartas(self, ctx):
        carpeta = "cartas"
        archivo_json = os.path.join(carpeta, "cartas.json")
        os.makedirs(carpeta, exist_ok=True)

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
                continue

            rareza = next((r for r in rarezas if nombre.startswith(r + " ")), "N")
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

        try:
            with open(archivo_json, "w", encoding="utf-8") as f:
                json.dump(cartas_existentes, f, ensure_ascii=False, indent=2)
            print("[OK] Archivo cartas.json actualizado correctamente.")
        except Exception as e:
            print(f"[ERROR] No se pudo guardar el archivo JSON: {e}")

        await ctx.send(f"Se han añadido {nuevas} cartas nuevas al archivo cartas.json.")
        
    @actualizar_cartas.error
    async def actualizar_cartas_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("🚫 Este comando solo puede usarlo el creador del bot.")


async def setup(bot):
    await bot.add_cog(Cartas(bot))
