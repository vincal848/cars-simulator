import unittest

import pygame

from cars.sim.entities import LAND_KINDS
from cars.ui.art.buildings import draw_building
from cars.ui.art.cities import city_sprite
from cars.ui.art.regiments import UnitSprites
from tests.support import SCREEN_SIZE, compact


class ArtworkTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode(SCREEN_SIZE)

    def tearDown(self):
        pygame.quit()

    def test_every_faction_and_role_has_its_own_look(self):
        state, _, _ = compact()
        sprites = UnitSprites()
        uniforms = {
            pygame.image.tobytes(sprites.sprite("infantry", (100, 120, 140), f.style), "RGBA")
            for f in state.factions.values()
        }
        self.assertEqual(len(uniforms), 8)
        roles = {
            pygame.image.tobytes(sprites.sprite(kind, (100, 120, 140), "atlantic"), "RGBA")
            for kind in LAND_KINDS
        }
        self.assertEqual(len(roles), 4)
        cities = {pygame.image.tobytes(city_sprite(f.style), "RGBA") for f in state.factions.values()}
        self.assertEqual(len(cities), 8)

    def test_producing_buildings_animate(self):
        for kind in ("farm", "lumber_mill", "mine"):
            frames = []
            for time in (0, 1):
                image = pygame.Surface((100, 100), pygame.SRCALPHA)
                draw_building(image, kind, (50, 50), 80, time)
                frames.append(pygame.image.tobytes(image, "RGBA"))
            self.assertNotEqual(*frames)


if __name__ == "__main__":
    unittest.main()
