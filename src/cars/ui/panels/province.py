"""The province panel: one scrolling page with the province's facts, production,
buildings and recruitment, and the forces standing in it."""

import pygame

from cars.sim.buildings import BUILDINGS, quote
from cars.sim.defines import DEFINES
from cars.sim.economy import RULES as ECONOMY
from cars.sim.entities import LAND_KINDS, RESOURCES
from cars.sim.recruitment import RECRUITS, REGIONAL, quote_recruit, recruit_option
from cars.sim.regional import unit_name
from cars.sim.supply import supplied_provinces
from cars.sim.upkeep import unit_upkeep
from cars.ui.frames import DockedPanel
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, facts, section


def short_cost(cost: dict) -> str:
    return "  ".join(f"{amount} {resource[0].upper()}" for resource, amount in cost.items() if amount)


class ProvincePanel(DockedPanel):
    name = "province"
    icon = "province"
    width = 500

    @property
    def province(self):
        return self.state.provinces.get(self.game.view.inspected)

    def heading(self) -> str:
        province = self.province
        return province.name if province else "Province"

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        province = self.province
        if province is None:
            return 0
        state = self.state
        y = rect.y
        region = state.regions[province.region_id]
        y += self._summary(ui, rect.x, y, rect.width, province, region)
        y += ui.px(8)
        y += section(ui, "Production each turn", rect.x, y, rect.width)
        y += self._production(ui, rect.x, y, rect.width, province, region)
        y += ui.px(14)
        y += section(ui, "Buildings", rect.x, y, rect.width)
        y += self._buildings(ui, rect.x, y, rect.width, province)
        if state.has_city(province.id):
            y += ui.px(14)
            y += section(ui, "Recruitment", rect.x, y, rect.width)
            y += self._recruitment(ui, rect.x, y, rect.width, province)
        y += ui.px(14)
        y += section(ui, "Forces here", rect.x, y, rect.width)
        y += self._forces(ui, rect.x, y, rect.width, province)
        if self.notice:
            y += ui.px(8)
            y += ui.paragraph(
                self.notice, pygame.Rect(rect.x, y, rect.width, ui.px(60)), style.SMALL, style.SLATE
            )
        return y - rect.y + ui.px(8)

    def _summary(self, ui, x: int, y: int, width: int, province, region) -> int:
        state = self.state
        controller = state.factions[province.controller]
        owner = state.factions[province.owner]
        held = controller.name if province.owner == province.controller else f"{controller.name} (occupied)"
        viewer = self.game.campaign.player or state.active
        supplied = province.id in supplied_provinces(state, province.controller)
        terrain = province.terrain
        pairs = [
            ("Held by", held),
            ("Claimed by", owner.name),
            ("Terrain", terrain.title()),
            ("Defence", f"×{DEFINES.combat.terrain_defense[terrain]:g} to defenders"),
            ("Movement cost", f"×{DEFINES.movement.terrain_cost[terrain]:g}"),
            ("Supply", ("Connected to a hub", style.GOOD) if supplied else ("Cut off", style.BAD)),
            ("Region", region.name),
            ("Population", f"{region.population:,} in the region"),
        ]
        if province.controller != viewer and state.at_war(viewer, province.controller):
            pairs[0] = ("Held by", (held + ", at war with you", style.BAD))
        cities = state.cities_in(province.id)
        if cities:
            city = cities[0]
            roles = [role for role, has in (("supply hub", city.supply_hub), ("port", city.port)) if has]
            towns = ", ".join(c.name for c in cities) + (f" ({', '.join(roles)})" if roles else "")
            pairs.insert(0, ("Town", towns))
        return facts(ui, x, y, width, pairs)

    def _production(self, ui, x: int, y: int, width: int, province, region) -> int:
        share = 1 / len(region.provinces)
        occupied = province.owner != province.controller
        factor = ECONOMY.occupied_yield if occupied else 1
        rows, total_row = [], []
        for resource in RESOURCES:
            base = region.production[resource] * share * factor
            sites = province.resource_sites.get(resource, 0) * factor
            built = sum(
                level * BUILDINGS[kind].output * factor
                for kind, level in province.buildings.items()
                if BUILDINGS[kind].resource == resource
            )
            total_row.append(base + sites + built)
            rows.append(
                [
                    resource.title(),
                    f"{base:.1f}",
                    f"{sites:g}",
                    f"{built:g}",
                    (f"{base + sites + built:.1f}", style.SLATE),
                ]
            )
        columns = [
            ("Resource", None, "left"),
            ("Region", 70, "right"),
            ("Sites", 60, "right"),
            ("Buildings", 86, "right"),
            ("Total", 70, "right"),
        ]
        hints = [
            (
                "Production",
                "This province's share of its region's output, its own resource sites and its buildings."
                + (" Occupied: half yield." if occupied else ""),
            )
        ] * len(rows)
        return draw_grid(ui, x, y, width, columns, rows, hints=hints)

    def _buildings(self, ui, x: int, y: int, width: int, province) -> int:
        state = self.state
        rows, hints = [], []
        for kind, spec in BUILDINGS.items():
            level = province.buildings.get(kind, 0)
            cost, error = quote(state, province.id, kind)
            complete = level >= spec.max_level
            price = "Complete" if complete else short_cost(cost)

            def build_cell(area, kind=kind, error=error, complete=complete):
                button = area.inflate(-ui.px(8), -ui.px(6))
                self.button(
                    button, "Build", "build:" + kind, enabled=not error and not complete, kind="primary"
                )

            rows.append(
                [
                    spec.name,
                    f"{level} / {spec.max_level}",
                    spec.summary(),
                    (price, style.INK_MUTED),
                    build_cell,
                ]
            )
            description = spec.description or f"Each level adds {spec.output} {spec.resource} a turn."
            hints.append((spec.name, (error + "\n" if error and not complete else "") + description))
        columns = [
            ("Building", 108, "left"),
            ("Level", 50, "center"),
            ("Effect", None, "left"),
            ("Next cost", 116, "right"),
            ("", 74, "center"),
        ]
        return draw_grid(ui, x, y, width, columns, rows, row_height=34, hints=hints)

    def _recruitment(self, ui, x: int, y: int, width: int, province) -> int:
        state = self.state
        rows, hints = [], []
        for kind in [*RECRUITS, REGIONAL]:
            option = recruit_option(state, province.id, kind)
            if option is None:
                continue
            cost, error = quote_recruit(state, province.id, kind)
            stats = option.stats

            def recruit_cell(area, kind=kind, error=error):
                button = area.inflate(-ui.px(8), -ui.px(6))
                self.button(button, "Raise", "recruit:" + kind, enabled=not error, kind="primary")

            fighting = (
                f"{stats['attack']:g} / {stats['defense']:g}" if option.base_kind in LAND_KINDS else "—"
            )
            rows.append(
                [
                    option.name,
                    f"{stats['allowance']:g}",
                    fighting,
                    (short_cost(cost), style.INK_MUTED),
                    recruit_cell,
                ]
            )
            upkeep = ", ".join(
                f"{amount:g} {resource}" for resource, amount in unit_upkeep(option.base_kind).items()
            )
            hints.append(
                (
                    option.name,
                    (error + "\n" if error else "") + f"{option.role}. Upkeep {upkeep} a turn. "
                    "One unit per city per turn; new units move next turn.",
                )
            )
        columns = [
            ("Unit", None, "left"),
            ("Move", 52, "center"),
            ("Atk / Def", 76, "center"),
            ("Cost", 104, "right"),
            ("", 74, "center"),
        ]
        return draw_grid(ui, x, y, width, columns, rows, row_height=34, hints=hints)

    def _forces(self, ui, x: int, y: int, width: int, province) -> int:
        state = self.state
        scene_visible = self.game.renderer.visible(self.game.view)
        units = [
            u
            for u in state.units.values()
            if u.location == province.id
            and (
                scene_visible is None or u.owner == self.game.campaign.player or province.id in scene_visible
            )
        ]
        if not units:
            ui.text("No forces in sight.", (x, y), style.BODY, style.INK_FAINT)
            return ui.px(24)
        rows = [
            [
                lambda area, u=u: ui.swatch(
                    (area.x + ui.px(12), area.centery), state.factions[u.owner].color, 6
                ),
                unit_name(u),
                state.factions[u.owner].name,
                (f"{u.hp:.1f}", style.GOOD if u.hp > 6 else style.WARN if u.hp > 3 else style.BAD),
            ]
            for u in sorted(units, key=lambda u: (u.owner, u.kind, u.id))
        ]
        columns = [
            ("", 26, "left"),
            ("Unit", None, "left"),
            ("Nation", 150, "left"),
            ("Strength", 76, "right"),
        ]
        return draw_grid(ui, x, y, width, columns, rows)

    def act(self, action: str) -> None:
        verb, _, name = action.partition(":")
        province = self.game.view.inspected
        if verb == "build":
            self.game.construct(province, name)
        elif verb == "recruit":
            self.game.recruit(province, name)
        self.notice = self.game.view.message
