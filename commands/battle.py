import asyncio
import discord
import random
from discord.ext import commands
from discord import app_commands
from core.firebase_storage import (
    cargar_inventario_usuario,
    cargar_mazo,
    guardar_mazo,
    cargar_propiedades,
)
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador_mazo import NavegadorMazo

from typing import Dict, Tuple, Optional
from views.battle_views import AcceptDuelView, ChooseDeckView, ChooseCardView

DECK_SIZE = 8  # Tamaño máximo del mazo
STATS_COMBAT = ["health", "attack", "defense", "speed"]
STAT_ICONS = {
    "health": "❤️",
    "attack": "⚔️",
    "defense": "🛡️",
    "speed": "💨",
}

def normalizar_mazo(nombre: str) -> str:
    nombre = nombre.strip().lower()

    if nombre in ("a", "1"):
        return "A"
    if nombre in ("b", "2"):
        return "B"
    if nombre in ("c", "3"):
        return "C"

    return "A"


class BattleSession:
    def __init__(self, guild_id: int, p1: discord.Member, p2: discord.Member):
        self.guild_id = guild_id
        self.p1 = p1
        self.p2 = p2
        self.last_round_result: str | None = None
        self.current_stats: list[str] = []

        # Canal público donde se anuncia la batalla
        self.public_channel: Optional[discord.TextChannel] = None

        # Interacciones necesarias para enviar mensajes efímeros
        self.interaction_p1: Optional[discord.Interaction] = None
        self.interaction_p2: Optional[discord.Interaction] = None

        # Mazos elegidos
        self.p1_deck_letter: Optional[str] = None
        self.p2_deck_letter: Optional[str] = None

        self.p1_deck_cards: list[str] = []
        self.p2_deck_cards: list[str] = []

        # Cartas usadas
        self.p1_used_indices: set[int] = set()
        self.p2_used_indices: set[int] = set()

        # Estado de la partida
        self.score_p1 = 0
        self.score_p2 = 0
        self.round = 1
        self.current_stat: Optional[str] = None

        # Info de cartas
        self.cartas_info = cartas_por_id()

        # Elecciones pendientes
        self.waiting_p1_card: Optional[Tuple[int, str]] = None
        self.waiting_p2_card: Optional[Tuple[int, str]] = None

    def best_of_limit(self) -> int:
        return 5

    # Comprueba si ya hay un ganador
    def has_winner(self) -> bool:
        if self.score_p1 >= 3 or self.score_p2 >= 3:
            return True
        if self.round > self.best_of_limit() and self.score_p1 != self.score_p2:
            return True
        return False

    # Devuelve el ganador
    def winner(self) -> Optional[discord.Member]:
        if self.score_p1 > self.score_p2:
            return self.p1
        if self.score_p2 > self.score_p1:
            return self.p2
        return None


class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_battles: Dict[Tuple[int, int, int], BattleSession] = {}

    # -----------------------------
    # Comando slash: /deck_add
    # -----------------------------
    @discord.app_commands.command(
        name="deck_add",
        description="Add a card to one of your decks (A, B or C).",
    )
    @app_commands.describe(
        deck="Deck name: A, B, C or 1, 2, 3",
        card_name="Exact name of the card",
    )
    async def deck_add_slash(
        self, interaction: discord.Interaction, deck: str, card_name: str
    ):
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next(
            (c for c in cards if c["nombre"].lower() == card_name.lower()), None
        )

        if not card:
            await interaction.response.send_message(
                f"No card found with the name '{card_name}'.",
                ephemeral=False,
            )
            return

        card_id = str(card["id"])

        user_cards = cargar_inventario_usuario(server_id, user_id)

        if card_id not in map(str, user_cards):
            await interaction.response.send_message(
                f"You do not own the card '{card['nombre']}'.",
                ephemeral=False,
            )
            return

        # Cargar los tres mazos
        mazo_a = cargar_mazo(server_id, user_id, "A")
        mazo_b = cargar_mazo(server_id, user_id, "B")
        mazo_c = cargar_mazo(server_id, user_id, "C")

        # Comprobar si la carta ya está en otro mazo
        total_en_mazos = (
            sum(1 for c in mazo_a if str(c) == card_id)
            + sum(1 for c in mazo_b if str(c) == card_id)
            + sum(1 for c in mazo_c if str(c) == card_id)
        )

        owned_count = sum(1 for c in user_cards if str(c) == card_id)

        if total_en_mazos >= owned_count:
            await interaction.response.send_message(
                f"You only own {owned_count} copies of '{card['nombre']}', "
                f"and all of them are already in other decks.",
                ephemeral=False,
            )
            return

        # Cargar el mazo elegido
        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if len(user_deck) >= DECK_SIZE:
            await interaction.response.send_message(
                f"Your deck {letra_mazo} already has {DECK_SIZE} cards.",
                ephemeral=False,
            )
            return

        user_deck.append(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await interaction.response.send_message(
            f"The card '{card['nombre']}' has been added to deck {letra_mazo}.",
            ephemeral=False,
        )

    # -----------------------------
    # Comando prefijo: y!deck_add
    # -----------------------------
    @commands.command(name="deck_add")
    async def deck_add_prefix(
        self, ctx: commands.Context, deck: str, *, card_name: str
    ):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next(
            (c for c in cards if c["nombre"].lower() == card_name.lower()), None
        )

        if not card:
            await ctx.send(f"No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        user_cards = cargar_inventario_usuario(server_id, user_id)

        if card_id not in map(str, user_cards):
            await ctx.send(f"You do not own the card '{card['nombre']}'.")
            return

        mazo_a = cargar_mazo(server_id, user_id, "A")
        mazo_b = cargar_mazo(server_id, user_id, "B")
        mazo_c = cargar_mazo(server_id, user_id, "C")

        total_en_mazos = (
            sum(1 for c in mazo_a if str(c) == card_id)
            + sum(1 for c in mazo_b if str(c) == card_id)
            + sum(1 for c in mazo_c if str(c) == card_id)
        )

        owned_count = sum(1 for c in user_cards if str(c) == card_id)

        if total_en_mazos >= owned_count:
            await ctx.send(
                f"You only own {owned_count} copies of '{card['nombre']}', "
                f"and all of them are already in other decks."
            )
            return

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if len(user_deck) >= DECK_SIZE:
            await ctx.send(
                f"Your deck {letra_mazo} already has {DECK_SIZE} cards."
            )
            return

        user_deck.append(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await ctx.send(
            f"The card '{card['nombre']}' has been added to deck {letra_mazo}."
        )

    # -----------------------------
    # Comando slash: /deck
    # -----------------------------
    @discord.app_commands.command(
        name="deck",
        description="Shows one of your decks (A, B, C or 1, 2, 3).",
    )
    @app_commands.describe(
        deck="Deck name: either A, B or C or 1, 2 or 3"
    )
    async def deck_slash(self, interaction: discord.Interaction, deck: str = "A"):
        await interaction.response.defer()

        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if not user_deck:
            await interaction.followup.send(
                f"{interaction.user.display_name}, your deck {letra_mazo} is empty."
            )
            return

        cartas_info = cartas_por_id()
        vista = NavegadorMazo(interaction, user_deck, cartas_info, interaction.user)

        await vista.enviar()

    # -----------------------------
    # Comando prefijo: y!deck
    # -----------------------------
    @commands.command(name="deck")
    async def deck_prefix(self, ctx: commands.Context, deck: str = "A"):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if not user_deck:
            await ctx.send(
                f"{ctx.author.display_name}, your deck {letra_mazo} is empty."
            )
            return

        cartas_info = cartas_por_id()
        vista = NavegadorMazo(ctx, user_deck, cartas_info, ctx.author)

        await vista.enviar()

    # -----------------------------
    # Comando slash: /deck_remove
    # -----------------------------
    @discord.app_commands.command(
        name="deck_remove",
        description="Remove a card from one of your decks (A, B or C).",
    )
    @app_commands.describe(
        deck="Deck name: A, B, C or 1, 2, 3",
        card_name="Exact name of the card",
    )
    async def deck_remove_slash(
        self, interaction: discord.Interaction, deck: str, card_name: str
    ):
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next(
            (c for c in cards if c["nombre"].lower() == card_name.lower()), None
        )

        if not card:
            await interaction.response.send_message(
                f"No card found with the name '{card_name}'.",
                ephemeral=False,
            )
            return

        card_id = str(card["id"])

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if card_id not in map(str, user_deck):
            await interaction.response.send_message(
                f"The card '{card['nombre']}' is not in deck {letra_mazo}.",
                ephemeral=False,
            )
            return

        user_deck.remove(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await interaction.response.send_message(
            f"The card '{card['nombre']}' has been removed from deck {letra_mazo}.",
            ephemeral=False,
        )

    # -----------------------------
    # Comando prefijo: y!deck_remove
    # -----------------------------
    @commands.command(name="deck_remove")
    async def deck_remove_prefix(
        self, ctx: commands.Context, deck: str, *, card_name: str
    ):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next(
            (c for c in cards if c["nombre"].lower() == card_name.lower()), None
        )

        if not card:
            await ctx.send(f"No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if card_id not in map(str, user_deck):
            await ctx.send(
                f"The card '{card['nombre']}' is not in deck {letra_mazo}."
            )
            return

        user_deck.remove(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await ctx.send(
            f"The card '{card['nombre']}' has been removed from deck {letra_mazo}."
        )

    # ------------------------------
    # Helpers battle
    # ------------------------------
    def _battle_key(self, guild_id: int, u1: int, u2: int):
        a, b = sorted([u1, u2])
        return (guild_id, a, b)

    def _set_session(self, session: BattleSession):
        key = self._battle_key(session.guild_id, session.p1.id, session.p2.id)
        self.active_battles[key] = session

    def _get_session(self, guild_id: int, u1: int, u2: int):
        return self.active_battles.get(self._battle_key(guild_id, u1, u2))

    def _clear_session(self, session: BattleSession):
        key = self._battle_key(session.guild_id, session.p1.id, session.p2.id)
        self.active_battles.pop(key, None)

    def mazos_llenos(self, server_id: str, user_id: str) -> list[str]:
        llenos = []
        for letra in ("A", "B", "C"):
            mazo = cargar_mazo(server_id, user_id, letra)
            if len(mazo) == DECK_SIZE:
                llenos.append(letra)
        return llenos

    def tiene_mazo_lleno(self, server_id: str, user_id: str) -> bool:
        return len(self.mazos_llenos(server_id, user_id)) > 0

    def obtener_stat(self, carta: dict, stat: str) -> int:
        try:
            return int(carta.get(stat, 0))
        except Exception:
            return 0


    # ------------------------------
    # /battle
    # ------------------------------
    @app_commands.command(
        name="battle",
        description="Challenge another user to a card battle.",
    )
    @app_commands.describe(user="User you want to challenge")
    async def battle_slash(
        self, interaction: discord.Interaction, user: discord.Member
    ):
        # No se permite retar a bots
        if user.bot:
            await interaction.response.send_message(
                "You cannot challenge a bot.", ephemeral=True
            )
            return

        # No se permite retarse a uno mismo
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot challenge yourself.", ephemeral=True
            )
            return

        # IDs del servidor y la guild
        guild_id = interaction.guild_id
        server_id = str(guild_id)

        # Si ya existe una batalla activa entre estos dos usuarios, no se puede iniciar otra
        if self._get_session(guild_id, interaction.user.id, user.id):
            await interaction.response.send_message(
                "There is already an active battle between you two.",
                ephemeral=True,
            )
            return

        # Comprobar que el retador tiene al menos un mazo lleno
        if not self.tiene_mazo_lleno(server_id, str(interaction.user.id)):
            await interaction.response.send_message(
                "You need at least one full deck to battle.",
                ephemeral=True,
            )
            return

        # Comprobar que el retado también tiene un mazo lleno
        if not self.tiene_mazo_lleno(server_id, str(user.id)):
            await interaction.response.send_message(
                f"{user.display_name} has no full decks.",
                ephemeral=True,
            )
            return

        # Crear sesión de batalla
        session = BattleSession(guild_id, interaction.user, user)

        # Guardamos la interacción del jugador 1 (necesaria para mensajes efímeros)
        session.interaction_p1 = interaction

        # Registrar la sesión como activa
        self._set_session(session)

        # Enviar mensaje al jugador retado con botones Accept/Decline
        view = AcceptDuelView(
            on_decision=self._on_duel_decision,
            on_timeout_callback=lambda: self._prebattle_timeout(session, session.p2)
        )

        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} challenges you to a battle.",
            view=view
        )

        # Mensaje donde vive la vista
        view.message = await interaction.original_response()
        
        
    async def _on_duel_decision(
        self,
        interaction: discord.Interaction,
        accepted: bool,
    ):
        session = self._get_session(interaction.guild_id, interaction.user.id, interaction.message.interaction.user.id)

        # Solo el jugador retado puede aceptar o rechazar
        if interaction.user.id != session.p2.id:
            await interaction.response.send_message(
                "Only the challenged user can decide.", ephemeral=True
            )
            return
    
        # REFERENCIA AL MENSAJE ORIGINAL DONDE VIVE LA VISTA
        original_msg = await session.interaction_p1.original_response()
    
        # -------------------------
        #   RECHAZAR BATALLA
        # -------------------------
        if not accepted:
        
            # Responder la interacción (obligatorio)
            if not interaction.response.is_done():
                try:
                    await interaction.response.defer()
                except:
                    pass
                
            # Editar el mensaje original donde estaba la vista
            try:
                original_msg = await session.interaction_p1.original_response()
                await original_msg.edit(
                    content=f"{interaction.user.display_name} declined the battle.",
                    view=None
                )
            except:
                pass
            
            # Mensaje público opcional
            try:
                await session.public_channel.send(
                    f"{interaction.user.display_name} declined the battle."
                )
            except:
                pass
            
            # Eliminar la batalla activa
            self._clear_session(session)

            return

    
        # -------------------------
        #   ACEPTAR BATALLA
        # -------------------------
    
        # Responder interacción
        if not interaction.response.is_done():
            try:
                await interaction.response.defer()
            except:
                pass
            
        # Editar mensaje original
        try:
            await original_msg.edit(
                content=(
                    f"{interaction.user.display_name} accepted the battle.\n"
                    f"The battle is about to start. Both players must now choose a deck."
                ),
                view=None
            )
        except:
            pass
        
        # Guardar interacción del jugador 2
        session.interaction_p2 = interaction
    
        # Canal público donde se narrará la batalla
        session.public_channel = interaction.channel
    
        # Pedir elección de mazo a ambos jugadores
        await self._ask_deck_choice(session, session.p1)
        await self._ask_deck_choice(session, session.p2)



    async def _ask_deck_choice(
        self, session: BattleSession, player: discord.Member
    ):
        # Obtener qué mazos del jugador están llenos
        server_id = str(session.guild_id)
        llenos = self.mazos_llenos(server_id, str(player.id))

        # Si ya no tiene mazos llenos, cancelar batalla
        if not llenos:
            await session.public_channel.send(
                f"{player.mention} no longer has any full deck. Battle cancelled."
            )
            self._clear_session(session)
            return

        # Elegir la interacción correcta (p1 o p2)
        inter = (
            session.interaction_p1
            if player.id == session.p1.id
            else session.interaction_p2
        )

        # Enviar menú para elegir mazo
        await inter.followup.send(
            "Choose your deck:",
            view = ChooseDeckView(
                player=player,
                available_decks=llenos,
                on_choose=lambda inter, letra: self._on_deck_chosen(inter, session, player, letra),
                on_timeout_callback=lambda p=player: self._prebattle_timeout(session, p)
            ),

            ephemeral=True,
        )



    async def _on_deck_chosen(self, interaction, session, player, letra):
        # Editar el mensaje donde estaban los botones
        try:
            await interaction.response.edit_message(
                content=f"You chose deck {letra}.",
                view=None
            )
        except:
            # Si ya estaba respondido, usamos followup.edit_original_response
            try:
                msg = await interaction.original_response()
                await msg.edit(content=f"You chose deck {letra}.", view=None)
            except:
                pass

        # Guardar la interacción si la necesitas después
        if player.id == session.p1.id:
            session.interaction_p1 = interaction
        else:
            session.interaction_p2 = interaction

        # Cargar el mazo
        server_id = str(session.guild_id)
        deck = cargar_mazo(server_id, str(player.id), letra)

        if len(deck) != DECK_SIZE:
            await session.public_channel.send(
                f"{player.mention}, your deck {letra} is no longer full. Battle cancelled."
            )
            self._clear_session(session)
            return

        if player.id == session.p1.id:
            session.p1_deck_letter = letra
            session.p1_deck_cards = [str(c) for c in deck]
        else:
            session.p2_deck_letter = letra
            session.p2_deck_cards = [str(c) for c in deck]

        # Si ambos han elegido, empieza la ronda
        if session.p1_deck_letter and session.p2_deck_letter:
            await self._start_round(session.public_channel, session)



    async def _start_round(self, channel, session):

        if session.has_winner():
            await self._finish_battle(channel, session)
            return

        # Probabilidad de número de stats:
        # 60% → 1 stat
        # 25% → 2 stats
        # 10% → 3 stats
        # 5%  → 4 stats
        r = random.random()

        if r < 0.60:
            n = 1
        elif r < 0.60 + 0.25:
            n = 2
        elif r < 0.60 + 0.25 + 0.10:
            n = 3
        else:
            n = 4

        session.current_stats = random.sample(STATS_COMBAT, n)

        # Construcción del texto de stats
        partes = []
        for st in session.current_stats:
            icono = STAT_ICONS.get(st, "")
            partes.append(f"{icono} **{st.upper()}**")

        texto_stats = " + ".join(partes)

        # Mensaje de inicio de ronda
        texto = ""

        if session.round > 1 and session.last_round_result:
            texto += f"{session.last_round_result}\n"
            texto += (
                f"Score: {session.p1.display_name} {session.score_p1} - "
                f"{session.score_p2} {session.p2.display_name}\n"
            )

        texto += f"Round {session.round}. Stats: {texto_stats}"

        await channel.send(texto)

        # Reset de elecciones
        session.waiting_p1_card = None
        session.waiting_p2_card = None

        # Pedir cartas
        await self._ask_card_choice(session, session.p1, True)
        await self._ask_card_choice(session, session.p2, False)


    async def _ask_card_choice(self, session, player, is_p1):

        deck = session.p1_deck_cards if is_p1 else session.p2_deck_cards
        used = session.p1_used_indices if is_p1 else session.p2_used_indices

        # Usamos la interacción original del duelo, no la del deck
        inter = (
            session.interaction_p1 if player.id == session.p1.id else session.interaction_p2
        )

        vista = ChooseCardView(
            player=player,
            deck_cards=deck,
            cartas_info=session.cartas_info,
            used_indices=used,
            on_choose=lambda interaction, idx, cid: self._on_card_chosen(
                interaction, session, player, is_p1, idx, cid
            ),
            on_timeout_callback=lambda p=player: self._player_timeout(session, p)  # ← NUEVO
        )

        await vista.enviar(inter)


    async def _on_card_chosen(
        self,
        interaction: discord.Interaction,
        session: BattleSession,
        player: discord.Member,
        is_p1: bool,
        index: int,
        card_id: str,
    ):
        # Asegurar que la interacción tiene una respuesta inicial
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                # Si por cualquier motivo ya está respondida, lo ignoramos
                pass
            
        # Registrar carta elegida
        if is_p1:
            session.p1_used_indices.add(index)
            session.waiting_p1_card = (index, card_id)
        else:
            session.p2_used_indices.add(index)
            session.waiting_p2_card = (index, card_id)
    
        # Si ambos han elegido, resolvemos la ronda
        if session.waiting_p1_card and session.waiting_p2_card:
            # Usamos el canal público guardado en la sesión
            if session.public_channel is not None:
                await self._resolve_round(session.public_channel, session)



    async def _resolve_round(self, channel, session):
        idx1, cid1 = session.waiting_p1_card
        idx2, cid2 = session.waiting_p2_card

        c1 = session.cartas_info.get(cid1, {})
        c2 = session.cartas_info.get(cid2, {})

        stat = session.current_stat
        icono = STAT_ICONS.get(stat, "")
        
        # Multi-stat: sumar todos los stats seleccionados
        total1 = 0
        total2 = 0
        
        for st in session.current_stats:
            total1 += self.obtener_stat(c1, st)
            total2 += self.obtener_stat(c2, st)
        

        nombre1 = c1.get("nombre", f"ID {cid1}")
        nombre2 = c2.get("nombre", f"ID {cid2}")

        # Determinar ganador
        if total1 > total2:
            session.score_p1 += 1
            resultado = f"{session.p1.display_name} wins the round!"
            color1, color2 = 0x4CAF50, 0xE53935
        elif total2 > total1:
            session.score_p2 += 1
            resultado = f"{session.p2.display_name} wins the round!"
            color1, color2 = 0xE53935, 0x4CAF50
        else:
            resultado = "Tie!"
            color1 = color2 = 0x9E9E9E

        # Stats en una sola línea
        def fmt(carta):
            def val(key):
                raw = carta.get(key, "—")
                icon = STAT_ICONS.get(key, "")

                # Destacar TODOS los stats usados en la ronda
                if key in session.current_stats:
                    return f"**{icon} {raw} ←**"

                return f"{icon} {raw}"

            return " | ".join([
                val("health"),
                val("attack"),
                val("defense"),
                val("speed")
            ])


        # Embed carta 1
        embed1 = discord.Embed(
            title=f"{session.p1.display_name}\n{nombre1}",
            color=color1
        )
        if c1.get("imagen"):
            embed1.set_image(url=c1["imagen"])
        embed1.add_field(name="Stats", value=fmt(c1), inline=False)

        # Construir texto de stats combinados (1 o varios)
        stats_text = " + ".join(
            f"{STAT_ICONS[s]} {s.upper()}"
            for s in session.current_stats
        )

        # Embed VS central
        embed_vs = discord.Embed(
            title="⚔️ VS ⚔️",
            description=(
                f"**{stats_text} battle**\n"
                f"**{total1}** vs **{total2}**\n"
                f"{resultado}"
            ),
            color=0xFFD700
        )

        # Embed carta 2
        embed2 = discord.Embed(
            title=f"{session.p2.display_name}\n{nombre2}",
            color=color2
        )
        if c2.get("imagen"):
            embed2.set_image(url=c2["imagen"])
        embed2.add_field(name="Stats", value=fmt(c2), inline=False)


        await channel.send(embeds=[embed1, embed_vs, embed2])
        
        # LOG DE RONDA
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = self.bot.get_guild(log_guild_id)
        
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(
                        f"[BATTLE ROUND] {session.p1.display_name} vs {session.p2.display_name} | "
                        f"Round {session.round}\n"
                        f"• {session.p1.display_name} played **{nombre1}** → {total1}\n"
                        f"• {session.p2.display_name} played **{nombre2}** → {total2}\n"
                        f"Stats used: {', '.join(session.current_stats)}\n"
                        f"Result: {resultado}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send battle round log: {e}")



        session.last_round_result = resultado
        session.round += 1
        if session.has_winner():
            await self._finish_battle(channel, session)
        else:
            await self._start_round(channel, session)




    async def _finish_battle(
            self, channel: discord.TextChannel, session: BattleSession
        ):
        # Determinar ganador
        winner = session.winner()

        if winner:
            # Embed de victoria
            embed = discord.Embed(
                title="🏆 BATTLE FINISHED! 🏆",
                description=(
                    f"**Winner:** {winner.mention}\n\n"
                    f"**Final Score:**\n"
                    f"{session.p1.display_name} {session.score_p1} – "
                    f"{session.score_p2} {session.p2.display_name}"
                ),
                color=0xFFD700
            )

            await channel.send(embed=embed)

        else:
            # Empate total (muy raro)
            embed = discord.Embed(
                title="🏆 BATTLE FINISHED! 🏆",
                description=(
                    "**The battle ended in a tie.**\n\n"
                    f"**Final Score:**\n"
                    f"{session.p1.display_name} {session.score_p1} – "
                    f"{session.score_p2} {session.p2.display_name}"
                ),
                color=0x9E9E9E
            )

            await channel.send(embed=embed)

        # LOG FINAL DE BATALLA
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = self.bot.get_guild(log_guild_id)

        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(
                        f"[BATTLE END] Winner: {winner.display_name if winner else 'Tie'} | "
                        f"Final Score: {session.p1.display_name} {session.score_p1} - "
                        f"{session.score_p2} {session.p2.display_name}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send battle end log: {e}")


        # Limpiar sesión
        self._clear_session(session)
        
        
    async def _player_timeout(self, session, player):

        # Marcar abandono
        if not hasattr(session, "abandonos"):
            session.abandonos = set()

        session.abandonos.add(player.id)

        # Si ambos abandonaron → empate
        if len(session.abandonos) == 2:
            await session.public_channel.send(
                "⚠️ **Both players failed to play a card in time.**\n"
                "**The battle ends in a draw by abandonment.**"
            )
            self._clear_session(session)
            return

        # Si solo uno abandonó → derrota por abandono
        other = session.p1 if player.id == session.p2.id else session.p2

        await session.public_channel.send(
            f"⚠️ **{player.display_name} did not play a card in time.**\n"
            f"🏳️ **{player.display_name} loses by abandonment.**\n"
            f"🏆 Winner: {other.display_name}"
        )

        self._clear_session(session)
        
        
    async def _prebattle_timeout(self, session, player):
        """
        Se llama cuando un jugador no acepta el duelo o no elige deck.
        La batalla aún no ha empezado, así que solo se cancela.
        """

        # Si ya se limpió la sesión, no hacer nada
        if session not in self.active_sessions.values():
            return

        # Si ambos fallan (muy raro pero posible)
        if not hasattr(session, "prebattle_abandon"):
            session.prebattle_abandon = set()

        session.prebattle_abandon.add(player.id)

        # Si ambos han fallado
        if len(session.prebattle_abandon) == 2:
            await session.public_channel.send(
                "⚠️ **The battle request was cancelled because neither player responded in time.**"
            )
            self._clear_session(session)
            return

        # Si solo uno falló → cancelar batalla
        await session.public_channel.send(
            f"⚠️ **{player.display_name} did not respond in time.**\n"
            f"The battle request has been cancelled."
        )

        self._clear_session(session)




# Setup del cog
async def setup(bot):
    await bot.add_cog(Battle(bot))