"""Headless Sync simulation engine.

Simulation logic for the thread/semaphore simulator distributed with
*The Little Book of Semaphores*. No Tkinter dependency.

The desktop UI in Sync.py and the future web UI both drive this engine.
"""

from __future__ import print_function, division

import copy
import random
import string

# --- Student-visible API (available inside simulated code) -----------------

CURRENT_THREAD = None


def noop(*args):
    """A handy function that does nothing."""


def balk():
    """Jumps to the top of the column."""
    CURRENT_THREAD.balk()


class Semaphore:
    """Represents a semaphore in the simulator.

    Maintains a random queue.
    """

    def __init__(self, n=0):
        self.n = n
        self.queue = []

    def __str__(self):
        return str(self.n)

    def wait(self):
        self.n -= 1
        if self.n < 0:
            self.block()
        return self.n

    def block(self):
        thread = CURRENT_THREAD
        thread.enqueue()
        self.queue.append(thread)

    def signal(self, n=1):
        for _ in range(n):
            self.n += 1
            if self.queue:
                self.unblock()

    def unblock(self):
        """Chooses a random thread and unblocks it."""
        thread = random.choice(self.queue)
        self.queue.remove(thread)
        thread.dequeue()
        thread.next_loop()


class FifoSemaphore(Semaphore):
    """Semaphore that implements a FIFO queue."""

    def unblock(self):
        """Chooses the first thread and unblocks it."""
        thread = self.queue.pop(0)
        thread.dequeue()
        thread.next_loop()


class Lightswitch:
    """Encapsulates the lightswitch pattern."""

    def __init__(self):
        self.counter = 0
        self.mutex = Semaphore(1)

    def lock(self, semaphore):
        self.mutex.wait()
        self.counter += 1
        if self.counter == 1:
            semaphore.wait()
        self.mutex.signal()

    def unlock(self, semaphore):
        self.mutex.wait()
        self.counter -= 1
        if self.counter == 0:
            semaphore.signal()
        self.mutex.signal()


def pid():
    """Gets the ID of the current thread."""
    return CURRENT_THREAD.name


def num_threads():
    """Gets the number of threads."""
    sync = CURRENT_THREAD.column.p
    return len(sync.threads)


# Snapshot of names available inside simulated student code.
SIM_GLOBALS = copy.copy(globals())
SIM_LOCALS = dict()

# --- Engine (not available inside simulated code) --------------------------

ALL_THREAD_NAMES = string.ascii_uppercase + string.ascii_lowercase


def subtract(d1, d2):
    """Subtracts two dictionaries.

    Returns a new dictionary containing all the keys from
    d1 that are not in d2.
    """
    d = {}
    for key in d1:
        if key not in d2:
            d[key] = d1[key]
    return d


def diff_dict(d1, d2):
    """Diffs two dictionaries.

    Returns two dictionaries: the first contains all the keys
    from d1 that are not in d2; the second contains all the keys
    that are in both dictionaries, but which have different values.
    """
    d = {}
    c = {}
    for key in d1:
        if key not in d2:
            d[key] = d1[key]
        elif d1[key] is not d2[key]:
            c[key] = d1[key]
    return d, c


def trim_block(block):
    """Removes comments from the beginning and empty lines from the end."""
    if block and block[0].startswith("#"):
        block.pop(0)

    while block and not block[-1].strip():
        block.pop(-1)


def parse_sync_file(filename):
    """Parse a Sync source file into blocks of lines.

    Lines that start with ## do not get special treatment except:
    a line that starts with "## thread" begins a new column of code.

    Returns a list of blocks where each block is a list of lines.
    """

    def is_new_thread(line):
        if line[0:2] != "##":
            return False

        words = line.strip("#").split()
        if not words:
            return False
        word = words[0].lower()
        return word == "thread"

    blocks = []
    block = []
    blocks.append(block)

    with open(filename) as fp:
        for line in fp:
            line = line.rstrip()

            if is_new_thread(line):
                block = []
                blocks.append(block)
            else:
                block.append(line)

    return blocks


class Namer(object):
    def __init__(self):
        self.names = ALL_THREAD_NAMES
        self.next_name = 0
        self.colors = [
            "red",
            "orange",
            "yellow",
            "greenyellow",
            "green",
            "mediumseagreen",
            "skyblue",
            "violet",
            "magenta",
        ]
        self.next_color = 0

    def next(self, name=None):
        if name is None:
            name = self.names[self.next_name]
            self.next_name += 1
            self.next_name %= len(self.names)

            color = self.colors[self.next_color]
            self.next_color += 1
            self.next_color %= len(self.colors)
            return name, color
        else:
            return name, "white"


class Namespace:
    """Used to store thread-local variables.

    Inside the simulator, self refers to the thread's namespace.
    """


class CodeRow:
    """A row of code as plain data (no GUI)."""

    def __init__(self, text=""):
        self.text = text
        self.display_value = None

    def get(self):
        return self.text

    def put(self, text):
        self.text = text

    def update(self, val):
        """Record a displayed variable value (headless stand-in for GUI)."""
        self.display_value = val

    def clear(self):
        self.display_value = None


class CodeColumn:
    """A list of code rows (no GUI)."""

    def __init__(self, simulator, lines=None, keep_blanks=False):
        self.p = simulator
        self.rows = []
        if lines is not None:
            self.add_rows(lines, keep_blanks=keep_blanks)

    def num_rows(self):
        return len(self.rows)

    def add_rows(self, block, keep_blanks=False):
        for line in block:
            if line or keep_blanks:
                self.add_row(line)

    def add_row(self, text=""):
        row = CodeRow(text)
        self.rows.append(row)
        return row

    def create_thread(self, name=None):
        return Thread(self, name=name)

    def next_row(self, row):
        if row is None:
            return self.rows[0] if self.rows else None

        index = self.rows.index(row)
        try:
            return self.rows[index + 1]
        except IndexError:
            return None


class Thread:
    """Represents simulated threads."""

    def __init__(self, column, name=None):
        self.column = column
        self.sync = column.p
        self.name, self.color = self.sync.get_name(name)
        self.namespace = Namespace()
        self.flag_map = {}
        self.while_stack = []
        self.sync.register(self)
        self.start()

    def __str__(self):
        return "<" + self.name + ">"

    def enqueue(self):
        """Puts this thread into queue."""
        self.queued = True
        self._gui_remove_from_runnable()
        self._gui_enqueue()

    def dequeue(self):
        """Removes this thread from queue."""
        self.queued = False
        self._gui_dequeue()
        self._gui_add_to_runnable()

    def jump_to(self, row):
        """Removes this thread from its current row and moves it to row."""
        if self.row:
            self._gui_remove_from_runnable()
        self.row = row
        if self.row:
            self._gui_add_to_runnable()

    def balk(self):
        if self.row:
            self._gui_remove_from_runnable()
        self.row = None

    def _gui_add_to_runnable(self):
        add = getattr(self.row, "add_thread", None)
        if add:
            add(self)

    def _gui_remove_from_runnable(self):
        remove = getattr(self.row, "remove_thread", None)
        if remove:
            remove(self)

    def _gui_enqueue(self):
        enqueue = getattr(self.row, "enqueue_thread", None)
        if enqueue:
            enqueue(self)

    def _gui_dequeue(self):
        dequeue = getattr(self.row, "dequeue_thread", None)
        if dequeue:
            dequeue(self)

    def start(self):
        """Moves this thread to the top of the column."""
        self.queued = False
        self.row = None
        self.next_loop()

    def next_loop(self):
        """Moves to the next row, looping to the top if necessary."""
        self.next_row()
        if self.row is None:
            self.start()

    def next_row(self):
        """Moves this thread to the next row in the column."""
        if self.queued:
            return

        row = self.column.next_row(self.row)
        self.jump_to(row)

    def skip_body(self):
        """Skips the body of a conditional."""
        source = self.row.get()
        head_indent = self.count_spaces(source)

        self.next_row()
        source = self.row.get()
        body_indent = self.count_spaces(source)

        indent = body_indent - head_indent

        if indent <= 0:
            raise SyntaxError("Body of compound statement must be indented.")

        while True:
            self.next_row()
            if self.row is None:
                break

            source = self.row.get()
            line_indent = self.count_spaces(source)
            if line_indent <= head_indent:
                break

    def count_spaces(self, source):
        """Returns the number of leading spaces after expanding tabs."""
        s = source.expandtabs(4)
        t = s.lstrip(" ")
        return len(s) - len(t)

    def step(self, event=None):
        """Executes the current line of code, then moves to the next row.

        The current limitation of this simulator is that each row
        has to contain a complete Python statement.  Also, each line
        of code is executed atomically.

        Args:
            event: unused, provided so that this method can be used
                   as a binding callback

        Returns:
            line of code that executed or None
        """
        if self.queued:
            return None

        if self.row is None:
            return None

        self.check_end_while()
        source = self.row.get()
        print(self, source)

        before = copy.copy(self.sync.locals)

        flag = self.exec_line(source, self.sync)

        # see if any variables were defined or changed
        after = self.sync.locals
        defined = subtract(after, before)

        for key in defined:
            self.sync.views[key] = self.row

        self.sync.update_views()

        # either skip to the next line or to the end of a false conditional
        if flag:
            self.next_row()
        else:
            self.skip_body()

        return source

    def exec_line(self, source, sync):
        """Runs a line of source code in the context of the given simulator.

        Args:
            source: source code from a Row
            sync: simulator object (Simulator or Sync)

        Returns:
            if the line is an if statement, returns the result of
            evaluating the condition
        """
        global CURRENT_THREAD
        CURRENT_THREAD = self

        sync.globals["self"] = self.namespace

        try:
            s = source.strip()
            code = compile(s, "<user-provided code>", "exec")
            exec(code, sync.globals, sync.locals)
            return True
        except SyntaxError as error:
            # check whether it's a conditional statement
            keyword = s.split()[0]
            if keyword in ["if", "else:", "while"]:
                flag = self.handle_conditional(keyword, source, sync)
                return flag
            else:
                raise error

    def handle_conditional(self, keyword, source, sync):
        """Evaluates the condition part of an if statement.

        Args:
            keyword: if, else or while
            source: source code from a Row
            sync: simulator object

        Returns:
            if the line is an if statement, returns the result of
            evaluating the condition; otherwise raises a SyntaxError
        """
        s = source.strip()
        if not s.endswith(":"):
            raise SyntaxError("Header must end with :")

        if keyword in ["if"]:
            # evaluate the condition
            n = len(keyword)
            condition = s[n:-1].strip()
            flag = eval(condition, sync.globals, sync.locals)

            # store the flag
            indent = self.count_spaces(source)
            self.flag_map[indent] = flag

            return flag

        elif keyword in ["while"]:
            # evaluate the condition
            n = len(keyword)
            condition = s[n:-1].strip()
            flag = eval(condition, sync.globals, sync.locals)

            if flag:
                indent = self.count_spaces(source)
                self.while_stack.append((indent, self.row))

            return flag

        else:
            assert keyword == "else:"
            # see whether the condition was true
            indent = self.count_spaces(source)
            try:
                flag = self.flag_map[indent]
                return not flag
            except KeyError:
                raise SyntaxError("else does not match if")

    def check_end_while(self):
        """Check if we are at the end of a while loop.

        If so, jump to the top.
        """
        if not self.while_stack:
            return

        indent, row = self.while_stack[-1]

        source = self.row.get()
        if self.count_spaces(source) <= indent:
            self.while_stack.pop()
            self.jump_to(row)

    def step_loop(self, event=None):
        self.step()
        if self.row is None:
            self.start()

    def run(self):
        while True:
            self.step()
            if self.row is None:
                break


class Simulator:
    """Headless thread simulator (no Tkinter)."""

    def __init__(self, filename=""):
        self.namer = Namer()
        self.locals = SIM_LOCALS
        self.globals = SIM_GLOBALS
        self.views = {}
        self.threads = []
        self.running = False
        self.delay = 0.2
        self.filename = filename
        self.blocks = []
        self.topcol = None
        self.cols = []

        if filename:
            self.read_file(filename)
            self.make_columns()
            self.run_init()
            for col in self.cols:
                col.create_thread()

    @classmethod
    def from_file(cls, filename):
        """Load a Sync source file and create one thread per column."""
        return cls(filename)

    def get_name(self, name=None):
        return self.namer.next(name)

    def get_threads(self):
        return self.threads

    def set_global(self, **kwds):
        self.globals.update(kwds)

    def get_global(self, attr):
        return self.globals[attr]

    def register(self, thread):
        """Adds a new thread."""
        self.threads.append(thread)

    def unregister(self, thread):
        """Removes a thread."""
        self.threads.remove(thread)

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

    def create_thread(self, column_index):
        """Create a thread in the given thread-code column."""
        return self.cols[column_index].create_thread()

    def read_file(self, filename):
        """Read a file that contains code for the simulator to execute."""
        self.filename = filename
        self.blocks = parse_sync_file(filename)

    def make_columns(self):
        """Build headless columns from self.blocks."""
        if not self.blocks:
            return

        self.topcol = CodeColumn(self, self.blocks[0])
        self.cols = []
        for block in self.blocks[1:]:
            self.cols.append(CodeColumn(self, block))

    def run_init(self):
        """Runs the initialization code in the top column."""
        if self.topcol is None or not self.topcol.num_rows():
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

    def get_state(self):
        """Return a JSON-friendly snapshot of the simulator for UIs/tests."""
        return snapshot_state(self)


def _is_json_primitive(value):
    return value is None or isinstance(value, (bool, int, float, str))


def _jsonable_value(value):
    """Convert a shared/local value to something JSON can represent."""
    if _is_json_primitive(value):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable_value(v) for k, v in value.items()}
    # Semaphores and other engine objects are handled elsewhere or stringified.
    return str(value)


def _namespace_locals(namespace):
    data = {}
    for key, value in vars(namespace).items():
        if key.startswith("_"):
            continue
        if isinstance(value, (Semaphore, Lightswitch, Namespace)):
            continue
        if callable(value):
            continue
        data[key] = _jsonable_value(value)
    return data


def snapshot_state(sim):
    """Build a serializable state dict from a Simulator (or Sync-like object).

    Schema (Task 2):
      init: list[str]
      columns: list[list[str]]
      threads: list[{name, column, row, row_text, blocked, waiting_on, color, locals}]
      semaphores: {name: {value, queue, fifo}}
      variables: {name: jsonable}  # non-semaphore shared locals
      views: {name: init_row_index|null}
      filename: str|null
    """
    waiting_on = {}
    semaphores = {}
    variables = {}

    for key, value in sim.locals.items():
        if isinstance(value, Semaphore):
            semaphores[key] = {
                "value": value.n,
                "queue": [thread.name for thread in value.queue],
                "fifo": isinstance(value, FifoSemaphore),
            }
            for thread in value.queue:
                waiting_on[thread.name] = key
        elif isinstance(value, Lightswitch):
            variables[key] = {
                "type": "Lightswitch",
                "counter": value.counter,
            }
        elif callable(value):
            continue
        elif isinstance(value, type):
            continue
        else:
            variables[key] = _jsonable_value(value)

    col_index = {id(col): i for i, col in enumerate(sim.cols)}

    threads = []
    for thread in sim.threads:
        column = thread.column
        if column is getattr(sim, "topcol", None):
            column_index = None
        else:
            column_index = col_index.get(id(column))

        row_index = None
        row_text = None
        if thread.row is not None and column is not None:
            try:
                row_index = column.rows.index(thread.row)
            except ValueError:
                row_index = None
            row_text = thread.row.get()

        threads.append(
            {
                "name": thread.name,
                "column": column_index,
                "row": row_index,
                "row_text": row_text,
                "blocked": bool(thread.queued),
                "waiting_on": waiting_on.get(thread.name),
                "color": thread.color,
                "locals": _namespace_locals(thread.namespace),
            }
        )

    init = []
    if getattr(sim, "topcol", None) is not None:
        init = [row.get() for row in sim.topcol.rows]

    columns = [[row.get() for row in col.rows] for col in sim.cols]

    views = {}
    top_rows = getattr(getattr(sim, "topcol", None), "rows", [])
    for key, row in getattr(sim, "views", {}).items():
        try:
            views[key] = top_rows.index(row)
        except ValueError:
            views[key] = None

    return {
        "filename": getattr(sim, "filename", None) or None,
        "init": init,
        "columns": columns,
        "threads": threads,
        "semaphores": semaphores,
        "variables": variables,
        "views": views,
    }
