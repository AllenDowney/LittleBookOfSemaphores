# This module is part of Swampy, a suite of programs available from
# allendowney.com/swampy.

# Copyright 2005 Allen B. Downey
# Distributed under the GNU General Public License at gnu.org/licenses/gpl.html.

from __future__ import print_function, division

"""

Wrapper classes for use with tkinter.

This module provides the following classes:

Gui: a sublass of Tk that provides wrappers for most of the
widget-creating methods from Tk.  The advantage of these wrappers is
that they use Python's optional argument capability to provide
appropriate default values, and that they combine widget creation and
packing into a single step.  They also eliminate the need to name the
parent widget explicitly by keeping track of a current frame and
packing new objects into it.

GuiCanvas: a subclass of Canvas that provides wrappers for most of the
item-creating methods from Canvas.  The advantage of the wrappers
is, again, that they use optional arguments to provide appropriate
defaults, and that they perform coordinate transformations.

Transform: an abstract class that provides basic methods inherited
by CanvasTransform and the other transforms.

CanvasTransform: a transformation that maps standard Cartesian
coordinates onto the 'graphics' coordinates used by Canvas objects.

Callable: the standard recipe from Python Cookbook for encapsulating
a function and its arguments in an object that can be used as a
callback.

The most important idea in this module is using a stack of frames to
avoid keeping track of parent widgets explicitly.


    WIDGET WRAPPERS:

    The Gui class contains wrappers for the widgets in tkinter.
    All of the wrappers invoke widget() to create and pack the new widget.

    The first four positional
    arguments determine how the widget is packed.  Some widgets
    take additional positional arguments.  In most cases, the
    keyword arguments are passed as options to the widget
    constructor.

    Widgets that use these defaults can just pass along
    args and options unmolested.  Widgets (like fr and en)
    that want different defaults have to roll the arguments
    in with the other options and then underride them
    (underride means set only if not already set).

    ITEM WRAPPERS:

    GuiCanvas provides wrappers for the canvas item methods.

"""

import math
import sys

try:
    import tkinter
    import tkinter.font as tkFont

    from tkinter import N, S, E, W
    from tkinter import TOP, BOTTOM, LEFT, RIGHT, END, ALL
except ImportError:
    import Tkinter as tkinter
    import tkFont

    from Tkinter import N, S, E, W
    from Tkinter import TOP, BOTTOM, LEFT, RIGHT, END, ALL



class Gui(tkinter.Tk):
    """Provides wrappers for many of the methods in the Tk class.

    Keeps track of the current frame so that
    you can create new widgets without naming the parent frame
    explicitly.
    """

    def __init__(self, debug=False):
        """Initializes the gui.

        Turning on debugging changes the behavior of Gui.fr so
        that the nested frame structure is apparent.

        Attributes:
        debug: is a boolean that makes Frames visible if True.
        frame: is the current Frame.
        frames: is the stack of pending Frames.
        """
        tkinter.Tk.__init__(self)
        self.debug = debug
        self.frame = self
        self.frames = []
        self.i = None
        self.j = None

    def pushfr(self, frame):
        """Pushes a frame onto the frame stack."""
        self.frames.append(self.frame)
        self.frame = frame

    def endfr(self):
        """Ends the current frame (and returns the new current frame)."""
        self.frame = self.frames.pop()
        return self.frame

    """Synonyms for endfr."""
    popfr = endfr
    endgr = endfr
    endrow = endfr
    endcol = endfr

    def tl(self, **options):
        """Makes and returns a top level window."""
        return tkinter.Toplevel(**options)

    def fr(self, *args, **options):
        """Makes and returns a frame.

        The new frame becomes the current frame.
        By default, frames use the pack geometry manager, unless
        self.gridding=True.
        """
        if self.debug:
            override(options, bd=5, relief=tkinter.RIDGE)

        # create the new frame and push it onto the stack
        frame = self.widget(tkinter.Frame, *args, **options)
        self.pushfr(frame)
        return frame

    def row(self, weights=None, **options):
        """Makes a frame that lays out widgets in a single row."""
        weights = weights if weights is not None else []
        return self.gr(10000, weights, [1], **options)

    def col(self, weights=None, **options):
        """Makes a frame that lays out widgets in a single column."""
        weights = weights if weights is not None else []
        return self.gr(1, [1], weights, **options)

    def gr(self, cols, cweights=None, rweights=None, **options):
        """Makes a frame and switches to grid mode.

        (cols) is the number of columns in the grid.

        (cweights) and (rweights) control how the widgets expand
        if the frame expands (see colweights
        and rowweights below).  By default, the first 8 rows and
        columns are set to expand.

        (options) is a dictionary that is underridden and passed along.
        """
        fr = self.fr(**options)
        fr.gridding = True
        fr.cols = cols
        fr.i = 0
        fr.j = 0
        fr.cweights = cweights if cweights is not None else []
        fr.rweights = rweights if rweights is not None else []
        self.colweights(fr.cweights)
        self.rowweights(fr.rweights)
        return fr

    def colweights(self, weights):
        """Attaches weights to the columns of the current grid.

        Args:
        weights: list of values, assigned to columns starting with 0.
        
        These weights control how the columns in the grid expand
        when the grid expands.  The default weight is 0, which
        means that the column doesn't expand.  If only one
        column has a value, it gets all the extra space.
        """
        for i, weight in enumerate(weights):
            self.frame.columnconfigure(i, weight=weight)

    def rowweights(self, weights):
        """Attaches weights to the rows of the current grid.

        Args:
        weights: is a list of values, which are assigned to
        rows starting with 0.
        
        These weights control how the rows in the grid expand
        when the grid expands.  The default weight is 0, which
        means that the row doesn't expand.  If only one
        row has a value, it gets all the extra space.
        """
        for i, weight in enumerate(weights):
            self.frame.rowconfigure(i, weight=weight)

    def colweight(self, i, weight):
        """Assigns (weight) to column (i)."""
        self.frame.columnconfigure(i, weight=weight)

    def rowweight(self, i, weight):
        """Assigns (weight) to row (i)."""
        self.frame.rowconfigure(i, weight=weight)

    def grid(self, widget, i=None, j=None, **options):
        """Packs the given widget in the current grid.

        By default, the widget is packed in the next available
        space, but parameters i and j can specify the row
        and column explicitly.
        """
        i = i if i is not None else self.frame.i
        j = j if j is not None else self.frame.j
        widget.grid(row=i, column=j, **options)

        # increment j by 1, or by columnspan
        # if the widget spans more than one column.
        incr = options.get('columnspan', 1)
        self.frame.j += incr

        # if the user didn't specify row or column weights,
        # fill them in with ones as we go along
        if self.frame.cweights == []:
            self.colweight(j, 1)

        if self.frame.j == self.frame.cols:
            self.frame.j = 0
            self.frame.i += 1
            if self.frame.rweights == []:
                self.rowweight(i, 1)

    def en(self, **options):
        """Makes an entry widget."""

        # pull the text option out
        text = options.pop('text', '')

        # create the entry and insert the text
        en = self.widget(tkinter.Entry, **options)
        en.insert(0, text)
        return en

    def ca(self, width=100, height=100, **options):
        """Makes a canvas widget."""
        return self.widget(GuiCanvas, width=width, height=height, **options)

    def la(self, text='', **options):
        """Makes a label widget."""
        return self.widget(tkinter.Label, text=text, **options)

    def lb(self, **options):
        """Makes a listbox."""
        return self.widget(tkinter.Listbox, **options)

    def bu(self, text='', command=None, **options):
        """Makes a button"""
        return self.widget(tkinter.Button, text=text, command=command, 
                           **options)

    def mb(self, **options):
        """Makes a menubutton"""
        underride(options, relief=tkinter.RAISED)
        mb = self.widget(tkinter.Menubutton, **options)
        mb.menu = tkinter.Menu(mb, tearoff=False)
        mb['menu'] = mb.menu
        return mb

    def mi(self, mb, text='', **options):
        """Makes a menu item"""
        mb.menu.add_command(label=text, **options)        

    def te(self, **options):
        """Makes a text entry"""
        return self.widget(tkinter.Text, **options)

    def sb(self, **options):
        """Makes a text scrollbar"""
        return self.widget(tkinter.Scrollbar, **options)

    def cb(self, **options):
        """Makes a checkbutton."""
        
        # if the user didn't provide a variable, create one
        try:
            var = options['variable']
        except KeyError:
            var = tkinter.IntVar()
            override(options, variable=var)
            
        w = self.widget(tkinter.Checkbutton, **options)
        w.swampy_var = var
        return w

    def rb(self, **options):
        """Makes a radiobutton"""

        w = self.widget(tkinter.Radiobutton, **options)
        w.swampy_var = options['variable']
        w.swampy_val = options['value']
        return w

    class ScrollableText(object):
        """A frame with a text entry and a scrollbar."""
        def __init__(self, gui, **options):
            self.frame = gui.row(**options)
            self.text = gui.te(wrap=tkinter.WORD)
            self.scrollbar = gui.sb(command=self.text.yview)
            self.text.configure(yscrollcommand=self.scrollbar.set)
            gui.endrow()

    def st(self, **options):
        """Makes a scrollable text entry."""
        return Gui.ScrollableText(self, **options)

    class ScrollableCanvas(object):
        """A grid with a canvas and two scrollbars."""
        def __init__(self, gui, width=200, height=200, **options):
            self.grid = gui.gr(2, **options)
            self.canvas = gui.ca(width=width, height=height, bg='white')

            self.yb = gui.sb(command=self.canvas.yview, sticky=N+S)
            self.xb = gui.sb(command=self.canvas.xview, 
                             orient=tkinter.HORIZONTAL,
                             sticky=E+W)

            self.canvas.configure(xscrollcommand=self.xb.set,
                                  yscrollcommand=self.yb.set,
                                  scrollregion=(0, 0, 400, 400))
            gui.endgr()

    def sc(self, **options):
        """Makes a scrollable canvas.

        The options provided  apply to the frame only;
        if you want to configure the other widgets, you have to do
        it after invoking st.
        """
        return Gui.ScrollableCanvas(self, **options)

    def widget(self, constructor, **options):
        """Makes a widget of the given type.

        options is split into widget options, pack options and grid options.

        Args:
            constructor: function called to build the new widget.
            options: option dictionary 

        Returns:
            new widget
        """
        underride(options, fill=tkinter.BOTH, expand=1, sticky=N+S+E+W)

        # roll the positional arguments into the option dictionary,
        # then divide into options for the widget constructor, pack
        # or grid
        widopt, packopt, gridopt = split_options(options)

        # Makes the widget and either pack or grid it
        widget = constructor(self.frame, **widopt)
        if hasattr(self.frame, 'gridding'):
            self.grid(widget, **gridopt)
        else:
            widget.pack(**packopt)
        return widget


def pop_options(options, names):
    """Remove the given keys from options.

    Return a new dictionary with those key-value pairs.

    Args:
        options: dictionary
        names: list of keys.
    
    Returns:
        dict
    """
    new = {}
    for name in names:
        if name in options:
            new[name] = options.pop(name)
    return new


def get_options(options, names):
    """Returns a dictionary with options for the given keys.

    Args:
        options: dict
        names: list of keys

    Returns:
        dict
    """
    new = {}
    for name in names:
        if name in options:
            new[name] = options[name]
    return new


def remove_options(options, names):
    """Removes options from the dictionary.

    Modifies options.

    Args:
        options: dict
        names: list of keys
    """
    for name in names:
        if name in options:
            del options[name]

def split_options(options):
    """Splits an options dictionary into into pack options and grid options.

    Anything left is assumed to be a widget option

    Args:
        options: dict

    Returns: tuple of (widget options, pack options, grid options)
    """
    
    packnames = ['side', 'fill', 'expand', 'anchor',
                 'padx', 'pady', 'ipadx', 'ipady']
    gridnames = ['column', 'columnspan', 'row', 'rowspan',
                 'padx', 'pady', 'ipadx', 'ipady', 'sticky']

    # some options appear in both packopts
    # and gridopts, so that's why I didn't use pop_options.
    packopts = get_options(options, packnames)
    gridopts = get_options(options, gridnames)

    widgetopts = dict(options)
    remove_options(widgetopts, packopts)
    remove_options(widgetopts, gridopts)

    return widgetopts, packopts, gridopts


def underride(d, **kwds):
    """Adds entries from (kwds) to (d) only if they are not already set."""
    for key, val in kwds.items():
        d.setdefault(key, val)


def override(d, **kwds):
    """Adds entries from (kwds) to (d) even if they are already set."""
    d.update(kwds)



class BBox(list):
    """List of coordinates, where each coordinate is a pair or a Point.

    The first coordinate is the upper-left corner; the second pair is
    the lower-right.

    Assumes pixel coordinates; that is, a higher y-value is lower.

    Creating a new bounding box makes a _shallow_ copy of
    the list of coordinates.  For a deep copy, use Bbox.copy().
    """
    __slots__ = ()

    def copy(self):
        t = [Point(coord) for coord in self]
        return BBox(t)

    # top, bottom, left, and right can be accessed as attributes
    def setleft(self, val): self[0][0] = val 
    def settop(self, val): self[0][1] = val 
    def setright(self, val): self[1][0] = val 
    def setbottom(self, val): self[1][1] = val 
    
    left = property(lambda self: self[0][0], setleft)
    top = property(lambda self: self[0][1], settop)
    right = property(lambda self: self[1][0], setright)
    bottom = property(lambda self: self[1][1], setbottom)

    def width(self):
        """Returns the width of the bbox."""
        return self.right - self.left
    
    def height(self):
        """Returns the height of the bbox."""
        return self.bottom - self.top

    def upperleft(self):
        """Returns the first corner of the bbox.

        Usually the upper left
        """
        return Point(self[0])
    
    def lowerright(self):
        """Returns the second corner of the bbox.

        Usually the lower right
        """
        return Point(self[1])

    def midright(self):
        """Returns the midpoint of the right edge as a Point object."""
        x = self.right
        y = (self.top + self.bottom) / 2.0
        return Point([x, y])

    def midleft(self):
        """Returns the midpoint of the left edge as a Point object."""
        x = self.left
        y = (self.top + self.bottom) / 2.0
        return Point([x, y])

    def center(self):
        """Returns the midpoint of the bbox as a Point object."""
        x = (self.left + self.right) / 2.0
        y = (self.top + self.bottom) / 2.0
        return Point([x, y])
        
    def union(self, other):
        """Returns a new bbox that covers self and other.
        
        Assumes that the positive y direction is UP.
        """
        left = min(self.left, other.left)
        right = max(self.right, other.right)
        top = max(self.top, other.top)
        bottom = min(self.bottom, other.bottom)
        return BBox([[left, top], [right, bottom]])

    def offset(self, pos):
        """Returns the vector between the upper-left corner of self and pos.

        Args:
            pos: Point object or coordinate tuple.

        Returns:
            Point
        """
        return Point([pos[0]-self.left, pos[1]-self.top])

    def pos(self, offset):
        """Returns the position at the given offset from the upper-left"""
        return Point([offset[0]+self.left, offset[1]+self.top])

    def flatten(self):
        """Returns a list of four coordinates."""
        return self[0] + self[1]


class Point(list):
    """A list of coordinates.

    Because Point inherits __init__ from list, it makes a copy
    of the argument to the constructor.
    """
    # TODO: replace this with a namedtuple
    __slots__ = ()

    copy = lambda pos: Point(pos)

    # x and y can be accessed as attributes
    def setx(pos, val): pos[0] = val 
    def sety(pos, val): pos[1] = val 
    
    x = property(lambda pos: pos[0], setx)
    y = property(lambda pos: pos[1], sety)


# pairiter, pair and flatten are utilities for dealing with
# lists of coordinates

def pairiter(seq):
    """Returns an iterator that yields consecutive pairs from seq."""
    it = iter(seq)
    while True:
        yield [next(it), next(it)]

def pair(seq):
    """Returns a list of consecutive pairs from seq."""
    return [x for x in pairiter(seq)]

def flatten(seq):
    """Concatenates the elements of seq.

    Given a list of lists, returns a new list that concatentes
    the elements of (seq).  This just does one level of flattening;
    it is not recursive.
    """
    return sum(seq, [])


class GuiCanvas(tkinter.Canvas):
    """A wrapper for the Canvas provided by Tkinter.

    The primary difference is that it supports coordinate
    transformations, the most common of which is the CanvasTranform,
    which makes canvas coordinates Cartesian (origin in the middle,
    positive y axis going up).

    It also provides methods like circle that provide a
    nice interface to the underlying canvas methods.

    The item-creating methods all return Item objects (as opposed
    to Tkinter tags) so you can perform subsequent operations by
    invoking methods on the Items, rather than the Canvas.
    """
    def __init__(self, w, scale=None, transforms=None, **options):
        tkinter.Canvas.__init__(self, w, **options)
        if transforms != None:
            self.transforms = transforms
        else:
            scale = scale if scale is not None else [1, 1]
            self.transforms = [CanvasTransform(self, scale)]

    def get_width(self):
        """Gets the nominal width of this canvas."""
        x = int(self.cget('width'))
        
        # winfo would return the actual width
        # x = self.winfo_width()
        return x

    def get_height(self):
        """Gets the nominal height of this canvas."""
        x = int(self.cget('height'))

        # winfo would return the actual height
        # x = self.winfo_height()
        return x

    # width and height are available as read-only attributes.
    width = property(get_width)
    height = property(get_height)

    def clear_transforms(self):
        """Removes all existing transforms."""
        self.transforms = []

    def add_transform(self, transform, index=None):
        """Add a transform.

        Args:
            transform: Transform object
            index: where in the list to insert it; appending is the default.
        """
        if index == None:
            self.transforms.append(transform)
        else:
            self.transforms.insert(index, transform)            
            
    def trans(self, coords):
        """Applies each of the transforms for this canvas, in order."""
        for trans in self.transforms:
            coords = trans.trans_list(coords)
        return coords

    def invert(self, coords):
        """Applies the inverse of each transforms, in reverse order."""
        t = self.transforms[::-1]
        for trans in t:
            coords = trans.invert_list(coords)
        return coords

    def canvas_coords(self, coords):
        """Convert a position from pixel coordinates to Canvas coordinates.

        Args:
            coords: Point object or list of coordinates.
        """
        return self.invert(coords)
        
    def canvas_itemcoords(self, item, coords=None):
        """Gets and sets item coordinates, with translation.

        Args:
            item: tag of a canvas item
            coords: Point object or list of coordinates
        """
        if coords != None:
            # set coords
            coords = self.trans(coords)
            coords = flatten(coords)
            tkinter.Canvas.coords(self, item, *coords)
        else:
            #get the coordinates and invert them
            coords = tkinter.Canvas.coords(self, item)
            coords = pair(coords)
            coords = self.invert(coords)
            return coords

    def translate_event(self, event):
        """Translates event strings into a canonical form.

        Args:
            event: Tkinter event string

        Returns:
            Tkinter event string
        """
        translator = {}
        for i in ['1', '2', '3']:
            translator['<Press-'+i+'>'] = '<ButtonPress-' + i + '>'
            translator['<Motion-'+i+'>'] = '<B' + i + '-Motion>'
            translator['<Release-'+i+'>'] = '<ButtonRelease-' + i + '>'
            translator['<Double-'+i+'>'] = '<Double-Button-' + i + '>'
        
        return translator.get(event, event)

    def clear(self):
        """Deletes all items on the canvas."""
        self.delete('all')

    def bbox(self, item):
        """Compute the bounding box of the given item.

        Transforms from pixel coordinates to canvas coordinates.

        Args:
            item: tag of a canvas item

        Returns:
            Bbox object in canvas coordinates.
        """
        if isinstance(item, list):
            item = item[0]

        # call the super
        bbox = tkinter.Canvas.bbox(self, item)

        if bbox == None:
            return bbox

        bbox = pair(bbox)
        bbox = self.invert(bbox)
        return BBox(bbox)

    def scroll_config(self, tag=tkinter.ALL):
        """Configure the canvas so the scroll region covers the given tag."""
        bbox = tkinter.Canvas.bbox(self, tag)
        self.configure(scrollregion=bbox)

    def move(self, item, dx, dy, transform=False):
        """Moves an item on the canvas.

        Args:
            item: string tag of a canvas item
            dx: distance to move on the x axis
            dy: distance to move on the y axis
            transform: boolean, whether to transform dx, dy
        """
        if transform:
            coords = [[0, 0], [dx, dy]]
            p1, p2 = self.trans(coords)
            dx = p2.x - p1.x
            dy = p2.y - p1.y
        tkinter.Canvas.move(self, item, dx, dy)
        

    # the following are wrappers for the item creation methods
    # inherited from the Canvas class.

    def arc(self, coords, start=0, extent=90, fill='', **options):
        """Makes an arc item.

        with bounding box (coords), sweeping out angle
        (extent) starting at (start) both in degrees.
        """
        tag = self.create_arc(self.trans(coords), options,
                                start=start, extent=extent, fill=fill)
        return Item(self, tag)

    def bitmap(self, coord, bitmap, **options):
        """Makes a bitmap item.

        with the given bitmap at the given position.
        The default anchor is center.
        """
        tag = self.create_bitmap(self.trans([coord]), options, bitmap=bitmap)
        return Item(self, tag)

    def image(self, coord, image, **options):
        """Makes an image item.

        with the given image at the given position.
        The default anchor is center.
        """
        tag = self.create_image(self.trans([coord]), options, image=image)
        return Item(self, tag)

    def line(self, coords, fill='black', **options):
        """Makes a polyline.

        with vertices at each point in (coords)
        and pen color (fill).
        """
        tag = self.create_line(self.trans(coords), options, fill=fill)
        return Item(self, tag)

    def oval(self, coords, fill='', **options):
        """Makes an oval.

        with bounding box (coords) and fill color (fill)
        """
        tag = self.create_oval(self.trans(coords), options, fill=fill)
        return Item(self, tag)

    def circle(self, coord, r, fill='', **options):
        """Makes a circle.

        with center at (x, y) and radius (r)
        """
        x, y = coord
        coords = self.trans([[x-r, y-r], [x+r, y+r]])
        tag = self.create_oval(coords, options, fill=fill)
        return Item(self, tag)
    
    def polygon(self, coords, fill='', **options):
        """Makes a closed polygon.

        with vertices at each point in (coords)
        and fill color (fill).
        """
        tag = self.create_polygon(self.trans(coords), options, fill=fill)
        return Item(self, tag)

    def rectangle(self, coords, fill='', **options):
        """Makes an oval.

        with bounding box (coords) and fill color (fill)
        """
        tag = self.create_rectangle(self.trans(coords), options, fill=fill)
        return Item(self, tag)
    
    def text(self, coord, text='', fill='black', **options):
        """Makes a text item.

        with the given text and fill color.
        The default anchor is center.
        """
        tag = self.create_text(self.trans([coord]), options,
                               text=text, fill=fill)
        return Item(self, tag)

    def window(self, coord, widget, **options):
        """Embeds a window (widget) in the canvas at the given coord."""
        tag = self.create_text(self.trans([coord]), options, window=widget)
        return Item(self, tag)

    def dump(self, filename='canvas.eps'):
        """Create a PostScipt file and dumps the contents of the canvas."""
        bbox = tkinter.Canvas.bbox(self, ALL)
        if bbox:
            x, y, width, height = bbox
        else:
            x, y, width, height = 0, 0, 100, 100
            
        width -= x
        height -= y
        ps = self.postscript(x=x, y=y, width=width, height=height)
        fp = open(filename, 'w')
        fp.write(ps)
        fp.close()


class Item(object):
    """Represents a canvas item.

    When you create a canvas item, Tkinter returns an integer 'tag'
    that identifies the new item.  To perform an operation on the
    item, you invoke a method on the canvas and pass the tag as
    a parameter.

    The Item class makes this interface more object-oriented:
    each Item object contains a canvas and a tag.  When you
    invoke methods on the Item, it invokes methods on its canvas.
    """
    def __init__(self, canvas, tag):
        self.canvas = canvas
        self.tag = tag

    def __str__(self):
        return str(self.tag)
        
    # the following are wrappers for canvas methods

    def delete(self):
        """Deletes this item from the canvas."""
        self.canvas.delete(self.tag)

    def cget(self, *args):
        """Looks up the value of the given option for this item."""
        return self.canvas.itemcget(self.tag, *args)
        
    def config(self, **options):
        """Reconfigures this item with the given options."""
        self.canvas.itemconfig(self.tag, **options)

    def coords(self, *args):
        """Gets or sets the canvas coordinates for this item."""
        return self.canvas.canvas_itemcoords(self.tag, *args)

    def bbox(self):
        """Get the approximate bounding box for this item.

        Returns:
            BBox object in canvas coordinates.
        """
        return self.canvas.bbox(self.tag)

    def bind(self, event, *args):
        """Applies a binding to this item.

        args can be (event, callback) or (event, callback, '+')

        For the event specifier, you can use Tkinter format,
        as in <Button-1>, or you can leave out the angle brackets.
        """
        if event[0] != '<':
            event = '<' + event + '>'
        event = self.canvas.translate_event(event)
        self.canvas.tag_bind(self.tag, event, *args)

    def unbind(self, *args):
        """Removes bindings from this items."""
        self.canvas.tag_unbind(self.tag, *args)

    def type(self):
        """Returns a string indicating the type of this item."""
        return self.canvas.type(self.tag)

    def lift(self):
        """Raises this item to the top of the pile."""
        return self.canvas.lift(self.tag)

    def lower(self):
        """Lowers this item to the bottom of the pile."""
        return self.canvas.lower(self.tag)

    def move(self, dx, dy):
        """Moves this item by (dx, dy) in canvas coordinates."""
        self.canvas.move(self.tag, dx, dy)

    def move_coord(self, i, dx, dy):
        """Moves the ith coordinate by (dx, dy) in canvas coordinates."""
        coords = self.coords()
        coords[i][0] += dx
        coords[i][1] += dy
        self.coords(coords)

    def replace_coord(self, i, coord):
        """Replaces the ith coordinate with the given coordinate."""
        coords = self.coords()
        coords[i] = coord
        self.coords(coords)

    def scale(self, scale, offset):
        """Shifts and scales the coordinates of this item.

        Shifts by -(offset) and multiplies by (scale)
        """
        xscale, yscale = scale
        xoffset, yoffset = offset
        self.canvas.scale(self.tag, xscale, yscale, xoffset, yoffset)


class Transform(object):
    """Provides methods for transforming lists of coordinates.

    Subclasses should implement trans() and invert().
    """
    def trans_list(self, points, func=None):
        """Applies (func) to a list of points.

        If (func) is none, applies self.trans.
        """
        if func == None:
            func = self.trans

        if isinstance(points[0], (list, tuple)):
            return [Point(func(p)) for p in points]
        else:
            return Point(func(points))

    def invert_list(self, points):
        """Applies the inverse transform to the list of points."""
        return self.trans_list(points, self.invert)
    
    def trans(self, p):
        raise NotImplementedError()

    def invert(self, p):
        raise NotImplementedError()


class CanvasTransform(Transform):
    """Transform for Cartesian coordinates.

    Under a CanvasTransform, the origin is in the middle of
    the canvas, the positive y-axis is up, and the coordinate
    [1, 1] maps to the point specified by scale.
    """
    def __init__(self, ca, scale=None):
        self.shift = [ca.get_width()/2, ca.get_height()/2]
        self.scale = scale if scale is not None else [1, 1]
    
    def trans(self, p):
        x =  p[0] * self.scale[0] + self.shift[0]
        y =  p[1] * -self.scale[1] + self.shift[1]
        return [x, y]

    def invert(self, p):
        x = (p[0] - self.shift[0]) / self.scale[0]
        y = (p[1] - self.shift[1]) / -self.scale[1]
        return [x, y]


class ScaleTransform(Transform):
    """Scales coordinates in the x and y directions.

    The origin is half a unit from the upper-left corner; the y axis
    points down.
    """
    def __init__(self, scale=None):
        self.scale = scale if scale is not None else [1, 1]
    
    def trans(self, p):
        x = p[0] * self.scale[0]
        y = p[1] * self.scale[1]
        return [x, y]

    def invert(self, p):
        x = p[0] / self.scale[0]
        y = p[1] / self.scale[1]
        return [x, y]


class RotateTransform(Transform):
    """Rotates the coordinate system."""
    def __init__(self, theta):
        """Rotates the coordinate system (theta) radians counterclockwise."""
        self.theta = theta

    def _rotate(self, p, theta):
        """Rotates the point p counterclockwise (theta) radians.

        Returns:
            coordinate pair
        """
        s = math.sin(theta)
        c = math.cos(theta)
        x =   c * p[0] + s * p[1]
        y =  -s * p[0] + c * p[1]
        return [x, y]
    
    def trans(self, p):
        return self._rotate(p, self.theta)

    def invert(self, p):
        return self._rotate(p, -self.theta)


class SwirlTransform(RotateTransform):
    """Rotates the coordinate system in proportion to distance from origin.

    Rotates (d) radians counterclockwise,
    where (d) is proportional to the distance from the origin
    """

    def trans(self, p):
        d = math.sqrt(p[0]*p[0] + p[1]*p[1])
        return self._rotate(p, self.theta*d)

    def invert(self, p):
        d = math.sqrt(p[0]*p[0] + p[1]*p[1])
        return self._rotate(p, -self.theta*d)


class Callable(object):
    """Wrap a function and its arguments in a callable object.

    Callables can can be passed as a callback parameter and invoked later.

    This code is adapted from the Python Cookbook 9.1, page 302,
    with one change: if call is invoked with args and kwds, they
    are added to the args and kwds stored in the Callable.
    """
    def __init__(self, func, *args, **kwds):
        self.func = func
        self.args = args
        self.kwds = kwds

    def __call__(self, *args, **kwds):
        d = dict(self.kwds)
        d.update(kwds)
        return self.func(*self.args+args, **d)

    def __str__(self):
        return self.func.__name__


def tk_example():
    """Creates a simple GUI using only tkinter functions."""
    tk = tkinter.Tk()
    
    def hello():
        ca.create_text(100, 100, text='hello', fill='blue')
    
    ca = tkinter.Canvas(tk, bg='white')
    ca.pack(side=LEFT)

    fr = tkinter.Frame(tk)
    fr.pack(side=LEFT)

    bu1 = tkinter.Button(fr, text='Hello', command=hello)
    bu1.pack()
    bu2 = tkinter.Button(fr, text='Quit', command=tk.quit)
    bu2.pack()
    
    tk.mainloop()


def gui_example():
    """Creates the same GUI as the previous function using Gui.py"""
    def hello():
        ca.text([0, 0], 'hello', 'blue')

    gui = Gui()
    gui.row()
    ca = gui.ca(bg='white')
    
    gui.col()
    gui.bu(text='Hello', command=hello)
    gui.bu(text='Quit', command=gui.quit)
    gui.endcol()

    gui.endrow()
    gui.mainloop()


def widget_demo():
    """Demonstrates a variety of widgets."""
    g = Gui()
    g.row()

    # COLUMN 1
    g.col()

    # a label
    la1 = g.la(text='This is a label.')

    # an entry
    en = g.en()
    en.insert(END, 'This is an entry widget.')

    # another label
    la2 = g.la(text='')

    def press_me():
        """Reads the text from the entry and display it as a label."""
        text = en.get()
        la2.configure(text=text)

    # a button
    bu = g.bu(side=TOP, text='Press me', command=press_me)

    g.endcol()

    # COLUMN 2

    g.col()
    la = g.la(text='List of colors:')

    def get_selection():
        """figure out which color is selected in the listbox"""
        t = lb.curselection()
        try:
            index = int(t[0])
            color = lb.get(index)
            return color
        except:
            return None

    def print_selection(event):
        """print the current color in the listbox
        """
        print(get_selection())

    def apply_color():
        """get the current color from the listbox and apply it
        to the circle in the canvas
        """
        color = get_selection()
        if color:
            item1.config(fill=color)

    # create a listbox with a scrollbar

    g.row()
    lb = g.lb()

    # when the user raises the button after selecting a color,
    # print the new selection (if you bind to the button press
    # you get the _previous_ selection)
    lb.bind('<ButtonRelease-1>', print_selection)

    # scrollbar
    sb = g.sb()
    g.endrow()

    # button
    bu = g.bu(text='Apply color', command=apply_color)

    # menubutton
    mb = g.mb(text='Choose a color')

    def set_color(color):
        item2.config(fill=color)

    # put some items in the menubutton
    for color in ['red', 'green', 'blue']:
        g.mi(mb, color, command=Callable(set_color, color))

    g.endcol()

    # fill the listbox with color names; if the X11 color list
    # is in the usual place, read it; otherwise use a short list.
    try:
        colors = open('/usr/share/X11/rgb.txt')
        colors.readline()
    except:
        colors = ['\t\t red', '\t\t orange', '\t\t yellow',
                  '\t\t green', '\t\t blue', '\t\t purple']
        
    for line in colors:
        t = line.split('\t')
        name = t[2].strip()
        lb.insert(END, name)

    # tell the listbox and the scrollbar about each other
    lb.configure(yscrollcommand=sb.set)
    sb.configure(command=lb.yview)

    # COLUMN 3

    g.col()

    # scrollable canvas
    sc = g.sc()
    ca = sc.canvas

    # make some items
    item1 = ca.circle([0, 0], 70, 'red')
    item2 = ca.rectangle([[0, 0], [60, 60]], 'blue')
    item3 = ca.text([0, 0], 'This is a canvas.', 'white')

    photo = tkinter.PhotoImage(file='danger.gif')
    item4 = ca.create_image(200, 300, image=photo)

    g.endcol()

    # COLUMN 4

    g.col()

    def set_font():
        """get the current settings from the font control widgets
        and configure item3 accordingly
        """
        family = 'helvetica'
        size = fontsize.get()
        weight = b1.swampy_var.get()
        slant = b2.swampy_var.get()
        font = tkFont.Font(family=family, size=size, weight=weight,
                           slant=slant)
        print(font.actual())
        item3.config(font=font)

    g.la(text='Font:')

    # fontsize is the variable associated with the radiobuttons
    fontsize = tkinter.IntVar()

    # make the radio buttons
    for size in [10, 12, 14, 15, 17, 20]:
        rb = g.rb(text=str(size), variable=fontsize, value=size,
                  command=set_font)

    # make the check buttons
    b1 = g.cb(text='Bold', command=set_font, variable=tkinter.StringVar(),
              onvalue=tkFont.BOLD, offvalue=tkFont.NORMAL)
    b1.deselect()
    
    b2 = g.cb(text='Italic', command=set_font, variable=tkinter.StringVar(),
              onvalue=tkFont.ITALIC, offvalue=tkFont.ROMAN)
    b2.deselect()

    # choose the initial font size
    fontsize.set(10)
    set_font()

    g.endcol()


    # COLUMN 5

    g.col()

    # text widget
    te = g.te(height=5, width=40)
    te.insert(END, "This is a Text widget.\n")
    te.insert(END, "It's like a little text editor.\n")
    te.insert(END, "It has more than one line, unlike an Entry widget.\n")

    # scrollable text widget
    st = g.st()
    st.text.configure(height=5, width=40)
    st.text.insert(END, "This is a Scrollable Text widget.\n")
    st.text.insert(END, "It is defined in Gui.py\n")

    # add some text
    for i in range(100):
        st.text.insert(END, "All work and no play.\n")

    g.endcol()


    # COLUMN 6

    g.col()
    # label
    g.la(text='A grid of buttons:')

    # start a grid with three columns (the weights control how
    # the buttons expand if there is extra space)
    g.gr(3)

    def print_num(i):
        print(i)

    # grid the buttons
    for i in range(1, 10):
        g.bu(text=str(i), command=Callable(print_num, i))

    g.endgr()
    g.endcol()

    g.mainloop()


def main(script, function=None, *args):
    if function == None:
        widget_demo()
    else:
        # function is normally tk_example or gui_example
        function = eval(function)
        function()

if __name__ == '__main__':
    main(*sys.argv)

