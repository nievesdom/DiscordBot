import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import datetime

# Core: carga/guardado en Gist y acceso a la base de cartas
from core.gist_settings import cargar_settings, guardar_settings
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas, cartas_por_id

# Views: componentes interactivos
from views.navegador import Navegador
from views.reclamar import ReclamarCarta
from views.navegador_paquete import NavegadorPaquete
from views.navegador_trade import TradeView

# ID del dueño (ocultamos /carta solo para él)
OWNER_ID = 182920174276575232


class Cartas(commands.Cog):
    """Cog principal para gestionar cartas y comandos del sistema RGGO."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Conjunto para marcar usuarios temporalmente si usas bloqueos en flujos (no imprescindible aquí)
        self.bloqueados = set()

    # -----------------------------
    # Utilidad: defer seguro
    # -----------------------------
    async def _safe_defer(self, interaction: discord.Interaction, ephemeral: bool = False):
        """
        Intenta hacer defer de la interacción (ephemeral opcional).
        Si ya se respondió, ignora el error para no romper el flujo.
        """
        try:
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.InteractionResponded:
            pass

    # -----------------------------
    # /carta (solo OWNER)
    # -----------------------------
    @app_commands.default_permissions()  # Comando no visible por permisos por defecto
    @app_commands.check(lambda i: i.user.id == OWNER_ID)  # Solo el dueño lo puede ejecutar
    @app_commands.command(name="carta", description="Draws a random RGGO card")
    async def carta(self, interaction: discord.Interaction):
        """
        Muestra una carta aleatoria con su imagen y stats.
        Útil para pruebas rápidas; restringido al OWNER_ID.
        """
        await interaction.response.defer()

        cartas = cargar_cartas()
        if not cartas:
            return await interaction.followup.send("No cards available.", ephemeral=True)

        elegida = random.choice(cartas)

        # Diccionarios de formato visual
        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}

        # Preparar datos de la carta
        rareza = elegida.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        attr_raw = str(elegida.get("atributo", "—")).lower()
        tipo_raw = str(elegida.get("tipo", "—")).lower()
        attr_symbol = atributos.get(attr_raw, "")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{elegida.get('nombre', 'Carta')}",
            color=color,
            description=(
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
                f"❤️ {elegida.get('health', '—')} | ⚔️ {elegida.get('attack', '—')} | "
                f"🛡️ {elegida.get('defense', '—')} | 💨 {elegida.get('speed', '—')}"
            ),
        )

        ruta = elegida.get("imagen")
        archivo = None
        if ruta and ruta.startswith("http"):
            embed.set_image(url=ruta)
        elif ruta and os.path.exists(ruta):
            # Enviar como archivo adjunto si la ruta es local
            archivo = discord.File(ruta, filename="carta.png")
            embed.set_image(url="attachment://carta.png")

        # Vista para reclamar la carta (tu clase ya existente)
        vista = ReclamarCarta(elegida["id"], embed, ruta)

        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)

    # -----------------------------
    # /album
    # -----------------------------
    @app_commands.command(name="album", description="Shows a user's card collection")
    @app_commands.describe(user="Mention a user to see their album")
    async def album(self, interaction: discord.Interaction, user: discord.Member = None):
        """
        Muestra la galería navegable de un usuario.
        Usa la vista Navegador, que envía y guarda su propio mensaje para ediciones.
        """
        await self._safe_defer(interaction)

        objetivo = user or interaction.user
        servidor_id = str(interaction.guild.id)
        usuario_id = str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.", ephemeral=True)
            return

        cartas_info = cartas_por_id()
        vista = Navegador(interaction, cartas_ids, cartas_info, objetivo)
        # Enviar la primera tarjeta y guardar el mensaje dentro de la vista
        await vista.enviar()

    # -----------------------------
    # /collection (texto)
    # -----------------------------
    @app_commands.command(name="collection", description="Shows a user's card collection in text mode")
    @app_commands.describe(user="Mention a user to see their collection")
    async def collection(self, interaction: discord.Interaction, user: discord.Member = None):
        """
        Muestra la colección como lista de nombres, en texto plano.
        Ideal para búsquedas o comprobaciones rápidas.
        """
        await self._safe_defer(interaction, ephemeral=True)

        objetivo = user or interaction.user
        servidor_id = str(interaction.guild.id)
        usuario_id = str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.", ephemeral=True)
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())

        texto = f"{objetivo.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        # Fragmentar si excede el límite de Discord
        bloques = [texto[i : i + 1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await interaction.followup.send(b)

    # -----------------------------
    # /search
    # -----------------------------
    @app_commands.command(name="search", description="Searches RGGO cards containing a term")
    @app_commands.describe(term="Term to search in cards")
    async def search(self, interaction: discord.Interaction, term: str):
        """
        Busca cartas que contengan el término en su nombre.
        Marca con + las que el usuario posee y con - las que no.
        """
        await self._safe_defer(interaction, ephemeral=True)

        if not term:
            await interaction.followup.send("You must provide a search term. Example: /search Yamai", ephemeral=True)
            return

        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await interaction.followup.send(f"No cards found containing '{term}'.", ephemeral=True)
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(str(interaction.guild.id), {}).get(str(interaction.user.id), [])

        # Formato diff para visual rápido (+ posee, - no posee)
        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"

        await interaction.followup.send(mensaje)
        await interaction.followup.send(f"{len(coincidencias)} cards found containing '{term}'.")

    # -----------------------------
    # /pack (diario)
    # -----------------------------
    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        """
        Permite abrir un paquete diario de 5 cartas.
        Controla intervalo diario por usuario y servidor vía settings en Gist.
        """
        await self._safe_defer(interaction)

        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        settings = cargar_settings()
        servidor_settings = settings.setdefault(servidor_id, {})
        usuario_settings = servidor_settings.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

        # Si ya abrió pack hoy, informar tiempo restante hasta medianoche
        if usuario_settings.get("ultimo_paquete") == hoy:
            mañana = ahora + datetime.timedelta(days=1)
            medianoche = datetime.datetime.combine(mañana.date(), datetime.time.min)
            restante = medianoche - ahora
            horas, resto = divmod(restante.seconds, 3600)
            minutos = resto // 60
            await interaction.followup.send(
                f"🚫 {interaction.user.mention}, you already opened today's pack, come back in {horas}h {minutos}m."
            )
            return

        cartas = cargar_cartas()
        if not cartas:
            await interaction.followup.send("❌ No cards available.", ephemeral=True)
            return

        # Seleccionar 5 cartas aleatorias y registrar apertura
        nuevas_cartas = random.sample(cartas, 5)
        usuario_settings["ultimo_paquete"] = hoy
        guardar_settings(settings)

        # Guardar IDs en propiedades del usuario
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        # Mostrar paquete en vista navegable
        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(interaction, cartas_ids, cartas_info, interaction.user)
        embed, archivo = vista.mostrar()

        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)

    # -----------------------------
    # /show (detalles de una carta)
    # -----------------------------
    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Card name")
    async def show(self, interaction: discord.Interaction, name: str):
        """
        Muestra una carta concreta buscando por nombre (subcadena, no exacto).
        Si hay imagen remota, la incrusta en el embed.
        """
        await self._safe_defer(interaction)

        if not name:
            await interaction.followup.send("⚠️ You must provide a card's name.", ephemeral=True)
            return

        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await interaction.followup.send(f"❌ No card found containing '{name}'.", ephemeral=True)
            return

        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}

        rareza = carta.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        attr_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = atributos.get(attr_raw, "")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{carta.get('nombre', 'Carta')}",
            color=color,
            description=(
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
                f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}"
            ),
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await interaction.followup.send(embed=embed)

    # -----------------------------
    # /trade (intercambio de cartas entre jugadores)
    # -----------------------------
    @app_commands.command(name="trade", description="Starts a card trade with another user")
    @app_commands.describe(user="User to trade with", card="Card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        """
        Inicia un intercambio de cartas con otro usuario.
        Flujo:
        1. Usuario1 inicia el trade con su carta.
        2. Usuario2 pulsa Accept y escribe la carta que ofrece.
        3. Se muestra una segunda confirmación a Usuario1 con botones Accept/Reject.
        4. Solo si Usuario1 acepta se ejecuta el intercambio en el Gist.
        """
        await self._safe_defer(interaction)

        servidor_id = str(interaction.guild.id)
        usuario1_id = str(interaction.user.id)
        usuario2_id = str(user.id)

        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(servidor_id, {}).get(usuario1_id, [])
        coleccion2 = propiedades.get(servidor_id, {}).get(usuario2_id, [])

        # Buscar la carta del iniciador en la base global
        cartas = cargar_cartas()
        carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
        if not carta1_obj:
            await interaction.followup.send(f"❌ The card '{card}' hasn't been found.", ephemeral=True)
            return

        carta1_id = carta1_obj["id"]
        if carta1_id not in coleccion1:
            await interaction.followup.send(f"❌ You don't own a card named {card}.", ephemeral=True)
            return

        # Enviar propuesta al usuario destino con vista interactiva
        await interaction.followup.send(
            f"{user.mention}, {interaction.user.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(interaction.user, user, carta1_obj),
        )



# -----------------------------
# Registro del cog en el bot
# -----------------------------
async def setup(bot: commands.Bot):
    """
    Función de setup para el loader de cogs:
    bot.load_extension(...) llamará a este setup para añadir el cog.
    """
    await bot.add_cog(Cartas(bot))