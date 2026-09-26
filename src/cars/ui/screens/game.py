"""The campaign screen: turns clicks and keys into simulation commands and runs rival turns.

Input is handled by a chain of small handlers in priority order: modal dialogs,
the tutorial card, top-bar shortcuts, the market, the menu, file shortcuts, the
faction picker and finally orders on the map.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from cars.persist.replay import Recorder
from cars.persist.savegame import SaveLibrary, load_game, save_game
from cars.sim.ai import Action, faction_actions
from cars.sim.air import REBASE, STRIKE, SUPPORT
from cars.sim.calendar import date_label
from cars.sim.campaign import Campaign
from cars.sim.entities import AIR, FLEET, INFANTRY
from cars.sim.journal import BATTLE_KINDS
from cars.sim.objectives import campaign_stage
from cars.sim.scenario import DETAILED_SCENARIO, load_scenario
from cars.sim.turn import end_turn
from cars.ui.dialogs import Dialogs
from cars.ui.map.animation import MoveAnimation
from cars.ui.renderer import GameRenderer, ViewState
from cars.ui.screens.replay import ReplayScreen
from cars.ui.tutorial import Tutorial
from cars.ui.typography import FONT_CHOICES

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.context import UiContext

# Where a focused unit is placed on screen: left of centre, clear of the council.
FOCUS_POINT = (490, 365)
DRAG_THRESHOLD = 6
AI_ACTION_SECONDS = 0.35
BUILD_EFFECT_SECONDS = 2
ZOOM_STEP = 1.2
TUTORIAL_RESOURCES = 80
LAYER_KEYS = {pygame.K_1: "land", pygame.K_2: "naval", pygame.K_3: "air", pygame.K_4: "supply"}
DIALOG_KEYS = {
    pygame.K_F1: "pedia",
    pygame.K_g: "strategy",
    pygame.K_r: "replay",
    pygame.K_j: "reports",
    pygame.K_u: "roster",
    pygame.K_F10: "settings",
}
LAYER_UNIT_KIND = {"land": INFANTRY, "supply": INFANTRY, "naval": FLEET, "air": AIR}
AIR_MODE_HELP = {
    STRIKE: "Click an enemy force within range. One sortie per turn.",
    SUPPORT: "Click a province to grant +25% land attack there.",
    REBASE: "Click another controlled airbase within range.",
}
SELECT_HINTS = {
    "supply": "Select an army to trace its supply route.",
    "air": "Gold borders show operational range.",
}
DEFAULT_SELECT_HINT = "Click a gold-bordered province or sea zone to move."


class GameScreen:
    def __init__(self, context: "UiContext", state: "GameState", shapes: dict, seas: list[dict]) -> None:
        self.context = context
        self.library = SaveLibrary()
        self.viewer: ReplayScreen | None = None
        self._begin(state, shapes, seas)

    def _begin(self, state: "GameState", shapes: dict, seas: list[dict]) -> None:
        """Bind the screen to a campaign; used for new games, loaded saves and the tutorial."""
        self.state = state
        self.campaign = Campaign(state)
        self.renderer = GameRenderer(self.context, state, shapes, seas, self.campaign)
        self.view = ViewState(
            message="Click infantry to plan a route. Right-click a province to develop it.",
            inspected=self._first_army_location(state.active),
        )
        self.ai_turn: Iterator[Action] | None = None
        self.ai_delay = 0.0
        self.map_press: pygame.event.Event | None = None
        self.map_dragged = False
        self.panning = False
        self.dragging_window = False
        self.dialogs = Dialogs(self)
        self.tutorial = Tutorial(self)
        self.renderer.blockers = [self.tutorial.blocks, self.dialogs.blocks]

    def _first_army_location(self, owner: str) -> str | None:
        return next((u.location for u in self.state.units.values() if u.owner == owner and u.is_land), None)

    # Campaign lifecycle ---------------------------------------------------------------

    def choose_faction(self, faction: str) -> None:
        if not self.campaign.choose(faction):
            return
        self.view.selected = None
        self.view.inspected = self._first_army_location(faction)
        self.view.message = (
            f"You command {self.state.factions[faction].name}. Other factions act automatically."
        )
        self.start_recording()

    def start_recording(self) -> None:
        self.campaign.recorder = Recorder(
            self.state, self.renderer.shapes, self.renderer.seas, self.campaign.player
        )

    def start_tutorial(self) -> None:
        state, shapes, seas = load_scenario(DETAILED_SCENARIO)
        state.factions["f0"].resources = dict.fromkeys(("wood", "food", "iron"), TUTORIAL_RESOURCES)
        state.tutorial = dict(active=True, step=0, seen=[], hidden=False)
        self._begin(state, shapes, seas)
        self.choose_faction("f0")
        infantry = next(u for u in state.units.values() if u.owner == "f0" and u.kind == INFANTRY)
        self.renderer.map.center_on(infantry.location, FOCUS_POINT)
        self.view.message = "Guided tutorial: ten lessons. Your manual saves are untouched."

    def save(self, path: Path | None = None) -> None:
        if self.view.animation or not self.campaign.human_turn:
            self.view.message = "Save once movement finishes on your turn."
            return
        try:
            save_game(
                self.state,
                self.renderer.shapes,
                self.renderer.seas,
                self.campaign.player,
                path or self.library.path(0),
            )
            self.view.message = "Campaign saved. F9 opens the campaign library."
        except (OSError, ValueError) as exc:
            self.view.message = f"Could not save: {exc}"

    def load(self, path: Path | None = None) -> bool:
        if self.view.animation:
            return False
        try:
            state, shapes, seas, player = load_game(path or self.library.path(0))
        except (OSError, ValueError) as exc:
            self.view.message = f"Could not load campaign: {exc}"
            return False
        self._begin(state, shapes, seas)
        self.campaign.player = player
        self.start_recording()
        self.view.message = "Campaign restored. Your orders, commander."
        return True

    def autosave(self) -> None:
        audio = self.context.audio
        if not (audio and audio.settings["autosave"]):
            return
        try:
            path = self.library.path(SaveLibrary.AUTOSAVE)
            save_game(self.state, self.renderer.shapes, self.renderer.seas, self.campaign.player, path)
        except (OSError, ValueError) as exc:
            self.view.message = "Autosave failed: " + str(exc)

    def watch_replay(self, data: dict) -> None:
        self.viewer = ReplayScreen(self.context, self, data)
        self.dialogs.close()

    # Selection and camera -------------------------------------------------------------

    def hit(self, point) -> str | None:
        return self.renderer.hit(point, self.view.layer)

    def inspect(self, province: str, point) -> None:
        self.view.inspected = province
        self.renderer.province_window.open(point, self.renderer.council.rect)

    def focus_unit(self, unit_id: str | None) -> None:
        """Select a unit, switch to its layer and centre the camera on it."""
        unit = self.state.units.get(unit_id)
        if not unit or unit.owner != self.campaign.player or self.view.animation:
            return
        self.view.selected = unit_id
        self.view.layer = unit.layer
        self.renderer.province_window.close()
        self.renderer.map.center_on(unit.location, FOCUS_POINT)
        if unit.location in self.state.provinces:
            self.view.inspected = unit.location
        orders = "Ready for orders." if unit.remaining > 0 else "Orders spent this turn."
        self.view.message = unit.kind.title() + " selected. " + orders

    def next_ready(self) -> None:
        if self.view.animation or not self.campaign.human_turn:
            return
        ready = [u.id for u in self.state.units.values() if u.owner == self.state.active and u.remaining > 0]
        if not ready:
            self.view.message = "All units have spent their orders this turn."
            return
        index = ready.index(self.view.selected) if self.view.selected in ready else -1
        self.focus_unit(ready[(index + 1) % len(ready)])

    def _layer_units(self, layer: str) -> list[str]:
        """The active faction's units commanded from ``layer``."""
        return [
            u.id
            for u in self.state.units.values()
            if u.owner == self.state.active
            and (u.is_land if layer in ("land", "supply") else u.kind == LAYER_UNIT_KIND[layer])
        ]

    def switch_layer(self, layer: str) -> None:
        self.view.layer = layer
        self.renderer.province_window.close()
        units = self._layer_units(layer)
        self.view.selected = units[0] if units and layer in ("naval", "air", "supply") else None
        if layer in ("naval", "air"):
            if not units:
                self.view.message = "This faction has no groups in this layer."
            elif layer == "naval":
                self.view.message = "Fleet selected: click a highlighted sea zone."
            else:
                self.view.message = "Choose Strike, Support or Rebase, then click a target in range."

    def cycle_font(self) -> None:
        theme = self.context.theme
        theme.set_font((theme.font_index + 1) % len(FONT_CHOICES))
        self.renderer.map.invalidate_labels()

    # Turn flow ------------------------------------------------------------------------

    def advance(self) -> None:
        """End the player's turn; rival turns then play out in :meth:`update`."""
        if not self.campaign.human_turn:
            return
        self.renderer.province_window.close()
        self.context.play("turn")
        end_turn(self.state)
        self.view.selected = None
        self.view.inspected = None
        self.view.message = "Enemy factions are taking their turns…"

    def update(self, dt: float) -> None:
        self.tutorial.observe()
        if self.dialogs.mode:
            return
        renderer = self.renderer
        renderer.time += dt
        renderer.build_effects = {
            p: t for p, t in renderer.build_effects.items() if renderer.time - t < BUILD_EFFECT_SECONDS
        }
        if self.campaign.player and not self.campaign.human_turn:
            self._play_rivals(dt)
        elif self.view.animation and self.view.animation.update(
            dt, renderer.map.anchors, renderer.map.camera.period
        ):
            self.view.animation = None

    def _play_rivals(self, dt: float) -> None:
        """Run one rival action every AI_ACTION_SECONDS so the player can follow along."""
        self.ai_delay -= dt
        if self.ai_delay > 0:
            return
        self.ai_delay = AI_ACTION_SECONDS
        if self.ai_turn is None:
            self.ai_turn = faction_actions(self.state)
        journal_before = {id(entry) for entry in self.state.reports}
        try:
            _unit, _route, message = next(self.ai_turn)
        except StopIteration:
            self._finish_rival_turn()
            return
        new_entries = [entry for entry in self.state.reports if id(entry) not in journal_before]
        if any(entry["kind"] in BATTLE_KINDS for entry in new_entries):
            self.context.play("battle")
        self.renderer.map.invalidate_labels()
        self.view.message = self.state.factions[self.state.active].name + ": " + message

    def _finish_rival_turn(self) -> None:
        end_turn(self.state)
        self.ai_turn = None
        if not self.campaign.human_turn:
            return
        stage = campaign_stage(self.state)
        self.view.message = f"{date_label(self.state.clock)} / {stage.name}: {stage.goal}"
        if self.campaign.recorder:
            self.campaign.recorder.append(self.state, "end_turn", [])
        self.autosave()
        self.context.play("turn")

    # Drawing --------------------------------------------------------------------------

    def draw(self, hover: str | None) -> None:
        self.renderer.draw(self.view, hover, dialog_open=self.dialogs.mode is not None)
        self.tutorial.draw()
        self.dialogs.draw()
        self.context.theme.tips.draw(self.context.theme)

    # Input ----------------------------------------------------------------------------

    def event(self, event: pygame.event.Event) -> bool:
        """Handle one event; returns False when the player quits."""
        if event.type == pygame.WINDOWFOCUSLOST:
            self.map_press = None
            self.map_dragged = self.panning = self.dragging_window = False
        # A left press on the map is held until release, so a drag can never issue an order.
        if self._is_left_press(event) and self._can_press_map(event.pos):
            self.map_press = event
            self.map_dragged = False
            return True
        if self.map_press is not None:
            if event.type == pygame.MOUSEMOTION:
                if self._travelled(event.pos) > DRAG_THRESHOLD:
                    self.map_dragged = True
                if self.map_dragged:
                    self.renderer.map.pan(*event.rel)
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                press = self.map_press
                dragged = self.map_dragged or self._travelled(event.pos) > DRAG_THRESHOLD
                self.map_press = None
                self.map_dragged = False
                return True if dragged else self._dispatch(press)
        return self._dispatch(event)

    def _travelled(self, point) -> float:
        return pygame.Vector2(point).distance_to(self.map_press.pos)

    def _can_press_map(self, point) -> bool:
        blocked = self.renderer.blocks_map(point, self.view.layer)
        return not blocked and self.campaign.human_turn and not self.view.animation

    @staticmethod
    def _is_left_press(event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

    @staticmethod
    def _is_key(event: pygame.event.Event, *keys: int) -> bool:
        return event.type == pygame.KEYDOWN and event.key in keys

    def _dispatch(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if self.dialogs.mode:
            return self.dialogs.event(event)
        if self.tutorial.event(event):
            return True
        handlers = (
            self._top_bar_input,
            self._market_input,
            self._menu_input,
            self._file_shortcuts,
            self._faction_choice,
        )
        if any(handler(event) for handler in handlers):
            return True
        if self.campaign.human_turn:
            self._command_input(event)
        return True

    def _top_bar_input(self, event) -> bool:
        renderer = self.renderer
        if self._is_left_press(event):
            if renderer.objectives.button.collidepoint(event.pos):
                renderer.objectives.toggle()
                return True
            if renderer.menu.pedia_button.collidepoint(event.pos):
                self.dialogs.open("pedia")
                return True
        if event.type == pygame.KEYDOWN and event.key in DIALOG_KEYS:
            self.dialogs.open(DIALOG_KEYS[event.key])
            return True
        on_calendar = self._is_left_press(event) and renderer.calendar.rect.collidepoint(event.pos)
        if self.campaign.player and (self._is_key(event, pygame.K_t) or on_calendar):
            self.dialogs.open("timeline")
            return True
        return False

    def _market_input(self, event) -> bool:
        market = self.renderer.market
        if market.open:
            if self._is_key(event, pygame.K_ESCAPE, pygame.K_m):
                market.open = False
            elif self._is_left_press(event):
                if market.close_button.collidepoint(event.pos):
                    market.open = False
                elif trade := market.trade_at(event.pos):
                    _, self.view.message = self.campaign.trade(*trade)
                    market.receipt = self.view.message
            return True
        if self._is_key(event, pygame.K_m) and self.campaign.player:
            market.open = True
            self.renderer.menu.open = False
            return True
        return False

    def _menu_input(self, event) -> bool:
        menu = self.renderer.menu
        if self._is_key(event, pygame.K_ESCAPE) and menu.open:
            menu.open = False
            return True
        if not self._is_left_press(event):
            return False
        if menu.button.collidepoint(event.pos):
            menu.open = not menu.open
            return True
        if not menu.open:
            return False
        item = menu.item_at(event.pos)
        if item == "font":
            self.cycle_font()
            return True
        if item in self.dialogs.dialogs:
            self.dialogs.open(item)
        elif item == "market" and self.campaign.player:
            self.renderer.market.open = True
        elif item == "display":
            self.context.request_display_toggle()
        # Any click while the menu is open closes it.
        menu.open = False
        return True

    def _file_shortcuts(self, event) -> bool:
        if self._is_key(event, pygame.K_F6):
            self.cycle_font()
        elif self._is_key(event, pygame.K_F9):
            self.dialogs.open("load")
        elif self._is_key(event, pygame.K_F5):
            self.dialogs.open("save")
        else:
            return False
        return True

    def _faction_choice(self, event) -> bool:
        """Before a faction is chosen, the picker captures all input."""
        if self.campaign.player is not None:
            return False
        if self._is_left_press(event):
            faction = self.renderer.picker.faction_at(event.pos)
            if faction:
                self.choose_faction(faction)
        if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_8:
            self.choose_faction(list(self.state.factions)[event.key - pygame.K_1])
        return True

    def _command_input(self, event) -> None:
        view, renderer = self.view, self.renderer
        if self._is_key(event, pygame.K_n):
            self.next_ready()
            return
        if self._is_key(event, pygame.K_f):
            self.focus_unit(view.selected)
            return
        if self._is_key(event, pygame.K_TAB):
            self._cycle_selection()
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging_window = False
        if event.type == pygame.MOUSEMOTION and self.dragging_window and renderer.province_window.is_open:
            renderer.province_window.drag(event.rel)
            return
        self._camera_input(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            province = self.hit(event.pos)
            if province in self.state.provinces:
                self.inspect(province, event.pos)
        if event.type == pygame.KEYDOWN:
            self._key_command(event.key)
        if self._is_left_press(event) and not view.animation:
            self._left_click(event.pos)

    def _cycle_selection(self) -> None:
        units = self._layer_units(self.view.layer)
        if units:
            index = units.index(self.view.selected) if self.view.selected in units else -1
            self.view.selected = units[(index + 1) % len(units)]
            self.renderer.province_window.close()

    def _camera_input(self, event) -> None:
        """Middle-drag pans and the wheel zooms, unless a move is animating."""
        map_view = self.renderer.map
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.panning = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2 and not self._blocked(event.pos):
            self.panning = True
        if event.type == pygame.MOUSEMOTION and self.panning and not self.view.animation:
            map_view.pan(*event.rel)
        if event.type == pygame.MOUSEWHEEL and not self.view.animation:
            point = self.context.mouse_pos()
            if not self._blocked(point):
                map_view.zoom(ZOOM_STEP**event.y, point)

    def _blocked(self, point) -> bool:
        return self.renderer.blocks_map(point, self.view.layer)

    def _key_command(self, key: int) -> None:
        if key == pygame.K_F3:
            self.view.debug = not self.view.debug
        if key == pygame.K_ESCAPE:
            self.view.selected = None
            self.renderer.province_window.close()
            self.dragging_window = False
        if key in LAYER_KEYS:
            self.switch_layer(LAYER_KEYS[key])
        if key == pygame.K_SPACE and not self.view.animation:
            self.advance()

    def _left_click(self, point) -> None:
        renderer, view = self.renderer, self.view
        if renderer.province_window.contains(point):
            self._province_window_click(point)
            return
        if renderer.council.ready_button.collidepoint(point):
            self.next_ready()
            return
        if view.layer == "air" and self._air_click(point):
            return
        city = renderer.city_at(point, view.layer) if view.layer in ("land", "supply") else None
        if city:
            self.inspect(self.state.cities[city].province, point)
            return
        action = renderer.council.action_at(point)
        if action == "home":
            renderer.map.reset_camera()
        elif action in LAYER_UNIT_KIND:
            self.switch_layer(action)
        elif action == "end":
            self.advance()
        else:
            self._map_click(point)

    def _air_click(self, point) -> bool:
        view = self.view
        mode = self.renderer.selection.air_mode_at(point)
        if mode:
            view.air_mode = mode
            view.message = AIR_MODE_HELP[mode]
            return True
        target = self.hit(point)
        unit = self.state.units.get(view.selected)
        if not (unit and target and target != unit.location):
            return False
        ok, view.message = self.campaign.air_mission(unit.id, target, view.air_mode)
        if ok:
            self.context.play("battle" if view.air_mode == STRIKE else "move")
        if view.selected not in self.state.units:
            view.selected = None
        return True

    def _map_click(self, point) -> None:
        """Move the selected unit there, select a unit standing there, or inspect the province."""
        state, view = self.state, self.view
        destination = self.hit(point)
        here = [
            u
            for u in state.units.values()
            if u.location == destination
            and u.owner == state.active
            and (u.is_land if view.layer in ("land", "supply") else u.kind == LAYER_UNIT_KIND[view.layer])
        ]
        selected = state.units.get(view.selected)
        if (
            selected
            and destination
            and view.layer != "supply"
            and self._is_move_target(selected, destination)
        ):
            self._move(selected.id, destination)
        elif here:
            self.renderer.province_window.close()
            index = next((i for i, u in enumerate(here) if u.id == view.selected), -1)
            view.selected = here[(index + 1) % len(here)].id
            if destination in state.provinces:
                view.inspected = destination
            view.message = SELECT_HINTS.get(view.layer, DEFAULT_SELECT_HINT)
        elif destination in state.provinces:
            self.inspect(destination, point)

    def _is_move_target(self, unit, destination: str) -> bool:
        """Any other node is a move order; a fleet's own sea is one only if an enemy fleet is there."""
        if destination != unit.location:
            return True
        return unit.kind == FLEET and any(
            u.kind == FLEET and u.owner != unit.owner and u.location == destination
            for u in self.state.units.values()
        )

    def _move(self, unit_id: str, destination: str) -> None:
        view = self.view
        route, view.message = self.campaign.move(unit_id, destination)
        self.renderer.map.invalidate_labels()
        if route:
            self.context.play("move" if "Movement completed" in view.message else "battle")
        if len(route) > 1:
            view.animation = MoveAnimation(unit_id, route, self.renderer.map.anchors[route[0]])
        if view.selected not in self.state.units:
            view.selected = None

    def _province_window_click(self, point) -> None:
        window, view = self.renderer.province_window, self.view
        hit = window.action_at(point)
        if hit is None:
            return
        action, name = hit
        if action == "close":
            window.close()
        elif action == "drag":
            self.dragging_window = True
        elif action == "tab":
            window.select_tab(name)
        elif action == "page":
            window.select_recruit_page(name)
        elif action == "recruit":
            unit_id, view.message = self.campaign.recruit(view.inspected, name)
            if unit_id:
                self.context.play("build")
                view.selected = unit_id
                view.layer = {FLEET: "naval", AIR: "air"}.get(name, "land")
                self.renderer.map.invalidate_labels()
        elif action == "build":
            built, view.message = self.campaign.construct(view.inspected, name)
            if built:
                self.context.play("build")
                self.renderer.build_effects[view.inspected] = self.renderer.time
