import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from cars.ui.audio import Audio


class AudioTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "settings.json"
        self.audio = Audio(self.path)

    def tearDown(self):
        pygame.quit()
        self.folder.cleanup()

    def test_bundled_recordings_match_their_checksums_and_cycle(self):
        audio = self.audio
        self.assertEqual(len(audio.tracks), 3)
        for i, track in enumerate(audio.tracks):
            digest = hashlib.sha256((audio.music_folder / track["file"]).read_bytes()).hexdigest()
            self.assertEqual(digest, track["sha256"])
            audio.select(i)
            self.assertTrue(audio.music_loaded)
            self.assertTrue(audio.music_channel.get_busy())
            self.assertGreater(track["duration"], 180)
            audio.music_channel.stop()
            audio.update()
            self.assertEqual(audio.index, (i + 1) % 3)

    def test_pause_shuffle_volume_and_preferences_persist(self):
        audio = self.audio
        audio.select(2)
        audio.toggle_pause()
        audio.update()
        self.assertEqual(audio.index, 2)
        self.assertFalse(audio.music_channel.get_busy())
        audio.change("shuffle")
        audio.change("music", -0.1)
        restored = Audio(self.path)
        self.assertEqual(restored.index, 2)
        self.assertTrue(restored.settings["paused"])
        self.assertTrue(restored.settings["shuffle"])
        restored.toggle_pause()
        before = restored.index
        restored.skip()
        self.assertNotEqual(before, restored.index)
        expected = restored.settings["master"] * restored.settings["music"]
        self.assertAlmostEqual(restored.music_channel.get_volume(), expected, delta=0.01)

    def test_missing_recordings_are_skipped_without_retry_loops(self):
        audio = self.audio
        real_load = audio.music_channel.load

        def load(path):
            if path.endswith("bach_aria.ogg"):
                raise pygame.error("missing")
            return real_load(path)

        with patch.object(audio.music_channel, "load", side_effect=load):
            audio.start(0)
            self.assertTrue(audio.music_loaded)
            self.assertEqual(audio.index, 1)
        with patch.object(audio.music_channel, "load", side_effect=pygame.error("missing")) as loader:
            audio.start(0)
            self.assertEqual(loader.call_count, 3)
            self.assertFalse(audio.music_loaded)
            for _ in range(10):
                audio.update()
            self.assertEqual(loader.call_count, 3)
            self.assertTrue(audio.available)
            audio.play("click")

    def test_no_audio_device_plays_silently(self):
        pygame.mixer.quit()
        with patch("pygame.mixer.init", side_effect=pygame.error("No device")):
            silent = Audio(Path(self.folder.name) / "missing.json")
        self.assertFalse(silent.available)
        silent.play("battle")
        silent.change("effects", -0.1)


if __name__ == "__main__":
    unittest.main()
