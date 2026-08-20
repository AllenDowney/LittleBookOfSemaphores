"""Headless tests for sync_core (no Tkinter / display required)."""

import os
import unittest

import sync_core
from sync_core import Simulator, Thread


class HeadlessTests(unittest.TestCase):

    def setUp(self):
        # Keep locals/globals from leaking across tests (same as desktop Sync).
        sync_core.SIM_LOCALS.clear()

    def _mutex_path(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, "sync_code", "mutex.py")

    def test_import_without_tkinter(self):
        self.assertFalse(hasattr(sync_core, "Gui"))
        self.assertIn("Semaphore", sync_core.SIM_GLOBALS)

    def test_from_file_mutex(self):
        sim = Simulator.from_file(self._mutex_path())
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
        sim = Simulator.from_file(self._mutex_path())
        self.assertEqual(len(sim.get_threads()), 1)
        sim.create_thread(0)
        self.assertEqual(len(sim.get_threads()), 2)
        sim.step()


if __name__ == "__main__":
    unittest.main()
