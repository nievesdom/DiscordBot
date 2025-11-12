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
        self.reclamada = False

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.reclamada:
                await interaction.response.send_message("Esta carta ya fue reclamada en este mensaje.", ephemeral=True)
                return

            usuario_id = str(interaction.user.id)
            servidor_id = str(interaction.guild.id)

            cartas_guardadas = cargar_cartas()
            carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
            if carta_info is None:
                await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
                return

            propiedades = cargar_propiedades()
            propiedades.setdefault(servidor_id, {}).setdefault(usuario_id, []).append(self.carta_id)
            guardar_propiedades(propiedades)

            # Reconstruir embed con formato unificado
            nombre_carta = carta_info.get("nombre", f"ID {self.carta_id}")
            rareza = carta_info.get("rareza", "N")
            color = self.colores.get(rareza, 0x8c8c8c)

            self.embed = discord.Embed(
                title=f"{nombre_carta} [{rareza}]",
                color=color,
                description=(
                    f"**Atributo:** {carta_info.get('atributo', '—')}\n"
                    f"**Tipo:** {carta_info.get('tipo', '—')}\n"
                    f"❤️ {carta_info.get('health', '—')} | ⚔️ {carta_info.get('attack', '—')} | "
                    f"🛡️ {carta_info.get('defense', '—')} | 💨 {carta_info.get('speed', '—')}"
                )
            )
            self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
            self.reclamada = True
            self.clear_items()  # Quita el botón tras reclamar

            archivo = None
            if self.imagen_ruta and self.imagen_ruta.startswith("http"):
                self.embed.set_image(url=self.imagen_ruta)
            elif self.imagen_ruta and os.path.exists(self.imagen_ruta):
                archivo = discord.File(self.imagen_ruta, filename="carta.png")
                self.embed.set_image(url="attachment://carta.png")
            else:
                self.embed.description += "\n⚠️ Imagen no encontrada."

            await interaction.response.edit_message(
                embed=self.embed,
                attachments=[archivo] if archivo else [],
                view=self
            )

            await interaction.followup.send(
                f"{interaction.user.mention} ha reclamado **{nombre_carta}**",
                ephemeral=False
            )

            print(f"[OK] {interaction.user.display_name} reclamó '{nombre_carta}' en {interaction.guild.name}.")

        except Exception as e:
            print(f"[ERROR] en ReclamarCarta: {type(e).__name__} - {e}")
            try:
                await interaction.response.send_message("Ocurrió un error al reclamar la carta.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("Ocurrió un error al reclamar la carta.", ephemeral=True)
