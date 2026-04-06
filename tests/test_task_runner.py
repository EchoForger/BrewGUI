from __future__ import annotations

import threading
import time
import unittest

from brew_gui_manager.task_runner import BackgroundTaskRunner


class BackgroundTaskRunnerTests(unittest.TestCase):
    def test_submit_emits_started_and_completed_events(self) -> None:
        runner = BackgroundTaskRunner()

        task_id = runner.submit("demo task", lambda: "done")

        events = self._wait_for_events(runner, expected=2)

        self.assertEqual(task_id, 1)
        self.assertEqual([event.status for event in events], ["started", "completed"])
        self.assertEqual(events[-1].payload, "done")

    def test_submit_emits_failed_event(self) -> None:
        runner = BackgroundTaskRunner()

        def boom() -> str:
            raise RuntimeError("boom")

        runner.submit("bad task", boom)
        events = self._wait_for_events(runner, expected=2)

        self.assertEqual(events[-1].status, "failed")
        self.assertEqual(str(events[-1].error), "boom")

    def test_tasks_run_off_main_thread(self) -> None:
        runner = BackgroundTaskRunner()
        main_thread = threading.get_ident()

        runner.submit("thread task", threading.get_ident)
        events = self._wait_for_events(runner, expected=2)

        self.assertNotEqual(events[-1].payload, main_thread)

    @staticmethod
    def _wait_for_events(runner: BackgroundTaskRunner, expected: int) -> list:
        deadline = time.time() + 2
        events = []
        while time.time() < deadline:
            events.extend(runner.drain_events())
            if len(events) >= expected:
                return events
            time.sleep(0.02)
        raise AssertionError(f"Timed out waiting for {expected} task events, got {len(events)}")


if __name__ == "__main__":
    unittest.main()
