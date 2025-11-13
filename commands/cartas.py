import discord
from discord.ext import commands
import os
import json
import random
from urllib.parse import quote
from core.gist_settings import cargar_settings, guardar_settings
from views.navegador_paquete import NavegadorPaquete
import datetime

# Para tener comandos que solo pueda usar el creador del bot (yo)
OWNER_ID = 182920174276575232

def es_dueno(ctx):
    return ctx.author.id == OWNER_ID

# Importar funciones desde módulos core y views
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
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
        
        # Diccionario de atributos con símbolo japonés
        atributos = {
            "heart": "心",
            "technique": "技",
            "body": "体",
            "light": "陽",
            "shadow": "陰",
        }
        
        # Diccionario de tipos con emoji
        tipos = {
            "attack": "⚔️ Attack",
            "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery",
            "support": "✨ Support",
        }
        
        rareza = elegida.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        
        atributo_raw = str(elegida.get("atributo", "—")).lower()
        tipo_raw = str(elegida.get("tipo", "—")).lower()
        
        # Formato de atributo y tipo
        attr_symbol = atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")
        
        # Embed con formato unificado
        embed = discord.Embed(
            title=f"{elegida.get('nombre', 'Carta')}",
            color=color,  # color por rareza
            description=(
                f"**Atributo:** {atributo_fmt}\n"
                f"**Tipo:** {tipo_fmt}\n"
                f"❤️ {elegida.get('health', '—')} | ⚔️ {elegida.get('attack', '—')} | "
                f"🛡️ {elegida.get('defense', '—')} | 💨 {elegida.get('speed', '—')}"
            )
        )

        ruta_img = elegida.get("imagen")
        archivo = None

        # Mostrar imagen (URL remota o archivo local)
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        elif ruta_img and os.path.exists(ruta_img):
            archivo = discord.File(ruta_img, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
        else:
            embed.description += "\n⚠️ Imagen no encontrada."

        # Vista para reclamar la carta (se mantiene)
        vista = ReclamarCarta(elegida["id"], embed, ruta_img)

        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)


    @commands.command(help="Muestra la colección de cartas de forma visual. Menciona a otro usuario para ver su colección.", extras={"categoria": "Cartas 🃏"})
    async def album(self, ctx, mencionado: discord.Member = None):
        try:
            # Si se menciona a una persona, ese será el objetivo, si no lo será el autor del mensaje
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            # Carga el archivo de propiedades y guarda las del objetivo
            propiedades = cargar_propiedades()
            cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
            # Si no tiene cartas aún, se dice
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return

            # Busca la información de las cartas para mostrarla
            cartas_info = cartas_por_id()
            vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
            embed, archivo = vista.mostrar()

            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    pass

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
            # Determina el objetivo de este comando según si se ha mencionado a otro usuario
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            # Carga las cartas del usuario y comprueba que tenga alguna
            propiedades = cargar_propiedades()
            cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} no tiene ninguna carta todavía.")
                return

            # Ordena las cartas en la lista
            cartas_info = cartas_por_id()
            nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
            nombres = sorted(nombres, key=lambda s: s.lower())

            texto = f"{ctx.author.mention}, estas son tus cartas ({len(nombres)}):\n" + "\n".join(nombres)

            # Si ocupa más de 2000 caracteres, divide el texto en varios mensajes
            if len(texto) <= 2000:
                await ctx.send(texto)
            else:
                partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
            print(f"[ERROR] en comando coleccion: {type(e).__name__} - {e}")
            await ctx.send("Ha ocurrido un error al intentar mostrar tu colección.")


    @commands.command(help="Busca cartas de RGGO.", extras={"categoria": "Cartas 🃏"})
    async def buscar(self, ctx, *, palabra=None):
        # Verificar que el usuario introduzca una palabra de búsqueda
        if palabra is None:
            await ctx.send("Introduce un término tras el comando para buscar cartas. Ejemplo: y!buscar Yamai")
            return

        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # Cargar todas las cartas y filtrar las que contienen la palabra buscada
        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if palabra.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        # Si no hay coincidencias, se notifica al usuario
        if not coincidencias:
            await ctx.send(f"No se encontraron cartas que contengan '{palabra}'.")
            return

        # Cargar propiedades para ver qué cartas posee el usuario
        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(servidor_id, {}).get(usuario_id, [])

        # Crear el mensaje con formato diff
        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            # Si el usuario tiene la carta, se muestra en verde (+)
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            # Si no la tiene, se muestra en rojo (-)
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"

        # Dividir el mensaje si supera el límite de Discord
        bloques = [mensaje[i:i+1900] for i in range(0, len(mensaje), 1900)]
        for b in bloques:
            await ctx.send(b)

        await ctx.send(f"Se han encontrado {len(coincidencias)} cartas que contienen '{palabra}'.")

    

    @commands.command(help="Abre un paquete diario de 5 cartas", extras={"categoria": "Cartas 🃏"})
    async def paquete(self, ctx):
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)
        
        # Comprueba si el usuario ya ha abierto un paquete hoy
        settings = cargar_settings()
        servidor_settings = settings.setdefault(servidor_id, {})
        usuario_settings = servidor_settings.setdefault(usuario_id, {})
        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()
        
        if usuario_settings.get("ultimo_paquete") == hoy:
            # Calcular tiempo restante hasta medianoche
            mañana = ahora + datetime.timedelta(days=1)
            medianoche = datetime.datetime.combine(mañana.date(), datetime.time.min)
            restante = medianoche - ahora
            horas, resto = divmod(restante.seconds, 3600)
            minutos = resto // 60
            await ctx.send(
                f"🚫 {ctx.author.mention}, ya has abierto tu paquete de hoy.\n"
                f"Podrás abrir otro en {horas}h {minutos}m."
            )
            return
        
        # Cargar las cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No hay cartas disponibles en el archivo.")
            return
        
        # Elegir 5 cartas aleatorias
        nuevas_cartas = random.sample(cartas, 5)
        
        # Guardar fecha de apertura del paquete en settings.json
        usuario_settings["ultimo_paquete"] = hoy
        guardar_settings(settings)
        
        # Guardar las cartas nuevas en propiedades.json
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)
        
        # Mostrar las cartas obtenidas en el paquete
        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(ctx, cartas_ids, cartas_info, ctx.author)
        embed, archivo = vista.mostrar()
        
        # Guardar el mensaje en la vista para que los botones funcionen
        vista.msg = await ctx.send(
            f"🎁 {ctx.author.mention} ha abierto su paquete diario de 5 cartas:",
            embed=embed,
            view=vista
        )


    @commands.command(help="Muestra una carta específica por nombre", extras={"categoria": "Cartas 🃏"})
    async def mostrar(self, ctx, *, nombre=None):
        # Comprueba que se haya escrito un nombre
        if not nombre:
            await ctx.send("⚠️ Debes escribir el nombre de la carta después del comando. Ejemplo: `y!mostrar UR Yutaka Yamai (LADIW)`")
            return

        # Carga las cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No hay cartas disponibles en el archivo.")
            return

        # Buscar carta por nombre (coincidencia parcial, insensible a mayúsculas)
        carta = next((c for c in cartas if nombre.lower() in c["nombre"].lower()), None)
        if not carta:
            await ctx.send(f"❌ No se encontró ninguna carta que contenga '{nombre}'.")
            return

        # Colores por rareza
        colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

        # Atributos con símbolo japonés
        atributos = {
            "heart": "心",
            "technique": "技",
            "body": "体",
            "light": "陽",
            "shadow": "陰"
        }

        # Tipos con emoji
        tipos = {
            "attack": "⚔️ Attack",
            "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery",
            "support": "✨ Support"
        }
        
        # Determina el color según la rareza y el resto de características de la carta
        rareza = carta.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)

        atributo_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()

        attr_symbol = atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name

        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        # Embed con formato
        embed = discord.Embed(
            title=f"{carta.get('nombre', 'Carta')}",
            color=color,
            description=(
                f"**Atributo:** {atributo_fmt}\n"
                f"**Tipo:** {tipo_fmt}\n"
                f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}"
            )
        )
        
        # Carga la imagen de la carta
        ruta_img = carta.get("imagen")
        archivo = None

        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Imagen no encontrada."
            
        await ctx.send(embed=embed)





    # Solo para el dueño del bot
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
