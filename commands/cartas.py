import asyncio
import discord
from discord.ext import commands
import os
import json
import random
from urllib.parse import quote
from core.gist_settings import cargar_settings, guardar_settings
from views.navegador_paquete import NavegadorPaquete
import datetime
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador import Navegador
from views.reclamar import ReclamarCarta

# Para tener comandos que solo pueda usar el creador del bot (yo)
OWNER_ID = 182920174276575232

def es_dueno(ctx):
    return ctx.author.id == OWNER_ID



class Cartas(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot
        self.bloqueados = set()  # Usuarios en intercambio activo

    # Solo el dueño del bot puede usar este comando, quitado para que puedas probarlo si quieres
    # @commands.check(es_dueno)
    @commands.command(help="Saca una carta aleatoria de RGGO.", extras={"categoria": "Cartas 🃏"})
    async def carta(self, ctx):
        # Cargar todas las cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("No hay cartas guardadas en el archivo.")
            return

        elegida = random.choice(cartas)  # Elegir una carta al azar

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
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
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
            embed.description += "\n⚠️ Card image not found."

        # Vista para reclamar la carta (se mantiene)
        vista = ReclamarCarta(elegida["id"], embed, ruta_img)

        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)


    @commands.command(help="Shows a user's card collection. Mention another user if you want to see their collection instead. Ex: `y!album (@user)`.", extras={"categoria": "Cards 🃏"})
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
                await ctx.send(f"{objetivo.display_name} has no cards yet.")
                return

            # Busca la información de las cartas para mostrarla
            cartas_info = cartas_por_id()
            vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
            embed, archivo = vista.mostrar()

            # Si puede borrar el mensaje con el comando, lo hace
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
            await ctx.send("An error happened while trying to show your album. Please, try again later or contact my creator.")


    @commands.command(help="Shows a user's card collection in text mode. Mention another user if you want to see their collection instead. Ex: `y!collection (@user)`.", extras={"categoria": "Cards 🃏"})
    async def collection(self, ctx, mencionado: discord.Member = None):
        try:
            # Determina el objetivo de este comando según si se ha mencionado a otro usuario
            objetivo = mencionado or ctx.author
            servidor_id = str(ctx.guild.id)
            usuario_id = str(objetivo.id)

            # Carga las cartas del usuario y comprueba que tenga alguna
            propiedades = cargar_propiedades()
            cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
            if not cartas_ids:
                await ctx.send(f"{objetivo.display_name} has no cards yet.")
                return

            # Ordena las cartas en la lista
            cartas_info = cartas_por_id()
            nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
            nombres = sorted(nombres, key=lambda s: s.lower())

            texto = f"{ctx.author.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)

            # Si ocupa más de 2000 caracteres, divide el texto en varios mensajes
            if len(texto) <= 2000:
                await ctx.send(texto)
            else:
                partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
            print(f"[ERROR] en comando coleccion: {type(e).__name__} - {e}")
            await ctx.send("An error happened while trying to show your collection. Please, try again later or contact my creator.")


    @commands.command(help="Searches a list of RGGO cards that contain a term. Ex: `y!search Tanimura`.", extras={"categoria": "Cards 🃏"})
    async def search(self, ctx, *, palabra=None):
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

        await ctx.send(f"{len(coincidencias)} cards found containing '{palabra}'.")

    

    @commands.command(help="Opens a daily pack of 5 cards.", extras={"categoria": "Cards 🃏"})
    async def pack(self, ctx):
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
                f"🚫 {ctx.author.mention}, you already opened today's pack, come back in {horas}h {minutos}m.")
            return
        
        # Cargar las cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available. Please, contact my creator.")
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
            f"{ctx.author.mention} opened their daily pack:",
            embed=embed,
            view=vista
        )


    @commands.command(help="Shows a card's image and data. Ex: `y!show UR Yutaka Yamai (LADIW)`.", extras={"categoria": "Cards 🃏"})
    async def show(self, ctx, *, nombre=None):
        # Comprueba que se haya escrito un nombre
        if not nombre:
            await ctx.send("⚠️ You must write a card's name with the command. Ex: `y!show UR Yutaka Yamai (LADIW)`")
            return

        # Carga las cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available. Please, contact my creator.")
            return

        # Buscar carta por nombre (coincidencia parcial, insensible a mayúsculas)
        carta = next((c for c in cartas if nombre.lower() in c["nombre"].lower()), None)
        if not carta:
            await ctx.send(f"❌ No card found containing '{nombre}'.")
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
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
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
            embed.description += "\n⚠️ Image not found. Please, contact my creator."
            
        await ctx.send(embed=embed)


    @commands.command(help="Starts a card trade with another user. Ex: `y!trade @user UR Yutaka Yamai (LADIW)`.", extras={"categoria": "Cards 🃏"})
    async def trade(self, ctx, usuario2: discord.Member = None, *, carta1: str = None):
        """
        Flujo del intercambio:
        1. Usuario 1 propone una carta y menciona a Usuario 2.
        2. El bot espera que Usuario 2 escriba el nombre de la carta que ofrece a cambio.
        3. El bot espera que Usuario 1 escriba 'aceptar' o 'denegar'.
        4. Se realiza o cancela el intercambio según la respuesta.
        """
    
        # Validar que se han pasado los argumentos necesarios
        if usuario2 is None or carta1 is None:
            await ctx.send("⚠️ You need to mention a user and a card to trade. Ex: `y!trade @user UR Yutaka Yamai (LADIW)`")
            return
    
        # Evitar que un usuario participe en dos intercambios simultáneos
        if ctx.author.id in self.bloqueados or usuario2.id in self.bloqueados:
            await ctx.send("🚫 One or more of the users is already in an active trade. Finish that before starting a new trade.")
            return
    
        propiedades = cargar_propiedades()
        # Colección de Usuario 1 en este servidor
        coleccion1 = propiedades.get(str(ctx.guild.id), {}).get(str(ctx.author.id), [])
    
        # Cargar el archivo de cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available. Please, contact my creator.")
            return
    
        # Buscar carta1 por nombre
        carta1_id = None
        carta1_obj = None
        for c in cartas:
            if carta1.lower() in c["nombre"].lower():
                carta1_id = c["id"]
                carta1_obj = c
                break
            
        if not carta1_obj:
            await ctx.send(f"❌ The card '{carta1}' hasn't been found.")
            return
    
        if carta1_id not in coleccion1:
            await ctx.send(f"❌ You don't have a card named {carta1}.")
            return
    
        # Bloquear a ambos usuarios mientras dure el intercambio
        self.bloqueados.add(ctx.author.id)
        self.bloqueados.add(usuario2.id)
    
        await ctx.send(
            f"Hey, {usuario2.mention}, {ctx.author.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Write the name of a card you want to exchange (you have 2 minutes)."
        )
    
        # Función de comprobación: solo aceptar mensajes de Usuario 2 en el mismo canal
        def check_usuario2(m):
            return m.author.id == usuario2.id and m.channel == ctx.channel
    
        try:
            respuesta2 = await self.bot.wait_for("message", timeout=120, check=check_usuario2)
        except asyncio.TimeoutError:
            await ctx.send("⌛ Time's up. The trade has been cancelled.")
            self.bloqueados.discard(ctx.author.id)
            self.bloqueados.discard(usuario2.id)
            return
    
        carta2 = respuesta2.content.strip()
        coleccion2 = propiedades.get(str(ctx.guild.id), {}).get(str(usuario2.id), [])
    
        # Buscar carta2 por nombre
        carta2_id = None
        carta2_obj = None
        for c2 in cartas:
            if carta2.lower() in c2["nombre"].lower():
                carta2_id = c2["id"]
                carta2_obj = c2
                break
            
        if not carta2_obj:
            await ctx.send(f"❌ The card {carta2} hasn't been found. Trade cancelled.")
            self.bloqueados.discard(ctx.author.id)
            self.bloqueados.discard(usuario2.id)
            return
    
        if carta2_id not in coleccion2:
            await ctx.send(f"❌ {usuario2.mention}, you don't have acard named {carta2}. Trade cancelled.")
            self.bloqueados.discard(ctx.author.id)
            self.bloqueados.discard(usuario2.id)
            return
    
        await ctx.send(
            f"{usuario2.mention} offers their card **{carta2_obj['nombre']}** in exchange of your card **{carta1_obj['nombre']}**.\n"
            f"Write `accept` o `reject` (you have two minutes)."
        )
    
        # Función de comprobación: solo aceptar mensajes de Usuario 1 con 'aceptar' o 'denegar'
        def check_usuario1(m):
            return m.author.id == ctx.author.id and m.channel == ctx.channel and m.content.lower() in ["accept", "reject"]
    
        try:
            respuesta1 = await self.bot.wait_for("message", timeout=120, check=check_usuario1)
        except asyncio.TimeoutError:
            await ctx.send("⌛ Time's up. The trade has been cancelled.")
            self.bloqueados.discard(ctx.author.id)
            self.bloqueados.discard(usuario2.id)
            return
    
        if respuesta1.content.lower() == "reject":
            await ctx.send(f"❌ {usuario2.mention}, {ctx.author.display_name} has rejected the trade.")
            self.bloqueados.discard(ctx.author.id)
            self.bloqueados.discard(usuario2.id)
            return
        
        # Volver a cargar propiedades para refrescar las colecciones
        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(str(ctx.guild.id), {}).get(str(ctx.author.id), [])
        coleccion2 = propiedades.get(str(ctx.guild.id), {}).get(str(usuario2.id), [])
    
        # Realizar el intercambio usando IDs
        coleccion1.remove(carta1_id)
        coleccion2.remove(carta2_id)
        coleccion1.append(carta2_id)
        coleccion2.append(carta1_id)
    
        # Guardar cambios en propiedades
        propiedades[str(ctx.guild.id)][str(ctx.author.id)] = coleccion1
        propiedades[str(ctx.guild.id)][str(usuario2.id)] = coleccion2
        guardar_propiedades(propiedades)
    
        await ctx.send(
            f"✅ Trade successful:\n"
            f"- {ctx.author.mention} traded **{carta1_obj['nombre']}** and received **{carta2_obj['nombre']}**\n"
            f"- {usuario2.mention} traded **{carta2_obj['nombre']}** and received **{carta1_obj['nombre']}**"
        )
    
        # Liberar bloqueo para que puedan iniciar otros intercambios
        self.bloqueados.discard(ctx.author.id)
        self.bloqueados.discard(usuario2.id)




async def setup(bot):
    await bot.add_cog(Cartas(bot))
