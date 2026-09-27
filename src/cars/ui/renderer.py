"""A campaign on screen: the map and the interface around it. Drawing and hit testing only.

The same view renders live play and read-only replays; input belongs to the screens.
Everything is laid out afresh each frame from the window size and the UI scale.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from cars.sim.balloons import OBSERVE, coverage
from cars.sim.entities import FLEET
from cars.sim.movement import reachable
from cars.sim.naval import reachable_seas
from cars.sim.visibility import visible_nodes
from cars.ui.hud.controls import Controls
from cars.ui.hud.forecast_card import ForecastCard
from cars.ui.hud.outliner import Outliner
from cars.ui.hud.sidebar import Sidebar
from cars.ui.hud.toasts import Toasts
from cars.ui.hud.top_bar import TopBar
from cars.ui.hud.unit_card import UnitCard
from cars.ui.kit import style
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.map_view import POLITICAL, SUPPLY, MapView, Scene

if TYPE_CHECKING:
    from cars.sim.campaign import Campaign
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.context import UiContext
    from cars.ui.frames import Frame

Point = tuple[int, int]


@dataclass
class ViewState:
    """The player's current selection and what the map is showing."""

    layer: str = "land"
    mode: str = POLITICAL
    selected: str | None = None
    inspected: str | None = None
    message: str = ""
    debug: bool = False
    animation: MoveAnimation | None = None
    mission_mode: str = OBSERVE


class GameRenderer:
    def __init__(
        self, context: "UiContext", state: "GameState", shapes: dict, seas: list[dict], campaign: "Campaign"
    ) -> None:
        self.context = context
        self.ui = context.ui
        self.state = state
        self.shapes = shapes
        self.seas = seas
        self.campaign = campaign
        self.map = MapView(state, shapes, seas, self.ui)
        self.top_bar = TopBar(self.ui)
        self.sidebar = Sidebar(self.ui)
        self.outliner = Outliner(self.ui)
        self.controls = Controls(self.ui)
        self.unit_card = UnitCard(self.ui)
        self.toasts = Toasts(self.ui)
        self.forecast = ForecastCard(self.ui)
        self.time = 0.0
        self.build_effects: dict[str, float] = {}
        # Hide enemy forces the player cannot see. Replays show everything.
        self.fog = True
        # Read-only replays show the map and top bar but none of the command interface.
        self.interactive = True
        self.panel: Frame | None = None
        # Overlays owned by the screen (windows, tutorial) that also capture the pointer.
        self.blockers: list[Callable[[Point], bool]] = []
        self.layout()

    def set_state(self, state: "GameState") -> None:
        """Show a different state of the same campaign (replay playback)."""
        self.state = state
        self.map.state = state
        self.map.names.state = state
        self.campaign.state = state
        self.map.invalidate_labels()

    @property
    def player(self) -> str:
        """The faction the interface reports on: the human, or whoever is active before one is chosen."""
        return self.campaign.player or self.state.active

    def place_name(self, node: str) -> str:
        if node in self.state.provinces:
            return self.state.provinces[node].name
        return self.map.seas.get(node, {}).get("name", node)

    # Layout ---------------------------------------------------------------------------

    def layout(self) -> None:
        screen = self.ui.screen
        self.top_bar.layout(screen)
        top = self.top_bar.rect.bottom
        self.sidebar.layout(screen, top)
        self.controls.layout(screen)
        self.outliner.layout(screen, top, self.controls.rect.top - self.ui.px(4))
        left = self.panel.place(screen).right if self.panel is not None else self.sidebar.rect.right
        self.unit_card.layout(screen, left)
        card = self.unit_card.rect
        if card.colliderect(self.controls.rect):
            # On narrow windows the card sits above the map-mode bar instead of beside it.
            card.bottom = self.controls.rect.top - self.ui.px(10)
            if card.right > self.controls.rect.right:
                card.right = self.controls.rect.right

    def interface_rects(self) -> list[pygame.Rect]:
        """Everything drawn over the map, for keeping labels clear of it."""
        rects = [self.top_bar.rect]
        if self.interactive:
            rects += [self.sidebar.rect, self.outliner.rect, self.controls.rect]
            if self.unit_card.areas:
                rects.append(self.unit_card.rect)
            if self.panel is not None and self.panel.rect is not None:
                rects.append(self.panel.rect)
        return rects

    # Hit testing ----------------------------------------------------------------------

    def blocks_map(self, point: Point, layer: str = "land") -> bool:
        """True when the interface, rather than the map, is under ``point``."""
        if any(blocker(point) for blocker in self.blockers) or self.top_bar.rect.collidepoint(point):
            return True
        if not self.interactive:
            return False
        return bool(
            self.sidebar.rect.collidepoint(point)
            or self.outliner.contains(point)
            or self.controls.contains(point)
            or self.unit_card.contains(point)
            or (self.panel is not None and self.panel.contains(point))
        )

    def hit(self, point: Point, layer: str) -> str | None:
        """The map node under ``point``, or None if the interface covers it."""
        if self.campaign.player is None or self.blocks_map(point, layer):
            return None
        return self.map.node_at(point, layer)

    def city_at(self, point: Point) -> str | None:
        if self.blocks_map(point) or self.campaign.player is None:
            return None
        return self.map.city_at(point)

    def reach(self, unit: "Unit | None") -> tuple["Paths | None", set[str]]:
        """Routes available to the selected unit and the nodes to highlight."""
        if unit is None:
            return None, set()
        if unit.is_land:
            paths = reachable(self.state, unit)
        elif unit.kind == FLEET:
            paths = reachable_seas(self.state, unit)
        else:
            return None, coverage(self.state, unit)
        return paths, set(paths.costs)

    def visible(self, view: ViewState) -> set[str] | None:
        """Nodes the player can see, or None when nothing is hidden (no player, fog off, debug)."""
        if not self.fog or self.campaign.player is None or view.debug:
            return None
        return visible_nodes(self.state, self.campaign.player)

    # Drawing --------------------------------------------------------------------------

    def draw(self, view: ViewState, hover: str | None, window_open: bool = False) -> None:
        ui, state = self.ui, self.state
        ui.tips.begin()
        self.layout()
        unit = state.units.get(view.selected)
        paths, highlights = self.reach(unit)
        visible = self.visible(view)
        layer = unit.layer if unit else "land"
        if view.mode == SUPPLY and unit and unit.is_land:
            layer = "supply"
        view.layer = layer
        scene = Scene(
            layer=layer,
            mode=view.mode,
            unit=unit,
            hover=hover,
            inspected=view.inspected if self.panel is not None else None,
            debug=view.debug,
            animation=view.animation,
            mission_mode=view.mission_mode,
            paths=paths,
            highlights=highlights if layer != "supply" else set(),
            city_hover=self.city_at(ui.mouse()),
            time=self.time,
            build_effects=self.build_effects,
            viewer=self.campaign.player,
            visible=visible,
        )
        rects = self.interface_rects()
        description = self.map.draw(ui.surface, scene, rects, rects)
        if self.interactive:
            self.unit_card.draw(state, unit, hover, paths, view.mission_mode, self.place_name)
            self.sidebar.draw(getattr(self.panel, "name", None))
            if self.campaign.player:
                self.outliner.draw(state, self.player, view.selected)
            self.controls.draw(state, self.player, view.mode, self.campaign.human_turn)
            if self.panel is not None:
                self.panel.draw()
        self.top_bar.draw(state, self.player)
        left = self.sidebar.rect.right if self.interactive else 0
        if self.interactive and self.panel is not None and self.panel.rect is not None:
            left = self.panel.rect.right
        right = self.outliner.rect.left if self.interactive and self.campaign.player else self.ui.screen.right
        self.toasts.draw(self.top_bar.rect.bottom, left, right)
        pointer_free = not window_open and not self.blocks_map(ui.mouse())
        # A forecast would reveal hidden defenders, so only forecast what can be seen.
        if pointer_free and (visible is None or hover in visible):
            self.forecast.draw(state, unit, hover, paths)
        if pointer_free and description:
            self._pointer_note(description)

    def _pointer_note(self, text: str) -> None:
        """A short line beside the pointer describing the map feature under it."""
        ui = self.ui
        font = ui.font(style.SMALL)
        label = font.render(text, True, style.ON_SLATE)
        x, y = ui.mouse()
        box = label.get_rect(topleft=(x + ui.px(18), y + ui.px(18))).inflate(ui.px(12), ui.px(6))
        box.clamp_ip(ui.screen)
        pygame.draw.rect(ui.surface, style.SLATE_DARK, box, border_radius=ui.px(3))
        ui.surface.blit(label, label.get_rect(center=box.center))
