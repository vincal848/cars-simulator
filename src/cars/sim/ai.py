"""Rival factions. A small deterministic commander that issues the same validated
commands a human player uses, so it can never make an illegal move."""

from collections import deque
from collections.abc import Iterator
from functools import partial
from typing import TYPE_CHECKING

from cars.sim.air import STRIKE, STRIKE_TARGET_KINDS, coverage, mission
from cars.sim.buildings import BUILDINGS, build, quote
from cars.sim.combat import supply_factor
from cars.sim.defines import DEFINES
from cars.sim.entities import AIR, FLEET, LAND_KINDS
from cars.sim.graph import step_cost
from cars.sim.movement import reachable
from cars.sim.naval import enemy_fleets, reachable_seas
from cars.sim.orders import issue_move
from cars.sim.recruitment import REQUIRED_FACILITY, quote_recruit, recruit
from cars.sim.upkeep import net_income, unit_upkeep

if TYPE_CHECKING:
    from cars.sim.entities import Unit
    from cars.sim.graph import Paths
    from cars.sim.state import GameState

RULES = DEFINES.ai

# (unit id or None, route travelled, message) for each action taken.
Action = tuple[str | None, list[str], str]


def faction_actions(state: "GameState") -> Iterator[Action]:
    """Play the active faction's turn one action at a time.

    Yielding between actions lets the UI animate each order as it happens.
    """
    return RivalCommander(state).take_turn()


class RivalCommander:
    def __init__(self, state: "GameState") -> None:
        self.state = state
        self.owner = state.active

    def take_turn(self) -> Iterator[Action]:
        yield from self._command_air_and_fleets()
        yield from self._command_armies()
        yield from self._develop()

    def _own_units(self) -> Iterator["Unit"]:
        """Units owned at the start, skipping any destroyed earlier in the turn."""
        for unit_id in sorted(self.state.units):
            unit = self.state.units.get(unit_id)
            if unit is not None and unit.owner == self.owner:
                yield unit

    # Air groups and fleets ------------------------------------------------------------

    def _command_air_and_fleets(self) -> Iterator[Action]:
        for unit in self._own_units():
            if unit.remaining <= 0:
                continue
            if unit.kind == AIR:
                yield from self._strike_nearest(unit)
            elif unit.kind == FLEET:
                yield from self._hunt_fleets(unit)

    def _strike_nearest(self, unit: "Unit") -> Iterator[Action]:
        in_range = coverage(self.state, unit)
        targets = sorted(
            {
                other.location
                for other in self.state.units.values()
                if other.owner != self.owner
                and other.kind in STRIKE_TARGET_KINDS
                and other.location in in_range
            }
        )
        if targets:
            ok, message = mission(self.state, unit.id, targets[0], STRIKE)
            if ok:
                yield unit.id, [], message

    def _hunt_fleets(self, unit: "Unit") -> Iterator[Action]:
        state = self.state
        if enemy_fleets(state, unit, unit.location):
            route, message = issue_move(state, unit.id, unit.location)
            yield unit.id, route, message
            return
        hostile = {u.location for u in state.units.values() if u.kind == FLEET and u.owner != self.owner}
        distances = state.naval.shortest_paths(unit.location, step_cost)
        targets = [sea for sea in hostile if sea in distances.costs]
        if not targets:
            return
        target = min(targets, key=lambda sea: (distances.costs[sea], sea))
        in_reach = reachable_seas(state, unit).costs
        # Sail as far along the route to the nearest enemy fleet as movement allows.
        destination = next(
            (sea for sea in reversed(distances.path(target)) if sea in in_reach and sea != unit.location),
            None,
        )
        if destination:
            traveled, message = issue_move(state, unit.id, destination)
            yield unit.id, traveled, message

    # Armies ---------------------------------------------------------------------------

    def _front_distance(self) -> dict[str, int]:
        """Land hops from each province to the nearest one this faction does not control."""
        state = self.state
        distance = {p.id: 0 for p in state.provinces.values() if p.controller != self.owner}
        queue = deque(distance)
        while queue:
            node = queue.popleft()
            for neighbor, _ in state.land.neighbors(node):
                if neighbor not in distance:
                    distance[neighbor] = distance[node] + 1
                    queue.append(neighbor)
        return distance

    def _command_armies(self) -> Iterator[Action]:
        front = self._front_distance()
        for unit in self._own_units():
            if unit.kind not in LAND_KINDS:
                continue
            paths = reachable(self.state, unit)
            score = partial(self._score_destination, unit, paths, front)
            destination = max(sorted(paths.costs), key=score)
            if destination != unit.location and score(destination) > score(unit.location):
                route, message = issue_move(self.state, unit.id, destination)
                yield unit.id, route, message

    def _score_destination(self, unit: "Unit", paths: "Paths", front: dict[str, int], province: str) -> float:
        """Prefer hostile provinces near the front; refuse attacks the unit cannot win."""
        hostile = self.state.provinces[province].controller != self.owner
        defenders = self.state.enemy_units_at(province, self.owner, LAND_KINDS)
        resistance = sum(defender.defense_power() for defender in defenders)
        strength = unit.attack_power() * supply_factor(unit)
        if hostile and defenders and strength < resistance * RULES.attack_margin:
            return RULES.rejected_score
        bonus = RULES.hostile_province_score if hostile else 0
        distance = front.get(province, RULES.unknown_front_distance)
        return (
            bonus - distance * RULES.front_distance_weight - paths.costs[province] * RULES.route_cost_weight
        )

    # Recruitment and construction -----------------------------------------------------

    def _can_support(self, kind: str) -> bool:
        """Whether income still covers upkeep with one more unit of ``kind``."""
        income = net_income(self.state, self.owner)
        return all(income[resource] >= cost for resource, cost in unit_upkeep(kind).items())

    def _develop(self) -> Iterator[Action]:
        """Recruit one unit of this turn's rotation if it can be fed, then build one thing."""
        state = self.state
        rotation = RULES.recruitment_rotation
        kind = rotation[(state.round + state.active_index) % len(rotation)]
        if self._can_support(kind):
            for city in state.cities.values():
                if not quote_recruit(state, city.province, kind)[1]:
                    unit_id, message = recruit(state, city.province, kind)
                    yield unit_id, [], message
                    break

        # A service turn first tries to build the facility that branch needs.
        facility = REQUIRED_FACILITY.get(kind)
        if facility:
            for city in state.cities.values():
                if not quote(state, city.province, facility)[1]:
                    _, message = build(state, city.province, facility)
                    yield None, [], message
                    return

        # Otherwise improve whichever resource currently has the lowest net income.
        income = net_income(state, self.owner)
        producers = [spec for spec in BUILDINGS.values() if spec.produces]
        for spec in sorted(producers, key=lambda spec: income[spec.resource]):
            for province in sorted(state.provinces):
                if not quote(state, province, spec.id)[1]:
                    _, message = build(state, province, spec.id)
                    yield None, [], message
                    return
