"""The province window, docked on the left: control, statistics, construction and recruitment."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.buildings import BUILDINGS, quote
from cars.sim.entities import AIR, LAND_KINDS
from cars.sim.recruitment import RECRUITS, REGIONAL, quote_recruit, recruit_option
from cars.sim.regional import CHARTERS
from cars.sim.upkeep import unit_upkeep
from cars.ui.art.buildings import celebration, draw_building
from cars.ui.art.cities import city_sprite
from cars.ui.art.landscape import landscape
from cars.ui.palette import DIM, GOLD, GREEN, PAPER

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.art.regiments import UnitSprites
    from cars.ui.theme import Theme

SIZE = (366, 560)
DOCK = (8, 52)
DRAG_BOUNDS = pygame.Rect(0, 44, 1200, 698)
TITLE_HEIGHT = 44
TABS = {
    "build": (
        "Estates",
        "Development: build farms, lumber mills and iron mines to improve resource production.",
    ),
    "infrastructure": (
        "Works",
        "Infrastructure: roads reduce movement costs; shipyards and airfields unlock service recruitment.",
    ),
    "recruit": (
        "Muster",
        "Recruitment: raise land forces, fleets or air groups in controlled cities. "
        "One unit per city per turn.",
    ),
}
RECRUIT_PAGES = {"land": "Land", "sea_air": "Navy / Air", "regional": "Regional"}


class ProvinceWindow:
    def __init__(self, theme: "Theme", sprites: "UnitSprites") -> None:
        self.theme = theme
        self.sprites = sprites
        self.rect: pygame.Rect | None = None
        self.tab = "build"
        self.recruit_page = "land"
        self.layout()

    @property
    def is_open(self) -> bool:
        return self.rect is not None

    def contains(self, point) -> bool:
        return self.rect is not None and self.rect.collidepoint(point)

    def open(self) -> None:
        """Open docked at the left edge, or wherever the player last dragged it."""
        if self.rect is None:
            self.rect = pygame.Rect(*DOCK, *SIZE)
        self.layout()

    def close(self) -> None:
        self.rect = None
        self.layout()

    def drag(self, rel) -> None:
        self.rect.move_ip(*rel)
        self.rect.clamp_ip(DRAG_BOUNDS)
        self.layout()

    def select_tab(self, tab: str) -> None:
        self.tab = tab
        self.layout()

    def select_recruit_page(self, page: str) -> None:
        self.recruit_page = page
        self.layout()

    def layout(self) -> None:
        self.tab_buttons: dict[str, pygame.Rect] = {}
        self.page_buttons: dict[str, pygame.Rect] = {}
        self.recruit_buttons: dict[str, pygame.Rect] = {}
        self.build_buttons: dict[str, pygame.Rect] = {}
        self.close_button = pygame.Rect(0, 0, 0, 0)
        if self.rect is None:
            return
        x, y = self.rect.topleft
        self.close_button = pygame.Rect(x + 328, y + 10, 26, 26)
        self.tab_buttons = {
            name: pygame.Rect(x + 16 + i * 114, y + 347, 108, 23) for i, name in enumerate(TABS)
        }
        if self.tab == "recruit":
            self.page_buttons = {
                name: pygame.Rect(x + 16 + i * 114, y + 374, 108, 22) for i, name in enumerate(RECRUIT_PAGES)
            }
            if self.recruit_page == "regional":
                kinds = [REGIONAL]
            else:
                kinds = [k for k in RECRUITS if (k in LAND_KINDS) == (self.recruit_page == "land")]
            self.recruit_buttons = {
                kind: pygame.Rect(x + 16, y + 400 + i * 33, 334, 31) for i, kind in enumerate(kinds)
            }
        else:
            infrastructure = self.tab == "infrastructure"
            kinds = [k for k, spec in BUILDINGS.items() if spec.is_infrastructure == infrastructure]
            self.build_buttons = {
                kind: pygame.Rect(x + 16, y + 376 + i * 52, 334, 48) for i, kind in enumerate(kinds)
            }

    def action_at(self, point) -> tuple[str, str] | None:
        """What a click at ``point`` does, e.g. ``("build", "farm")`` or ``("drag", "")``."""
        if self.close_button.collidepoint(point):
            return "close", ""
        if point[1] < self.rect.y + TITLE_HEIGHT:
            return "drag", ""
        for group, buttons in (
            ("tab", self.tab_buttons),
            ("page", self.page_buttons),
            ("recruit", self.recruit_buttons),
            ("build", self.build_buttons),
        ):
            for name, rect in buttons.items():
                if rect.collidepoint(point):
                    return group, name
        return None

    # Drawing --------------------------------------------------------------------------

    def draw(
        self, state: "GameState", province_id: str | None, player: str, time: float, effects: dict
    ) -> None:
        province = state.provinces.get(province_id)
        if self.rect is None or province is None:
            return
        t = self.theme
        x, y = self.rect.topleft
        t.shadow(self.rect, 8, 4, 90)
        t.panel(self.rect)
        t.seal("province", (x + 32, y + 29), 34)
        t.text(province.name, x + 56, y + 13, t.serif, width=266)
        t.hint(
            (x + 12, y + 8, 310, 39),
            province.name,
            "Province seat. Drag this title to reposition the window; Esc closes it.",
        )
        t.button(self.close_button, "×")
        region = state.regions[province.region_id]
        setting = province.geography.get("admin", region.name) + " / " + province.geography.get("country", "")
        t.text(setting, x + 17, y + 48, t.body, GOLD, width=330)
        t.hint((x + 16, y + 44, 334, 28), "Geographic setting", setting)
        t.rule(x + 16, y + 78, 334)
        self._draw_vignette(state, province, time, effects)
        self._draw_facts(state, province, region)
        for tab, button in self.tab_buttons.items():
            label, help_text = TABS[tab]
            t.emblem_button(button, label, tab, self.tab == tab, help_text)
        if self.tab == "recruit":
            self._draw_recruitment(state, province, player)
            t.text("Hover a regiment for its charter", x + 17, y + 536, t.small, DIM)
        else:
            self._draw_construction(state, province, time)
            t.text("Hover an improvement for its charter", x + 17, y + 536, t.small, DIM)

    def _draw_vignette(self, state, province, time: float, effects: dict) -> None:
        t = self.theme
        x, y = self.rect.topleft
        key = ("landscape", province.terrain)
        if key not in t.cache:
            t.cache[key] = landscape((334, 72), province.terrain)
        t.screen.blit(t.cache[key], (x + 16, y + 88))
        for i, kind in enumerate(province.buildings):
            if province.cities:
                draw_building(t.screen, kind, (x + 110 + i * 43, y + 126), 34, time)
            else:
                draw_building(t.screen, kind, (x + 44 + i * 54, y + 126), 42, time)
        effect = effects.get(province.id)
        if effect is not None:
            celebration(t.screen, (x + 180, y + 127), time - effect)
        pygame.draw.rect(t.screen, (161, 130, 78), (x + 16, y + 88, 334, 72), 1)
        cities = state.cities_in(province.id)
        if cities:
            city = cities[0]
            style = city.style or state.factions[province.owner].style
            t.screen.blit(pygame.transform.smoothscale(city_sprite(style), (68, 57)), (x + 22, y + 91))
            tag = pygame.Rect(x + 20, y + 138, 238, 19)
            pygame.draw.rect(t.screen, (35, 29, 27), tag, border_radius=2)
            t.text(city.name + " / 1 victory point", tag.x + 4, tag.y + 1, t.small, GOLD, width=230)

    def _draw_facts(self, state, province, region) -> None:
        t = self.theme
        x, y = self.rect.topleft
        for i, (label, value, color) in enumerate(
            (
                ("CONTROL", state.factions[province.controller].name, PAPER),
                ("CLAIM", state.factions[province.owner].name, DIM),
            )
        ):
            t.text(label, x + 17, y + 176 + i * 24, t.small, GOLD)
            t.text(value, x + 110, y + 173 + i * 24, t.body, color, width=230)
        t.text("TERRAIN", x + 17, y + 224, t.small, GOLD)
        t.text(province.terrain.title(), x + 110, y + 221, t.body)
        t.inset((x + 16, y + 251, 162, 44))
        t.inset((x + 187, y + 251, 163, 44))
        t.seal("population", (x + 36, y + 273), 29)
        t.text("POPULATION", x + 57, y + 255, t.small, GOLD)
        t.text(f"{region.population:,}", x + 57, y + 271, t.heading)
        t.hint(
            (x + 16, y + 251, 162, 44),
            "Regional population",
            f"{region.population:,} people across {region.name}. "
            "This is the administrative region total, not a separate province population.",
        )
        t.seal("industry", (x + 207, y + 273), 29)
        t.text("INDUSTRY", x + 228, y + 255, t.small, GOLD)
        t.text(str(region.industry), x + 228, y + 271, t.heading)
        t.hint(
            (x + 187, y + 251, 163, 44),
            "Regional industry",
            f"{region.industry} industry in {region.name}. Cities contribute to this regional aggregate.",
        )
        t.text("REGIONAL YIELD", x + 17, y + 306, t.small, GOLD)
        t.hint(
            (x + 16, y + 300, 334, 45),
            "Regional yield",
            f"Base production across {len(region.provinces)} provinces in {region.name}. "
            "Each faction receives the share it controls; resource sites and buildings add local output.",
        )
        yields = "  /  ".join(
            f"{resource.title()} {amount:g}" for resource, amount in region.production.items()
        )
        t.text(yields, x + 17, y + 328, t.body, width=330)

    def _draw_recruitment(self, state, province, player: str) -> None:
        t = self.theme
        for page, button in self.page_buttons.items():
            t.button(button, RECRUIT_PAGES[page], self.recruit_page == page)
        faction = state.factions[player]
        for kind, button in self.recruit_buttons.items():
            option = recruit_option(state, province.id, kind)
            if option is None:
                continue
            cost, error = quote_recruit(state, province.id, kind)
            t.panel(button, not error and button.collidepoint(t.mouse_pos()))
            style = CHARTERS[option.charter].style if kind == REGIONAL else faction.style
            icon = self.sprites.sprite(option.base_kind, faction.color, style)
            t.screen.blit(pygame.transform.smoothscale(icon, (30, 30)), button.topleft)
            t.text(option.name, button.x + 39, button.y + 1, t.body, DIM if error else PAPER, width=188)
            stats = option.stats
            if kind == AIR:
                detail = f"Range {stats['allowance']} / Operational coverage"
            else:
                detail = f"Move {stats['allowance']}  Attack {stats['attack']}  Guard {stats['defense']}"
            t.text(detail, button.x + 39, button.y + 17, t.small, DIM)
            short_cost = " ".join(f"{amount}{resource[0].upper()}" for resource, amount in cost.items())
            t.text(short_cost, button.right - 102, button.y + 3, t.small, GOLD, width=97)
            full_cost = " / ".join(f"{amount} {resource}" for resource, amount in cost.items())
            t.hint(
                button,
                option.name,
                (error + "\n" if error else "")
                + option.role
                + "\nCost: "
                + full_cost
                + "\nUpkeep: "
                + " / ".join(
                    f"{amount:g} {resource}" for resource, amount in unit_upkeep(option.base_kind).items()
                )
                + " per turn"
                + "\nOne unit per city per turn. Newly formed units act next turn.",
            )

    def _draw_construction(self, state, province, time: float) -> None:
        t = self.theme
        for kind, button in self.build_buttons.items():
            spec = BUILDINGS[kind]
            cost, error = quote(state, province.id, kind)
            level = province.buildings.get(kind, 0)
            t.panel(button, not error and button.collidepoint(t.mouse_pos()))
            draw_building(t.screen, kind, (button.x + 21, button.y + 27), 34, time, level > 0)
            t.text(spec.name, button.x + 43, button.y + 4, t.heading, DIM if error else PAPER)
            t.text(
                f"Level {level}/{spec.max_level} / " + spec.summary(),
                button.x + 43,
                button.y + 27,
                t.small,
                GREEN,
                width=285,
            )
            if level >= spec.max_level:
                price = "Complete"
            else:
                price = "  ".join(
                    f"{amount}{resource[0].upper()}" for resource, amount in cost.items() if amount
                )
            t.text(price, button.x + 197, button.y + 7, t.small, DIM, width=130)
            description = spec.description or (
                f"Each level adds {spec.output} {spec.resource} to your faction's production per turn."
            )
            full_cost = " / ".join(f"{amount} {resource}" for resource, amount in cost.items() if amount)
            t.hint(button, spec.name, (error + "\n" if error else "") + description + "\nCost: " + full_cost)
