import pickle
import unittest

from cars.sim.ai import faction_actions
from cars.sim.balloons import coverage
from cars.sim.calendar import date_label, turn_phase
from cars.sim.campaign import Campaign
from cars.sim.entities import Unit
from cars.sim.forecast import forecast_order, signature
from cars.sim.graph import Graph
from cars.sim.objectives import announce_stage, begin, campaign_stage, controlled_cities, evaluate
from cars.sim.orders import issue_move
from cars.sim.turn import end_turn
from tests.support import compact, detailed


class CampaignTests(unittest.TestCase):
    def test_faction_is_chosen_once_and_foreign_orders_are_refused(self):
        state, _, _ = detailed()
        campaign = Campaign(state)
        self.assertFalse(campaign.choose("missing"))
        self.assertTrue(campaign.choose("f3"))
        self.assertFalse(campaign.choose("f0"))
        enemy = next(u for u in state.units.values() if u.owner == "f0" and u.kind == "infantry")
        before = enemy.location
        self.assertEqual(campaign.move(enemy.id, next(iter(state.land.adj[before])))[0], [])
        self.assertEqual(enemy.location, before)
        end_turn(state)
        self.assertFalse(campaign.human_turn)
        self.assertFalse(campaign.construct(before, "farm")[0])

    def test_every_rival_acts_before_the_player_again(self):
        for faction in ("f0", "f3", "f7"):
            state, _, _ = detailed()
            campaign = Campaign(state)
            campaign.choose(faction)
            end_turn(state)
            turns = 0
            while not campaign.human_turn:
                self.assertLess(turns, 7)
                list(faction_actions(state))
                end_turn(state)
                turns += 1
            self.assertEqual(turns, 7)
            self.assertEqual(state.round, 2)

    def test_recruiting_needs_the_players_turn(self):
        state, _, _ = compact()
        state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        campaign = Campaign(state)
        campaign.choose("f0")
        end_turn(state)
        self.assertIsNone(campaign.recruit(state.units["infantry0"].location, "scout")[0])

    def test_long_rival_campaign_keeps_state_consistent(self):
        state, _, _ = detailed()
        for _ in range(20 * len(state.factions)):
            list(faction_actions(state))
            end_turn(state)
        for unit in state.units.values():
            if unit.is_land:
                self.assertIn(unit.id, state.provinces[unit.location].units)
            else:
                self.assertIn(unit.location, state.naval.adj if unit.kind == "fleet" else state.provinces)
            self.assertGreater(unit.hp, 0)
        for faction in state.factions.values():
            self.assertTrue(all(amount >= 0 for amount in faction.resources.values()))
            self.assertGreaterEqual(faction.gold, 0)


class RivalTests(unittest.TestCase):
    def test_rivals_use_balloons_and_fleets(self):
        state, _, _ = compact()
        corps = state.units["balloon0"]
        target = next(p for p in sorted(coverage(state, corps)) if p != corps.location)
        state.provinces[target].controller = "f1"
        front = min(p for p, _ in state.land.neighbors(target))
        state.provinces[front].controller = "f0"
        state.units["infantry0"].location = front
        naval = Graph()
        naval.connect("a", "b")
        state.naval = naval
        state.units["fleet0"].location = "a"
        state.units["enemyfleet"] = Unit("enemyfleet", "f1", "b", "fleet")
        list(faction_actions(state))
        kinds = {report["kind"] for report in state.reports}
        self.assertIn("ascent", kinds)
        self.assertIn("naval battle", kinds)

    def test_rivals_never_trade(self):
        state, _, _ = compact()
        before, gold = state.market.copy(), state.factions["f0"].gold
        list(faction_actions(state))
        self.assertEqual(state.market, before)
        self.assertEqual(state.factions["f0"].gold, gold)


class ObjectiveTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        begin(self.state, "f0")
        for province in self.state.provinces.values():
            province.controller = "f1"
        for city in list(self.state.cities.values())[:3]:
            self.state.provinces[city.province].controller = "f0"

    def test_streak_counts_once_per_round_until_victory(self):
        for _ in range(7):
            end_turn(self.state)
        self.assertEqual(self.state.objectives["held"], 0)
        end_turn(self.state)
        self.assertEqual(self.state.objectives["held"], 1)
        for _ in range(32):
            end_turn(self.state)
        self.assertEqual(self.state.objectives["status"], "victory")
        self.assertEqual(self.state.objectives["held"], 5)

    def test_losing_a_city_resets_the_streak(self):
        evaluate(self.state, True)
        city = controlled_cities(self.state, "f0")[0]
        self.state.provinces[city.province].controller = "f1"
        evaluate(self.state)
        self.assertEqual(self.state.objectives["held"], 0)
        self.state.provinces[city.province].controller = "f0"
        evaluate(self.state)
        self.assertEqual(self.state.objectives["held"], 0)
        evaluate(self.state, True)
        self.assertEqual(self.state.objectives["held"], 1)

    def test_defeat_without_cities_or_armies(self):
        for province in self.state.provinces.values():
            province.controller = "f1"
        self.state.units = {k: u for k, u in self.state.units.items() if u.owner != "f0"}
        evaluate(self.state)
        self.assertEqual(self.state.objectives["status"], "defeat")


class CalendarTests(unittest.TestCase):
    def test_the_date_changes_once_every_faction_has_acted(self):
        for player in ("f0", "f3", "f7"):
            state, _, _ = compact()
            Campaign(state).choose(player)
            self.assertEqual(date_label(state.clock), "Spring 1836")
            for i in range(7):
                end_turn(state)
                self.assertEqual(date_label(state.clock), "Spring 1836")
                self.assertEqual(turn_phase(state)[1], i)
            end_turn(state)
            self.assertEqual(date_label(state.clock), "Summer 1836")
            self.assertEqual(turn_phase(state)[0], "Your orders")

    def test_year_boundary_and_look_ahead(self):
        state, _, _ = compact()
        state.clock["elapsed"] = 3
        self.assertEqual(date_label(state.clock), "Winter 1836")
        self.assertEqual(date_label(state.clock, 1), "Spring 1837")
        self.assertEqual(state.clock["elapsed"], 3)

    def test_stages_follow_control_through_to_dominion(self):
        state, _, _ = compact()
        Campaign(state).choose("f0")
        for province in state.provinces.values():
            province.controller = "f1"
        self.assertEqual(campaign_stage(state).name, "Foothold")
        cities = list(state.cities.values())
        state.provinces[cities[0].province].controller = "f0"
        self.assertEqual(campaign_stage(state).name, "Expansion")
        for city in cities[:3]:
            state.provinces[city.province].controller = "f0"
        self.assertEqual(campaign_stage(state).name, "Consolidation")
        for _ in range(40):
            end_turn(state)
        self.assertEqual(campaign_stage(state).name, "Dominion")

    def test_stage_milestones_are_not_repeated(self):
        state, _, _ = compact()
        Campaign(state).choose("f0")
        count = len(state.reports)
        announce_stage(state)
        self.assertEqual(len(state.reports), count)
        for city in list(state.cities.values())[:3]:
            state.provinces[city.province].controller = "f0"
        evaluate(state, tick=True)
        self.assertEqual(state.objectives["held"], 1)
        for province in state.provinces.values():
            province.controller = "f1"
        evaluate(state)
        self.assertEqual(state.objectives["held"], 0)
        self.assertEqual(campaign_stage(state).name, "Foothold")
        self.assertEqual(state.reports[-1]["kind"], "milestone")


class ForecastTests(unittest.TestCase):
    def test_forecast_matches_real_combat_without_mutation(self):
        state, _, _ = compact()
        unit = state.units["infantry0"]
        unit.location = "canadian_shield"
        unit.remaining = 20
        target = next(p for p in state.land.adj[unit.location] if state.provinces[p].controller != "f0")
        before = pickle.dumps(state)
        result = forecast_order(state, unit.id, target)
        self.assertEqual(pickle.dumps(state), before)

        def strength(own: bool) -> float:
            return sum(u.hp for u in state.units.values() if (u.owner == "f0") == own)

        own_hp, enemy_hp = strength(True), strength(False)
        _, message = issue_move(state, unit.id, target)
        self.assertEqual(result["message"], message)
        self.assertIn(["River crossing", "×1"], result["factors"])
        self.assertAlmostEqual(result["own_loss"], own_hp - strength(True))
        self.assertAlmostEqual(result["enemy_loss"], enemy_hp - strength(False))

    def test_signature_changes_with_supply_roads_and_ascents(self):
        state, _, _ = compact()
        unit = state.units["infantry0"]
        before = signature(state)
        unit.supplied = False
        self.assertNotEqual(before, signature(state))
        before = signature(state)
        state.provinces[unit.location].buildings["roads"] = 1
        self.assertNotEqual(before, signature(state))
        before = signature(state)
        state.ascents.append(dict(unit="balloon0", owner="f0", target=unit.location))
        self.assertNotEqual(before, signature(state))


if __name__ == "__main__":
    unittest.main()
