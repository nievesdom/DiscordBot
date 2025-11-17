import discord, random, asyncio, datetime, os
from discord.ext import commands
from core.gist_settings import cargar_settings, guardar_settings
from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta

class CartasAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cargar settings remotos
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}
        # Diccionario de tareas por servidor (guild_id -> asyncio.Task)
        self.tasks = {}
        print("[INFO] CartasAuto inicializado.")
        # Al iniciar, re-crear tareas para servidores con la función activada
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                print(f"[INFO] Activando cartas automáticas en servidor {gid}.")
                self.tasks[gid] = self.bot.loop.create_task(self.spawn_for_guild(int(gid)))

    def cog_unload(self):
        # Al descargar el Cog (apagado), cancelar tareas y limpiar estado
        print("[INFO] CartasAuto descargado. Cancelando tareas...")
        for gid, task in list(self.tasks.items()):
            try:
                task.cancel()
            except Exception:
                pass
        self.tasks.clear()
        # Limpiar atributos relacionados en settings
        for gid in list(self.settings["guilds"].keys()):
            self.settings["guilds"][gid]["enabled"] = False
            self.settings["guilds"][gid]["count"] = 0
            self.settings["guilds"][gid].pop("next_spawn", None)
        guardar_settings(self.settings)

    @commands.command(help="Activates or deactivates automatic card spawning. Activate: `y!auto_cards #channel (max_hour_wait) (max_daily_number)`. Deactivate: `y!auto_cards`", extras={"categoria": "Cards 🃏"})
    @commands.has_permissions(administrator=True)
    async def auto_cards(self, ctx, canal: discord.TextChannel = None, max_horas: int = None, max_diarias: int = None):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)

        # Caso 1: sin argumentos → desactivar
        if canal is None and max_horas is None and max_diarias is None:
            if config and config.get("enabled"):
                config["enabled"] = False
                # Cancelar tarea si existe
                if gid in self.tasks:
                    try:
                        self.tasks[gid].cancel()
                    except Exception:
                        pass
                    self.tasks.pop(gid, None)
                # Limpiar atributos
                config["count"] = 0
                config.pop("next_spawn", None)
                guardar_settings(self.settings)
                await ctx.send(f"❌ Automatic card spawning deactivated.")
            else:
                await ctx.send("⚠️ Automatic card spawning is already deactivated. If you want to activate it, use the command like this: `y!auto_cards #channel (max_hour_wait) (max_daily_number)`")
            return

        # Caso 2: activar o reconfigurar → canal obligatorio
        if canal is None:
            await ctx.send("⚠️ You must at least include in the command the channel where spawning will occur. Use like this: `y!auto_cards #channel (max_hour_wait) (max_daily_number)`")
            return

        # Valores por defecto si no se pasan horas o máximo diario
        if max_horas is None:
            max_horas = 5  # ejemplo de valor por defecto
        if max_diarias is None:
            max_diarias = 5  # ejemplo de valor por defecto

        # Activar con nuevos parámetros (mínimo de horas siempre 0)
        self.settings["guilds"][gid] = {
            "enabled": True,
            "channel_id": canal.id,
            "interval": [0, max_horas],          # intervalo en horas (min fijo 0)
            "max_daily": max_diarias,            # máximo de cartas al día
            "count": 0,                          # contador diario
            "last_reset": datetime.date.today().isoformat()
        }
        guardar_settings(self.settings)

        # Crear tarea independiente para este servidor
        self.tasks[gid] = self.bot.loop.create_task(self.spawn_for_guild(ctx.guild.id))
        await ctx.send(f"✅ Automatic card spawning enabled in {canal.mention}, every 0 to {max_horas}h for a maximum of {max_diarias} daily cards. Please, make sure I have permission to write and share media in that channel.")

    async def spawn_for_guild(self, gid: int):
        # Tarea independiente que controla apariciones automáticas en un servidor
        while True:
            config = self.settings["guilds"].get(str(gid))
            # Si no hay config o está desactivado, esperar y reintentar
            if not config or not config.get("enabled"):
                await asyncio.sleep(60)
                continue

            # Reinicio diario automático (compara fecha)
            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                guardar_settings(self.settings)

            # Si alcanzó el máximo diario, esperar
            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Calcular próxima aparición aleatoria (segundos entre 0 y max_horas)
            wait = random.randint(0, config["interval"][1] * 3600)
            next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
            config["next_spawn"] = next_spawn
            guardar_settings(self.settings)

            # Espera hasta el próximo spawn
            await asyncio.sleep(wait)

            # Verificar que sigue habilitado antes de enviar
            if not config.get("enabled"):
                continue

            # Obtener servidor y canal
            guild = self.bot.get_guild(gid)
            if not guild:
                continue
            channel = guild.get_channel(config["channel_id"])
            if not channel:
                continue

            # Elegir carta aleatoria
            cartas = cargar_cartas()
            if not cartas:
                # Si no hay cartas, saltar y no incrementar contador
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

            rareza = carta.get("rareza", "N")
            color = colores.get(rareza, 0x8c8c8c)

            atributo_raw = str(carta.get("atributo", "—")).lower()
            tipo_raw = str(carta.get("tipo", "—")).lower()

            # Formato atributo y tipo (como en tu comando carta)
            attr_symbol = atributos.get(atributo_raw, "")
            attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
            atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
            tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

            # Embed unificado
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

            # Imagen (URL remota o archivo local)
            ruta_img = carta.get("imagen")
            archivo = None
            if ruta_img and isinstance(ruta_img, str) and ruta_img.startswith("http"):
                embed.set_image(url=ruta_img)
            elif ruta_img and isinstance(ruta_img, str) and os.path.exists(ruta_img):
                archivo = discord.File(ruta_img, filename="carta.png")
                embed.set_image(url="attachment://carta.png")
            else:
                embed.description += "\n⚠️ Card image not found. Please, contact my creator."

            # Vista para reclamar (usa tu clase de views/reclamar.py)
            vista = ReclamarCarta(carta_id, embed, ruta_img)

            # Enviar mensaje con embed y vista
            try:
                if archivo:
                    await channel.send(file=archivo, embed=embed, view=vista)
                else:
                    await channel.send(embed=embed, view=vista)
            except Exception as e:
                # Si falla el envío (permisos, etc.), no incrementar contador
                print(f"[ERROR] Envío de carta automática en guild {gid}: {type(e).__name__} - {e}")
                await asyncio.sleep(30)
                continue

            # Incrementar contador y persistir
            config["count"] += 1
            guardar_settings(self.settings)

    @commands.command(help="Shows the status of automatic card spawning in the server", extras={"categoria": "Cards 🃏"})
    @commands.has_permissions(administrator=True)
    async def estado_cartas(self, ctx):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)
        if not config or not config.get("enabled"):
            await ctx.send("❌ Automatic card spawning is deactivated.")
            return

        # Calcular tiempo restante (si hay próxima aparición programada)
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
                tiempo_str = "No more cards today."

        await ctx.send(
            f"📊 Automatic card spawning status:\n"
            f"- Channel: <#{config['channel_id']}>\n"
            f"- Interval: 0–{config['interval'][1]} hours\n"
            f"- Maximum daily cards: {config['max_daily']}\n"
            f"- Cards spawned today: {config['count']}\n"
            f"- Next card in: {tiempo_str}"
        )

async def setup(bot):
    # Registrar el Cog en el bot
    await bot.add_cog(CartasAuto(bot))
