import unittest
from unittest.mock import patch

import tests.support  # noqa: F401  (isolated user profile)
from cars import __version__
from cars.app import main
from cars.crash import MAX_LOG_CHARACTERS, write_report
from cars.paths import crash_log_path


def failing() -> None:
    raise RuntimeError("the map fell off the table")


class CrashReportTests(unittest.TestCase):
    def setUp(self):
        crash_log_path().unlink(missing_ok=True)

    def test_report_records_version_and_traceback(self):
        try:
            failing()
        except RuntimeError as error:
            path = write_report(error)
        text = crash_log_path().read_text(encoding="utf-8")
        self.assertEqual(path, str(crash_log_path()))
        self.assertIn(__version__, text)
        self.assertIn("RuntimeError: the map fell off the table", text)
        self.assertIn("in failing", text)

    def test_log_keeps_only_the_newest_reports(self):
        error = RuntimeError("x" * 1000)
        for _ in range(MAX_LOG_CHARACTERS // 500):
            write_report(error)
        self.assertLessEqual(len(crash_log_path().read_text(encoding="utf-8")), MAX_LOG_CHARACTERS)

    def test_a_crashing_game_writes_a_report_and_tells_the_player(self):
        with (
            patch("cars.ui.app.App", side_effect=RuntimeError("boom")),
            patch("pygame.display.message_box") as message_box,
            self.assertRaises(RuntimeError),
        ):
            main(["--smoke"])
        self.assertIn("RuntimeError: boom", crash_log_path().read_text(encoding="utf-8"))
        message_box.assert_called_once()


if __name__ == "__main__":
    unittest.main()
