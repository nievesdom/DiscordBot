import discord

# Navegar visualmente por las cartas de un usuario
class Navegador(discord.ui.View):
    def __init__(self, ctx, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=120)  # La vista expira tras 2 minutos
        self.ctx = ctx  # Contexto del comando
        self.cartas_ids = cartas_ids  # Lista de IDs de cartas del usuario
        self.cartas_info = cartas_info  # Diccionario con info de cada carta
        self.dueño = dueño  # Usuario dueño de la colección
        self.orden = "original"  # Estado del orden actual ("original" o "alfabetico")
        self.i = 0  # Índice de la carta actual
        self.msg = None  # Mensaje que contiene el embed

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

    # Devuelve la lista ordenada según el estado actual
    def lista(self):
        if self.orden == "alfabetico":
            return sorted(self.cartas_ids, key=lambda cid: self.cartas_info.get(str(cid), {}).get("nombre", "").lower())
        return self.cartas_ids

    # Crea el embed y usa la imagen desde el JSON (sin archivos locales)
    def mostrar(self):
        lista_actual = self.lista()
        carta_id = str(lista_actual[self.i])
        carta = self.cartas_info.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")
        descripcion=f"Type: {carta.get('tipo', 'sin tipo')}",

        embed = discord.Embed(title=nombre, color=color, description=descripcion)
        embed.set_footer(text=f"Carta {self.i + 1} de {len(lista_actual)} • Propiedad de {self.dueño.display_name}")

        # Mostrar la imagen directamente desde la URL
        if imagen and imagen.startswith("http"):
            embed.set_image(url=imagen)
            return embed, None
        else:
            embed.description = "⚠️ Imagen no encontrada."
            return embed, None

    # Actualiza el mensaje con la carta actual
    async def actualizar(self):
        lista_actual = self.lista()
        if self.i >= len(lista_actual):
            self.i = 0
        embed, archivo = self.mostrar()
        if archivo:
            await self.msg.edit(embed=embed, attachments=[archivo], view=self)
        else:
            await self.msg.edit(embed=embed, view=self)

    # Botón para ir a la carta anterior
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para ir a la carta siguiente
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para cambiar el orden de visualización
    @discord.ui.button(label="📆 Orden: por fecha", style=discord.ButtonStyle.primary, custom_id="orden")
    async def cambiar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.orden = "alfabetico" if self.orden == "original" else "original"
        self.i = 0  # Reiniciar índice
        nuevo_label = "🔤 Orden: alfabético" if self.orden == "alfabetico" else "📆 Orden: por fecha"
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "orden":
                item.label = nuevo_label
        await self.actualizar()
        await interaction.response.defer()
