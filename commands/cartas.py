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
        OWNER_ID = 182920174276575232


    # ---- /carta ----
    # -------------------------------
    #  OCULTAR comando + restringirlo
    # -------------------------------

    @app_commands.default_permissions()  # comando NO visible para nadie
    @app_commands.check(lambda i: i.user.id == OWNER_ID)  # solo el dueño
    @app_commands.command(
        name="carta",
        description="Draws a random RGGO card"
    )
    async def carta(self, interaction: discord.Interaction):
        await interaction.response.defer()

        cartas = cargar_cartas()
        if not cartas:
            return await interaction.followup.send("No cards available.", ephemeral=True)

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

    # ---- /album ----
    @app_commands.command(name="album", description="Shows a user's card collection")
    @app_commands.describe(user="Mention a user to see their album")
    async def album(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._safe_defer(interaction)
        try:
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
            embed, archivo = vista.mostrar()

            if archivo:
                await interaction.followup.send(file=archivo, embed=embed, view=vista)
            else:
                await interaction.followup.send(embed=embed, view=vista)
        except Exception as e:
            print(f"[ERROR] album: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened while trying to show the album.", ephemeral=True)
            except Exception:
                pass

    # ---- /collection ----
    @app_commands.command(name="collection", description="Shows a user's card collection in text mode")
    @app_commands.describe(user="Mention a user to see their collection")
    async def collection(self, interaction: discord.Interaction, user: discord.Member = None):
        await self._safe_defer(interaction, ephemeral=True)
        try:
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
            texto = f"{interaction.user.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
            bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]

            # enviar el primer mensaje y los siguientes como followups
            for b in bloques:
                await interaction.followup.send(b)
        except Exception as e:
            print(f"[ERROR] collection: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened while trying to show your collection.", ephemeral=True)
            except Exception:
                pass

    # ---- /search ----
    @app_commands.command(name="search", description="Searches RGGO cards containing a term")
    @app_commands.describe(term="Term to search in cards")
    async def search(self, interaction: discord.Interaction, term: str):
        await self._safe_defer(interaction, ephemeral=True)
        try:
            if not term:
                await interaction.followup.send("You must provide a search term. Example: /search Yamai", ephemeral=True)
                return
            servidor_id = str(interaction.guild.id)
            usuario_id = str(interaction.user.id)
            cartas = cargar_cartas()
            coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
            coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])
            if not coincidencias:
                await interaction.followup.send(f"No cards found containing '{term}'.", ephemeral=True)
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
                await interaction.followup.send(b)
            await interaction.followup.send(f"{len(coincidencias)} cards found containing '{term}'.")
        except Exception as e:
            print(f"[ERROR] search: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened during the search.", ephemeral=True)
            except Exception:
                pass

    # ---- /pack ----
    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        await self._safe_defer(interaction)
        try:
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
                await interaction.followup.send(f"🚫 {interaction.user.mention}, you already opened today's pack, come back in {horas}h {minutos}m.")
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
        except Exception as e:
            print(f"[ERROR] pack: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened opening the pack.", ephemeral=True)
            except Exception:
                pass

    # ---- /show ----
    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Card name")
    async def show(self, interaction: discord.Interaction, name: str):
        await self._safe_defer(interaction)
        try:
            if not name:
                await interaction.followup.send("⚠️ You must provide a card's name.", ephemeral=True)
                return
            cartas = cargar_cartas()
            carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
            if not carta:
                await interaction.followup.send(f"❌ No card found containing '{name}'.", ephemeral=True)
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

            await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] show: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened showing the card.", ephemeral=True)
            except Exception:
                pass

    # ---- /trade ----
    @app_commands.command(name="trade", description="Starts a card trade with another user")
    @app_commands.describe(user="User to trade with", card="Card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        # Safe defer para evitar 'interaction failed'
        await self._safe_defer(interaction, ephemeral=True)
    
        try:
            # ---- Comprobación de usuarios bloqueados ----
            if interaction.user.id in self.bloqueados or user.id in self.bloqueados:
                await interaction.followup.send("🚫 One or more of the users is already in an active trade.", ephemeral=True)
                return
    
            # ---- Aviso y petición de carta al segundo usuario ----
            await interaction.followup.send(
                f"{user.mention}, {interaction.user.display_name} wants to trade their card **{card}** with you. "
                "Write the name of a card you want to exchange (you have 2 minutes).",
                ephemeral=False
            )
    
            # Solo acepta mensajes del usuario 2 en el mismo canal
            def check_usuario2(m):
                return m.author.id == user.id and m.channel.id == interaction.channel_id
    
            try:
                respuesta2 = await self.bot.wait_for("message", timeout=120, check=check_usuario2)
            except asyncio.TimeoutError:
                await interaction.followup.send("⌛ Time's up. The trade has been cancelled.")
                return
    
            carta2 = respuesta2.content.strip()
    
            # ---- Cargar inventarios desde archivo ----
            propiedades = cargar_propiedades()
            coleccion1 = propiedades.get(str(interaction.guild.id), {}).get(str(interaction.user.id), [])
            coleccion2 = propiedades.get(str(interaction.guild.id), {}).get(str(user.id), [])
    
            # ---- Cargar datos de cartas ----
            cartas = cargar_cartas()
    
            # Buscar carta 1 (del usuario iniciador)
            carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
    
            # Buscar carta 2 (del usuario que responde)
            carta2_obj = next((c for c in cartas if carta2.lower() in c["nombre"].lower()), None)
    
            # ---- Validar cartas ----
            if not carta1_obj:
                await interaction.followup.send(f"❌ The card '{card}' hasn't been found.", ephemeral=True)
                return
    
            if not carta2_obj:
                await interaction.followup.send(f"❌ The card '{carta2}' hasn't been found. Trade cancelled.")
                return
    
            carta1_id = carta1_obj["id"]
            carta2_id = carta2_obj["id"]
    
            # ---- Comprobar si realmente las tienen ----
            # (SIN cambiar tu forma original de validación)
            if carta1_id not in coleccion1:
                await interaction.followup.send(f"❌ You don't have a card named {card}.", ephemeral=True)
                return
    
            if carta2_id not in coleccion2:
                await interaction.followup.send(
                    f"❌ {user.mention}, you don't have a card named {carta2}. Trade cancelled."
                )
                return
    
            # ---- Pedir confirmación al usuario 1 ----
            await interaction.followup.send(
                f"{user.mention} offers their card **{carta2_obj['nombre']}** in exchange of your card **{carta1_obj['nombre']}**.\n"
                "Write `accept` or `reject` (you have two minutes)."
            )
    
            # Solo acepta mensaje del usuario 1 con "accept" o "reject"
            def check_usuario1(m):
                return (m.author.id == interaction.user.id 
                        and m.channel.id == interaction.channel_id 
                        and m.content.lower() in ["accept", "reject"])
    
            try:
                respuesta1 = await self.bot.wait_for("message", timeout=120, check=check_usuario1)
            except asyncio.TimeoutError:
                await interaction.followup.send("⌛ Time's up. The trade has been cancelled.")
                return
    
            if respuesta1.content.lower() == "reject":
                await interaction.followup.send(
                    f"❌ {user.mention}, {interaction.user.display_name} has rejected the trade."
                )
                return
    
            # ---- Intercambio final (sin modificar tu logica original) ----
            propiedades[str(interaction.guild.id)][str(interaction.user.id)].remove(carta1_id)
            propiedades[str(interaction.guild.id)][str(user.id)].remove(carta2_id)
            propiedades[str(interaction.guild.id)][str(interaction.user.id)].append(carta2_id)
            propiedades[str(interaction.guild.id)][str(user.id)].append(carta1_id)
    
            guardar_propiedades(propiedades)
    
            # ---- Mensaje de confirmación ----
            await interaction.followup.send(
                f"✅ Trade successful:\n"
                f"- {interaction.user.mention} traded **{carta1_obj['nombre']}** and received **{carta2_obj['nombre']}**\n"
                f"- {user.mention} traded **{carta2_obj['nombre']}** and received **{carta1_obj['nombre']}**"
            )
    
        except Exception as e:
            print(f"[ERROR] trade: {type(e).__name__} - {e}")
            try:
                await interaction.followup.send("An error happened during the trade.", ephemeral=True)
            except Exception:
                pass
            

async def setup(bot):
    await bot.add_cog(Cartas(bot))
