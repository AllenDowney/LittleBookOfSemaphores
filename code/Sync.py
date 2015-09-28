"""This module is part of Swampy, a suite of programs available from
allendowney.com/swampy.

Copyright 2011 Allen B. Downey
Distributed under the GNU General Public License at gnu.org/licenses/gpl.html.
"""

from __future__ import print_function, division

import optparse
import os
import copy
import random
import sys
import string
import time

# the following definitions can be accessed in the simulator

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


# make globals and locals for the simulator

SIM_GLOBALS = copy.copy(globals())
SIM_LOCALS = dict()

# anything defined after this point is not available inside the simulator

try:
    from tkinter import N, S, E, W, TOP, BOTTOM, LEFT, RIGHT, END
except ImportError:
    from Tkinter import N, S, E, W, TOP, BOTTOM, LEFT, RIGHT, END

from Gui import Gui, GuiCanvas


ALL_THREAD_NAMES = string.ascii_uppercase + string.ascii_lowercase

COURIER = ("Courier", 12)
FSU = 9                     # FSU, the fundamental Sync unit,
                            # determines the size of most things.

class Sync(Gui):
    """Represents the thread simulator."""

    def __init__(self, args=['']):
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
        parser.add_option('-w', '--write', dest='write',
                          action='store_true', default=False,
                          help='Write thread code in code subdirectory?')
        parser.add_option('-s', '--side', dest='initside',
                          action='store_true', default=False,
                          help='Move the initialization code to the left side?')

        (self.options, args) = parser.parse_args(args)

        if args:
            self.filename = args[0]
        else:
            self.filename = ''

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
        self.bu(side=RIGHT, text='Add\ncolumn', command=self.add_col)
        self.endfr()
        self.buttons()

    def buttons(self):
        """Makes the buttons."""
        self.row([1, 1, 1, 1, 1])
        self.bu(text='Run', command=self.run)
        self.bu(text='Random Run', command=self.random_run)
        self.bu(text='Stop', command=self.stop)
        self.bu(text='Step', command=self.step)
        self.bu(text='Random Step', command=self.random_step)
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
            print('There are currently no threads that can run.')
            return
        thread = random.choice(threads)
        thread.step_loop()

    def stop(self):
        """Stops running."""
        self.running = False

    def read_file(self, filename):
        """Read a file that contains code for the simulator to execute.

        Lines that start with ## do not appear
        in the display.

        A line that starts with "## thread" indicates the beginning of
        a new column of code.

        Returns a list of blocks where each block is a list of lines.
        """
        def is_new_thread(line):
            if line[0:2] != '##':
                return False

            words = line.strip('#').split()
            word = words[0].lower()
            return word == 'thread'

        self.blocks = []
        block = []
        self.blocks.append(block)

        fp = open(filename)
        for line in fp:
            line = line.rstrip()

            if is_new_thread(line):
                block = []
                self.blocks.append(block)
            else:
                block.append(line)

        fp.close()

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

    def write_files(self, filename, dirname='book_code'):
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
            self.write_file(block, dest, i+1)

    def write_file(self, block, filename, suffix=0):
        trim_block(block)

        name = '%s.%s' % (filename, str(suffix))
        fp = open(name, 'w')
        for line in block:
            fp.write(line + '\n')
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

        print('running init')
        self.clear_views()
        self.views = {}

        thread = Thread(self.topcol, name='0')
        while True:
            thread.step()
            if thread.row == None:
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
    if block and block[0].startswith('#'):
        block.pop(0)

    while block and not block[-1].strip():
        block.pop(-1)

    
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
    def setup(self, text=''):
        self.tag = None
        self.fr = self.w.row([0, 0, 1])
        self.queued = self.w.qu(side=LEFT, n=3)
        self.runnable = self.w.qu(side=LEFT, n=3, label='Run')
        self.en = self.w.en(side=LEFT, font=COURIER)
        self.en.bind('<Key>', self.keystroke)
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
        width = self.en.cget('width')
        l = len(text) + 2
        if l > width:
            self.en.configure(width=l)

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
    def setup(self, text=''):
        Row.setup(self, text)
        self.queued.destroy()
        self.runnable.delete('all')


class Column(Widget):
    """A list of rows and a few buttons."""
    def setup(self, side=TOP, n=0, row_factory=Row):
        self.fr = self.w.fr(side=side, bd=3)
        self.row_factory = row_factory
        self.rows = [self.row_factory(self) for i in range(n)]

        self.buttons = self.w.row([1, 1], side=BOTTOM)
        self.bu1 = self.w.bu(text='Create thread',
                                 command=self.create_thread)
        self.bu2 = self.w.bu(text='Add row',
                             command=self.add_row)
        self.w.endrow()
        self.w.endfr()

    def num_rows(self):
        return len(self.rows)

    def add_rows(self, block, keep_blanks=False):
        for line in block:
            if line or keep_blanks:
                self.add_row(line)

    def add_row(self, text=''):
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
            return self.rows[index+1]
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
        self.bu1.configure(text='Run initialization',
                                 command=self.p.run_init)

class QueueCanvas(GuiCanvas):
    """Displays the runnable and queued threads."""
    def __init__(self, w, n=1, label='Queue'):
        self.n = n
        self.label = label
        width = 2 * n * FSU
        height = 3 * FSU
        GuiCanvas.__init__(self, w, width=width, height=height,
                           transforms=[])
        self.threads = []
        self.setup()
        
    def setup(self):
        self.text([3, 15], self.label, font=COURIER, anchor=W, fill='white')
        
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
            x += 1.5*r
            if x > self.get_width():
                x = FSU
                y += 1.5*r
        
    def undraw_queue(self):
        for thread in self.threads:
            self.delete(thread.tag)

    def draw_thread(self, thread, x=FSU, y=FSU, r=0.9*FSU):
        thread.tag = 'Thread' + thread.name
        self.circle([x, y], r, fill=thread.color, tags=thread.tag)
        font = ('Courier', int(r+3))
        self.text([x, y], thread.name, font=font, tags=thread.tag)
        self.tag_bind(thread.tag, '<Button-1>', thread.step_loop)

    def undraw_thread(self, thread):
        self.delete(thread.tag)

    def display_text(self, text):
        """Displays text on this canvas.

        text: string
        """
        tag = self.text([15, 15], text, font=COURIER)
        return tag


class Namer(object):
    def __init__(self):
        self.names = ALL_THREAD_NAMES
        self.next_name = 0
        self.colors = ['red', 'orange', 'yellow', 'greenyellow',
                  'green', 'mediumseagreen', 'skyblue',
                  'violet', 'magenta']
        self.next_color = 0

    def next(self, name=None):
        if name == None:
            name = self.names[self.next_name]
            self.next_name += 1
            self.next_name %= len(self.names)

            color = self.colors[self.next_color]
            self.next_color += 1
            self.next_color %= len(self.colors)
            return name, color
        else:
            return name, 'white'
        

class Namespace:
    """Used to store thread-local variables.

    Inside the simulator, self refers to the thread's namespace.
    """


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
        return '<' + self.name + '>'

    def enqueue(self):
        """Puts this thread into queue."""
        self.queued = True
        self.row.remove_thread(self)
        self.row.enqueue_thread(self)

    def dequeue(self):
        """Removes this thread from queue."""
        self.queued = False
        self.row.dequeue_thread(self)
        self.row.add_thread(self)

    def jump_to(self, row):
        """Removes this thread from its current row and moves it to row."""
        if self.row:
            self.row.remove_thread(self)
        self.row = row
        if self.row:
            self.row.add_thread(self)

    def balk(self):
        self.row.remove_thread(self)
        self.row = None

    def start(self):
        """Moves this thread to the top of the column."""
        self.queued = False
        self.row = None
        self.next_loop()

    def next_loop(self):
        """Moves to the next row, looping to the top if necessary."""
        self.next_row()
        if self.row == None:
            self.start()

    def next_row(self):
        """Moves this thread to the next row in the column."""
        if self.queued:
            return

        row = self.column.next_row(self.row)
        self.jump_to(row)

    def skip_body(self):
        """Skips the body of a conditional."""
        # get the current line
        # get the next line
        # compute the change in indent
        # find the outdent
        source = self.row.get()
        head_indent = self.count_spaces(source)

        self.next_row()
        source = self.row.get()
        body_indent = self.count_spaces(source)

        indent = body_indent - head_indent

        if indent <= 0:
            raise SyntaxError('Body of compound statement must be indented.')

        while True:
            self.next_row()
            if self.row == None:
                break

            source = self.row.get()
            line_indent = self.count_spaces(source)
            if line_indent <= head_indent:
                break
            

    def count_spaces(self, source):
        """Returns the number of leading spaces after expanding tabs."""
        s = source.expandtabs(4)
        t = s.lstrip(' ')
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

        if self.row == None:
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
        """Runs a line of source code in the context of the given Sync.

        Args:
            source: source code from a Row
            sync: Sync object

        Returns:
            if the line is an if statement, returns the result of
            evaluating the condition
        """
        global CURRENT_THREAD 
        CURRENT_THREAD = self

        sync.globals['self'] = self.namespace

        try:
            s = source.strip()
            code = compile(s, '<user-provided code>', 'exec')
            exec(code, sync.globals, sync.locals)
            return True
        except SyntaxError as error:
            # check whether it's a conditional statement
            keyword = s.split()[0]
            if keyword in ['if', 'else:', 'while']:
                flag = self.handle_conditional(keyword, source, sync)
                return flag
            else:
                raise error

    def handle_conditional(self, keyword, source, sync):
        """Evaluates the condition part of an if statement.

        Args:
            keyword: if, else or while
            source: source code from a Row
            sync: Sync object

        Returns:
            if the line is an if statement, returns the result of
            evaluating the condition; otherwise raises a SyntaxError
        """
        s = source.strip()
        if not s.endswith(':'):
            raise SyntaxError('Header must end with :')

        if keyword in ['if']:
            # evaluate the condition
            n = len(keyword)
            condition = s[n:-1].strip()
            flag = eval(condition, sync.globals, sync.locals)

            # store the flag
            indent = self.count_spaces(source)
            self.flag_map[indent] = flag

            return flag

        elif keyword in ['while']:
            # evaluate the condition
            n = len(keyword)
            condition = s[n:-1].strip()
            flag = eval(condition, sync.globals, sync.locals)

            if flag:
                indent = self.count_spaces(source)
                self.while_stack.append((indent, self.row))

            return flag

        else:
            assert keyword == 'else:'
            # see whether the condition was true
            indent = self.count_spaces(source)
            try:
                flag = self.flag_map[indent]
                return not flag
            except KeyError:
                raise SyntaxError('else does not match if')

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
        if self.row == None:
            self.start()
        
    def run(self):
        while True:
            self.step()
            if self.row == None: break


def main():
    sync = Sync(sys.argv[1:])
    sync.mainloop()


if __name__ == '__main__':
    main()
