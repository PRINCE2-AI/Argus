import time
import unittest

from argus.fleet import run_fleet


class FakeHarness:
    def __init__(self, workdir):
        self.workdir = workdir

    def run(self, task):
        delay = 0.05 if "slow" in task else 0
        time.sleep(delay)
        if "fail" in task:
            raise ValueError("job failed")
        return f"{self.workdir}:{task}"


class FleetTests(unittest.TestCase):
    def test_results_keep_input_order(self):
        jobs = [
            {"name": "first", "workdir": "a", "task": "slow work"},
            {"name": "second", "workdir": "b", "task": "fast work"},
            {"name": "third", "workdir": "c", "task": "normal work"},
        ]
        results = run_fleet(jobs, FakeHarness, max_workers=3)
        self.assertEqual([result["name"] for result in results], ["first", "second", "third"])
        self.assertEqual(results[0]["report"], "a:slow work")
        self.assertEqual(results[1]["report"], "b:fast work")
        self.assertTrue(all(result["ok"] for result in results))
        self.assertTrue(all(isinstance(result["seconds"], float) for result in results))

    def test_failures_are_captured_per_job(self):
        jobs = [
            {"name": "good", "workdir": "a", "task": "work"},
            {"name": "bad", "workdir": "b", "task": "fail now"},
        ]
        results = run_fleet(jobs, FakeHarness, max_workers=2)
        self.assertTrue(results[0]["ok"])
        self.assertFalse(results[1]["ok"])
        self.assertIn("ValueError: job failed", results[1]["report"])
        self.assertEqual(results[1]["name"], "bad")

    def test_zero_workers_still_executes(self):
        jobs = [{"name": "only", "workdir": "a", "task": "work"}]
        results = run_fleet(jobs, FakeHarness, max_workers=0)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["ok"])

    def test_empty_fleet(self):
        self.assertEqual(run_fleet([], FakeHarness), [])


if __name__ == "__main__":
    unittest.main()
