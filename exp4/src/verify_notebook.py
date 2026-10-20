import argparse
import copy
import io
import json
from pathlib import Path
import random
import sys
import tokenize
import types
import unittest


NOTEBOOK = Path(__file__).with_name("实验4_动态优先数进程调度.ipynb")
DATA = [(3, 3), (5, 4), (4, 2), (2, 3), (1, 2)]
DOCUMENT = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
MODULE = types.ModuleType("exp4_notebook_core")
sys.modules[MODULE.__name__] = MODULE
for cell in DOCUMENT["cells"]:
    if cell["cell_type"] == "code" and "core" in cell.get("metadata", {}).get("tags", []):
        exec(compile("".join(cell["source"]), "<notebook core>", "exec"), MODULE.__dict__)
Scheduler = MODULE.Scheduler


def reference_trace(settings):
    queue = [{"name": f"P{index}", "priority": priority, "remaining": runtime}
             for index, (priority, runtime) in enumerate(settings, 1)]
    queue.sort(key=lambda pcb: -pcb["priority"])
    trace = []
    while queue:
        pcb = queue.pop(0)
        trace.append(pcb["name"])
        pcb["priority"] -= 1
        pcb["remaining"] -= 1
        if pcb["remaining"]:
            queue.append(pcb)
            queue.sort(key=lambda item: -item["priority"])
    return trace


class SchedulerTests(unittest.TestCase):
    def check_history(self, scheduler):
        self.assertEqual(len(scheduler.memory), 5)
        for pointer, pcb in scheduler.memory.items():
            self.assertEqual(pointer, id(pcb))
        identities = {pcb["name"]: pcb["id"] for pcb in scheduler.history[0]["pcbs"]}
        for record in scheduler.history:
            pcbs = {pcb["id"]: pcb for pcb in record["pcbs"]}
            queue = record["queue"]
            self.assertEqual(record["head"], queue[0] if queue else 0)
            self.assertEqual(len(queue), len(set(queue)))
            self.assertEqual(set(queue), {pointer for pointer, pcb in pcbs.items()
                                          if pcb["state"] == "R"})
            priorities = [pcbs[pointer]["priority"] for pointer in queue]
            self.assertEqual(priorities, sorted(priorities, reverse=True))
            self.assertEqual(sum(pcb["remaining"] for pcb in pcbs.values()),
                             scheduler.total_runtime - record["tick"])
            for index, pointer in enumerate(queue):
                self.assertEqual(pcbs[pointer]["next"],
                                 queue[index + 1] if index + 1 < len(queue) else 0)
            for pcb in pcbs.values():
                self.assertEqual(pcb["id"], identities[pcb["name"]])
                if pcb["state"] == "E":
                    self.assertEqual((pcb["remaining"], pcb["next"]), (0, 0))
                else:
                    self.assertGreater(pcb["remaining"], 0)
        for before, after in zip(scheduler.history, scheduler.history[1:]):
            old = {pcb["name"]: pcb for pcb in before["pcbs"]}
            new = {pcb["name"]: pcb for pcb in after["pcbs"]}
            selected = after["selected"]
            self.assertEqual(selected, next(pcb["name"] for pcb in before["pcbs"]
                                            if pcb["id"] == before["head"]))
            self.assertEqual(after["tick"], before["tick"] + 1)
            self.assertEqual(after["before"], (old[selected]["priority"], old[selected]["remaining"]))
            for name in old:
                decrement = int(name == selected)
                self.assertEqual(new[name]["priority"], old[name]["priority"] - decrement)
                self.assertEqual(new[name]["remaining"], old[name]["remaining"] - decrement)
            self.assertGreaterEqual(after["elapsed_ns"], 0)

    def test_default_hand_checked_trace(self):
        scheduler = Scheduler(DATA)
        scheduler.run_to_end()
        expected = ["P2", "P3", "P2", "P1", "P3", "P2", "P4",
                    "P1", "P2", "P5", "P4", "P1", "P5", "P4"]
        self.assertEqual([record["selected"] for record in scheduler.history[1:]], expected)
        self.assertEqual(scheduler.tick, 14)
        self.assertEqual(scheduler.head, 0)
        self.check_history(scheduler)

    def test_equal_priorities_and_negative_priorities(self):
        scheduler = Scheduler([(0, 2)] * 5)
        scheduler.run_to_end()
        self.assertEqual([record["selected"] for record in scheduler.history[1:]],
                         [f"P{index}" for index in range(1, 6)] * 2)
        self.assertTrue(all(pcb.priority == -2 for pcb in scheduler.memory.values()))
        self.check_history(scheduler)

    def test_finish_without_reinsertion(self):
        scheduler = Scheduler([(2, 1), (5, 1), (5, 1), (-1, 1), (0, 1)])
        scheduler.run_to_end()
        self.assertEqual([record["selected"] for record in scheduler.history[1:]],
                         ["P2", "P3", "P1", "P5", "P4"])
        self.check_history(scheduler)

    def test_finished_step_is_unchanged(self):
        scheduler = Scheduler(DATA)
        scheduler.run_to_end()
        saved = copy.deepcopy(scheduler.history)
        self.assertIsNone(scheduler.step())
        scheduler.run_to_end()
        self.assertEqual(scheduler.history, saved)

    def test_snapshots_and_input_are_independent(self):
        settings = [list(item) for item in DATA]
        saved_input = copy.deepcopy(settings)
        scheduler = Scheduler(settings)
        initial = copy.deepcopy(scheduler.history[0])
        scheduler.run_to_end()
        self.assertEqual(scheduler.history[0], initial)
        self.assertEqual(settings, saved_input)

    def test_invalid_input(self):
        invalid = [[], DATA[:4], DATA + [(1, 1)],
                   [(1, 0)] + DATA[1:], [(1, -1)] + DATA[1:],
                   [(1.5, 1)] + DATA[1:], [(1, 1.5)] + DATA[1:],
                   [(True, 1)] + DATA[1:], [(1, True)] + DATA[1:],
                   [("3", 1)] + DATA[1:], [(1,)] + DATA[1:]]
        for settings in invalid:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Scheduler(settings)

    def test_random_cases_against_independent_reference(self):
        generator = random.Random(2026)
        for case in range(100):
            settings = [(generator.randint(-3, 8), generator.randint(1, 6)) for _ in range(5)]
            with self.subTest(case=case):
                scheduler = Scheduler(settings)
                scheduler.run_to_end()
                self.assertEqual([record["selected"] for record in scheduler.history[1:]],
                                 reference_trace(settings))
                self.assertEqual(scheduler.tick, sum(runtime for priority, runtime in settings))
                self.check_history(scheduler)

    def test_markdown_before_code_and_no_code_comments(self):
        self.assertEqual(DOCUMENT["nbformat"], 4)
        for index, cell in enumerate(DOCUMENT["cells"]):
            if cell["cell_type"] == "code":
                self.assertGreater(index, 0)
                self.assertEqual(DOCUMENT["cells"][index - 1]["cell_type"], "markdown")
                tokens = tokenize.generate_tokens(io.StringIO("".join(cell["source"])).readline)
                self.assertFalse(any(token.type == tokenize.COMMENT for token in tokens))
                self.assertFalse(any(output.get("output_type") == "error"
                                     for output in cell.get("outputs", [])))


def execute_notebook():
    import nbformat
    from nbclient import NotebookClient

    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    integration = nbformat.v4.new_code_cell('''
assert lab["state"]["scheduler"].tick == 0
assert lab["state"]["scheduler"].total_runtime == 14
lab["step"].click()
assert lab["state"]["scheduler"].tick == 1
assert lab["state"]["scheduler"].history[-1]["selected"] == "P2"
assert "第 1 步" in lab["output"].value
lab["finish"].click()
assert lab["state"]["scheduler"].tick == 14
assert lab["state"]["scheduler"].head == 0
assert lab["step"].disabled and lab["finish"].disabled
assert "全部进程已结束" in lab["status"].value
for priority, runtime in lab["inputs"]:
    priority.value = 0
    runtime.value = 2
lab["initialize"].click()
assert lab["state"]["scheduler"].tick == 0
assert len(lab["state"]["scheduler"].history) == 1
assert not lab["step"].disabled and not lab["finish"].disabled
lab["finish"].click()
assert lab["state"]["scheduler"].tick == 10
assert [r["selected"] for r in lab["state"]["scheduler"].history[1:]] == ["P1", "P2", "P3", "P4", "P5"] * 2
previous = lab["state"]["scheduler"]
lab["inputs"][0][1].value = 0
lab["initialize"].click()
assert lab["state"]["scheduler"] is previous
assert "初始化失败" in lab["status"].value
lab["inputs"][0][1].value = 1
lab["initialize"].click()
assert lab["state"]["scheduler"].total_runtime == 9
assert lab["state"]["scheduler"].tick == 0
print("Notebook execution and widget integration: PASS")
'''.strip())
    notebook.cells.append(integration)
    NotebookClient(notebook, timeout=120, kernel_name="python3").execute(cwd=str(NOTEBOOK.parent))
    notebook.cells.pop()
    validation = NOTEBOOK.parent.parent / ".validation"
    validation.mkdir(exist_ok=True)
    nbformat.write(notebook, validation / "executed.ipynb")
    print("Notebook execution and widget integration: PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SchedulerTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    if arguments.execute:
        execute_notebook()
