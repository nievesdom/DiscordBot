import discord
import os
from core.propiedades import propiedades, guardar_propiedades

# Reclamar una carta
class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=60)  # El botón expira tras 1 minuto
        self.carta_id = carta_id  # ID de la carta mostrada
        self.embed = embed  # Embed que se actualizará al reclamar
        self.imagen_ruta = imagen_ruta  # Ruta de la imagen local
        self.reclamada = False  # Estado de la carta (si ya fue reclamada)

    # Botón para reclamar la carta
    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.reclamada:
            await interaction.response.send_message("Esta carta ya ha sido reclamada.", ephemeral=True)
            return

        usuario_id = str(interaction.user.id)
        servidor_id = str(interaction.guild.id)

        # Cargar todas las cartas
        cartas_guardadas = cargar_cartas()
        carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
        if carta_info is None:
            await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
            return

        # Inicializar propiedades si no existen
        if servidor_id not in propiedades:
            propiedades[servidor_id] = {}
        if usuario_id not in propiedades[servidor_id]:
            propiedades[servidor_id][usuario_id] = []

        # Verificar si la carta ya fue reclamada por alguien
        for persona in propiedades[servidor_id]:
            if self.carta_id in propiedades[servidor_id][persona]:
                await interaction.response.send_message("Esa carta ya tiene dueño.", ephemeral=True)
                return

        # Asignar carta al usuario
        propiedades[servidor_id][usuario_id].append(self.carta_id)
        guardar_propiedades()

        # Actualizar el embed: cambiar color a negro y mostrar quién la reclamó
        self.embed.color = discord.Color.dark_theme()
        self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
        self.reclamada = True
        self.clear_items()  # Eliminar el botón

        # Adjuntar imagen si existe
        archivo = discord.File(self.imagen_ruta, filename="carta.png") if self.imagen_ruta and os.path.exists(self.imagen_ruta) else None

        # Editar el mensaje original con el nuevo embed y sin botón
        await interaction.message.edit(embed=self.embed, attachments=[archivo] if archivo else None, view=self)

        # Confirmación al usuario
        await interaction.response.send_message(f"{interaction.user.mention} ha obtenido **{carta_info['nombre']}**")