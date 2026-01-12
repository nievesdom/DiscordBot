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

    def has_winner(self) -> bool:
        if self.score_p1 >= 3 or self.score_p2 >= 3:
            return True
        if self.round > self.best_of_limit() and self.score_p1 != self.score_p2:
            return True
        return False

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
            on_decision=lambda i, accepted: asyncio.create_task(
                self._on_duel_decision(i, session, accepted)
            )
        )

        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} challenges you to a battle.",
            view=view
        )

        # ESTE es el mensaje real donde vive la vista
        view.message = await interaction.original_response()
        
        
    async def _on_duel_decision(
        self,
        interaction: discord.Interaction,
        session: BattleSession,
        accepted: bool,
    ):
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
            view=ChooseDeckView(
                player=player,
                available_decks=llenos,
                on_choose=lambda i, letra: asyncio.create_task(
                    self._on_deck_chosen(i, session, player, letra)
                ),
            ),
            ephemeral=True,
        )



    async def _on_deck_chosen(
        self,
        interaction: discord.Interaction,
        session: BattleSession,
        player: discord.Member,
        letra: str,
    ):
        # Mantener viva la interacción del botón
        await interaction.response.defer(ephemeral=True)

        # Guardar interacción fresca (muy importante para futuros followups)
        if player.id == session.p1.id:
            session.interaction_p1 = interaction
        else:
            session.interaction_p2 = interaction

        # Confirmación efímera
        await interaction.followup.send(
            f"You chose deck {letra}.", ephemeral=True
        )

        # Cargar mazo elegido
        server_id = str(session.guild_id)
        deck = cargar_mazo(server_id, str(player.id), letra)

        # Si el mazo ya no está lleno, cancelar batalla
        if len(deck) != DECK_SIZE:
            await session.public_channel.send(
                f"{player.mention}, your deck {letra} is no longer full. Battle cancelled."
            )
            self._clear_session(session)
            return

        # Guardar mazo en la sesión
        if player.id == session.p1.id:
            session.p1_deck_letter = letra
            session.p1_deck_cards = [str(c) for c in deck]
        else:
            session.p2_deck_letter = letra
            session.p2_deck_cards = [str(c) for c in deck]
       

        # Si ambos ya eligieron mazo, iniciar primera ronda
        if session.p1_deck_letter and session.p2_deck_letter:
            await self._start_round(session.public_channel, session)



    async def _start_round(
        self, channel: discord.TextChannel, session: BattleSession
    ):
        try:
            # Si ya hay ganador, terminar batalla
            if session.has_winner():
                await self._finish_battle(channel, session)
                return

            # Elegir stat aleatorio para este round
            session.current_stat = random.choice(STATS_COMBAT)

            # Anunciar stat del round
            icono = STAT_ICONS.get(session.current_stat, "")
            nombre = session.current_stat.upper()

            await channel.send(
                f"Round {session.round}. Stat: {icono} **{nombre}**"
            )

            # Resetear elecciones
            session.waiting_p1_card = None
            session.waiting_p2_card = None

            # Pedir carta a ambos jugadores
            await self._ask_card_choice(session, session.p1, True)
            await self._ask_card_choice(session, session.p2, False)

        except Exception as e:
            print(f"[ERROR] in _start_round: {repr(e)}")
            await channel.send(f"ERROR] in _start_round: `{repr(e)}`")


    async def _ask_card_choice(
        self, session: BattleSession, player: discord.Member, is_p1: bool
    ):
        # Obtener mazo y cartas ya usadas
        deck = session.p1_deck_cards if is_p1 else session.p2_deck_cards
        used = session.p1_used_indices if is_p1 else session.p2_used_indices
    
        # Interacción efímera correcta
        inter = (
            session.interaction_p1
            if player.id == session.p1.id
            else session.interaction_p2
        )
    
        # Crear vista de selección de carta
        vista = ChooseCardView(
            player=player,
            deck_cards=deck,
            cartas_info=session.cartas_info,
            used_indices=used,
            on_choose=lambda interaction, idx, cid: self._on_card_chosen(
                interaction, session, player, is_p1, idx, cid
            ),
        )
    
        # Enviar embed inicial + vista
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



    async def _resolve_round(
        self, channel: discord.TextChannel, session: BattleSession
    ):
        # Recuperamos las cartas elegidas por cada jugador:
        # idx = índice dentro del mazo, cid = ID de la carta
        idx1, cid1 = session.waiting_p1_card
        idx2, cid2 = session.waiting_p2_card

        # Obtenemos la información completa de cada carta
        c1 = session.cartas_info.get(cid1, {})
        c2 = session.cartas_info.get(cid2, {})

        # Extraemos el valor de la estadística actual (health/attack/defense/speed)
        v1 = self.obtener_stat(c1, session.current_stat)
        v2 = self.obtener_stat(c2, session.current_stat)

        # Nombres legibles de las cartas
        nombre1 = c1.get("nombre", f"ID {cid1}")
        nombre2 = c2.get("nombre", f"ID {cid2}")

        # Comparamos los valores de la stat para determinar el ganador del round
        if v1 > v2:
            session.score_p1 += 1  # Suma punto jugador 1
            result = (
                f"{session.p1.mention} wins the round. "
                f"{nombre1} ({v1}) vs {nombre2} ({v2})."
            )
        elif v2 > v1:
            session.score_p2 += 1  # Suma punto jugador 2
            result = (
                f"{session.p2.mention} wins the round. "
                f"{nombre1} ({v1}) vs {nombre2} ({v2})."
            )
        else:
            # Empate: nadie suma puntos
            result = (
                f"Tie. {nombre1} ({v1}) vs {nombre2} ({v2})."
            )

        # Enviamos al canal público el resultado del round y el marcador actual
        await channel.send(
            f"Round {session.round} result:\n{result}\n"
            f"Score: {session.p1.display_name} {session.score_p1} – "
            f"{session.score_p2} {session.p2.display_name}"
        )

        # Pasamos al siguiente round
        session.round += 1

        # Si ya hay ganador (3 puntos o final BO5), terminamos la batalla
        if session.has_winner():
            await self._finish_battle(channel, session)
        else:
            # Si no, iniciamos el siguiente round
            await self._start_round(channel, session)



    async def _finish_battle(
        self, channel: discord.TextChannel, session: BattleSession
    ):
        # Determinamos quién ganó la batalla completa
        winner = session.winner()

        if winner:
            # Mensaje de victoria
            await channel.send(
                f"Battle finished. Winner: {winner.mention} "
                f"({session.p1.display_name} {session.score_p1} – "
                f"{session.score_p2} {session.p2.display_name})."
            )
        else:
            # Caso improbable: empate total
            await channel.send(
                "Battle finished with a tie. "
                f"Score: {session.p1.display_name} {session.score_p1} – "
                f"{session.score_p2} {session.p2.display_name}."
            )

        # Eliminamos la sesión activa de la memoria del bot
        self._clear_session(session)


# Setup del cog
async def setup(bot):
    await bot.add_cog(Battle(bot))