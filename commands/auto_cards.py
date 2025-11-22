import discord, random, asyncio, datetime, os
from discord.ext import commands
from discord import app_commands
from core.gist_settings import cargar_settings, guardar_settings
from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta


class CartasAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        # Bot y carga inicial de settings desde Gist
        self.bot = bot
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}

        # Diccionario de tareas por servidor (gid -> asyncio.Task)
        self.tasks: dict[str, asyncio.Task] = {}

        # Bandera para indicar que hay cambios pendientes de guardar
        self._pending_save: bool = False

        # Arrancar el bucle de autosave (guarda cada 60s si hay cambios)
        asyncio.create_task(self._autosave_loop())

        print("[INFO] CartasAuto inicializado.")

        # Recrear tareas activas desde settings (por si el bot se reinicia)
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                print(f"[INFO] Activando cartas automáticas en servidor {gid}.")
                # Creamos tarea de spawn por servidor
                self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(int(gid)))

    def cog_unload(self):
        """
        Al descargar el cog:
        - Cancelar tareas activas.
        - Marcar como desactivado en settings y resetear contadores.
        - No guardar inmediatamente, solo marcar cambios y dejar que autosave haga el resto.
        """
        print("[INFO] CartasAuto descargado. Cancelando tareas...")
        for gid, task in list(self.tasks.items()):
            try:
                task.cancel()
            except Exception:
                pass
        self.tasks.clear()

        # Marcar configuración como desactivada para todos los servidores
        for gid in list(self.settings["guilds"].keys()):
            self.settings["guilds"][gid]["enabled"] = False
            self.settings["guilds"][gid]["count"] = 0
            self.settings["guilds"][gid].pop("next_spawn", None)

        # Marcar que hay cambios, autosave se encargará de subirlos
        self.marcar_cambios()

    # ================================================================
    # Sistema de autosave (cola de guardado)
    # ================================================================
    def marcar_cambios(self):
        """
        Marca que hay cambios pendientes para guardar en el Gist.
        No guarda inmediatamente; el bucle _autosave_loop lo hará pasado un tiempo.
        """
        self._pending_save = True

    async def _autosave_loop(self):
        """
        Bucle de autosave:
        - Cada 60 segundos, si hay cambios pendientes, sube settings al Gist.
        - Esto agrupa múltiples modificaciones y reduce peticiones PATCH.
        """
        while True:
            await asyncio.sleep(60)
            if self._pending_save:
                try:
                    guardar_settings(self.settings)
                    print("[OK] Autosave ejecutado en Gist.")
                except Exception as e:
                    # Si hay error (incluido rate limit), lo logueamos y
                    # mantenemos la bandera para reintentar en el siguiente ciclo.
                    print("[ERROR] autosave:", e)
                else:
                    # Solo si guardó correctamente, limpiamos la bandera
                    self._pending_save = False

    # ================================================================
    # SLASH COMMAND: auto_cards (activar/desactivar/configurar)
    # ================================================================
    @app_commands.command(
        name="auto_cards",
        description="Activates or deactivates automatic card spawning."
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
        # Defer para evitar timeouts mientras procesamos
        await interaction.response.defer(ephemeral=False)

        gid = str(interaction.guild_id)
        config = self.settings["guilds"].get(gid)

        # ---------------------------
        # DESACTIVAR (si no hay argumentos)
        # ---------------------------
        if canal is None and max_horas is None and max_diarias is None:
            # Desactivar si estaba activo
            if config and config.get("enabled"):
                config["enabled"] = False

                # Cancelar tarea del servidor si existía
                if gid in self.tasks:
                    try:
                        self.tasks[gid].cancel()
                    except Exception:
                        pass
                    self.tasks.pop(gid, None)

                # Reset de contadores y próxima aparición
                config["count"] = 0
                config.pop("next_spawn", None)

                # Marcar cambios (no guardar inmediato)
                self.marcar_cambios()

                await interaction.followup.send("❌ Automatic card spawning deactivated.")
            else:
                # Ya estaba desactivado
                await interaction.followup.send(
                    "⚠️ Automatic card spawning is already deactivated. Use `/auto_cards` with a channel."
                )
            return

        # ---------------------------
        # ACTIVAR / RECONFIGURAR
        # ---------------------------
        if canal is None:
            # Para activar, el canal es obligatorio
            await interaction.followup.send(
                "⚠️ You must specify the channel: `/auto_cards #channel (max_hour_wait) (max_daily_number)`"
            )
            return

        # Valores por defecto si no se especifican
        if max_horas is None:
            max_horas = 5
        if max_diarias is None:
            max_diarias = 5

        # Configuración del servidor en memoria
        self.settings["guilds"][gid] = {
            "enabled": True,
            "channel_id": canal.id,
            "interval": [0, max_horas],  # espera entre 0 y max_horas
            "max_daily": max_diarias,    # máximo de cartas por día
            "count": 0,                  # cartas aparecidas hoy
            "last_reset": datetime.date.today().isoformat()
        }

        # Marcar cambios para que autosave los suba después
        self.marcar_cambios()

        # Crear o recrear la tarea de spawn para este servidor
        # Nota: interaction.guild_id es int, lo convertimos a int para el loop
        self.tasks[gid] = asyncio.create_task(self.spawn_for_guild(interaction.guild_id))

        await interaction.followup.send(
            f"✅ Automatic card spawning enabled in {canal.mention}, "
            f"every 0–{max_horas}h, max {max_diarias} cards/day."
        )

    # ================================================================
    # SLASH COMMAND: estado_cartas (estado actual)
    # ================================================================
    @app_commands.command(
        name="estado_cartas",
        description="Shows the status of automatic card spawning."
    )
    async def estado_cartas_slash(self, interaction: discord.Interaction):
        """
        Muestra el estado del sistema de cartas automáticas para el servidor actual:
        - Canal configurado, intervalo, máximo diario, cuántas van y tiempo restante hasta la próxima.
        """
        gid = str(interaction.guild_id)
        config = self.settings["guilds"].get(gid)

        # Si está desactivado o no hay configuración
        if not config or not config.get("enabled"):
            await interaction.response.send_message("❌ Automatic card spawning is deactivated.")
            return

        # Calcular texto de tiempo restante hasta la siguiente aparición
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
                    # next_spawn en pasado pero aún no disparada (pendiente)
                    tiempo_str = "Programmed, pending."
            except Exception:
                # Si falla el parseo, no rompemos la respuesta
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
    # BUCLE DE TAREA POR SERVIDOR (spawn_for_guild)
    # ================================================================
    async def spawn_for_guild(self, gid: int):
        """
        Bucle principal por servidor:
        - Resetea contador diario si cambia el día.
        - Programa la siguiente aparición con espera aleatoria dentro del intervalo.
        - Envía la carta al canal configurado y actualiza el contador.
        - Todos los cambios se marcan para autosave en vez de guardarse inmediatamente.
        """
        while True:
            # Leer configuración actual del servidor
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                # Si no está habilitado, dormir un poco y volver a comprobar
                await asyncio.sleep(60)
                continue

            # Reset diario: al cambiar la fecha, reiniciamos contador
            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                self.marcar_cambios()

            # Si alcanzó el máximo diario, esperar y revisar más tarde
            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Programar próxima aparición: intervalo aleatorio 0..max_horas
            wait = random.randint(0, config["interval"][1] * 3600)
            next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
            config["next_spawn"] = next_spawn
            self.marcar_cambios()

            # Dormimos hasta el próximo spawn
            await asyncio.sleep(wait)

            # Comprobar si sigue habilitado
            if not config.get("enabled"):
                continue

            # Obtener guild y canal desde el bot (ambos pueden ser None si no están en caché)
            guild = self.bot.get_guild(gid)
            if not guild:
                # Si no encontramos la guild, esperar y seguir
                await asyncio.sleep(10)
                continue

            channel = guild.get_channel(config["channel_id"])
            if not channel:
                # Si el canal fue borrado o no accesible, desactivar para evitar bucles vacíos
                config["enabled"] = False
                self.marcar_cambios()
                continue

            # Cargar base de cartas y elegir una aleatoria
            cartas = cargar_cartas()
            if not cartas:
                # Si no hay cartas, esperar un poco y reintentar
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
    await bot.add_cog(CartasAuto(bot))