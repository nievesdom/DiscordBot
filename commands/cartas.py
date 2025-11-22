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
        self.bloqueados = set()  # Conjunto opcional para bloquear usuarios en flujos

    async def _safe_defer(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Hace defer seguro para evitar errores si ya se respondió."""
        try:
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.InteractionResponded:
            pass

    # -----------------------------
    # SOLO OWNER (no se tocan)
    # -----------------------------
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="servers_info", description="(Owner only) Shows the servers where the bot is and their member counts.")
    async def servers_info(self, interaction: discord.Interaction):
        """Muestra información de todos los servidores donde está el bot."""
        await interaction.response.defer(ephemeral=True)
        guilds = self.bot.guilds
        total_servers = len(guilds)
        info_lines = [f"• **{g.name}** (ID: {g.id}) → 👥 {g.member_count} members" for g in guilds]
        listado = "\n".join(info_lines)
        embed = discord.Embed(
            title="🌐 Servers where the bot is present",
            description=f"Currently in **{total_servers} servers**:\n\n{listado}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="avisar_update", description="**[Bot owner only]** Send update notice to all servers with auto_cards enabled.")
    async def avisar_update(self, interaction: discord.Interaction):
        """Envía aviso de actualización a todos los servidores con auto_cards activado."""
        await interaction.response.defer(ephemeral=True)
        message = (
            "🚀 **The bot has been updated to version 1.1 and now supports slash commands!**\n"
            "Use `/help` to see the full list of available commands or `/update` in order to see a more detailed description of all the changes.\n"
            "Sorry for the downtime and if you experienced any issues before."
        )
        sent, failed = 0, 0
        cartas_cog = self.bot.get_cog("CartasAuto")
        if not cartas_cog:
            await interaction.followup.send("❌ CartasAuto cog not found.", ephemeral=True)
            return
        for gid, config in cartas_cog.settings.get("guilds", {}).items():
            if config.get("enabled"):
                guild = self.bot.get_guild(int(gid))
                if not guild:
                    continue
                channel = guild.get_channel(config["channel_id"])
                if not channel:
                    continue
                try:
                    await channel.send(message)
                    sent += 1
                except Exception as e:
                    print(f"[ERROR] No se pudo enviar aviso en guild {gid}: {e}")
                    failed += 1
        await interaction.followup.send(f"✅ Aviso enviado a {sent} servidores. ❌ Fallos: {failed}.", ephemeral=True)

    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="carta", description="Draws a random RGGO card")
    async def carta(self, interaction: discord.Interaction):
        """Muestra una carta aleatoria (solo owner)."""
        await interaction.response.defer()
        cartas = cargar_cartas()
        if not cartas:
            return await interaction.followup.send("No cards available.", ephemeral=True)
        elegida = random.choice(cartas)
        # Diccionarios de formato visual
        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}
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
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {elegida.get('health', '—')} | ⚔️ {elegida.get('attack', '—')} | "
                         f"🛡️ {elegida.get('defense', '—')} | 💨 {elegida.get('speed', '—')}")
        )
        ruta = elegida.get("imagen")
        archivo = None
        if ruta and ruta.startswith("http"):
            embed.set_image(url=ruta)
        elif ruta and os.path.exists(ruta):
            archivo = discord.File(ruta, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
        vista = ReclamarCarta(elegida["id"], embed, ruta)
        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)

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
    # /pack (diario)
    # -----------------------------
    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        """Permite abrir un paquete diario de 5 cartas (slash)."""
        await self._safe_defer(interaction)

        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        settings = cargar_settings()
        servidor_settings = settings.setdefault(servidor_id, {})
        usuario_settings = servidor_settings.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

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

        nuevas_cartas = random.sample(cartas, 5)
        usuario_settings["ultimo_paquete"] = hoy
        guardar_settings(settings)

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(interaction, cartas_ids, cartas_info, interaction.user)
        embed, archivo = vista.mostrar()

        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)

    @commands.command(name="pack")
    async def pack_prefix(self, ctx: commands.Context):
        """Permite abrir un paquete diario de 5 cartas (prefijo)."""
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        settings = cargar_settings()
        servidor_settings = settings.setdefault(servidor_id, {})
        usuario_settings = servidor_settings.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

        if usuario_settings.get("ultimo_paquete") == hoy:
            mañana = ahora + datetime.timedelta(days=1)
            medianoche = datetime.datetime.combine(mañana.date(), datetime.time.min)
            restante = medianoche - ahora
            horas, resto = divmod(restante.seconds, 3600)
            minutos = resto // 60
            await ctx.send(
                f"🚫 {ctx.author.mention}, you already opened today's pack, come back in {horas}h {minutos}m."
            )
            return

        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available.")
            return

        nuevas_cartas = random.sample(cartas, 5)
        usuario_settings["ultimo_paquete"] = hoy
        guardar_settings(settings)

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(ctx, cartas_ids, cartas_info, ctx.author)
        embed, archivo = vista.mostrar()

        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)

    # -----------------------------
    # /show (detalles de una carta)
    # -----------------------------
    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Name of the card you want to see")
    async def show(self, interaction: discord.Interaction, name: str):
        """Muestra una carta concreta buscando por nombre (slash)."""
        await self._safe_defer(interaction)

        if not name:
            await interaction.followup.send("⚠️ You must provide a card's name.", ephemeral=True)
            return

        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await interaction.followup.send(f"❌ No card found containing '{name}'.")
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
        """Muestra una carta concreta buscando por nombre (prefijo)."""
        if not name:
            await ctx.send("⚠️ You must provide a card's name.")
            return

        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await ctx.send(f"❌ No card found containing '{name}'.")
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
    @app_commands.describe(user="User to trade with", card="Card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        """Inicia un intercambio de cartas con otro usuario (slash)."""
        await self._safe_defer(interaction)

        servidor_id = str(interaction.guild.id)
        usuario1_id = str(interaction.user.id)
        usuario2_id = str(user.id)

        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(servidor_id, {}).get(usuario1_id, [])
        coleccion2 = propiedades.get(servidor_id, {}).get(usuario2_id, [])

        cartas = cargar_cartas()
        carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
        if not carta1_obj:
            await interaction.followup.send(f"❌ The card '{card}' hasn't been found.")
            return

        carta1_id = carta1_obj["id"]
        if carta1_id not in coleccion1:
            await interaction.followup.send(f"❌ You don't own a card named {card}.")
            return

        await interaction.followup.send(
            f"{user.mention}, {interaction.user.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(interaction.user, user, carta1_obj, interaction),
        )

    @commands.command(name="trade")
    async def trade_prefix(self, ctx: commands.Context, user: discord.Member, *, card: str):
        """Inicia un intercambio de cartas con otro usuario (prefijo)."""
        servidor_id = str(ctx.guild.id)
        usuario1_id = str(ctx.author.id)
        usuario2_id = str(user.id)

        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(servidor_id, {}).get(usuario1_id, [])
        coleccion2 = propiedades.get(servidor_id, {}).get(usuario2_id, [])

        cartas = cargar_cartas()
        carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
        if not carta1_obj:
            await ctx.send(f"❌ The card '{card}' hasn't been found.")
            return

        carta1_id = carta1_obj["id"]
        if carta1_id not in coleccion1:
            await ctx.send(f"❌ You don't own a card named {card}.")
            return

        await ctx.send(
            f"{user.mention}, {ctx.author.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(ctx.author, user, carta1_obj, ctx),
        )


# -----------------------------
# Registro del cog en el bot
# -----------------------------
async def setup(bot: commands.Bot):
    """Función de setup para registrar el cog en el bot."""
    await bot.add_cog(Cartas(bot))
