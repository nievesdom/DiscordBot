import discord, random, asyncio, datetime
from discord.ext import commands
from core.gist_settings import cargar_settings, guardar_settings
from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta

class CartasAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}
        # Diccionario de tareas activas por servidor
        self.tasks = {}
        # Feedback al iniciar
        print("[INFO] CartasAuto inicializado.")
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                print(f"[INFO] Activando cartas automáticas en servidor {gid}.")
                self.tasks[gid] = self.bot.loop.create_task(self.spawn_for_guild(int(gid)))

    def cog_unload(self):
        """Se ejecuta al descargar el Cog (por ejemplo, al apagar el bot)."""
        print("[INFO] CartasAuto descargado. Cancelando tareas...")
        for gid, task in self.tasks.items():
            task.cancel()
            # Limpiar atributos relacionados
            if gid in self.settings["guilds"]:
                self.settings["guilds"][gid].pop("next_spawn", None)
                self.settings["guilds"][gid]["enabled"] = False
                self.settings["guilds"][gid]["count"] = 0
        guardar_settings(self.settings)

    @commands.command(
        help="Activa o desactiva cartas automáticas.\nUso: !cartas_auto #canal max_horas max_diarias"
    )
    @commands.has_permissions(administrator=True)
    async def cartas_auto(self, ctx, canal: discord.TextChannel = None, max_horas: int = None, max_diarias: int = None):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)

        # Validación de parámetros
        if canal is None or max_horas is None or max_diarias is None:
            await ctx.send("⚠️ Debes indicar canal, horas máximas y máximo diario.\nEjemplo: `!cartas_auto #cartas 5 5`")
            return

        # Toggle: si ya está activado → desactivar
        if config and config.get("enabled"):
            config["enabled"] = False
            # Cancelar tarea activa
            if gid in self.tasks:
                self.tasks[gid].cancel()
                self.tasks.pop(gid)
            guardar_settings(self.settings)
            await ctx.send(f"❌ Cartas automáticas desactivadas en {ctx.guild.name}.")
            return

        # Activar con nuevos parámetros
        self.settings["guilds"][gid] = {
            "enabled": True,
            "channel_id": canal.id,
            "interval": [0, max_horas],
            "max_daily": max_diarias,
            "count": 0,
            "last_reset": datetime.date.today().isoformat()
        }
        guardar_settings(self.settings)
        # Crear tarea independiente
        self.tasks[gid] = self.bot.loop.create_task(self.spawn_for_guild(ctx.guild.id))
        await ctx.send(f"✅ Cartas automáticas activadas en {canal.mention}, cada 0-{max_horas}h, máximo {max_diarias} al día.")

    async def spawn_for_guild(self, gid: int):
        """Tarea independiente para cada servidor"""
        while True:
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                await asyncio.sleep(60)
                continue

            # Reinicio diario
            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                guardar_settings(self.settings)

            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Calcular próxima aparición
            wait = random.randint(0, config["interval"][1]*3600)
            next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
            config["next_spawn"] = next_spawn
            guardar_settings(self.settings)
            await asyncio.sleep(wait)

            guild = self.bot.get_guild(gid)
            if not guild:
                continue
            channel = guild.get_channel(config["channel_id"])
            if not channel:
                continue

            # Elegir carta aleatoria
            carta = random.choice(cargar_cartas())
            carta_id = carta.get("id")
            nombre_carta = carta.get("nombre", "Carta")
            imagen_ruta = carta.get("imagen", None)

            # Embed inicial
            embed = discord.Embed(
                title=nombre_carta,
                description="Haz clic en el botón para reclamar esta carta 🐉",
                color=0x8c8c8c
            )

            # Vista ReclamarCarta
            view = ReclamarCarta(carta_id, embed, imagen_ruta)
            await channel.send("🎴 ¡Ha aparecido una carta sorpresa!", embed=embed, view=view)

            config["count"] += 1
            guardar_settings(self.settings)

    @commands.command(help="Muestra el estado de las cartas automáticas en este servidor")
    @commands.has_permissions(administrator=True)
    async def estado_cartas(self, ctx):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)
        if not config or not config.get("enabled"):
            await ctx.send("❌ Las cartas automáticas están desactivadas en este servidor.")
            return

        # Calcular tiempo restante
        tiempo_str = "No programado."
        if "next_spawn" in config:
            try:
                next_spawn = datetime.datetime.fromisoformat(config["next_spawn"])
                delta = next_spawn - datetime.datetime.now()
                if delta.total_seconds() > 0:
                    minutos = int(delta.total_seconds() // 60)
                    horas = minutos // 60
                    minutos_restantes = minutos % 60
                    tiempo_str = f"{horas}h {minutos_restantes}m"
            except Exception:
                pass

        await ctx.send(
            f"📊 Estado de cartas automáticas:\n"
            f"- Canal: <#{config['channel_id']}>\n"
            f"- Intervalo: 0–{config['interval'][1]} horas\n"
            f"- Máximo diario: {config['max_daily']}\n"
            f"- Lanzadas hoy: {config['count']}\n"
            f"- Próxima carta en: {tiempo_str}"
        )

async def setup(bot):
    await bot.add_cog(CartasAuto(bot))
