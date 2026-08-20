"""Sync is a thread simulator that is distributed with
*The Little Book of Semaphores*, by Allen Downey,
available from https://greenteapress.com/wp/semaphores/

Copyright 2011 Allen B. Downey
Distributed under the GNU General Public License at gnu.org/licenses/gpl.html.

Simulation logic lives in sync_core.py (headless). This module provides the
Tkinter UI and re-exports the engine API for compatibility.
"""

from __future__ import print_function, division

import optparse
import os
import random
import sys
import time

try:
    from tkinter import W, TOP, BOTTOM, LEFT, RIGHT, END
except ImportError:
    from Tkinter import W, TOP, BOTTOM, LEFT, RIGHT, END

from Gui import Gui, GuiCanvas

from sync_core import (
    CURRENT_THREAD,
    CodeColumn,
    CodeRow,
    FifoSemaphore,
    Lightswitch,
    Namespace,
    Namer,
    SIM_GLOBALS,
    SIM_LOCALS,
    Semaphore,
    Simulator,
    Thread,
    balk,
    noop,
    num_threads,
    parse_sync_file,
    pid,
    snapshot_state,
    trim_block,
)

# Re-export engine names for existing imports / Sync_test.py
__all__ = [
    "Sync",
    "Thread",
    "Simulator",
    "Semaphore",
    "FifoSemaphore",
    "Lightswitch",
    "Namespace",
    "Namer",
    "CodeRow",
    "CodeColumn",
    "CURRENT_THREAD",
    "SIM_GLOBALS",
    "SIM_LOCALS",
    "balk",
    "noop",
    "pid",
    "num_threads",
    "snapshot_state",
]


# The Anaconda installation of Tkinter does not use Freetype
# https://github.com/ContinuumIO/anaconda-issues/issues/6833

# If you have a system-level installation of Tkinter, it will
# probably work better.


FONT = ("Ubuntu Mono", 20)
# FSU, the fundamental Sync unit, determines the size of most things.
FSU = 20


class Sync(Gui):
    """Represents the thread simulator (Tkinter UI over sync_core)."""

    def __init__(self, args=[""]):
        Gui.__init__(self)
        self.parse_args(args)
        self.namer = Namer()

        self.locals = SIM_LOCALS
        self.globals = SIM_GLOBALS

        # views is a map from a variable name to the row that
        # should be updated when the variable changes
        self.views = {}
        self.w = self
        self.threads = []
        self.running = False
        self.delay = 0.2
        self.setup()
        self.run_init()
        for col in self.cols:
            col.create_thread()

    def parse_args(self, args):
        parser = optparse.OptionParser()
        parser.add_option(
            "-w",
            "--write",
            dest="write",
            action="store_true",
            default=False,
            help="Write thread code in code subdirectory?",
        )
        parser.add_option(
            "-s",
            "--side",
            dest="initside",
            action="store_true",
            default=False,
            help="Move the initialization code to the left side?",
        )

        self.options, args = parser.parse_args(args)

        if args:
            self.filename = args[0]
        else:
            self.filename = ""

    def get_name(self, name=None):
        return self.namer.next(name)

    def get_threads(self):
        return self.threads

    def set_global(self, **kwds):
        self.globals.update(kwds)

    def get_global(self, attr):
        return self.globals[attr]

    def destroy(self):
        """Closes the top window."""
        self.running = False
        Gui.destroy(self)

    def setup(self):
        """Makes the GUI."""
        if self.filename:
            self.read_file(self.filename)
            self.make_columns()
            if self.options.write:
                self.write_files(self.filename)
            return

        self.topcol = Column(self, n=5)
        self.colfr = self.fr()
        self.cols = [Column(self, LEFT, n=5) for i in range(2)]
        self.bu(side=RIGHT, text="Add\ncolumn", font=FONT, command=self.add_col)
        self.endfr()
        self.buttons()

    def buttons(self):
        """Makes the buttons."""
        self.row([1, 1, 1, 1, 1])
        self.bu(text="Run", font=FONT, command=self.run)
        self.bu(text="Random Run", font=FONT, command=self.random_run)
        self.bu(text="Stop", font=FONT, command=self.stop)
        self.bu(text="Step", font=FONT, command=self.step)
        self.bu(text="Random Step", font=FONT, command=self.random_step)
        self.endfr()

    def register(self, thread):
        """Adds a new thread."""
        self.threads.append(thread)

    def unregister(self, thread):
        """Removes a thread."""
        self.threads.remove(thread)

    def run(self):
        """Runs the simulator with round-robin scheduling."""
        self.run_helper(self.step)

    def random_run(self):
        """Runs the simulator with random scheduling."""
        self.run_helper(self.random_step)

    def run_helper(self, step=None):
        """Runs the threads until someone clears self.running."""
        self.running = True
        while self.running:
            step()
            self.update()
            time.sleep(self.delay)

    def step(self):
        """Advances all the threads in order"""
        for thread in self.threads:
            thread.step_loop()

    def random_step(self):
        """Advances one random thread."""
        threads = [thread for thread in self.threads if not thread.queued]
        if not threads:
            print("There are currently no threads that can run.")
            return
        thread = random.choice(threads)
        thread.step_loop()

    def stop(self):
        """Stops running."""
        self.running = False

    def read_file(self, filename):
        """Read a file that contains code for the simulator to execute."""
        self.blocks = parse_sync_file(filename)

    def make_columns(self):
        """Adds the code in self.blocks to the GUI."""
        if not self.blocks:
            return

        side = LEFT if self.options.initside else TOP
        self.topcol = TopColumn(self, side=side)

        self.topcol.add_rows(self.blocks[0])

        self.colfr = self.fr()
        self.cols = []
        self.endfr()

        for block in self.blocks[1:]:
            col = self.add_col(0)
            col.add_rows(block)

        self.buttons()

    def write_files(self, filename, dirname="book_code"):
        """Writes the code into separate files for the init and threads.

        filename: name of the file we read
        dirname: name of the destination subdirectory

        Destination is a subdirectory of the directory the filename is in.
        """
        path, filename = os.path.split(filename)

        dest = os.path.join(path, dirname, filename)

        block = self.blocks[0]
        self.write_file(block, dest, 0)

        for i, block in enumerate(self.blocks[1:]):
            self.write_file(block, dest, i + 1)

    def write_file(self, block, filename, suffix=0):
        trim_block(block)

        name = "%s.%s" % (filename, str(suffix))
        fp = open(name, "w")
        for line in block:
            fp.write(line + "\n")
        fp.close()

    def add_col(self, n=5):
        """Adds a new column of code to the display."""
        self.pushfr(self.colfr)
        col = Column(self, LEFT, n)
        self.cols.append(col)
        self.popfr()
        return col

    def run_init(self):
        """Runs the initialization code in the top column."""
        if not self.topcol.num_rows():
            return

        print("running init")
        self.clear_views()
        self.views = {}

        thread = Thread(self.topcol, name="0")
        while True:
            thread.step()
            if thread.row is None:
                break

        self.unregister(thread)

    def update_views(self):
        """Loops through the views and updates them."""
        for key, view in self.views.items():
            view.update(self.locals[key])

    def clear_views(self):
        """Loops through the views and clears them."""
        for view in self.views.values():
            view.clear()

    def qu(self, **options):
        """Makes a queue."""
        return self.widget(QueueCanvas, **options)


"""
The following classes define the composite objects that make
up the display: Row, TopRow, Column and TopColumn.  They are
all subclasses of Widget.
"""


class Widget:
    """Superclass of all display objects.

    Each Widget keeps a reference to its immediate parent Widget (p)
    and to the top-most thing (w).
    """

    def __init__(self, p, *args, **options):
        self.p = p
        self.w = p.w
        self.setup(*args, **options)


class Row(Widget):
    """A row of code.

    Each row contains two queues, runnable and queued,
    and an entry that contains a line of code.
    """

    def setup(self, text=""):
        self.tag = None
        self.fr = self.w.row([0, 0, 1])
        self.queued = self.w.qu(side=LEFT, n=3)
        self.runnable = self.w.qu(side=LEFT, n=3, label="Run")
        self.en = self.w.en(side=LEFT, font=FONT)
        self.en.bind("<Key>", self.keystroke)
        self.w.endrow()
        self.put(text)

    def update(self, val):
        """Updates the text in the runnable widget.

        val: value to display (can be anything that provides str)
        """
        # TODO: maybe config existing text rather than delete
        if self.tag:
            self.clear()
        text = str(val)
        self.tag = self.runnable.display_text(text)

    def clear(self):
        self.runnable.delete(self.tag)

    def keystroke(self, event=None):
        "resize the entry whenever the user types a character"
        self.entry_size()

    def entry_size(self):
        "resize the entry"
        text = self.get()
        width = self.en.cget("width")
        text_len = len(text) + 2
        if text_len > width:
            self.en.configure(width=text_len)

    def add_thread(self, thread):
        self.runnable.add_thread(thread)

    def remove_thread(self, thread):
        self.runnable.remove_thread(thread)

    def enqueue_thread(self, thread):
        self.queued.add_thread(thread)

    def dequeue_thread(self, thread):
        self.queued.remove_thread(thread)

    def put(self, text):
        self.en.delete(0, END)
        self.en.insert(0, text)
        self.entry_size()

    def get(self):
        return self.en.get()


class TopRow(Row):
    """Rows in the initialization code at the top.

    The top row is special because there is no queue for
    queued threads, and the "runnable" queue is actually used
    to display the value of variables.
    """

    def setup(self, text=""):
        Row.setup(self, text)
        self.queued.destroy()
        self.runnable.delete("all")


class Column(Widget):
    """A list of rows and a few buttons."""

    def setup(self, side=TOP, n=0, row_factory=Row):
        self.fr = self.w.fr(side=side, bd=3)
        self.row_factory = row_factory
        self.rows = [self.row_factory(self) for i in range(n)]

        self.buttons = self.w.row([1, 1], side=BOTTOM)
        self.bu1 = self.w.bu(
            text="Create thread", font=FONT, command=self.create_thread
        )
        self.bu2 = self.w.bu(text="Add row", font=FONT, command=self.add_row)
        self.w.endrow()
        self.w.endfr()

    def num_rows(self):
        return len(self.rows)

    def add_rows(self, block, keep_blanks=False):
        for line in block:
            if line or keep_blanks:
                self.add_row(line)

    def add_row(self, text=""):
        self.w.pushfr(self.fr)
        row = self.row_factory(self, text)
        self.w.popfr()
        self.rows.append(row)

    def create_thread(self):
        new = Thread(self)
        return new

    def next_row(self, row):
        if row is None:
            return self.rows[0]

        index = self.rows.index(row)
        try:
            return self.rows[index + 1]
        except IndexError:
            return None


class TopColumn(Column):
    """The top column where the initialization code is.

    The top column is different from the other columns in
    two ways: it has different buttons, and it uses the TopRow
    constructor to make new rows rather than the Row constructor.
    """

    def setup(self, side=TOP, n=0, row_factory=TopRow):
        Column.setup(self, side, n, row_factory)
        self.bu1.configure(
            text="Run initialization", font=FONT, command=self.p.run_init
        )


class QueueCanvas(GuiCanvas):
    """Displays the runnable and queued threads."""

    def __init__(self, w, n=1, label="Queue"):
        self.n = n
        self.label = label
        width = 2 * n * FSU
        height = 3 * FSU
        GuiCanvas.__init__(self, w, width=width, height=height, transforms=[])
        self.threads = []
        self.setup()

    def setup(self):
        self.text([3, 15], self.label, font=FONT, anchor=W, fill="white")

    def add_thread(self, thread):
        self.undraw_queue()
        self.threads.append(thread)
        self.draw_queue()

    def remove_thread(self, thread):
        self.undraw_queue()
        self.threads.remove(thread)
        self.draw_queue()

    def draw_queue(self):
        x = FSU
        y = FSU
        r = 0.9 * FSU
        for thread in self.threads:
            self.draw_thread(thread, x, y, r)
            x += 1.5 * r
            if x > self.get_width():
                x = FSU
                y += 1.5 * r

    def undraw_queue(self):
        for thread in self.threads:
            self.delete(thread.tag)

    def draw_thread(self, thread, x=FSU, y=FSU, r=0.9 * FSU):
        thread.tag = "Thread" + thread.name
        self.circle([x, y], r, fill=thread.color, tags=thread.tag)
        font = ("FONT", int(r + 3))
        self.text([x, y], thread.name, font=font, tags=thread.tag)
        self.tag_bind(thread.tag, "<Button-1>", thread.step_loop)

    def undraw_thread(self, thread):
        self.delete(thread.tag)

    def display_text(self, text):
        """Displays text on this canvas.

        text: string
        """
        tag = self.text([15, 15], text, font=FONT)
        return tag


def main():
    sync = Sync(sys.argv[1:])
    sync.mainloop()


if __name__ == "__main__":
    main()
