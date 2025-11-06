import discord
import os
from core.gist_propiedades import cargar_propiedades, guardar_propiedades  # Sistema remoto
from core.cartas import cargar_cartas


# Reclamar una carta
class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=60)  # El botón expira tras 1 minuto
        self.carta_id = carta_id  # ID de la carta mostrada
        self.embed = embed  # Embed que se actualizará al reclamar
        self.imagen_ruta = imagen_ruta  # Ruta o URL de la imagen
        self.reclamada = False  # Estado de la carta (si ya fue reclamada en este mensaje)

    # Botón para reclamar la carta
    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo comprobamos si esta instancia ya fue reclamada
        if self.reclamada:
            await interaction.response.send_message("Esta carta ya ha sido reclamada en este mensaje.", ephemeral=True)
            return

        usuario_id = str(interaction.user.id)
        servidor_id = str(interaction.guild.id)

        # Cargar todas las cartas
        cartas_guardadas = cargar_cartas()
        carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
        if carta_info is None:
            await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
            return

        # Cargar propiedades desde el Gist remoto
        propiedades = cargar_propiedades()

        # Inicializar propiedades si no existen
        if servidor_id not in propiedades:
            propiedades[servidor_id] = {}
        if usuario_id not in propiedades[servidor_id]:
            propiedades[servidor_id][usuario_id] = []

        # Asignar carta al usuario (ya no comprobamos si otro la tiene)
        propiedades[servidor_id][usuario_id].append(self.carta_id)
        guardar_propiedades(propiedades)  # Guarda en el Gist remoto

        # Actualizar el embed
        self.embed.color = discord.Color.from_rgb(0, 0, 0)
        self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
        self.reclamada = True
        self.clear_items()  # Eliminar el botón

        # Mostrar subtítulo con el tipo de carta
        if "tipo" in carta_info:
            self.embed.title = f"{carta_info['nombre']} — {carta_info['tipo']}"
        else:
            self.embed.title = carta_info["nombre"]

        # Mostrar imagen (URL o archivo local)
        if self.imagen_ruta and self.imagen_ruta.startswith("http"):
            self.embed.set_image(url=self.imagen_ruta)
            archivo = None
        elif self.imagen_ruta and os.path.exists(self.imagen_ruta):
            archivo = discord.File(self.imagen_ruta, filename="carta.png")
            self.embed.set_image(url="attachment://carta.png")
        else:
            archivo = None
            self.embed.description = "⚠️ Imagen no encontrada."

        # Editar el mensaje original (respuesta principal)
        await interaction.response.edit_message(embed=self.embed, attachments=[archivo] if archivo else [], view=self)

        # Confirmación al usuario (segunda respuesta)
        await interaction.followup.send(
            f"{interaction.user.mention} ha obtenido **{carta_info['nombre']}** ({carta_info.get('tipo', 'sin tipo')})",
            ephemeral=False
        )
