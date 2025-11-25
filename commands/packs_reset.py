import datetime
import discord
from discord.ext import commands, tasks
from core.firebase_storage import cargar_packs, guardar_packs

class PacksReset(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Iniciar la tarea de reset
        self.reset_packs_daily.start()

    def cog_unload(self):
        # Detener la tarea si se descarga el cog
        self.reset_packs_daily.cancel()

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0))
    async def reset_packs_daily(self):
        """
        Reset diario de packs_opened a las 00:00.
        """
        packs = cargar_packs()
        for servidor_id, servidor_packs in packs.items():
            for usuario_id, usuario_packs in servidor_packs.items():
                usuario_packs["packs_opened"] = 0
        guardar_packs(packs)
        print("[PACK RESET] packs_opened reset to 0 for all users.")

    @reset_packs_daily.before_loop
    async def before_reset(self):
        # Esperar a que el bot esté listo antes de iniciar la tarea
        await self.bot.wait_until_ready()