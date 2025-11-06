import discord
import os
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas


# Reclamar una carta
class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=60)  # El botón expira tras 1 minuto
        self.carta_id = carta_id
        self.embed = embed
        self.imagen_ruta = imagen_ruta
        self.reclamada = False  # Estado local del botón

    # Botón para reclamar la carta
    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Evitar reclamos múltiples del mismo mensaje
            if self.reclamada:
                await interaction.response.send_message("Esta carta ya fue reclamada en este mensaje.", ephemeral=True)
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

            # Inicializar estructuras si no existen
            if servidor_id not in propiedades:
                propiedades[servidor_id] = {}
            if usuario_id not in propiedades[servidor_id]:
                propiedades[servidor_id][usuario_id] = []

            # Registrar la carta (permitiendo duplicados)
            propiedades[servidor_id][usuario_id].append(self.carta_id)

            # Guardar en el Gist remoto
            guardar_propiedades(propiedades)

            # Actualizar el embed
            self.embed.color = discord.Color.from_rgb(0, 0, 0)
            self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
            self.reclamada = True
            self.clear_items()  # Quita el botón tras reclamar

            # Mostrar tipo de carta (si existe)
            nombre_carta = carta_info["nombre"]
            tipo_carta = carta_info.get("tipo")
            if tipo_carta:
                self.embed.title = f"{nombre_carta} — {tipo_carta}"
            else:
                self.embed.title = nombre_carta

            # Imagen (remota o local)
            archivo = None
            if self.imagen_ruta and self.imagen_ruta.startswith("http"):
                self.embed.set_image(url=self.imagen_ruta)
            elif self.imagen_ruta and os.path.exists(self.imagen_ruta):
                archivo = discord.File(self.imagen_ruta, filename="carta.png")
                self.embed.set_image(url="attachment://carta.png")
            else:
                self.embed.description = "⚠️ Imagen no encontrada."

            # Editar mensaje original
            await interaction.response.edit_message(
                embed=self.embed,
                attachments=[archivo] if archivo else [],
                view=self
            )

            # Mensaje de confirmación público
            await interaction.followup.send(
                f"{interaction.user.mention} ha reclamado **{nombre_carta}** ({tipo_carta or 'sin tipo'})",
                ephemeral=False
            )

            print(f"[OK] {interaction.user.display_name} reclamó '{nombre_carta}' en {interaction.guild.name}.")

        except Exception as e:
            print(f"[ERROR] en ReclamarCarta: {type(e).__name__} - {e}")
            try:
                await interaction.response.send_message("Ocurrió un error al reclamar la carta.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("Ocurrió un error al reclamar la carta.", ephemeral=True)
