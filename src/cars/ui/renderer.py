"""A campaign on screen: the map plus every HUD panel. Drawing and hit testing only.

The same view renders live play and read-only replays; input belongs to the screens.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cars.sim.air import STRIKE, coverage
from cars.sim.entities import FLEET
from cars.sim.movement import reachable
from cars.sim.naval import reachable_seas
from cars.sim.supply import supplied_provinces
from cars.sim.visibility import visible_nodes
from cars.ui.hud.bottom_bar import EMBLEM_RECT, SelectionCard, draw_compass, draw_emblem, draw_status_bar
from cars.ui.hud.council import CouncilPanel
from cars.ui.hud.faction_picker import FactionPicker
from cars.ui.hud.forecast_card import ForecastCard
from cars.ui.hud.market import MarketPanel
from cars.ui.hud.menu import GameMenu
from cars.ui.hud.objectives import CalendarHeader, ObjectivesPanel
from cars.ui.hud.province_window import ProvinceWindow
from cars.ui.map.animation import MoveAnimation
from cars.ui.map.map_view import MapView, Scene
from cars.ui.palette import MAP_AREA

if TYPE_CHECKING:
    from cars.sim.campaign import Campaign
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState
    from cars.ui.context import UiContext

Point = tuple[int, int]


@dataclass
class ViewState:
    """The player's current selection and what the map is showing."""

    layer: str = "land"
    selected: str | None = None
    inspected: str | None = None
    message: str = ""
    debug: bool = False
    animation: MoveAnimation | None = None
    air_mode: str = STRIKE


class GameRenderer:
    def __init__(
        self, context: "UiContext", state: "GameState", shapes: dict, seas: list[dict], campaign: "Campaign"
    ) -> None:
        self.context = context
        self.theme = context.theme
        self.state = state
        self.shapes = shapes
        self.seas = seas
        self.campaign = campaign
        self.map = MapView(state, shapes, seas, self.theme)
        self.council = CouncilPanel(self.theme)
        self.selection = SelectionCard(self.theme)
        self.province_window = ProvinceWindow(self.theme, self.map.sprites)
        self.calendar = CalendarHeader(self.theme)
        self.objectives = ObjectivesPanel(self.theme)
        self.forecast = ForecastCard(self.theme)
        self.picker = FactionPicker(self.theme, list(state.factions))
        self.menu = GameMenu(context)
        self.market = MarketPanel(self.theme)
        self.time = 0.0
        self.build_effects: dict[str, float] = {}
        # Hide enemy forces the player cannot see. Replays show everything.
        self.fog = True
        # Overlays owned by the screen (dialogs, tutorial) that also capture the pointer.
        self.blockers: list[Callable[[Point], bool]] = []

    def set_state(self, state: "GameState") -> None:
        """Show a different state of the same campaign (replay playback)."""
        self.state = state
        self.map.state = state
        self.campaign.state = state
        self.map.invalidate_labels()

    @property
    def player(self) -> str:
        """The faction the HUD reports on: the human, or whoever is active before one is chosen."""
        return self.campaign.player or self.state.active

    # Hit testing ----------------------------------------------------------------------

    def blocks_map(self, point: Point, layer: str) -> bool:
        """True when a panel, rather than the map, is under ``point``."""
        return bool(
            any(blocker(point) for blocker in self.blockers)
            or (layer == "air" and self.selection.air_mode_at(point))
            or self.market.open
            or (self.state.player and self.calendar.rect.collidepoint(point))
            or EMBLEM_RECT.collidepoint(point)
            or self.menu.blocks(point)
            or self.objectives.blocks(point)
            or not MAP_AREA.collidepoint(point)
            or self.council.rect.collidepoint(point)
            or self.province_window.contains(point)
        )

    def hit(self, point: Point, layer: str) -> str | None:
        """The map node under ``point``, or None if a panel covers it."""
        if self.campaign.player is None or self.blocks_map(point, layer):
            return None
        return self.map.node_at(point, layer)

    def city_at(self, point: Point, layer: str) -> str | None:
        if self.blocks_map(point, layer) or self.campaign.player is None:
            return None
        return self.map.city_at(point)

    def reach(self, unit: "Unit | None", layer: str) -> tuple["Paths | None", set[str]]:
        """Routes available to the selected unit and the nodes to highlight."""
        if layer == "supply":
            return None, supplied_provinces(self.state, self.state.active)
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

    def draw(self, view: ViewState, hover: str | None, dialog_open: bool = False) -> None:
        theme, state = self.theme, self.state
        theme.tips.begin()
        unit = state.units.get(view.selected)
        paths, highlights = self.reach(unit, view.layer)
        visible = self.visible(view)
        scene = Scene(
            layer=view.layer,
            unit=unit,
            hover=hover,
            inspected=view.inspected,
            debug=view.debug,
            animation=view.animation,
            air_mode=view.air_mode,
            paths=paths,
            highlights=highlights,
            city_hover=self.city_at(self.context.mouse_pos(), view.layer),
            time=self.time,
            build_effects=self.build_effects,
            viewer=self.campaign.player,
            visible=visible,
        )
        covered = [self.council.rect]
        if self.province_window.is_open:
            covered.append(self.province_window.rect)
        message = self.map.draw(theme.screen, scene, view.message, [EMBLEM_RECT], covered)

        self.council.draw(state, self.player, view.layer)
        draw_emblem(theme)
        draw_compass(theme)
        self.selection.draw(state, unit, hover, paths, view.debug, view.air_mode)
        draw_status_bar(theme, message)
        self.province_window.draw(state, view.inspected, self.player, self.time, self.build_effects)
        self.calendar.draw(state)
        self.objectives.draw(state)
        overlay_open = self.market.open or self.province_window.is_open or self.menu.open or dialog_open
        # A forecast would reveal hidden defenders, so only forecast what can be seen.
        hover_seen = visible is None or hover in visible
        if view.layer != "supply" and not overlay_open and hover_seen:
            self.forecast.draw(state, unit, hover, paths, view.air_mode)
        if self.campaign.player is None:
            self.picker.draw(state)
        self.menu.draw()
        if self.market.open and self.campaign.player:
            theme.tips.begin()
            self.market.draw(state, self.campaign.player)
