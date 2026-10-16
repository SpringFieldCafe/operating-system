"""Run real spawn/Pool integration checks without loading ManimGL."""

from collections import Counter
import time
import unittest

from .engine import ProcessLab, ROLES


class Driver:
    def __init__(self, lab):
        self.lab, self.events = lab, []

    def pump(self, service=True):
        events = self.lab.poll()
        self.events.extend(events)
        if service:
            for event in events:
                command = {"granted": "commit", "committed": "release", "released": "finished"}.get(event["kind"])
                if command:
                    self.lab.acknowledge(event["role"], event["task"], command)
        return events

    def until(self, predicate, service=True, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(service)
            if predicate(self.lab.snapshot()):
                return self.lab.snapshot()
            # IPC polling only; this delay does not choose worker order.
            time.sleep(0.003)
        raise AssertionError(f"Condition timed out: {self.lab.snapshot()}")


class EngineChecks(unittest.TestCase):
    def setUp(self):
        self.lab = ProcessLab()
        self.driver = Driver(self.lab)
        self.driver.until(lambda s: all(v["pid"] for v in s["roles"].values()))

    def tearDown(self):
        self.lab.close()

    def test_real_workers_and_balanced_competition(self):
        self.assertEqual(len({v["pid"] for v in self.lab.snapshot()["roles"].values()}), 4)
        self.lab.submit_many(father=12, mother=12, son=12, daughter=12)
        result = self.driver.until(lambda s: all(v["completed"] == 12 for v in s["roles"].values()))
        self.assertEqual(result["slots"], [None, None])
        self.driver.pump()
        owner, slots, committed = None, [None, None], Counter()
        for e in self.driver.events:
            if e["kind"] == "granted":
                self.assertIsNone(owner)
                owner = e["role"]
            elif e["kind"] == "committed":
                self.assertEqual(owner, e["role"])
                slot = e["slot"]
                if owner in ("father", "mother"):
                    self.assertIsNone(slots[slot])
                    slots[slot] = e["fruit"]
                else:
                    self.assertEqual(slots[slot], e["fruit"])
                    slots[slot] = None
                committed[owner] += 1
                self.assertLessEqual(sum(v is not None for v in slots), 2)
            elif e["kind"] == "released":
                self.assertEqual(owner, e["role"])
                owner = None
        self.assertEqual(committed, Counter({role: 12 for role in ROLES}))

    def test_missing_fruit_then_real_wakeup(self):
        self.lab.submit("son")
        self.driver.until(lambda s: s["roles"]["son"]["reason"] == "orange")
        self.lab.submit("mother")
        self.driver.until(lambda s: s["roles"]["son"]["completed"] == 1)

    def test_capacity_two_same_fruit_and_append(self):
        self.lab.submit("father", 3)
        result = self.driver.until(lambda s: s["roles"]["father"]["completed"] == 2)
        self.assertEqual(result["slots"], ["apple", "apple"])
        self.driver.until(lambda s: s["roles"]["father"]["reason"] == "space")
        self.lab.submit("father", 2)
        self.assertEqual(self.lab.snapshot()["roles"]["father"]["pending"], 3)
        self.lab.submit("daughter", 5)
        self.driver.until(lambda s: s["roles"]["daughter"]["completed"] == 5)

    def test_wrong_fruit_does_not_wake_son(self):
        self.lab.submit_many(father=1, son=1)
        result = self.driver.until(lambda s: s["roles"]["father"]["completed"] == 1)
        self.assertEqual(result["roles"]["son"]["completed"], 0)
        self.driver.until(lambda s: s["roles"]["son"]["reason"] == "orange")
        self.lab.submit("mother")
        self.driver.until(lambda s: s["roles"]["son"]["completed"] == 1)

    def test_cancel_preserves_started_trip_and_reset(self):
        self.lab.submit("father", 4)
        self.driver.until(lambda s: s["owner"] == "father", service=False)
        self.lab.cancel("father")
        self.assertEqual(self.lab.snapshot()["roles"]["father"]["cancelled"], 3)
        grant = next(e for e in self.driver.events if e["kind"] == "granted")
        self.lab.acknowledge("father", grant["task"], "commit")
        self.driver.until(lambda s: s["roles"]["father"]["completed"] == 1)
        self.lab.prepare_reset()
        result = self.lab.reset()
        self.assertEqual(result["slots"], [None, None])
        self.assertTrue(all(v["requested"] == 0 for v in result["roles"].values()))
        self.lab.submit_many(mother=2, son=2)
        self.driver.until(lambda s: s["roles"]["son"]["completed"] == 2)

    def test_pause_and_single_transfer(self):
        self.lab.pause()
        self.lab.submit_many(father=3, daughter=3)
        self.driver.until(lambda s: s["roles"]["father"]["reason"] == "paused", service=False)
        self.assertIsNone(self.lab.snapshot()["owner"])
        self.lab.step()
        self.driver.until(lambda s: len([e for e in self.driver.events if e["kind"] == "released"]) == 1)
        self.assertEqual(len([e for e in self.driver.events if e["kind"] == "committed"]), 1)
        self.assertTrue(self.lab.snapshot()["paused"])
        self.assertFalse(self.lab.snapshot()["stepping"])
        self.lab.step()
        self.driver.until(lambda s: len([e for e in self.driver.events if e["kind"] == "released"]) == 2)
        self.assertEqual(len([e for e in self.driver.events if e["kind"] == "committed"]), 2)
        self.lab.resume()
        self.driver.until(lambda s: all(s["roles"][r]["completed"] == 3 for r in ("father", "daughter")))

    def test_pause_preserves_resource_wait(self):
        self.lab.submit("son")
        self.driver.until(lambda s: s["roles"]["son"]["reason"] == "orange")
        self.lab.pause()
        self.driver.until(lambda s: s["paused"] and s["roles"]["son"]["reason"] == "orange")
        self.assertEqual(self.lab.snapshot()["roles"]["son"]["pending"], 1)
        self.lab.resume()
        self.lab.submit("mother")
        self.driver.until(lambda s: s["roles"]["son"]["completed"] == 1)

    def test_validation_is_atomic(self):
        for kwargs in ({"father": 0}, {"father": True}, {"father": 1.5}, {"unknown": 1}, {"father": 1, "son": -2}):
            with self.assertRaises(ValueError):
                self.lab.submit_many(**kwargs)
        self.assertEqual(sum(v["requested"] for v in self.lab.snapshot()["roles"].values()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
