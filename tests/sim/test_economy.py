import unittest

from cars.sim.buildings import build, quote
from cars.sim.economy import RULES, forecast, produce, storage
from cars.sim.market import quote as quote_trade
from cars.sim.market import trade, treasury_income
from cars.sim.turn import end_turn
from tests.support import compact, detailed


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = detailed()
        self.province = next(p.id for p in self.state.provinces.values() if p.controller == "f0")
        self.stock = self.state.factions["f0"].resources

    def test_build_cost_upgrade_price_and_income(self):
        before = forecast(self.state, "f0")
        stock = self.stock.copy()
        self.assertTrue(build(self.state, self.province, "farm")[0])
        self.assertEqual(self.stock["wood"], stock["wood"] - 4)
        self.assertEqual(self.stock["iron"], stock["iron"] - 2)
        # The United States' Yeoman Farms trait adds 15% to food.
        self.assertAlmostEqual(forecast(self.state, "f0")["food"], before["food"] + 2 * 1.15)
        self.assertEqual(quote(self.state, self.province, "farm")[0]["wood"], 8)
        self.assertAlmostEqual(produce(self.state, "f0")["food"], before["food"] + 2 * 1.15)

    def test_rejections_change_nothing(self):
        enemy = next(p.id for p in self.state.provinces.values() if p.controller == "f1")
        stock = self.stock.copy()
        self.assertFalse(build(self.state, enemy, "mine")[0])
        self.assertFalse(build(self.state, None, "farm")[0])
        self.assertFalse(build(self.state, self.province, "unknown")[0])
        self.assertEqual(stock, self.stock)
        self.stock["wood"] = 0
        self.assertFalse(build(self.state, self.province, "farm")[0])
        self.assertEqual(self.state.provinces[self.province].buildings, {})

    def test_max_level_and_buildings_change_hands(self):
        self.state.factions["f0"].resources = dict(wood=100, food=100, iron=100)
        for _ in range(3):
            self.assertTrue(build(self.state, self.province, "mine")[0])
        stock = self.state.factions["f0"].resources.copy()
        self.assertFalse(build(self.state, self.province, "mine")[0])
        self.assertEqual(stock, self.state.factions["f0"].resources)
        self.state.provinces[self.province].controller = "f1"
        with_mine = forecast(self.state, "f1")["iron"]
        self.state.provinces[self.province].buildings.clear()
        # Occupied: f1 controls the province but f0 still owns it, so it yields half.
        self.assertAlmostEqual(with_mine - forecast(self.state, "f1")["iron"], 3)

    def test_shipyard_needs_a_port(self):
        self.state.factions["f0"].resources = dict(wood=1000, food=1000, iron=1000)
        port = next(
            c.province
            for c in self.state.cities.values()
            if self.state.provinces[c.province].controller == "f0" and c.province in self.state.ports
        )
        self.state.ports.pop(port)
        stock = self.state.factions["f0"].resources.copy()
        self.assertFalse(build(self.state, port, "shipyard")[0])
        self.assertEqual(stock, self.state.factions["f0"].resources)


class ProductionTests(unittest.TestCase):
    def test_regional_share_and_turn_order(self):
        state, _, _ = compact()
        self.assertEqual(produce(state, "f0"), dict(wood=3, food=5 * 1.15, iron=4))
        state.provinces["cascadia"].controller = "f1"
        self.assertAlmostEqual(produce(state, "f0")["iron"], 4 / 3)
        unit = state.units["infantry0"]
        unit.remaining = 0
        for _ in range(8):
            end_turn(state)
        self.assertEqual(state.active, "f0")
        self.assertEqual(state.round, 2)
        self.assertEqual(unit.remaining, 6)

    def test_occupied_provinces_yield_half(self):
        state, _, _ = compact()
        state.provinces["cascadia"].owner = "f1"
        state.provinces["cascadia"].controller = "f1"
        owned = forecast(state, "f1")
        state.provinces["cascadia"].owner = "f0"
        occupied = forecast(state, "f1")
        for resource, amount in owned.items():
            self.assertLessEqual(occupied[resource], amount)
        self.assertLess(sum(occupied.values()), sum(owned.values()))

    def test_stockpiles_are_limited_by_city_storage(self):
        state, _, _ = compact()
        limit = storage(state, "f0")
        self.assertEqual(limit, RULES.storage_base + RULES.storage_per_city)  # One city.
        stock = state.factions["f0"].resources
        stock.update(wood=limit - 1, food=limit + 50, iron=0)
        produce(state, "f0")
        self.assertEqual(stock["wood"], limit)
        self.assertEqual(stock["food"], limit + 50)  # Never reduced, only capped.
        self.assertEqual(stock["iron"], 4)


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.state, _, _ = compact()
        self.faction = self.state.factions["f0"]

    def test_full_lot_price_and_spread(self):
        wood, gold = self.faction.resources["wood"], self.faction.gold
        price, error = quote_trade(self.state, "f0", "wood", "buy")
        self.assertFalse(error)
        self.assertTrue(trade(self.state, "f0", "wood", "buy")[0])
        self.assertEqual(self.faction.resources["wood"], wood + 10)
        self.assertEqual(self.faction.gold, gold - price)
        self.assertEqual(self.state.market["wood"], 50)
        self.assertGreater(quote_trade(self.state, "f0", "wood", "buy")[0], price)
        self.assertTrue(trade(self.state, "f0", "wood", "sell")[0])
        self.assertEqual(self.faction.resources["wood"], wood)
        self.assertLess(self.faction.gold, gold)
        self.assertEqual(set(self.faction.resources), {"wood", "food", "iron"})

    def test_rejections_change_nothing(self):
        self.state.market["iron"] = 0
        before = (self.faction.resources.copy(), self.faction.gold, self.state.market.copy())
        for owner, resource, side in [
            ("f0", "iron", "buy"),
            ("f1", "food", "buy"),
            ("f0", "gold", "buy"),
            ("f0", "food", "x"),
        ]:
            self.assertFalse(trade(self.state, owner, resource, side)[0])
        self.assertEqual(before, (self.faction.resources, self.faction.gold, self.state.market))
        self.faction.resources["wood"] = 9
        self.assertFalse(trade(self.state, "f0", "wood", "sell")[0])
        self.faction.gold = 0
        self.assertFalse(trade(self.state, "f0", "wood", "buy")[0])
        self.state.market["wood"] = 100
        self.faction.resources["wood"] = 20
        self.assertFalse(trade(self.state, "f0", "wood", "sell")[0])

    def test_stock_restocks_once_per_round_and_cities_pay_gold(self):
        self.state.market["wood"] = 10
        gold, income = self.faction.gold, treasury_income(self.state, "f0")
        end_turn(self.state)
        self.assertEqual(self.faction.gold, gold + income)
        self.assertEqual(self.state.market["wood"], 10)
        for _ in range(7):
            end_turn(self.state)
        self.assertEqual(self.state.market["wood"], 30)
        self.assertLessEqual(max(self.state.market.values()), 100)


if __name__ == "__main__":
    unittest.main()
