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
from core.firebase_storage import cargar_packs, guardar_packs, cargar_propiedades, guardar_propiedades

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
        """Bucle de autosave: guarda en Firestore cada 60s si hay cambios."""
        while True:
            await asyncio.sleep(60)
            if self._pending_save:
                try:
                    guardar_settings(self.settings)
                    print("[OK] Autosave ejecutado en Firestore.")
                    self._pending_save = False
                except Exception as e:
                    print("[ERROR] autosave:", e)
                    # Mantenemos la bandera para reintentar
                    self._pending_save = True


    # -----------------------------
    # /pack (diario)
    # -----------------------------
    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        """Permite abrir un paquete diario de 5 cartas (slash)."""
        await interaction.response.defer(ephemeral=False)

        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        packs = cargar_packs()
        servidor_packs = packs.setdefault(servidor_id, {})
        usuario_packs = servidor_packs.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

        # Cooldown: ya abrió hoy
        if usuario_packs.get("ultimo_paquete") == hoy:
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
            await interaction.followup.send("❌ No cards available.")
            return

        # Seleccionar 5 cartas aleatorias
        nuevas_cartas = random.sample(cartas, 5)
        usuario_packs["ultimo_paquete"] = hoy
        guardar_packs(packs)

        # Guardar en propiedades (colección del usuario)
        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        # Mostrar pack
        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(interaction, cartas_ids, cartas_info, interaction.user)
        embed, archivo = vista.mostrar()

        # 🔥 Enviar log al servidor/canal de logs con nombres e IDs
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = interaction.client.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {interaction.user.display_name} ({interaction.user.id}) abrió un paquete en "
                        f"{interaction.guild.name} ({interaction.guild.id}) con las cartas: {nombres_cartas}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

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

        packs = cargar_packs()
        servidor_packs = packs.setdefault(servidor_id, {})
        usuario_packs = servidor_packs.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

        if usuario_packs.get("ultimo_paquete") == hoy:
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
        usuario_packs["ultimo_paquete"] = hoy
        guardar_packs(packs)

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(ctx, cartas_ids, cartas_info, ctx.author)
        embed, archivo = vista.mostrar()

        # 🔥 Enviar log al servidor/canal de logs con nombres e IDs
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = ctx.bot.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {ctx.author.display_name} ({ctx.author.id}) abrió un paquete en "
                        f"{ctx.guild.name} ({ctx.guild.id}) con las cartas: {nombres_cartas}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)

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
