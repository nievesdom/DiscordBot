import asyncio
import discord
from discord.ext import commands
from core.firebase_storage import cargar_mazos, guardar_mazos, cargar_cartas, cargar_propiedades

class Battle(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot
        
        
    # -----------------------------
    # Comando slash: /deck_add
    # -----------------------------
    @discord.app_commands.command(
        name="deck_add",
        description="Añade una carta a tu mazo buscando por nombre exacto (slash)."
    )
    async def add_deck_slash(self, interaction: discord.Interaction, nombre_carta: str):
        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)

        # Buscar carta por nombre exacto
        cartas = cargar_cartas()
        carta = next((c for c in cartas if c["nombre"].lower() == nombre_carta.lower()), None)

        if not carta:
            await interaction.response.send_message(
                f"❌ No existe ninguna carta con el nombre exacto '{nombre_carta}'.", ephemeral=False
            )
            return

        carta_id = str(carta["id"])

        # Comprobar si el usuario tiene la carta en propiedad
        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(servidor_id, {}).get(usuario_id, [])

        if carta_id not in map(str, cartas_usuario):
            await interaction.response.send_message(
                f"❌ No tienes la carta '{carta['nombre']}' en tu colección.", ephemeral=False
            )
            return

        # Añadir al mazo
        mazos = cargar_mazos()
        servidor_mazos = mazos.setdefault(servidor_id, {})
        mazo_usuario = servidor_mazos.setdefault(usuario_id, [])

        if carta_id in mazo_usuario:
            await interaction.response.send_message(
                f"⚠️ La carta '{carta['nombre']}' ya está en tu mazo.", ephemeral=False
            )
            return

        mazo_usuario.append(carta_id)
        guardar_mazos(mazos)

        await interaction.response.send_message(
            f"✅ Carta '{carta['nombre']}' añadida a tu mazo.", ephemeral=False
        )
        
    # -----------------------------
    # Comando prefijo: y!add_deck
    # -----------------------------
    @commands.command(name="add_deck")
    async def add_deck_prefix(self, ctx: commands.Context, *, nombre_carta: str):
        """Añade una carta al mazo del usuario buscando por nombre exacto (prefijo)."""
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # Buscar carta por nombre exacto
        cartas = cargar_cartas()
        carta = next((c for c in cartas if c["nombre"].lower() == nombre_carta.lower()), None)

        if not carta:
            await ctx.send(f"❌ No existe ninguna carta con el nombre exacto '{nombre_carta}'.")
            return

        carta_id = str(carta["id"])

        # Comprobar si el usuario tiene la carta en propiedad
        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(servidor_id, {}).get(usuario_id, [])

        if carta_id not in map(str, cartas_usuario):
            await ctx.send(f"❌ No tienes la carta '{carta['nombre']}' en tu colección.")
            return

        # Añadir al mazo
        mazos = cargar_mazos()
        servidor_mazos = mazos.setdefault(servidor_id, {})
        mazo_usuario = servidor_mazos.setdefault(usuario_id, [])

        if carta_id in mazo_usuario:
            await ctx.send(f"⚠️ La carta '{carta['nombre']}' ya está en tu mazo.")
            return

        mazo_usuario.append(carta_id)
        guardar_mazos(mazos)

        await ctx.send(f"✅ Carta '{carta['nombre']}' añadida a tu mazo.")
        
        
async def setup(bot):
    await bot.add_cog(Battle(bot))
