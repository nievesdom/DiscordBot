import discord, random, asyncio, datetime, os
from discord.ext import commands
from discord import app_commands
from core.gist_settings import cargar_settings, guardar_settings
from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta

class CartasAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}

        self.tasks = {}
        print("[INFO] CartasAuto inicializado.")

        # Recrear tareas activas
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                print(f"[INFO] Activando cartas automáticas en servidor {gid}.")
                self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(int(gid)))

    def cog_unload(self):
        print("[INFO] CartasAuto descargado. Cancelando tareas...")
        for gid, task in list(self.tasks.items()):
            try:
                task.cancel()
            except:
                pass
        self.tasks.clear()

        for gid in list(self.settings["guilds"].keys()):
            self.settings["guilds"][gid]["enabled"] = False
            self.settings["guilds"][gid]["count"] = 0
            self.settings["guilds"][gid].pop("next_spawn", None)

        guardar_settings(self.settings)

    # ======================================================================
    # SLASH COMMAND: auto_cards
    # ======================================================================

    @app_commands.command(
        name="auto_cards",
        description="Activates or deactivates automatic card spawning."
    )
    @app_commands.describe(
        canal="Channel where cards will spawn",
        max_horas="Maximum wait time in hours",
        max_diarias="Maximum cards per day"
    )
    async def auto_cards_slash(self, interaction: discord.Interaction,
                               canal: discord.TextChannel | None = None,
                               max_horas: int | None = None,
                               max_diarias: int | None = None):

        await interaction.response.defer(ephemeral=False)

        gid = str(interaction.guild_id)
        config = self.settings["guilds"].get(gid)

        # ---------------------------
        # DESACTIVAR
        # ---------------------------
        if canal is None and max_horas is None and max_diarias is None:
            if config and config.get("enabled"):
                config["enabled"] = False
                if gid in self.tasks:
                    try:
                        self.tasks[gid].cancel()
                    except:
                        pass
                    self.tasks.pop(gid, None)

                config["count"] = 0
                config.pop("next_spawn", None)
                guardar_settings(self.settings)

                await interaction.followup.send("❌ Automatic card spawning deactivated.")
            else:
                await interaction.followup.send(
                    "⚠️ Automatic card spawning is already deactivated. Use `/auto_cards` with a channel."
                )
            return

        # ---------------------------
        # ACTIVAR / RECONFIGURAR
        # ---------------------------
        if canal is None:
            await interaction.followup.send(
                "⚠️ You must specify the channel: `/auto_cards #channel (max_hour_wait) (max_daily_number)`"
            )
            return

        if max_horas is None:
            max_horas = 5
        if max_diarias is None:
            max_diarias = 5

        self.settings["guilds"][gid] = {
            "enabled": True,
            "channel_id": canal.id,
            "interval": [0, max_horas],
            "max_daily": max_diarias,
            "count": 0,
            "last_reset": datetime.date.today().isoformat()
        }

        guardar_settings(self.settings)

        self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(interaction.guild_id))

        await interaction.followup.send(
            f"✅ Automatic card spawning enabled in {canal.mention}, "
            f"every 0–{max_horas}h, max {max_diarias} cards/day."
        )

    # ======================================================================
    # SLASH COMMAND: estado_cartas
    # ======================================================================

    @app_commands.command(
        name="estado_cartas",
        description="Shows the status of automatic card spawning."
    )
    async def estado_cartas_slash(self, interaction: discord.Interaction):

        gid = str(interaction.guild_id)
        config = self.settings["guilds"].get(gid)

        if not config or not config.get("enabled"):
            await interaction.response.send_message("❌ Automatic card spawning is deactivated.")
            return

        tiempo_str = "No more cards today."
        if "next_spawn" in config:
            try:
                next_spawn = datetime.datetime.fromisoformat(config["next_spawn"])
                delta = next_spawn - datetime.datetime.now()

                if delta.total_seconds() > 0:
                    minutos = int(delta.total_seconds() // 60)
                    horas = minutos // 60
                    minutos_restantes = minutos % 60
                    tiempo_str = f"{horas}h {minutos_restantes}m"
                else:
                    tiempo_str = "Programmed, pending."
            except:
                pass

        await interaction.response.send_message(
            f"📊 **Automatic card spawning status:**\n"
            f"- Channel: <#{config['channel_id']}>\n"
            f"- Interval: 0–{config['interval'][1]} hours\n"
            f"- Max daily cards: {config['max_daily']}\n"
            f"- Cards spawned today: {config['count']}\n"
            f"- Next card in: {tiempo_str}"
        )

    # ======================================================================
    # TASK LOOP
    # ======================================================================

    async def spawn_for_guild(self, gid: int):
        while True:
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                await asyncio.sleep(60)
                continue

            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                guardar_settings(self.settings)

            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            wait = random.randint(0, config["interval"][1] * 3600)
            next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
            config["next_spawn"] = next_spawn
            guardar_settings(self.settings)

            await asyncio.sleep(wait)

            if not config.get("enabled"):
                continue

            guild = self.bot.get_guild(gid)
            if not guild:
                continue
            channel = guild.get_channel(config["channel_id"])
            if not channel:
                continue

            cartas = cargar_cartas()
            if not cartas:
                await asyncio.sleep(30)
                continue

            carta = random.choice(cartas)
            carta_id = carta.get("id")

            colores = {
                "UR": 0x8841f2,
                "KSR": 0xabfbff,
                "SSR": 0x57ffae,
                "SR": 0xfcb63d,
                "R": 0xfc3d3d,
                "N": 0x8c8c8c
            }

            atributos = {
                "heart": "心",
                "technique": "技",
                "body": "体",
                "light": "陽",
                "shadow": "陰",
            }

            tipos = {
                "attack": "⚔️ Attack",
                "defense": "🛡️ Defense",
                "recovery": "❤️ Recovery",
                "support": "✨ Support",
            }

            rareza = carta.get("rareza", "N")
            color = colores.get(rareza, 0x8c8c8c)

            atributo_raw = str(carta.get("atributo", "—")).lower()
            tipo_raw = str(carta.get("tipo", "—")).lower()

            attr_symbol = atributos.get(atributo_raw, "")
            attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
            atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
            tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

            embed = discord.Embed(
                title=carta.get("nombre", "Carta"),
                color=color,
                description=(
                    f"**Attribute:** {atributo_fmt}\n"
                    f"**Type:** {tipo_fmt}\n"
                    f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                    f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}"
                )
            )

            ruta_img = carta.get("imagen")
            archivo = None

            if ruta_img and isinstance(ruta_img, str) and ruta_img.startswith("http"):
                embed.set_image(url=ruta_img)
            elif ruta_img and isinstance(ruta_img, str) and os.path.exists(ruta_img):
                archivo = discord.File(ruta_img, filename="carta.png")
                embed.set_image(url="attachment://carta.png")
            else:
                embed.description += "\n⚠️ Card image not found."

            vista = ReclamarCarta(carta_id, embed, ruta_img)

            try:
                if archivo:
                    await channel.send(file=archivo, embed=embed, view=vista)
                else:
                    await channel.send(embed=embed, view=vista)
            except Exception as e:
                print(f"[ERROR] Spawn error in guild {gid}: {type(e).__name__} - {e}")
                await asyncio.sleep(30)
                continue

            config["count"] += 1
            guardar_settings(self.settings)

async def setup(bot):
    await bot.add_cog(CartasAuto(bot))
