import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import datetime
from core.gist_settings import cargar_settings, guardar_settings
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador import Navegador
from views.reclamar import ReclamarCarta
from views.navegador_paquete import NavegadorPaquete

OWNER_ID = 182920174276575232

class Cartas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bloqueados = set()  # Users in active trades

    # ---- /carta ----
    @app_commands.command(name="carta", description="Draws a random RGGO card")
    async def carta(self, interaction: discord.Interaction):
        cartas = cargar_cartas()
        if not cartas:
            await interaction.response.send_message("No cards available.", ephemeral=True)
            return

        elegida = random.choice(cartas)
        colores = {"UR":0x8841f2,"KSR":0xabfbff,"SSR":0x57ffae,"SR":0xfcb63d,"R":0xfc3d3d,"N":0x8c8c8c}
        atributos = {"heart":"心","technique":"技","body":"体","light":"陽","shadow":"陰"}
        tipos = {"attack":"⚔️ Attack","defense":"🛡️ Defense","recovery":"❤️ Recovery","support":"✨ Support"}

        rareza = elegida.get("rareza","N")
        color = colores.get(rareza,0x8c8c8c)
        attr_raw = str(elegida.get("atributo","—")).lower()
        tipo_raw = str(elegida.get("tipo","—")).lower()

        attr_symbol = atributos.get(attr_raw,"")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{elegida.get('nombre','Carta')}",
            color=color,
            description=f"**Attribute:** {atributo_fmt}\n**Type:** {tipo_fmt}\n❤️ {elegida.get('health','—')} | ⚔️ {elegida.get('attack','—')} | 🛡️ {elegida.get('defense','—')} | 💨 {elegida.get('speed','—')}"
        )

        ruta_img = elegida.get("imagen")
        archivo = None
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        elif ruta_img and os.path.exists(ruta_img):
            archivo = discord.File(ruta_img, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
        else:
            embed.description += "\n⚠️ Card image not found."

        vista = ReclamarCarta(elegida["id"], embed, ruta_img)
        if archivo:
            await interaction.response.send_message(file=archivo, embed=embed, view=vista)
        else:
            await interaction.response.send_message(embed=embed, view=vista)

    # ---- /album ----
    @app_commands.command(name="album", description="Shows a user's card collection")
    @app_commands.describe(user="Mention a user to see their album")
    async def album(self, interaction: discord.Interaction, user: discord.Member = None):
        objetivo = user or interaction.user
        servidor_id = str(interaction.guild.id)
        usuario_id = str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.response.send_message(f"{objetivo.display_name} has no cards yet.", ephemeral=True)
            return

        cartas_info = cartas_por_id()
        vista = Navegador(interaction, cartas_ids, cartas_info, objetivo)
        embed, archivo = vista.mostrar()
        if archivo:
            await interaction.response.send_message(embed=embed, file=archivo, view=vista)
        else:
            await interaction.response.send_message(embed=embed, view=vista)

    # ---- /collection ----
    @app_commands.command(name="collection", description="Shows a user's card collection in text mode")
    @app_commands.describe(user="Mention a user to see their collection")
    async def collection(self, interaction: discord.Interaction, user: discord.Member = None):
        objetivo = user or interaction.user
        servidor_id = str(interaction.guild.id)
        usuario_id = str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.response.send_message(f"{objetivo.display_name} has no cards yet.", ephemeral=True)
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())
        texto = f"{interaction.user.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await interaction.response.send_message(b)

    # ---- /search ----
    @app_commands.command(name="search", description="Searches RGGO cards containing a term")
    @app_commands.describe(term="Term to search in cards")
    async def search(self, interaction: discord.Interaction, term: str):
        if not term:
            await interaction.response.send_message("You must provide a search term. Example: /search Yamai", ephemeral=True)
            return
        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)
        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])
        if not coincidencias:
            await interaction.response.send_message(f"No cards found containing '{term}'.", ephemeral=True)
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(servidor_id, {}).get(usuario_id, [])
        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"
        bloques = [mensaje[i:i+1900] for i in range(0, len(mensaje), 1900)]
        for b in bloques:
            await interaction.response.send_message(b)
        await interaction.response.send_message(f"{len(coincidencias)} cards found containing '{term}'.")

    # ---- /pack ----
    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
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
            await interaction.response.send_message(f"🚫 {interaction.user.mention}, you already opened today's pack, come back in {horas}h {minutos}m.")
            return

        cartas = cargar_cartas()
        if not cartas:
            await interaction.response.send_message("❌ No cards available.", ephemeral=True)
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
        vista.msg = await interaction.response.send_message(f"{interaction.user.mention} opened their daily pack:", embed=embed, view=vista)

    # ---- /show ----
    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Card name")
    async def show(self, interaction: discord.Interaction, name: str):
        if not name:
            await interaction.response.send_message("⚠️ You must provide a card's name.", ephemeral=True)
            return
        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await interaction.response.send_message(f"❌ No card found containing '{name}'.", ephemeral=True)
            return

        colores = {"UR":0x8841f2,"KSR":0xabfbff,"SSR":0x57ffae,"SR":0xfcb63d,"R":0xfc3d3d,"N":0x8c8c8c}
        atributos = {"heart":"心","technique":"技","body":"体","light":"陽","shadow":"陰"}
        tipos = {"attack":"⚔️ Attack","defense":"🛡️ Defense","recovery":"❤️ Recovery","support":"✨ Support"}

        rareza = carta.get("rareza","N")
        color = colores.get(rareza,0x8c8c8c)
        attr_raw = str(carta.get("atributo","—")).lower()
        tipo_raw = str(carta.get("tipo","—")).lower()
        attr_symbol = atributos.get(attr_raw,"")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{carta.get('nombre','Carta')}",
            color=color,
            description=f"**Attribute:** {atributo_fmt}\n**Type:** {tipo_fmt}\n❤️ {carta.get('health','—')} | ⚔️ {carta.get('attack','—')} | 🛡️ {carta.get('defense','—')} | 💨 {carta.get('speed','—')}"
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await interaction.response.send_message(embed=embed)

    # ---- /trade ----
    @app_commands.command(name="trade", description="Starts a card trade with another user")
    @app_commands.describe(user="User to trade with", card="Card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        if interaction.user.id in self.bloqueados or user.id in self.bloqueados:
            await interaction.response.send_message("🚫 One or more of the users is already in an active trade.", ephemeral=True)
            return
        # Logic of message-based trade goes here
        await interaction.response.send_message("Trade started (message-based interaction)")

async def setup(bot):
    await bot.add_cog(Cartas(bot))
