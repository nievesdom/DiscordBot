import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import datetime
from core.firebase_client import db

# Core: carga/guardado en Gist y acceso a la base de cartas
from core.firebase_storage import cargar_settings, guardar_settings
from core.firebase_storage import cargar_packs, guardar_packs, cargar_propiedades, guardar_propiedades

from core.cartas import cargar_cartas, cartas_por_id

# Views: componentes interactivos
from views.navegador import Navegador
from views.reclamar import ReclamarCarta
from views.navegador_paquete import NavegadorPaquete
from views.navegador_trade import TradeView
from views.gift_view import GiftView

# ID del dueño (ocultamos /carta solo para él)
OWNER_ID = 182920174276575232

def backup_settings(settings: dict) -> None:
    """Guarda una copia completa de settings en la colección settings_backup."""
    timestamp = datetime.datetime.now().isoformat()
    db.collection("settings_backup").document(timestamp).set(settings)
    
def _find_card_by_name_fragment(name_fragment: str):
    """
    Busca una carta como hace 'show': primer elemento cuyo nombre contiene el fragmento (case-insensitive).
    Devuelve el objeto carta o None.
    """
    cartas = cargar_cartas()
    fragment = name_fragment.strip().lower()
    return next((c for c in cartas if fragment in str(c.get("nombre", "")).lower()), None)


def _remove_one_copy(user_cards: list, card_id) -> bool:
    """Quita solo la primera coincidencia de card_id en user_cards (normalizando a str)."""
    target = str(card_id)
    for idx, uid in enumerate(user_cards):
        if str(uid) == target:
            del user_cards[idx]
            return True
    return False
    
class Cartas(commands.Cog):
    """Cog principal para gestionar cartas y comandos del sistema RGGO."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bloqueados = set()  # Conjunto opcional para bloquear usuarios en flujos

    async def _safe_defer(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Hace defer seguro para evitar errores si ya se respondió."""
        try:
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.InteractionResponded:
            pass
    

    # -----------------------------
    # COMANDOS PÚBLICOS (slash + prefijo)
    # -----------------------------
    @app_commands.command(name="album", description="Shows a user's card collection in a visual format")
    async def album(self, interaction: discord.Interaction, user: discord.Member = None):
        """Muestra la galería navegable de un usuario (slash)."""
        await self._safe_defer(interaction)
        objetivo = user or interaction.user
        servidor_id, usuario_id = str(interaction.guild.id), str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.")
            return
        cartas_info = cartas_por_id()
        vista = Navegador(interaction, cartas_ids, cartas_info, objetivo)
        await vista.enviar()

    @commands.command(name="album")
    async def album_prefix(self, ctx: commands.Context, user: discord.Member = None):
        """Muestra la galería navegable de un usuario (prefijo)."""
        objetivo = user or ctx.author
        servidor_id, usuario_id = str(ctx.guild.id), str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await ctx.send(f"{objetivo.display_name} has no cards yet.")
            return
        cartas_info = cartas_por_id()
        vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
        await vista.enviar()
        
        
    # -----------------------------
    # /collection (texto)
    # -----------------------------
    @app_commands.command(name="collection", description="Shows a user's card collection in text mode")
    async def collection(self, interaction: discord.Interaction, user: discord.Member = None):
        """Muestra la colección como lista de nombres en texto plano (slash)."""
        await self._safe_defer(interaction, ephemeral=True)

        objetivo = user or interaction.user
        servidor_id, usuario_id = str(interaction.guild.id), str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.")
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())

        texto = f"{objetivo.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        # Fragmentar si excede el límite de Discord
        bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await interaction.followup.send(b)

    @commands.command(name="collection")
    async def collection_prefix(self, ctx: commands.Context, user: discord.Member = None):
        """Muestra la colección como lista de nombres en texto plano (prefijo)."""
        objetivo = user or ctx.author
        servidor_id, usuario_id = str(ctx.guild.id), str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await ctx.send(f"{objetivo.display_name} has no cards yet.")
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())

        texto = f"{objetivo.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await ctx.send(b)

    # -----------------------------
    # /search
    # -----------------------------
    @app_commands.command(name="search", description="Searches RGGO cards containing a term")
    async def search(self, interaction: discord.Interaction, term: str):
        """Busca cartas que contengan el término en su nombre (slash)."""
        await self._safe_defer(interaction, ephemeral=True)

        if not term:
            await interaction.followup.send("You must provide a search term. Example: /search Yamai", ephemeral=True)
            return

        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await interaction.followup.send(f"No cards found containing '{term}'.")
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(str(interaction.guild.id), {}).get(str(interaction.user.id), [])

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

    @commands.command(name="search")
    async def search_prefix(self, ctx: commands.Context, *, term: str):
        """Busca cartas que contengan el término en su nombre (prefijo)."""
        if not term:
            await ctx.send("You must provide a search term. Example: y!search Yamai")
            return

        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await ctx.send(f"No cards found containing '{term}'.")
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(str(ctx.guild.id), {}).get(str(ctx.author.id), [])

        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"

        await ctx.send(mensaje)
        await ctx.send(f"{len(coincidencias)} cards found containing '{term}'.")

    # -----------------------------
    # /pack
    # -----------------------------
    @app_commands.command(name="pack", description="Opens a pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        """Permite abrir un paquete diario de 5 cartas (slash)."""
        await interaction.response.defer(ephemeral=False)

        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        # Leer pack_limit desde settings
        settings = cargar_settings()
        servidor_settings = settings.get("guilds", {}).get(servidor_id, {})
        pack_limit = servidor_settings.get("pack_limit", 1)

        # Usar colección principal packs
        packs = cargar_packs()
        servidor_packs = packs.setdefault(servidor_id, {})
        usuario_packs = servidor_packs.setdefault(usuario_id, {})

        ahora = datetime.datetime.now()
        inicio_dia = datetime.datetime.combine(ahora.date(), datetime.time.min)
        medianoche = inicio_dia + datetime.timedelta(days=1)

        # Comprobar packs_opened
        packs_opened = usuario_packs.get("packs_opened", 0)
        if packs_opened >= pack_limit:
            restante = medianoche - ahora
            horas, resto = divmod(int(restante.total_seconds()), 3600)
            minutos = resto // 60
            await interaction.followup.send(
                f"🚫 {interaction.user.mention}, you have already opened the maximum of {pack_limit} packs today. "
                f"You can open more in {horas}h {minutos}m."
            )
            return

        # Cada franja dura (24 / pack_limit) horas
        intervalo_horas = 24 / pack_limit
        franja_actual = int(ahora.hour // intervalo_horas)

        # Comprobar último pack
        ultimo_str = usuario_packs.get("ultimo_paquete")
        if ultimo_str:
            try:
                ultimo_dt = datetime.datetime.fromisoformat(ultimo_str)
            except ValueError:
                # Caso especial: solo fecha YYYY-MM-DD → asumir medianoche
                ultimo_dt = datetime.datetime.fromisoformat(ultimo_str + "T00:00:00")
                usuario_packs["ultimo_paquete"] = ultimo_dt.isoformat()
                guardar_packs(packs)

            if ultimo_dt.date() == ahora.date():
                franja_ultimo = int(ultimo_dt.hour // intervalo_horas)
                if franja_actual == franja_ultimo:
                    siguiente_inicio = inicio_dia + datetime.timedelta(hours=(franja_actual + 1) * intervalo_horas)
                    restante = siguiente_inicio - ahora
                    horas, resto = divmod(int(restante.total_seconds()), 3600)
                    minutos = resto // 60
                    await interaction.followup.send(
                        f"🚫 {interaction.user.mention}, you must wait {horas}h {minutos}m before opening another pack."
                    )
                    return

        # Cargar cartas
        cartas = cargar_cartas()
        if not cartas:
            await interaction.followup.send("❌ No cards available.", ephemeral=True)
            return

        nuevas_cartas = random.sample(cartas, 5)

        # Guardar fecha/hora exacta y actualizar packs_opened
        usuario_packs["ultimo_paquete"] = ahora.isoformat()
        usuario_packs["packs_opened"] = packs_opened + 1
        guardar_packs(packs)

        # Guardar cartas obtenidas
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        # Preparar vista
        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(interaction, cartas_ids, cartas_info, interaction.user)
        embed, archivo = vista.mostrar()

        # Enviar log
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = interaction.client.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {interaction.user.display_name} abrió un paquete en {interaction.guild.name} "
                        f"con las cartas: {nombres_cartas}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

        # Enviar resultado al usuario
        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)



    # -----------------------------
    # y!pack (diario)
    # -----------------------------
    @commands.command(name="pack")
    async def pack_prefix(self, ctx: commands.Context):
        """Permite abrir un paquete diario de 5 cartas (prefijo)."""
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # Leer pack_limit desde settings
        settings = cargar_settings()
        servidor_settings = settings.get("guilds", {}).get(servidor_id, {})
        pack_limit = servidor_settings.get("pack_limit", 1)

        # Usar colección principal packs
        packs = cargar_packs()
        servidor_packs = packs.setdefault(servidor_id, {})
        usuario_packs = servidor_packs.setdefault(usuario_id, {})

        ahora = datetime.datetime.now()
        inicio_dia = datetime.datetime.combine(ahora.date(), datetime.time.min)
        medianoche = inicio_dia + datetime.timedelta(days=1)

        # Comprobar packs_opened
        packs_opened = usuario_packs.get("packs_opened", 0)
        if packs_opened >= pack_limit:
            restante = medianoche - ahora
            horas, resto = divmod(int(restante.total_seconds()), 3600)
            minutos = resto // 60
            await ctx.send(
                f"🚫 {ctx.author.mention}, you have already opened the maximum of {pack_limit} packs today. "
                f"You can open more in {horas}h {minutos}m."
            )
            return

        # Cada franja dura (24 / pack_limit) horas
        intervalo_horas = 24 / pack_limit
        franja_actual = int(ahora.hour // intervalo_horas)

        # Comprobar último pack
        ultimo_str = usuario_packs.get("ultimo_paquete")
        if ultimo_str:
            try:
                ultimo_dt = datetime.datetime.fromisoformat(ultimo_str)
            except ValueError:
                # Caso especial: solo fecha YYYY-MM-DD → asumir medianoche
                ultimo_dt = datetime.datetime.fromisoformat(ultimo_str + "T00:00:00")
                usuario_packs["ultimo_paquete"] = ultimo_dt.isoformat()
                guardar_packs(packs)

            if ultimo_dt.date() == ahora.date():
                franja_ultimo = int(ultimo_dt.hour // intervalo_horas)
                if franja_actual == franja_ultimo:
                    siguiente_inicio = inicio_dia + datetime.timedelta(hours=(franja_actual + 1) * intervalo_horas)
                    restante = siguiente_inicio - ahora
                    horas, resto = divmod(int(restante.total_seconds()), 3600)
                    minutos = resto // 60
                    await ctx.send(
                        f"🚫 {ctx.author.mention}, you must wait {horas}h {minutos}m before opening another pack."
                    )
                    return

        # Cargar cartas
        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available.")
            return

        nuevas_cartas = random.sample(cartas, 5)

        # Guardar fecha/hora exacta y actualizar packs_opened
        usuario_packs["ultimo_paquete"] = ahora.isoformat()
        usuario_packs["packs_opened"] = packs_opened + 1
        guardar_packs(packs)

        # Guardar cartas obtenidas
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        # Preparar vista
        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(ctx, cartas_ids, cartas_info, ctx.author)
        embed, archivo = vista.mostrar()

        # Enviar log al servidor/canal de logs
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = ctx.bot.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {ctx.author.display_name} abrió un paquete en {ctx.guild.name} "
                        f"con las cartas: {nombres_cartas}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

        # Enviar resultado al usuario
        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)
            
    
    @app_commands.command(
        name="pack_limit",
        description="[Admin only] Define the daily pack_limit for this server in settings."
    )
    @app_commands.default_permissions(administrator=True)
    async def pack_limit(self, interaction: discord.Interaction, value: int):
        """
        Permite al admin del servidor definir cuántos packs diarios se pueden abrir.
        Actualiza directamente la colección settings.
        """

        if interaction.guild is None:
            await interaction.response.send_message(
                "🚫 This command can only be used in servers.", ephemeral=True
            )
            return

        if value < 1 or value > 6:
            await interaction.response.send_message(
                "🚫 pack_limit must be between 1 and 6.", ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # 1. Cargar settings actuales
            settings = cargar_settings()

            # 2. Actualizar pack_limit solo para este servidor
            guilds = settings.setdefault("guilds", {})
            guild_config = guilds.setdefault(str(interaction.guild.id), {})
            guild_config["pack_limit"] = value

            # 3. Guardar settings actualizados en la colección principal
            guardar_settings(settings)

            await interaction.followup.send(
                f"✅ Daily pack limit set to {value} for **{interaction.guild.name}**.",
                
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Could not update the pack limit", ephemeral=True
            )
            
            
    # -----------------------------
    # Prefijo: y!pack_limit
    # -----------------------------
    @commands.command(name="pack_limit")
    @commands.has_permissions(administrator=True)
    async def pack_limit_prefix(self, ctx: commands.Context, value: int):
        """Comando de prefijo para definir el pack_limit."""
        # Comprueba que el valor sea entre 1 y 6
        if value < 1 or value > 6:
            await ctx.send("🚫 Pack limit must be between 1 and 6.")
            return

        try:
            # Carga los servidores de settings
            settings = cargar_settings()
            guilds = settings.setdefault("guilds", {})
            guild_config = guilds.setdefault(str(ctx.guild.id), {})
            # Configura el límite de packs
            guild_config["pack_limit"] = value
            guardar_settings(settings)

            await ctx.send(
                f"✅ Daily pack limit set to {value} for **{ctx.guild.name}**."
            )
        except Exception:
            await ctx.send("❌ Could not update the pack limit.")


    # -----------------------------
    # /gift (regalar carta)
    # -----------------------------
    @app_commands.command(name="gift", description="Gift a card to another user")
    @app_commands.describe(user="User to gift to", card="Exact name of the card to gift")
    async def gift(self, interaction: discord.Interaction, user: discord.Member, card: str):
        servidor_id = str(interaction.guild.id)
        sender_id = str(interaction.user.id)

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        sender_cards = servidor_props.setdefault(sender_id, [])

        # Buscar carta por nombre exacto
        cartas = cargar_cartas()
        name_lower = card.strip().lower()
        carta_obj = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta_obj:
            await interaction.response.send_message(f"❌ No card found with exact name '{card}'.", ephemeral=True)
            return

        if str(carta_obj["id"]) not in [str(cid) for cid in sender_cards]:
            await interaction.response.send_message(f"❌ You don't own a card named {card}.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} wants to gift you the card **{carta_obj['nombre']}**.\nDo you accept?",
            view=GiftView(interaction.user, user, carta_obj, propiedades, servidor_id, interaction.client)
        )
        
    # -----------------------------
    # y!gift (regalar carta)
    # -----------------------------
    @commands.command(name="gift")
    async def gift_prefix(self, ctx: commands.Context, user: discord.Member, *, card: str):
        servidor_id = str(ctx.guild.id)
        sender_id = str(ctx.author.id)

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        sender_cards = servidor_props.setdefault(sender_id, [])

        cartas = cargar_cartas()
        name_lower = card.strip().lower()
        carta_obj = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta_obj:
            await ctx.send(f"❌ No card found with exact name '{card}'.")
            return

        if str(carta_obj["id"]) not in [str(cid) for cid in sender_cards]:
            await ctx.send(f"❌ You don't own a card named {card}.")
            return

        await ctx.send(
            f"{user.mention}, {ctx.author.display_name} wants to gift you the card **{carta_obj['nombre']}**.\nDo you accept?",
            view=GiftView(ctx.author, user, carta_obj, propiedades, servidor_id, ctx.bot)
        )       



    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Exact name of the card you want to see")
    async def show(self, interaction: discord.Interaction, name: str):
        """Muestra una carta concreta buscando por nombre exacto (slash)."""
        await self._safe_defer(interaction)

        if not name:
            await interaction.followup.send("⚠️ You must provide a card's name.", ephemeral=True)
            return

        cartas = cargar_cartas()
        name_lower = name.strip().lower()

        # ✅ Buscar coincidencia exacta (case-insensitive)
        carta = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta:
            await interaction.followup.send(f"❌ No card found with exact name '{name}'.", ephemeral=True)
            return

        # Diccionarios de formato visual
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
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await interaction.followup.send(embed=embed)


    @commands.command(name="show")
    async def show_prefix(self, ctx: commands.Context, *, name: str):
        """Muestra una carta concreta buscando por nombre exacto (prefijo)."""
        if not name:
            await ctx.send("⚠️ You must provide a card's name.")
            return

        cartas = cargar_cartas()
        name_lower = name.strip().lower()

        # ✅ Buscar coincidencia exacta (case-insensitive)
        carta = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta:
            await ctx.send(f"❌ No card found with exact name '{name}'.")
            return

        # Diccionarios de formato visual
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
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await ctx.send(embed=embed)


    # -----------------------------
    # /trade (intercambio de cartas entre jugadores)
    # -----------------------------
    @app_commands.command(name="trade", description="Starts a card trade with another user")
    @app_commands.describe(user="User to trade with", card="Exact name of the card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        servidor_id = str(interaction.guild.id)
        usuario1_id = str(interaction.user.id)

        # Inventario del iniciador
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        coleccion1 = servidor_props.setdefault(usuario1_id, [])

        # Definición local: buscar carta por nombre exacto (case-insensitive)
        def find_card_by_exact_name(name: str):
            cartas = cargar_cartas()
            name_lower = name.strip().lower()
            return next((c for c in cartas if str(c.get("nombre", "")).lower() == name_lower), None)

        # Definición local: comprobar posesión normalizando IDs
        def owns_card(user_cards: list, card_id) -> bool:
            target = str(card_id)
            return any(str(cid) == target for cid in user_cards)

        # Buscar carta exacta
        carta1_obj = find_card_by_exact_name(card)
        if not carta1_obj:
            await interaction.response.send_message(f"❌ No card found with exact name '{card}'.", ephemeral=True)
            return

        # Comprobar posesión
        if not owns_card(coleccion1, carta1_obj.get("id")):
            await interaction.response.send_message(f"❌ You don't own a card named {card}.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(interaction.user, user, carta1_obj)
        )

    # -----------------------------
    # Prefijo: y!trade
    # -----------------------------
    @commands.command(name="trade")
    async def trade_prefix(self, ctx: commands.Context, user: discord.Member, *, card: str):
        servidor_id = str(ctx.guild.id)
        usuario1_id = str(ctx.author.id)

        # Inventario del iniciador
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        coleccion1 = servidor_props.setdefault(usuario1_id, [])

        # Definición local: buscar carta por nombre exacto (case-insensitive)
        def find_card_by_exact_name(name: str):
            cartas = cargar_cartas()
            name_lower = name.strip().lower()
            return next((c for c in cartas if str(c.get("nombre", "")).lower() == name_lower), None)

        # Definición local: comprobar posesión normalizando IDs
        def owns_card(user_cards: list, card_id) -> bool:
            target = str(card_id)
            return any(str(cid) == target for cid in user_cards)

        # Buscar carta exacta
        carta1_obj = find_card_by_exact_name(card)
        if not carta1_obj:
            await ctx.send(f"❌ No card found with exact name '{card}'.")
            return

        # Comprobar posesión
        if not owns_card(coleccion1, carta1_obj.get("id")):
            await ctx.send(f"❌ You don't own a card named {card}.")
            return

        await ctx.send(
            f"{user.mention}, {ctx.author.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(ctx.author, user, carta1_obj)
        )

        
    
    # -----------------------------
    # Slash command: /discard
    # -----------------------------
    @app_commands.command(
        name="discard",
        description="Discard one card from your inventory by exact name."
    )
    @app_commands.describe(nombre_carta="Exact name of the card to discard")
    async def discard_slash(self, interaction: discord.Interaction, nombre_carta: str):
        await interaction.response.defer(ephemeral=True)

        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        # Inventario
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])

        # ✅ Buscar coincidencia exacta (case-insensitive)
        cartas = cargar_cartas()
        name_lower = nombre_carta.strip().lower()
        carta = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta:
            await interaction.followup.send(f"❌ No card found with exact name '{nombre_carta}'.", ephemeral=True)
            return

        carta_id = carta.get("id")
        carta_nombre = carta.get("nombre", "Unknown")

        # Comprobar posesión y quitar solo una copia
        if not _remove_one_copy(usuario_cartas, carta_id):
            await interaction.followup.send(
                f"🚫 You don't have **{carta_nombre}** in your inventory.", ephemeral=True
            )
            return

        guardar_propiedades(propiedades)
        await interaction.followup.send(
            f"✅ Discarded one copy of **{carta_nombre}**.", ephemeral=True
        )

    # -----------------------------
    # Prefijo: y!discard
    # -----------------------------
    @commands.command(name="discard")
    async def discard_prefix(self, ctx: commands.Context, *, nombre_carta: str):
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # Inventario
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])

        # ✅ Buscar coincidencia exacta (case-insensitive)
        cartas = cargar_cartas()
        name_lower = nombre_carta.strip().lower()
        carta = next((c for c in cartas if c.get("nombre", "").lower() == name_lower), None)

        if not carta:
            await ctx.send(f"❌ No card found with exact name '{nombre_carta}'.")
            return

        carta_id = carta.get("id")
        carta_nombre = carta.get("nombre", "Unknown")

        # Comprobar posesión y quitar solo una copia
        if not _remove_one_copy(usuario_cartas, carta_id):
            await ctx.send(f"🚫 {ctx.author.mention}, no tienes **{carta_nombre}** en tu inventario.")
            return

        guardar_propiedades(propiedades)
        await ctx.send(f"✅ {ctx.author.mention}, has descartado una copia de **{carta_nombre}**.")

# -----------------------------
# Registro del cog en el bot
# -----------------------------
async def setup(bot: commands.Bot):
    """Función de setup para registrar el cog en el bot."""
    await bot.add_cog(Cartas(bot))
