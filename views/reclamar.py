import discord
import os
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas

# Reclamar una carta
class ReclamarCarta(discord.ui.View):
    def __init__(self, carta_id, embed, imagen_ruta):
        super().__init__(timeout=180)  # El botón expira tras 3 minutos
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
        
        # Diccionario de atributos con color y símbolo
        atributos = {
            "heart": ("心", 0xFF0000),       # rojo
            "technique": ("技", 0x00FF00),   # verde
            "body": ("体", 0x0000FF),        # azul
            "light": ("陽", 0xFFFF00),       # amarillo
            "shadow": ("陰", 0x800080)       # morado/magenta
        }

        # Diccionario de tipos con emoji
        tipos = {
            "attack": "⚔️ Attack",
            "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery",
            "support": "✨ Support"
        }

    @discord.ui.button(label="Reclamar carta 🐉", style=discord.ButtonStyle.success)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Si ya se ha reclamado, avisa al usuario
            if self.reclamada:
                await interaction.response.send_message("Esta carta ya ha sido reclamada.", ephemeral=True)
                return
    
            usuario_id = str(interaction.user.id)
            servidor_id = str(interaction.guild.id)

            # Se cargan las cartas y se busca la carta correspondiente entre ellas
            cartas_guardadas = cargar_cartas()
            carta_info = next((c for c in cartas_guardadas if c["id"] == self.carta_id), None)
            if carta_info is None:
                await interaction.response.send_message("No se encontró información de esta carta.", ephemeral=True)
                return
    
            propiedades = cargar_propiedades()
            propiedades.setdefault(servidor_id, {}).setdefault(usuario_id, []).append(self.carta_id)
            guardar_propiedades(propiedades)
    
            # Diccionario de símbolos de atributos
            atributos = {
                "heart": "心",
                "technique": "技",
                "body": "体",
                "light": "陽",
                "shadow": "陰",
            }
    
            # Diccionario de tipos con emoji
            tipos = {
                "attack": "⚔️ Attack",
                "defense": "🛡️ Defense",
                "recovery": "❤️ Recovery",
                "support": "✨ Support",
            }
    
            # Reconstruir embed con formato unificado
            nombre_carta = carta_info.get("nombre", f"ID {self.carta_id}")
            rareza = carta_info.get("rareza", "N")
            color = self.colores.get(rareza, 0x8c8c8c)
    
            atributo_raw = str(carta_info.get("atributo", "—")).lower()
            tipo_raw = str(carta_info.get("tipo", "—")).lower()
    
            # Formato de atributo y tipo
            attr_symbol = atributos.get(atributo_raw, "")
            attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
            atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
    
            tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")
    
            self.embed = discord.Embed(
                title=f"{nombre_carta}",
                color=color,
                description=(
                    f"**Atributo:** {atributo_fmt}\n"
                    f"**Tipo:** {tipo_fmt}\n"
                    f"❤️ {carta_info.get('health', '—')} | ⚔️ {carta_info.get('attack', '—')} | "
                    f"🛡️ {carta_info.get('defense', '—')} | 💨 {carta_info.get('speed', '—')}"
                )
            )
            self.embed.set_footer(text=f"Carta reclamada por {interaction.user.display_name}")
            self.reclamada = True
            self.clear_items()  # Quita el botón tras reclamar


            # Imagen
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
