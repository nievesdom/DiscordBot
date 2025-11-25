import datetime
from discord.ext import commands, tasks
from core.firebase_storage import cargar_packs, guardar_packs

class PacksReset(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reset_packs_daily.start()

    def cog_unload(self):
        self.reset_packs_daily.cancel()

    @tasks.loop(time=datetime.time(hour=18, minute=0, second=0))
    async def reset_packs_daily(self):
        """
        Reset diario de packs_opened a las 00:00 y log en canal de administración.
        """
        packs = cargar_packs()
        total_reseteados = 0

        for servidor_id, servidor_packs in packs.items():
            for usuario_id, usuario_packs in servidor_packs.items():
                usuario_packs["packs_opened"] = 0
                total_reseteados += 1

        guardar_packs(packs)
        print(f"[PACK RESET] packs_opened reset to 0 for {total_reseteados} users.")

        # Enviar log al canal de administración
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = self.bot.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(
                        f"[PACK RESET] Se han reseteado los packs_opened de {total_reseteados} usuarios."
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

    @reset_packs_daily.before_loop
    async def before_reset(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(PacksReset(bot))
