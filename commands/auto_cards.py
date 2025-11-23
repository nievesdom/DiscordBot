"""
CartasAuto: sistema de aparición automática de cartas en canales de Discord.

Características principales:
- Permite activar/desactivar el spawn automático de cartas por servidor.
- Usa un sistema de autosave para reducir llamadas al Gist (se guarda cada 60s si hay cambios).
- Captura errores de límite de GitHub y avisa en el canal configurado del servidor.
"""

import discord, random, asyncio, datetime, os
from discord.ext import commands
from discord import app_commands
from core.firebase_storage import cargar_settings, guardar_settings

from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta
from github.GithubException import RateLimitExceededException


class CartasAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        # Guardamos referencia al bot
        self.bot = bot

        # Cargamos settings desde el Gist remoto
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}

        # Diccionario de tareas activas por servidor (gid -> asyncio.Task)
        self.tasks: dict[str, asyncio.Task] = {}

        # Bandera para indicar si hay cambios pendientes de guardar
        self._pending_save: bool = False

        # Arrancamos el bucle de autosave (cada 60s guarda si hay cambios)
        asyncio.create_task(self._autosave_loop())

        print("[INFO] CartasAuto inicializado.")

        # Recreamos tareas activas desde settings (por si el bot se reinicia)
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                print(f"[INFO] Activando cartas automáticas en servidor {gid}.")
                self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(int(gid)))

    def cog_unload(self):
        """
        Al descargar el cog:
        - Cancelamos todas las tareas activas.
        - Marcamos como desactivado en settings y reseteamos contadores.
        - No guardamos inmediatamente, solo marcamos cambios y dejamos que autosave lo suba.
        """
        print("[INFO] CartasAuto descargado. Cancelando tareas...")
        for gid, task in list(self.tasks.items()):
            try:
                task.cancel()
            except Exception:
                pass
        self.tasks.clear()

        for gid in list(self.settings["guilds"].keys()):
            self.settings["guilds"][gid]["enabled"] = False
            self.settings["guilds"][gid]["count"] = 0
            self.settings["guilds"][gid].pop("next_spawn", None)

        self.marcar_cambios()

    # ================================================================
    # Sistema de autosave
    # ================================================================
    def marcar_cambios(self):
        """Marca que hay cambios pendientes para guardar en el Gist."""
        self._pending_save = True

    async def _autosave_loop(self):
        """
        Bucle de autosave:
        - Cada 60 segundos, si hay cambios pendientes, intenta guardarlos en el Gist.
        - Si se excede el límite de GitHub, avisa en los canales configurados.
        """
        while True:
            await asyncio.sleep(60)
            if self._pending_save:
                try:
                    guardar_settings(self.settings)
                    print("[OK] Autosave ejecutado en Gist.")
                except RateLimitExceededException as e:
                    print("[ERROR] Rate limit excedido:", e)
                    # Avisamos en todos los servidores activos
                    for gid, config in self.settings["guilds"].items():
                        if config.get("enabled"):
                            guild = self.bot.get_guild(int(gid))
                            if guild:
                                channel = guild.get_channel(config["channel_id"])
                                if channel:
                                    try:
                                        await channel.send(
                                            "⚠️ The request limit has been reached."
                                            "Changes won't be saved until the limit is released, please wait about an hour before using this bot."
                                        )
                                    except Exception as send_error:
                                        print(f"[ERROR] No se pudo enviar aviso en guild {gid}: {send_error}")
                    # Mantenemos la bandera para reintentar en el siguiente ciclo
                    self._pending_save = True
                except Exception as e:
                    print("[ERROR] autosave:", e)
                else:
                    # Si guardó correctamente, limpiamos la bandera
                    self._pending_save = False

    # ================================================================
    # SLASH COMMAND: auto_cards
    # ================================================================
    @app_commands.default_permissions(administrator=True)  # Solo visible para administradores
    @app_commands.checks.has_permissions(administrator=True)  # Solo ejecutable por administradores
    @app_commands.command(
        name="auto_cards",
        description="**[Administrator only]** Activates or deactivates automatic card spawning."
    )
    @app_commands.describe(
        canal="Channel where cards will spawn",
        max_horas="Maximum wait time in hours",
        max_diarias="Maximum cards per day"
    )
    async def auto_cards_slash(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        max_horas: int | None = None,
        max_diarias: int | None = None
    ):
        """
        Slash command para activar/desactivar el sistema de cartas automáticas.
        - Si no se pasan argumentos, desactiva.
        - Si se pasa canal y parámetros, activa o reconfigura.
        """
        await interaction.response.defer(ephemeral=False)
        gid = str(interaction.guild_id)
        config = self.settings["guilds"].get(gid)

        # Caso: desactivar
        if canal is None and max_horas is None and max_diarias is None:
            if config and config.get("enabled"):
                config["enabled"] = False
                if gid in self.tasks:
                    try:
                        self.tasks[gid].cancel()
                    except Exception:
                        pass
                    self.tasks.pop(gid, None)
                config["count"] = 0
                config.pop("next_spawn", None)
                self.marcar_cambios()
                await interaction.followup.send("❌ Automatic card spawning deactivated.")
            else:
                await interaction.followup.send(
                    "⚠️ Automatic card spawning is already deactivated. Use `/auto_cards` with a channel to activate it."
                )
            return

        # Caso: activar/reconfigurar
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

        self.marcar_cambios()
        self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(interaction.guild_id))

        await interaction.followup.send(
            f"✅ Automatic card spawning enabled in {canal.mention}, "
            f"every 0–{max_horas}h, max {max_diarias} cards/day."
        )

    # ================================================================
    # SLASH COMMAND: estado_cartas
    # ================================================================
    @app_commands.default_permissions(administrator=True)  # Solo visible para administradores
    @app_commands.checks.has_permissions(administrator=True)  # Solo ejecutable por administradores
    @app_commands.command(
        name="spawning_status",
        description="**[Administrator only]** Shows the status of automatic card spawning."
    )
    async def estado_cartas_slash(self, interaction: discord.Interaction):
        """
        Muestra el estado actual del sistema de cartas automáticas en el servidor:
        - Canal configurado, intervalo, máximo diario, cartas lanzadas y tiempo hasta la próxima.
        """
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
            except Exception:
                pass

        await interaction.response.send_message(
            f"📊 **Automatic card spawning status:**\n"
            f"- Channel: <#{config['channel_id']}>\n"
            f"- Interval: 0–{config['interval'][1]} hours\n"
            f"- Max daily cards: {config['max_daily']}\n"
            f"- Cards spawned today: {config['count']}\n"
            f"- Next card in: {tiempo_str}"
        )

    # ================================================================
    # Bucle de spawn por servidor
    # ================================================================
    async def spawn_for_guild(self, gid: int):
        """
        Bucle principal por servidor:
        - Resetea contador diario si cambia el día.
        - Programa la siguiente aparición con espera aleatoria.
        - Envía la carta al canal configurado y actualiza el contador.
        """
        while True:
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                await asyncio.sleep(60)
                continue

            # Reset diario si cambia el día
            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                self.marcar_cambios()

            # Si alcanzó el máximo diario, esperar y revisar más tarde
            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Programar próxima aparición con espera aleatoria dentro del intervalo
            wait = random.randint(0, config["interval"][1] * 3600)
            next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
            config["next_spawn"] = next_spawn
            self.marcar_cambios()

            # Dormir hasta el próximo spawn
            await asyncio.sleep(wait)

            # Comprobar si sigue habilitado
            if not config.get("enabled"):
                continue

            # Obtener guild y canal
            guild = self.bot.get_guild(gid)
            if not guild:
                await asyncio.sleep(10)
                continue

            channel = guild.get_channel(config["channel_id"])
            if not channel:
                # Si el canal no existe/acceso denegado, desactivar para evitar bucles vacíos
                config["enabled"] = False
                self.marcar_cambios()
                continue

            # Cargar base de cartas y elegir una aleatoria
            cartas = cargar_cartas()
            if not cartas:
                await asyncio.sleep(30)
                continue

            carta = random.choice(cartas)
            carta_id = carta.get("id")

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

            # Preparar estilos y campos del embed
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

            # Imagen: remota o adjunta si es local; si no existe, avisar en la descripción
            ruta_img = carta.get("imagen")
            archivo = None
            if ruta_img and isinstance(ruta_img, str) and ruta_img.startswith("http"):
                embed.set_image(url=ruta_img)
            elif ruta_img and isinstance(ruta_img, str) and os.path.exists(ruta_img):
                archivo = discord.File(ruta_img, filename="carta.png")
                embed.set_image(url="attachment://carta.png")
            else:
                embed.description += "\n⚠️ Card image not found."

            # Vista para reclamar la carta (usa tu clase existente)
            vista = ReclamarCarta(carta_id, embed, ruta_img)

            # Enviar al canal; si falla, registrar el error y continuar
            try:
                if archivo:
                    await channel.send(file=archivo, embed=embed, view=vista)
                else:
                    await channel.send(embed=embed, view=vista)
            except Exception as e:
                print(f"[ERROR] Spawn error in guild {gid}: {type(e).__name__} - {e}")
                await asyncio.sleep(30)
                continue

            # Incrementar contador de cartas diarias
            config["count"] += 1
            # Marcar cambios para que autosave suba el nuevo estado
            self.marcar_cambios()


# Setup para registrar el cog en el bot
async def setup(bot: commands.Bot):
    # Registrar el cog en el bot al cargar la extensión
    await bot.add_cog(CartasAuto(bot))
