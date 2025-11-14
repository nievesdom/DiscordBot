import discord, random, asyncio
from discord.ext import commands
import datetime
from core.gist_settings import cargar_settings, guardar_settings
from core.cartas import cargar_cartas
from views.reclamar import ReclamarCarta  # Importamos la vista con el botón de reclamar

class Auto_cards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cargar settings desde el gist remoto
        self.settings = cargar_settings()
        if "guilds" not in self.settings:
            self.settings["guilds"] = {}
        # Crear tareas independientes para cada servidor que ya tenga activada la función
        for gid, config in self.settings["guilds"].items():
            if config.get("enabled"):
                # Cada servidor tiene su propia tarea asincrónica
                self.bot.loop.create_task(self.spawn_for_guild(int(gid)))

    @commands.command(help="Activa cartas automáticas en este servidor")
    @commands.has_permissions(administrator=True)
    async def cartas_auto(self, ctx, canal: discord.TextChannel = None, max_horas: int = None, max_diarias: int = None):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)

        # Si no se especifica el canal → mostrar mensaje de ayuda
        if canal is None or max_horas is None or max_diarias is None:
            await ctx.send(
                "⚠️ Debes indicar el canal, las horas máximas y el máximo de cartas diarias.\n"
                "Ejemplo: `!cartas_auto #cartas 5 5`"
            )
            return

        # Si ya estaba activado → desactivar
        if config and config.get("enabled"):
            config["enabled"] = False
            guardar_settings(self.settings)
            await ctx.send(f"❌ Cartas automáticas desactivadas en {ctx.guild.name}.")
            return

        # Si estaba desactivado → activar con nuevos parámetros
        self.settings["guilds"][gid] = {
            "enabled": True,             # Activado
            "channel_id": canal.id,      # Canal donde aparecerán las cartas
            "interval": [0, max_horas],  # Intervalo en horas (mínimo siempre 0)
            "max_daily": max_diarias,    # Máximo de cartas al día
            "count": 0,                  # Contador de cartas enviadas hoy
            "last_reset": datetime.date.today().isoformat()  # Fecha del último reinicio
        }
        next_spawn = (datetime.datetime.now() + datetime.timedelta(seconds=wait)).isoformat()
        config["next_spawn"] = next_spawn
        guardar_settings(self.settings)

        # Crear tarea independiente para este servidor
        self.bot.loop.create_task(self.spawn_for_guild(ctx.guild.id))
        await ctx.send(f"✅ Cartas automáticas activadas en {canal.mention}, cada 0-{max_horas} horas, máximo {max_diarias} al día.")
        
     
    @commands.command(help="Muestra el estado de las cartas automáticas en este servidor")
    @commands.has_permissions(administrator=True)
    async def estado_cartas(self, ctx):
        gid = str(ctx.guild.id)
        config = self.settings["guilds"].get(gid)
        if not config or not config.get("enabled"):
            await ctx.send("❌ Las cartas automáticas están desactivadas en este servidor.")
            return

        # Calcular tiempo restante
        if "next_spawn" in config:
            next_spawn = datetime.datetime.fromisoformat(config["next_spawn"])
            delta = next_spawn - datetime.datetime.now()
            minutos = int(delta.total_seconds() // 60)
            horas = minutos // 60
            minutos_restantes = minutos % 60
            tiempo_str = f"{horas}h {minutos_restantes}m"
        else:
            tiempo_str = "No programado (esperando cálculo)."

        await ctx.send(
            f"📊 Estado de cartas automáticas:\n"
            f"- Canal: <#{config['channel_id']}>\n"
            f"- Intervalo: 0–{config['interval'][1]} horas\n"
            f"- Máximo diario: {config['max_daily']}\n"
            f"- Lanzadas hoy: {config['count']}\n"
            f"- Próxima carta en: {tiempo_str}"
        )
   
        

    # Proceso independiente para cada servidor
    async def spawn_for_guild(self, gid: int):
        while True:
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                await asyncio.sleep(60)
                continue

            # Reinicio diario automático a medianoche
            hoy = datetime.date.today().isoformat()
            if config.get("last_reset") != hoy:
                config["count"] = 0
                config["last_reset"] = hoy
                guardar_settings(self.settings)

            # Si ya se alcanzó el máximo diario, esperar un minuto
            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Esperar un tiempo aleatorio entre 0 y max_horas
            wait = random.randint(config["interval"][0]*3600, config["interval"][1]*3600)
            await asyncio.sleep(wait)

            # Obtener el servidor y canal configurado
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
            imagen_ruta = carta.get("imagen", None)  # si tienes guardada la ruta/URL

            # Embed inicial (sin footer, se completará al reclamar)
            embed = discord.Embed(
                title=nombre_carta,
                description="Haz clic en el botón para reclamar esta carta 🐉",
                color=0x8c8c8c
            )

            # Crear la vista con botón de reclamar
            view = ReclamarCarta(carta_id, embed, imagen_ruta)

            await channel.send(
                content="🎴 ¡Ha aparecido una carta sorpresa!",
                embed=embed,
                view=view
            )

            # Incrementar contador y guardar settings
            config["count"] += 1
            guardar_settings(self.settings)
            

async def setup(bot):
    # Registrar el Cog en el bot
    await bot.add_cog(Auto_cards(bot))

