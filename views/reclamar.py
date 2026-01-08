import discord
import os

# Sustituimos propiedades por inventario
from core.firebase_storage import (
    agregar_cartas_inventario,
    cargar_inventario_usuario
)

from core.cartas import cargar_cartas


class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=900)
        self.carta_id = carta_id
        self.embed = embed
        self.imagen_ruta = imagen_ruta
        self.reclamada = False

        self.colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

    @discord.ui.button(label="Claim 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.reclamada:
                await interaction.response.send_message("Esta carta ya ha sido reclamada.", ephemeral=True)
                return

            usuario_id = str(interaction.user.id)
            servidor_id = str(interaction.guild.id)

            # Buscar carta en la base de datos
            cartas_guardadas = cargar_cartas()
            carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
            if carta_info is None:
                await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
                return

            # Guardar la carta en el inventario del usuario
            agregar_cartas_inventario(servidor_id, usuario_id, [self.carta_id])

            # Reconstruir embed
            nombre_carta = carta_info.get("nombre", f"ID {self.carta_id}")
            rareza = carta_info.get("rareza", "N")
            color = self.colores.get(rareza, 0x8c8c8c)

            atributos = {
                "heart": "心",
                "technique": "技",
                "body": "体",
                "light": "陽",
                "shadow": "陰",
            }

            tipos = {
                "attack": "⚔️ Attack",
                "defense": "🛡️ Defense",
                "recovery": "❤️ Recovery",
                "support": "✨ Support",
            }

            atributo_raw = str(carta_info.get("atributo", "—")).lower()
            tipo_raw = str(carta_info.get("tipo", "—")).lower()

            attr_symbol = atributos.get(atributo_raw, "")
            attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
            atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name

            tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

            self.embed = discord.Embed(
                title=f"{nombre_carta}",
                color=color,
                description=(
                    f"**Attribute:** {atributo_fmt}\n"
                    f"**Type:** {tipo_fmt}\n"
                    f"❤️ {carta_info.get('health', '—')} | ⚔️ {carta_info.get('attack', '—')} | "
                    f"🛡️ {carta_info.get('defense', '—')} | 💨 {carta_info.get('speed', '—')}"
                )
            )

            self.embed.set_footer(text=f"Card claimed by {interaction.user.display_name}")
            self.reclamada = True
            self.clear_items()

            # Imagen
            archivo = None
            if self.imagen_ruta and self.imagen_ruta.startswith("http"):
                self.embed.set_image(url=self.imagen_ruta)
            elif self.imagen_ruta and os.path.exists(self.imagen_ruta):
                archivo = discord.File(self.imagen_ruta, filename="carta.png")
                self.embed.set_image(url="attachment://carta.png")
            else:
                self.embed.description += "\n⚠️ Image not found. Please, contact my creator."

            await interaction.response.edit_message(
                embed=self.embed,
                attachments=[archivo] if archivo else [],
                view=self
            )

            await interaction.followup.send(
                f"{interaction.user.display_name} claimed **{nombre_carta}**",
                ephemeral=False
            )

            # Log
            log_guild_id = 286617766516228096
            log_channel_id = 1441990735883800607

            log_guild = interaction.client.get_guild(log_guild_id)
            if log_guild:
                log_channel = log_guild.get_channel(log_channel_id)
                if log_channel:
                    try:
                        await log_channel.send(
                            f"[CLAIM] {interaction.user.display_name} reclamó '{nombre_carta}' en {interaction.guild.name}."
                        )
                    except Exception as e:
                        print(f"[ERROR] Could not send log: {e}")

            print(f"[CLAIM] {interaction.user.display_name} reclamó '{nombre_carta}' en {interaction.guild.name}.")

        except Exception as e:
            print(f"[ERROR] en ReclamarCarta: {type(e).__name__} - {e}")
            try:
                await interaction.response.send_message(
                    "Sorry, an error occured while trying to claim this card.",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "Sorry, an error occured while trying to claim this card.",
                    ephemeral=True
                )
