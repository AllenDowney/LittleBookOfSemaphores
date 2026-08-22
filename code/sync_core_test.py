"""Headless tests for sync_core (no Tkinter / display required).

Task 3: behavior coverage without a display. Ports Sync_test expectations
where noted; adds FIFO, scheduling, loop, and thread-local cases.
"""

import io
import json
import os
import random
import unittest
from contextlib import redirect_stdout

import sync_core
from sync_core import CodeColumn, Simulator, Thread


def _code_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(_code_dir(), *parts)


class HeadlessTestCase(unittest.TestCase):
    """Base: clear shared locals and silence simulator print noise."""

    def setUp(self):
        sync_core.SIM_LOCALS.clear()
        self._stdout = redirect_stdout(io.StringIO())
        self._stdout.__enter__()

    def tearDown(self):
        self._stdout.__exit__(None, None, None)

    def make_sim(self, init_lines, *thread_blocks):
        """Build a Simulator from in-memory blocks (no file / no GUI)."""
        sim = Simulator()
        sim.blocks = [list(init_lines)] + [list(block) for block in thread_blocks]
        sim.make_columns()
        sim.run_init()
        for col in sim.cols:
            col.create_thread()
        return sim


class ImportTests(HeadlessTestCase):

    def test_import_without_tkinter(self):
        self.assertFalse(hasattr(sync_core, "Gui"))
        self.assertIn("Semaphore", sync_core.SIM_GLOBALS)
        self.assertIn("FifoSemaphore", sync_core.SIM_GLOBALS)


class MutexTests(HeadlessTestCase):
    """Ported from Sync_test.test_sync_mutex (GUI → headless)."""

    def test_from_file_mutex(self):
        sim = Simulator.from_file(_path("sync_code", "mutex.py"))
        self.assertEqual(len(sim.cols), 1)
        self.assertGreater(sim.topcol.num_rows(), 0)
        self.assertEqual(len(sim.get_threads()), 1)

        threads = sim.get_threads()
        thread_a = threads[0]
        column = thread_a.column

        source = thread_a.step()
        self.assertEqual(source, "mutex.wait()")

        thread_b = Thread(column)
        source = thread_b.step()
        self.assertEqual(source, "mutex.wait()")

        self.assertFalse(thread_a.queued)
        self.assertTrue(thread_b.queued)

        source = thread_b.step()
        self.assertEqual(source, None)

        source = thread_a.step()
        source = thread_a.step()
        source = thread_a.step()
        self.assertEqual(source, "mutex.signal()")

        self.assertFalse(thread_a.queued)
        self.assertFalse(thread_b.queued)

        source = thread_a.exec_line("pid = pid()", sim)
        self.assertEqual(sim.locals["pid"], "A")

    def test_step_and_create_thread(self):
        sim = Simulator.from_file(_path("sync_code", "mutex.py"))
        self.assertEqual(len(sim.get_threads()), 1)
        sim.create_thread(0)
        self.assertEqual(len(sim.get_threads()), 2)
        sim.step()


class GetStateTests(HeadlessTestCase):
    """Task 2 snapshot shape (kept here for one headless suite)."""

    def test_get_state_after_init(self):
        sim = Simulator.from_file(_path("sync_code", "mutex.py"))
        state = json.loads(json.dumps(sim.get_state()))

        self.assertTrue(state["filename"].endswith("mutex.py"))
        self.assertIn("mutex = Semaphore(1)", state["init"])
        self.assertEqual(state["columns"][0][0], "mutex.wait()")
        self.assertEqual(state["variables"]["counter"], 0)
        self.assertEqual(state["semaphores"]["mutex"]["value"], 1)
        self.assertEqual(state["semaphores"]["mutex"]["queue"], [])
        self.assertFalse(state["semaphores"]["mutex"]["fifo"])

        self.assertEqual(len(state["threads"]), 1)
        thread = state["threads"][0]
        self.assertEqual(thread["name"], "A")
        self.assertEqual(thread["column"], 0)
        self.assertEqual(thread["row"], 0)
        self.assertEqual(thread["row_text"], "mutex.wait()")
        self.assertFalse(thread["blocked"])
        self.assertIsNone(thread["waiting_on"])
        self.assertIn("counter", state["views"])

    def test_get_state_blocked_on_mutex(self):
        sim = Simulator.from_file(_path("sync_code", "mutex.py"))
        thread_a = sim.get_threads()[0]
        thread_a.step()
        thread_b = Thread(thread_a.column)
        thread_b.step()

        state = json.loads(json.dumps(sim.get_state()))
        by_name = {t["name"]: t for t in state["threads"]}

        self.assertEqual(state["semaphores"]["mutex"]["value"], -1)
        self.assertEqual(state["semaphores"]["mutex"]["queue"], ["B"])
        self.assertFalse(by_name["A"]["blocked"])
        self.assertTrue(by_name["B"]["blocked"])
        self.assertEqual(by_name["B"]["waiting_on"], "mutex")
        self.assertEqual(by_name["A"]["row_text"], "# critical section")


class ConditionalTests(HeadlessTestCase):
    """Ported from Sync_test.test_sync_conditional."""

    def test_conditional(self):
        sim = Simulator.from_file(_path("sync_code", "conditional.py"))
        thread_a = sim.get_threads()[0]

        source = thread_a.step()
        self.assertEqual(source, "if counter == 0:")

        source = thread_a.step()
        self.assertEqual(source, "    print(True)")

        source = thread_a.step()
        self.assertEqual(source, "if counter == 1:")

        source = thread_a.step()
        self.assertEqual(source, "pass")

        source = thread_a.step()
        source = thread_a.step()
        self.assertEqual(source, "else:")

        source = thread_a.step()
        self.assertEqual(source, "    print(False)")

        source = thread_a.step()
        source = thread_a.step()
        self.assertEqual(source, "    print(True)")

        source = thread_a.step()
        source = thread_a.step()
        self.assertEqual(source, "pass")


class WhileTests(HeadlessTestCase):
    """Ported from Sync_test.test_sync_while."""

    def test_while(self):
        sim = Simulator.from_file(_path("sync_code", "while.py"))
        thread_a = sim.get_threads()[0]

        source = thread_a.step()
        self.assertEqual(source, "while counter == 1:")

        source = thread_a.step()
        self.assertEqual(source, "while counter < 1:")

        source = thread_a.step()
        self.assertEqual(source, "    counter += 1")

        source = thread_a.step()
        self.assertEqual(source, "while counter < 1:")

        source = thread_a.step()
        self.assertEqual(source, "pass")


class SemaphoreSignalTests(HeadlessTestCase):
    """wait/signal unblock using sync_code/signal.py (two columns)."""

    def test_signal_unblocks_waiter(self):
        sim = Simulator.from_file(_path("sync_code", "signal.py"))
        self.assertEqual(len(sim.cols), 2)
        thread_a, thread_b = sim.get_threads()

        # B waits first and blocks on initComplete (value 0).
        source = thread_b.step()
        self.assertEqual(source, "initComplete.wait()")
        self.assertTrue(thread_b.queued)

        # A signals and wakes B.
        source = thread_a.step()
        self.assertEqual(source.strip(), "# perform initialization")
        source = thread_a.step()
        self.assertEqual(source, "initComplete.signal()")

        self.assertFalse(thread_b.queued)
        state = sim.get_state()
        self.assertEqual(state["semaphores"]["initComplete"]["queue"], [])


class FifoSemaphoreTests(HeadlessTestCase):

    def test_fifo_wakes_in_arrival_order(self):
        sim = self.make_sim(
            ["sem = FifoSemaphore(0)"],
            ["sem.wait()", "pass"],
        )
        # from_file-style already created thread A; add B and C.
        col = sim.cols[0]
        thread_a = sim.get_threads()[0]
        thread_b = Thread(col)
        thread_c = Thread(col)

        for thread in (thread_a, thread_b, thread_c):
            self.assertEqual(thread.step(), "sem.wait()")
            self.assertTrue(thread.queued)

        state = sim.get_state()
        self.assertEqual(state["semaphores"]["sem"]["queue"], ["A", "B", "C"])
        self.assertTrue(state["semaphores"]["sem"]["fifo"])

        # One signal → A only (FIFO).
        thread_a.exec_line("sem.signal()", sim)
        self.assertFalse(thread_a.queued)
        self.assertTrue(thread_b.queued)
        self.assertTrue(thread_c.queued)
        self.assertEqual(sim.get_state()["semaphores"]["sem"]["queue"], ["B", "C"])

        thread_a.exec_line("sem.signal()", sim)
        self.assertFalse(thread_b.queued)
        self.assertTrue(thread_c.queued)
        self.assertEqual(sim.get_state()["semaphores"]["sem"]["queue"], ["C"])


class RandomSemaphoreTests(HeadlessTestCase):

    def test_random_semaphore_unblock_is_seeded(self):
        def run_once(seed):
            sync_core.SIM_LOCALS.clear()
            sim = self.make_sim(
                ["sem = Semaphore(0)"],
                ["sem.wait()", "pass"],
            )
            col = sim.cols[0]
            threads = [sim.get_threads()[0], Thread(col), Thread(col)]
            for thread in threads:
                thread.step()
            random.seed(seed)
            threads[0].exec_line("sem.signal()", sim)
            woken = [t.name for t in threads if not t.queued]
            self.assertEqual(len(woken), 1)
            return woken[0]

        first = run_once(42)
        second = run_once(42)
        self.assertEqual(first, second)


class SchedulingTests(HeadlessTestCase):

    def test_round_robin_step_advances_all_runnable(self):
        sim = self.make_sim(
            ["count = 0"],
            ["count += 1", "pass"],
            ["count += 10", "pass"],
        )
        self.assertEqual(sim.locals["count"], 0)
        sim.step()
        # Each column's thread executed its first row once.
        self.assertEqual(sim.locals["count"], 11)
        state = sim.get_state()
        self.assertEqual(state["threads"][0]["row_text"], "pass")
        self.assertEqual(state["threads"][1]["row_text"], "pass")

    def test_random_step_seeded(self):
        sync_core.SIM_LOCALS.clear()
        sim = self.make_sim(
            ["hits = 0"],
            ["hits += 1", "pass"],
            ["hits += 1", "pass"],
        )
        random.seed(1)
        sim.random_step()
        # Exactly one runnable thread should have advanced.
        rows = [t["row"] for t in sim.get_state()["threads"]]
        self.assertEqual(sorted(rows), [0, 1])
        self.assertEqual(sim.locals["hits"], 1)

        random.seed(1)
        sync_core.SIM_LOCALS.clear()
        sim2 = self.make_sim(
            ["hits = 0"],
            ["hits += 1", "pass"],
            ["hits += 1", "pass"],
        )
        random.seed(1)
        sim2.random_step()
        rows2 = [t["row"] for t in sim2.get_state()["threads"]]
        self.assertEqual(rows, rows2)


class InitAndLocalsTests(HeadlessTestCase):

    def test_init_sets_shared_variables(self):
        sim = self.make_sim(
            ["x = 3", "y = x + 1"],
            ["pass"],
        )
        self.assertEqual(sim.locals["x"], 3)
        self.assertEqual(sim.locals["y"], 4)
        state = sim.get_state()
        self.assertEqual(state["variables"]["x"], 3)
        self.assertEqual(state["variables"]["y"], 4)

    def test_thread_local_namespace_and_pid(self):
        sim = self.make_sim(
            [],
            ["self.n = pid()", "pass"],
        )
        # Empty init still creates a Top column with no rows; run_init no-ops.
        if sim.topcol is None:
            sim.topcol = CodeColumn(sim, [])
        thread = sim.get_threads()[0]
        thread.step()
        self.assertEqual(thread.namespace.n, "A")
        state = sim.get_state()
        self.assertEqual(state["threads"][0]["locals"]["n"], "A")


class LoopTests(HeadlessTestCase):

    def test_thread_restarts_at_top_of_column(self):
        sim = self.make_sim(
            ["n = 0"],
            ["n += 1"],
        )
        thread = sim.get_threads()[0]

        # step_loop executes the last row then restarts at the top.
        thread.step_loop()
        self.assertEqual(sim.locals["n"], 1)
        self.assertEqual(thread.row.get(), "n += 1")

        thread.step_loop()
        self.assertEqual(sim.locals["n"], 2)
        self.assertEqual(thread.row.get(), "n += 1")


class ExampleLoaderTests(HeadlessTestCase):
    """Task 11: Sync source parser + representative sync_code loads."""

    # Curated set from web/examples.json (must load under headless Sync).
    MANIFEST_FILES = [
        "mutex.py",
        "signal.py",
        "rendez.py",
        "multiplex.py",
        "barrier.py",
        "barrier3.py",
        "conditional.py",
        "while.py",
        "deadlock.py",
        "barber.py",
        "barber4.py",
        "readwrite.py",
        "coke.py",
    ]

    def test_parse_sync_source_thread_delimiter(self):
        text = "a = 1\n## thread\nx = 2\n## Thread B\ny = 3\n"
        blocks = sync_core.parse_sync_source(text)
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0], ["a = 1"])
        self.assertEqual(blocks[1], ["x = 2"])
        self.assertEqual(blocks[2], ["y = 3"])

    def test_from_source_matches_from_file(self):
        path = _path("sync_code", "mutex.py")
        with open(path) as fp:
            text = fp.read()
        sync_core.SIM_LOCALS.clear()
        from_text = Simulator.from_source(text, filename=path)
        state_a = from_text.get_state()
        sync_core.SIM_LOCALS.clear()
        from_file = Simulator.from_file(path)
        state_b = from_file.get_state()
        self.assertEqual(state_a["init"], state_b["init"])
        self.assertEqual(state_a["columns"], state_b["columns"])
        self.assertEqual(len(state_a["threads"]), len(state_b["threads"]))

    def test_manifest_examples_load(self):
        for name in self.MANIFEST_FILES:
            sync_core.SIM_LOCALS.clear()
            with self.subTest(example=name):
                sim = Simulator.from_file(_path("sync_code", name))
                state = sim.get_state()
                self.assertGreaterEqual(len(state["columns"]), 1, name)
                self.assertGreaterEqual(len(state["threads"]), 1, name)

    def test_examples_json_matches_manifest_files(self):
        manifest_path = os.path.join(
            os.path.dirname(_code_dir()), "web", "examples.json"
        )
        with open(manifest_path) as fp:
            data = json.load(fp)
        files = [item["file"] for item in data["examples"]]
        self.assertEqual(files, self.MANIFEST_FILES)


if __name__ == "__main__":
    unittest.main()
