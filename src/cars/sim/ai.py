"""Rival factions. A small deterministic commander that issues the same validated
commands a human player uses, so it can never make an illegal move. It plays
under the same fog of war as the player: it only reacts to enemy forces it can see."""

from collections import deque
from collections.abc import Iterator
from functools import partial
from typing import TYPE_CHECKING

from cars.sim.air import STRIKE, STRIKE_TARGET_KINDS, coverage, mission
from cars.sim.buildings import BUILDINGS, build, quote
from cars.sim.combat import assess
from cars.sim.defines import DEFINES
from cars.sim.diplomacy import coalition_partners, declare_war, join_coalition, wants_war
from cars.sim.entities import AIR, FLEET, LAND_KINDS
from cars.sim.graph import step_cost
from cars.sim.movement import reachable
from cars.sim.naval import enemy_fleets, reachable_seas
from cars.sim.orders import issue_move
from cars.sim.recruitment import REQUIRED_FACILITY, quote_recruit, recruit
from cars.sim.upkeep import net_income, unit_upkeep
from cars.sim.visibility import visible_nodes

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
        yield from self._join_coalition()
        yield from self._consider_war()
        yield from self._command_air_and_fleets()
        yield from self._command_armies()
        yield from self._develop()

    def _own_units(self) -> Iterator["Unit"]:
        """Units owned at the start, skipping any destroyed earlier in the turn."""
        for unit_id in sorted(self.state.units):
            unit = self.state.units.get(unit_id)
            if unit is not None and unit.owner == self.owner:
                yield unit

    def _join_coalition(self) -> Iterator[Action]:
        for partner in coalition_partners(self.state, self.owner):
            yield None, [], join_coalition(self.state, self.owner, partner)

    def _consider_war(self) -> Iterator[Action]:
        """Break at most one peace per turn, and only against a much weaker nation."""
        for other in self.state.factions:
            if other != self.owner and wants_war(self.state, self.owner, other):
                _, message = declare_war(self.state, self.owner, other)
                yield None, [], message
                return

    # Air groups and fleets ------------------------------------------------------------

    def _command_air_and_fleets(self) -> Iterator[Action]:
        for unit in self._own_units():
            if unit.remaining <= 0:
                continue
            if unit.kind == AIR:
                yield from self._strike_nearest(unit)
            elif unit.kind == FLEET:
                yield from self._hunt_fleets(unit)

    def _visible(self) -> set[str]:
        return visible_nodes(self.state, self.owner)

    def _strike_nearest(self, unit: "Unit") -> Iterator[Action]:
        in_range = coverage(self.state, unit) & self._visible()
        targets = sorted(
            {
                other.location
                for other in self.state.units.values()
                if self.state.at_war(self.owner, other.owner)
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
        visible = self._visible()
        hostile = {
            u.location
            for u in state.units.values()
            if u.kind == FLEET and state.at_war(self.owner, u.owner) and u.location in visible
        }
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
        """Land hops from each province to the nearest enemy one, never crossing the
        territory of a nation at peace, which grants no military access."""
        state = self.state
        distance = {p.id: 0 for p in state.provinces.values() if state.at_war(self.owner, p.controller)}
        queue = deque(distance)
        while queue:
            node = queue.popleft()
            for neighbor, _ in state.land.neighbors(node):
                if neighbor not in distance and state.provinces[neighbor].controller == self.owner:
                    distance[neighbor] = distance[node] + 1
                    queue.append(neighbor)
        return distance

    def _command_armies(self) -> Iterator[Action]:
        front = self._front_distance()
        for unit in self._own_units():
            if unit.kind not in LAND_KINDS:
                continue
            paths = reachable(self.state, unit)
            score = partial(self._score_destination, unit, paths, front, self._visible())
            destination = max(sorted(paths.costs), key=score)
            if destination != unit.location and score(destination) > score(unit.location):
                route, message = issue_move(self.state, unit.id, destination)
                yield unit.id, route, message

    def _score_destination(
        self, unit: "Unit", paths: "Paths", front: dict[str, int], visible: set[str], province: str
    ) -> float:
        """Prefer hostile provinces near the front; refuse attacks that are not worth fighting."""
        hostile = self.state.at_war(self.owner, self.state.provinces[province].controller)
        if hostile and not self._worth_attacking(unit, paths.path(province), visible):
            return RULES.rejected_score
        bonus = RULES.hostile_province_score if hostile else 0
        distance = front.get(province, RULES.unknown_front_distance)
        return (
            bonus - distance * RULES.front_distance_weight - paths.costs[province] * RULES.route_cost_weight
        )

    def _worth_attacking(self, unit: "Unit", route: list[str], visible: set[str]) -> bool:
        """Judge an attack with the battle rules themselves, against the defenders in sight.

        Worth it when the province would fall, or when the attacker survives and
        trades damage favourably by at least ``attack_margin``.
        """
        if len(route) < 2:
            return False
        origin, target = route[-2], route[-1]
        state = self.state
        defenders = state.enemy_units_at(target, self.owner, LAND_KINDS) if target in visible else []
        odds = assess(state, unit, origin, target, state.land.edge(origin, target), defenders)
        if odds.captures(unit, defenders):
            return True
        taken = odds.attacker_loss()
        if taken >= unit.hp:
            return False
        dealt = sum(min(defender.hp, odds.defender_loss(len(defenders))) for defender in defenders)
        return dealt >= taken * RULES.attack_margin

    # Recruitment and construction -----------------------------------------------------

    def _can_support(self, kind: str) -> bool:
        """Whether income still covers upkeep with one more unit of ``kind``."""
        income = net_income(self.state, self.owner)
        return all(income[resource] >= cost for resource, cost in unit_upkeep(kind).items())

    def _develop(self) -> Iterator[Action]:
        """Recruit what the realm can feed, then spend what is left on construction."""
        state = self.state
        rotation = RULES.recruitment_rotation
        first = state.round + state.active_index
        for index in range(RULES.recruits_per_turn):
            kind = rotation[(first + index) % len(rotation)]
            yield from self._recruit(kind)
        for _ in range(RULES.builds_per_turn):
            action = self._build(rotation[first % len(rotation)])
            if action is None:
                return
            yield action

    def _recruit(self, kind: str) -> Iterator[Action]:
        if not self._can_support(kind):
            return
        for city in self.state.cities.values():
            if not quote_recruit(self.state, city.province, kind)[1]:
                unit_id, message = recruit(self.state, city.province, kind)
                yield unit_id, [], message
                return

    def _build(self, kind: str) -> Action | None:
        """Build the facility this turn's service branch needs, or else a producer
        of whichever resource has the lowest net income."""
        state = self.state
        facility = REQUIRED_FACILITY.get(kind)
        if facility:
            for city in state.cities.values():
                if not quote(state, city.province, facility)[1]:
                    _, message = build(state, city.province, facility)
                    return None, [], message
        income = net_income(state, self.owner)
        producers = [spec for spec in BUILDINGS.values() if spec.produces]
        for spec in sorted(producers, key=lambda spec: income[spec.resource]):
            for province in sorted(state.provinces):
                if not quote(state, province, spec.id)[1]:
                    _, message = build(state, province, spec.id)
                    return None, [], message
        return None
