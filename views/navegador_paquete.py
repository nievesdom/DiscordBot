import discord

# Vista para navegar visualmente por las cartas de un paquete diario
class NavegadorPaquete(discord.ui.View):
    def __init__(self, context, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=180)  # La vista expira tras 3 minutos
        self.context = context          # Puede ser Interaction (slash) o Context (prefijo)
        self.cartas_ids = cartas_ids    # Lista de IDs de cartas obtenidas en el pack
        self.cartas_info = cartas_info  # Diccionario con información de todas las cartas
        self.dueño = dueño              # Usuario dueño del pack
        self.i = 0                      # Índice actual de la carta mostrada
        self.msg = None                 # Mensaje que se enviará y luego se editará

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae,
            "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c
        }

        # Diccionario de atributos con símbolo japonés
        self.atributos = {
            "heart": "心", "technique": "技", "body": "体",
            "light": "陽", "shadow": "陰"
        }

        # Diccionario de tipos con emoji
        self.tipos = {
            "attack": "⚔️ Attack", "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery", "support": "✨ Support"
        }

    def mostrar(self):
        """Construye el embed de la carta actual del pack."""
        carta_id = str(self.cartas_ids[self.i])  # ID de la carta actual
        carta = self.cartas_info.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")

        # Formato de atributo y tipo
        atributo_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = self.atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = self.tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        # Crear embed con stats
        embed = discord.Embed(
            title=f"{nombre}",
            color=color,
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )
        embed.set_footer(
            text=f"Card {self.i + 1} out of {len(self.cartas_ids)} • {self.dueño.display_name}'s daily pack"
        )

        # Comprobar que la imagen existe
        if imagen and imagen.startswith("http"):
            embed.set_image(url=imagen)
        else:
            embed.description += "\n⚠️ Card image not found. Please, contact my creator."

        return embed, None

    async def enviar(self):
        """Envía el primer embed y guarda el mensaje para futuras ediciones."""
        embed, archivo = self.mostrar()
        if isinstance(self.context, discord.Interaction):
            # Caso slash command
            if archivo:
                self.msg = await self.context.followup.send(file=archivo, embed=embed, view=self)
            else:
                self.msg = await self.context.followup.send(embed=embed, view=self)
        else:
            # Caso prefijo
            if archivo:
                self.msg = await self.context.send(file=archivo, embed=embed, view=self)
            else:
                self.msg = await self.context.send(embed=embed, view=self)

    async def actualizar(self):
        """Actualiza el embed mostrado al cambiar de carta."""
        embed, archivo = self.mostrar()
        if self.msg:
            if archivo:
                await self.msg.edit(embed=embed, attachments=[archivo], view=self)
            else:
                await self.msg.edit(embed=embed, view=self)

    # Botón anterior
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Muestra la carta anterior en la lista."""
        self.i = (self.i - 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()

    # Botón siguiente
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Muestra la carta siguiente en la lista."""
        self.i = (self.i + 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()
