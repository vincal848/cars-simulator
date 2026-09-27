"""The campaign screen: turns clicks and keys into simulation commands and runs rival turns.

Input goes, in order, to an open window, the tutorial card, keyboard shortcuts,
the docked panel, the interface around the map, and finally to the map itself.
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
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.map_view import MAP_MODES
from cars.ui.panels import PANELS
from cars.ui.renderer import GameRenderer, ViewState
from cars.ui.screens.replay import ReplayScreen
from cars.ui.tutorial import Tutorial
from cars.ui.typography import FONT_CHOICES
from cars.ui.windows import WINDOWS

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.context import UiContext
    from cars.ui.frames import Frame

DRAG_THRESHOLD = 6
AI_ACTION_SECONDS = 0.35
BUILD_EFFECT_SECONDS = 2
ZOOM_STEP = 1.2
TUTORIAL_RESOURCES = 80
MODE_KEYS = dict(zip((pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4), MAP_MODES, strict=True))
PANEL_KEYS = {
    pygame.K_i: "nation",
    pygame.K_u: "military",
    pygame.K_d: "diplomacy",
    pygame.K_m: "market",
    pygame.K_j: "chronicle",
}
WINDOW_KEYS = {
    pygame.K_F1: "pedia",
    pygame.K_g: "strategy",
    pygame.K_r: "replay",
    pygame.K_t: "timeline",
    pygame.K_F5: "save",
    pygame.K_F9: "load",
    pygame.K_F10: "settings",
}
AIR_MODE_HELP = {
    STRIKE: "Click an enemy force within range. One sortie per turn.",
    SUPPORT: "Click a province to grant +25% land attack there.",
    REBASE: "Click another controlled airbase within range.",
}


def headline(message: str) -> str:
    """A battle report without its list of modifiers, which the chronicle keeps."""
    return message.split(" Terrain ×")[0]


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
        self.view = ViewState(message="Choose your nation to begin.")
        self.ai_turn: Iterator[Action] | None = None
        self.ai_delay = 0.0
        self.map_press: pygame.event.Event | None = None
        self.map_dragged = False
        self.panning = False
        self.panels = {name: cls(self) for name, cls in PANELS.items()}
        self.windows = {name: cls(self) for name, cls in WINDOWS.items()}
        self.window: Frame | None = None
        self.tutorial = Tutorial(self)
        self.renderer.blockers = [self.tutorial.blocks, lambda _point: self.window is not None]
        self._shown_message = ""
        if self.campaign.player is None:
            self.open_window("picker")

    # Frames ---------------------------------------------------------------------------

    @property
    def panel(self) -> "Frame | None":
        return self.renderer.panel

    @property
    def window_name(self) -> str | None:
        return getattr(self.window, "name", None)

    def open_panel(self, name: str) -> None:
        """Open a docked panel, or close it if it is already open."""
        if self.panel is self.panels[name] and name != "province":
            self.renderer.panel = None
            return
        panel = self.panels[name]
        panel.on_open()
        self.renderer.panel = panel

    def open_window(self, name: str) -> None:
        window = self.windows[name]
        window.on_open()
        self.window = window
        if getattr(window, "text_input", False):
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

    def open_pedia(self, article: str) -> None:
        """Open the CARSapedia at ``article``."""
        self.open_window("pedia")
        self.windows["pedia"].go(article)

    def close_frame(self, frame: "Frame") -> None:
        if frame is self.window:
            self.window = None
            pygame.key.stop_text_input()
            if self.campaign.player is None and self.viewer is None:
                self.open_window("picker")
        elif frame is self.panel:
            self.renderer.panel = None

    # Campaign lifecycle ---------------------------------------------------------------

    def choose_faction(self, faction: str) -> None:
        if not self.campaign.choose(faction):
            return
        if self.window_name == "picker":
            self.window = None
        self.view.selected = None
        army = next((u for u in self.state.units.values() if u.owner == faction and u.is_land), None)
        if army:
            self.renderer.map.center_on(army.location)
        self.view.message = f"You command {self.state.factions[faction].name}. Seven rivals act on their own."
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
        self.renderer.map.center_on(infantry.location)
        self.view.message = "Guided tutorial: ten lessons. Your saved campaigns are untouched."

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
            self.view.message = "Campaign saved."
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
        self.campaign.player = player  # Keep the picker from opening while rebinding.
        self._begin(state, shapes, seas)
        self.campaign.player = player
        self.window = None
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
        self.window = None

    # Selection and camera -------------------------------------------------------------

    def hit(self, point) -> str | None:
        return self.renderer.hit(point, self.view.layer)

    def inspect(self, province: str, point=None) -> None:
        """Open the province panel for ``province``."""
        self.view.inspected = province
        self.open_panel("province")

    def select(self, unit_id: str | None) -> None:
        unit = self.state.units.get(unit_id)
        self.view.selected = unit_id if unit else None
        if unit:
            self.view.layer = unit.layer

    def focus_unit(self, unit_id: str | None) -> None:
        """Select a unit and centre the camera on it."""
        unit = self.state.units.get(unit_id)
        if not unit or unit.owner != self.campaign.player or self.view.animation:
            return
        self.select(unit_id)
        self.renderer.map.center_on(unit.location)
        orders = "ready for orders" if unit.remaining > 0 else "orders spent this turn"
        self.view.message = f"{unit.kind.title()} selected, {orders}."

    def next_ready(self) -> None:
        if self.view.animation or not self.campaign.human_turn:
            return
        ready = [u.id for u in self.state.units.values() if u.owner == self.state.active and u.remaining > 0]
        if not ready:
            self.view.message = "Every unit has spent its orders this turn."
            return
        index = ready.index(self.view.selected) if self.view.selected in ready else -1
        self.focus_unit(ready[(index + 1) % len(ready)])

    def set_mode(self, mode: str) -> None:
        self.view.mode = mode

    def cycle_font(self) -> None:
        ui = self.context.ui
        ui.set_font((ui.font_index + 1) % len(FONT_CHOICES))
        if self.context.audio:
            self.context.audio.set("font", ui.font_index)
        self.renderer.map.invalidate_labels()

    # Turn flow ------------------------------------------------------------------------

    def advance(self) -> None:
        """End the player's turn; rival turns then play out in :meth:`update`."""
        if not self.campaign.human_turn or self.view.animation:
            return
        self.context.play("turn")
        end_turn(self.state)
        self.view.selected = None
        self.view.message = "The rival nations are taking their turns…"

    def update(self, dt: float) -> None:
        self.tutorial.observe()
        renderer = self.renderer
        renderer.toasts.update(dt)
        if self.view.message != self._shown_message:
            self._shown_message = self.view.message
            renderer.toasts.push(self.view.message)
        if self.window is not None:
            return
        if self.campaign.human_turn and self.state.events["pending"] and not self.view.animation:
            self.open_window("event")
            return
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
        self.view.message = self.state.factions[self.state.active].name + ": " + headline(message)

    def _finish_rival_turn(self) -> None:
        end_turn(self.state)
        self.ai_turn = None
        if not self.campaign.human_turn:
            return
        stage = campaign_stage(self.state)
        self.view.message = f"{date_label(self.state.clock)}: {stage.goal}"
        if self.campaign.recorder:
            self.campaign.recorder.append(self.state, "end_turn", [])
        self.autosave()
        self.context.play("turn")

    # Drawing --------------------------------------------------------------------------

    def draw(self, hover: str | None) -> None:
        ui = self.context.ui
        self.renderer.draw(self.view, hover, window_open=self.window is not None)
        self.tutorial.draw()
        if self.window is not None:
            ui.tips.begin()
            self.window.draw()
        ui.tips.draw(ui)

    # Input ----------------------------------------------------------------------------

    def event(self, event: pygame.event.Event) -> bool:
        """Handle one event; returns False when the player quits."""
        if event.type == pygame.WINDOWFOCUSLOST:
            self.map_press = None
            self.map_dragged = self.panning = False
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
                    self.renderer.map.pan(*event.rel, dragging=True)
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                press = self.map_press
                dragged = self.map_dragged or self._travelled(event.pos) > DRAG_THRESHOLD
                self.map_press = None
                self.map_dragged = False
                if not dragged and not self.view.animation:
                    self._map_click(press.pos)
                return True
        return self._dispatch(event)

    def _travelled(self, point) -> float:
        return pygame.Vector2(point).distance_to(self.map_press.pos)

    def _can_press_map(self, point) -> bool:
        return (
            self.window is None and not self.renderer.blocks_map(point) and self.campaign.player is not None
        )

    @staticmethod
    def _is_left_press(event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1

    @staticmethod
    def _is_key(event: pygame.event.Event, *keys: int) -> bool:
        return event.type == pygame.KEYDOWN and event.key in keys

    def _dispatch(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if self.window is not None:
            self.window.handle(event)
            return True
        if self.tutorial.event(event):
            return True
        if event.type == pygame.KEYDOWN:
            self._key(event.key)
            return True
        if self.panel is not None and self.panel.handle(event):
            return True
        if self._interface_input(event):
            return True
        self._map_input(event)
        return True

    def _key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.panel is not None:
                self.renderer.panel = None
            elif self.view.selected:
                self.view.selected = None
            else:
                self.open_window("menu")
            return
        if key in WINDOW_KEYS:
            self.open_window(WINDOW_KEYS[key])
        elif key in PANEL_KEYS and self.campaign.player:
            self.open_panel(PANEL_KEYS[key])
        elif key in MODE_KEYS:
            self.set_mode(MODE_KEYS[key])
        elif key == pygame.K_F6:
            self.cycle_font()
        elif key == pygame.K_F3:
            self.view.debug = not self.view.debug
        elif key == pygame.K_HOME:
            self.renderer.map.reset_camera()
        elif not self.campaign.human_turn:
            return
        elif key == pygame.K_n:
            self.next_ready()
        elif key == pygame.K_f:
            self.focus_unit(self.view.selected)
        elif key == pygame.K_TAB:
            self._cycle_selection()
        elif key == pygame.K_SPACE:
            self.advance()

    def _interface_input(self, event: pygame.event.Event) -> bool:
        """Clicks and scrolling on the interface around the map; True when consumed."""
        renderer = self.renderer
        point = getattr(event, "pos", None) or self.context.mouse_pos()
        if event.type == pygame.MOUSEWHEEL and renderer.outliner.contains(point):
            renderer.outliner.scroll_by(event.y)
            return True
        if not self._is_left_press(event):
            return event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and renderer.blocks_map(point)
        if renderer.top_bar.date_rect.collidepoint(point) and self.campaign.player:
            self.open_window("timeline")
            return True
        action = renderer.sidebar.action_at(point)
        if action:
            if action == "menu":
                self.open_window("menu")
            elif action == "pedia":
                self.open_window("pedia")
            elif self.campaign.player:
                self.open_panel(action)
            return True
        action = renderer.outliner.action_at(point)
        if action:
            renderer.outliner.handle_action(action, self)
            return True
        action = renderer.controls.action_at(point)
        if action:
            self._control(action)
            return True
        action = renderer.unit_card.action_at(point)
        if action:
            if action == "deselect":
                self.view.selected = None
            elif action.startswith("mission:"):
                self.view.air_mode = action.removeprefix("mission:")
                self.view.message = AIR_MODE_HELP[self.view.air_mode]
            return True
        return renderer.blocks_map(point)

    def _control(self, action: str) -> None:
        if action in MAP_MODES:
            self.set_mode(action)
        elif action == "home":
            self.renderer.map.reset_camera()
        elif action == "ready":
            self.next_ready()
        elif action == "end":
            self.advance()

    def _map_input(self, event: pygame.event.Event) -> None:
        """Camera movement, and right-clicks that open a province."""
        map_view = self.renderer.map
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.panning = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self.panning = True
        if event.type == pygame.MOUSEMOTION and self.panning:
            map_view.pan(*event.rel, dragging=True)
        if event.type == pygame.MOUSEWHEEL:
            map_view.zoom(ZOOM_STEP**event.y, self.context.mouse_pos())
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.campaign.player:
            province = self.renderer.map.node_at(event.pos, "land")
            if province in self.state.provinces:
                self.inspect(province)

    def _cycle_selection(self) -> None:
        unit = self.state.units.get(self.view.selected)
        if unit is None:
            return
        here = [
            u.id
            for u in self.state.units.values()
            if u.owner == unit.owner and u.location == unit.location and u.layer == unit.layer
        ]
        self.select(here[(here.index(unit.id) + 1) % len(here)])

    def _map_click(self, point) -> None:
        """Order the selected unit there, select a stack, or open a province."""
        state, view = self.state, self.view
        if not self.campaign.human_turn:
            return
        selected = state.units.get(view.selected)
        if selected and selected.kind == AIR and self._air_order(selected, point):
            return
        stack = [u for u in self.renderer.map.stack_at(point) if state.units[u].owner == state.active]
        destination = self.renderer.map.node_at(point, selected.layer if selected else "land")
        if selected and not stack and destination and self._is_move_target(selected, destination):
            self._move(selected.id, destination)
        elif stack:
            index = stack.index(view.selected) if view.selected in stack else -1
            self.select(stack[(index + 1) % len(stack)])
        elif destination in state.provinces:
            self.inspect(destination)

    def _air_order(self, unit, point) -> bool:
        target = self.renderer.map.node_at(point, "air")
        if not target or target == unit.location:
            return False
        ok, self.view.message = self.campaign.air_mission(unit.id, target, self.view.air_mode)
        if ok:
            self.context.play("battle" if self.view.air_mode == STRIKE else "move")
        if self.view.selected not in self.state.units:
            self.view.selected = None
        return True

    def _is_move_target(self, unit, destination: str) -> bool:
        """Any other node is a move order; a fleet's own sea is one only if an enemy fleet is there."""
        if destination != unit.location:
            return True
        return unit.kind == FLEET and any(
            u.kind == FLEET and self.state.at_war(unit.owner, u.owner) and u.location == destination
            for u in self.state.units.values()
        )

    def _move(self, unit_id: str, destination: str) -> None:
        view = self.view
        route, message = self.campaign.move(unit_id, destination)
        view.message = headline(message)
        self.renderer.map.invalidate_labels()
        if route:
            self.context.play("move" if "Movement completed" in view.message else "battle")
        if len(route) > 1:
            view.animation = MoveAnimation(unit_id, route, self.renderer.map.anchors[route[0]])
        if view.selected not in self.state.units:
            view.selected = None

    # Commands from panels -------------------------------------------------------------

    def recruit(self, province: str, kind: str) -> None:
        unit_id, self.view.message = self.campaign.recruit(province, kind)
        if unit_id:
            self.context.play("build")
            self.select(unit_id)
            self.renderer.map.invalidate_labels()

    def construct(self, province: str, kind: str) -> None:
        built, self.view.message = self.campaign.construct(province, kind)
        if built:
            self.context.play("build")
            self.renderer.build_effects[province] = self.renderer.time
