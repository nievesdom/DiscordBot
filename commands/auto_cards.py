import discord, random, asyncio
from discord.ext import commands
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
    async def activar_cartas(self, ctx, canal: discord.TextChannel, horas_min: int = 0, horas_max: int = 5, max_diarias: int = 5):
        # Guardar configuración en settings.json para este servidor
        gid = str(ctx.guild.id)
        self.settings["guilds"][gid] = {
            "enabled": True,             # Activado
            "channel_id": canal.id,      # Canal donde aparecerán las cartas
            "interval": [horas_min, horas_max],  # Intervalo en horas (mínimo y máximo)
            "max_daily": max_diarias,    # Máximo de cartas al día
            "count": 0                   # Contador de cartas enviadas hoy
        }
        guardar_settings(self.settings)
        # Crear tarea independiente para este servidor
        self.bot.loop.create_task(self.spawn_for_guild(ctx.guild.id))
        await ctx.send(f"✅ Cartas automáticas activadas en {canal.mention}, cada {horas_min}-{horas_max} horas, máximo {max_diarias} al día.")

    async def spawn_for_guild(self, gid: int):
        """Tarea independiente para cada servidor"""
        while True:
            config = self.settings["guilds"].get(str(gid))
            if not config or not config.get("enabled"):
                # Si no está activado, esperar un minuto y volver a comprobar
                await asyncio.sleep(60)
                continue

            # Si ya se alcanzó el máximo diario, esperar un minuto
            if config["count"] >= config["max_daily"]:
                await asyncio.sleep(60)
                continue

            # Esperar un tiempo aleatorio entre el intervalo configurado
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

