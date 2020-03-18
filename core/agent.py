
# This file contains (a) the Agent class and (b) the PyLogo function, which starts a model run.

from math import sqrt

import pygame as pg
from pygame.color import Color
from pygame.colordict import THECOLORS
from pygame import Surface
import pygame.transform as pgt

import core.gui as gui
from core.gui import HALF_PATCH_SIZE, PATCH_SIZE, SHAPES
import core.pairs as pairs
from core.pairs import heading_and_speed_to_velocity, Pixel_xy, RowCol, Velocity, XY
import core.utils as utils
from core.world_patch_block import Block, Patch, World

import math
from random import choice, randint
from statistics import mean


def is_acceptable_color(rgb):
    """
    Require reasonably bright colors (sum_rgb >= 150) for which r, g, and b are not too close to each other,
    i.e., not too close to gray. The numbers 150 and 100 are arbitrary.
    """
    sum_rgb = sum(rgb)
    avg_rgb = sum_rgb/3
    return avg_rgb >= 160 and sum(abs(avg_rgb-x) for x in rgb) > 100


# These are colors defined by pygame that satisfy is_acceptable_color() above.
PYGAME_COLORS = [(name, rgba[:3]) for (name, rgba) in THECOLORS.items() if is_acceptable_color(rgba[:3])]

# These are NetLogo primary colors -- more or less.
NETLOGO_PRIMARY_COLORS = [(color_name, Color(color_name))
                          for color_name in ['gray', 'red', 'orange', 'brown', 'yellow', 'green', 'limegreen',
                                             'turquoise', 'cyan', 'skyblue3', 'blue', 'violet', 'magenta', 'pink']]

SQRT_2 = sqrt(2)


class Agent(Block):

    color_palette = choice([NETLOGO_PRIMARY_COLORS, PYGAME_COLORS])

    half_patch_pixel = pairs.Pixel_xy((HALF_PATCH_SIZE(), HALF_PATCH_SIZE()))

    id = 0

    # SQRT_2 = sqrt(2)

    def __init__(self, center_pixel=None, color=None, scale=1.4, shape_name='netlogo_figure'):
        # Can't make this a default value because pairs.CENTER_PIXEL() isn't defined
        # when the default values are compiled
        if center_pixel is None:
            center_pixel = pairs.center_pixel()

        if color is None:
            # Select a color at random from the color_palette
            color = choice(Agent.color_palette)[1]

        super().__init__(center_pixel, color)

        self.scale = scale

        self.shape_name = shape_name
        self.base_image = self.create_base_image()

        self.id = Agent.id
        Agent.id += 1
        self.label = None
        World.agents.add(self)
        self.current_patch().add_agent(self)

        # Agents are created with a random heading and a velocity of 0.
        # In NetLogo, agents do not have a speed attribute. They have a heading attribute.
        # They are able to move by a given amount (forward(amount)) in the heading direction.
        # After each forward() action, the agent is no longer moving. (But it retains its heading.)
        self.heading = randint(0, 359)
        self.velocity = Velocity.velocity_00

    def __str__(self):
        class_name = utils.get_class_name(self)
        return f'{class_name}-{self.id}{tuple(self.center_pixel.round())}'

    def agents_in_radius(self, distance):
        qualifying_agents = [agent for agent in World.agents
                             if agent is not self and self.distance_to(agent) < distance]
        return qualifying_agents

    def all_links(self):
        return [lnk for lnk in World.links if self in (lnk.agent_1, lnk.agent_2)]

    def average_of_headings(self, agent_set, fn):
        """
        fn extracts a heading from an agent. This function returns the average of those headings.
        Cannot be static because fn may refer to self.
        agent_set may not be all the agents. So it must be passed as an argument.
        """
        # dx and dy are the x and y components of traveling one unit in the heading direction.
        dx = mean([utils.dx(fn(agent)) for agent in agent_set])
        dy = mean([utils.dy(fn(agent)) for agent in agent_set])
        return utils.dxdy_to_heading(dx, dy, default_heading=self.heading)

    def bounce_off_screen_edge(self, dxdy):
        """
       Bounce agent off the screen edges. dxdv is the current agent velocity.
       If the agent should bounce, change it as needed.
       """
        # The center pixel of this agent.
        current_center_pixel = self.center_pixel
        # Where the agent will be it if moves by dxdy.
        next_center_pixel = current_center_pixel + dxdy
        # The patch's row_col or next_center_pixel. Is that off the screen? If so, the agent should bounce.
        next_row_col = next_center_pixel.pixel_to_row_col()
        if next_row_col.row < 0 or gui.PATCH_ROWS <= next_row_col.row:
            dxdy = Velocity((dxdy.dx, dxdy.dy*(-1)))
        if next_row_col.col < 0 or gui.PATCH_COLS <= next_row_col.col:
            dxdy = Velocity((dxdy.dx*(-1), dxdy.dy))

        return dxdy

    def create_base_image(self):
        base_image = self.create_blank_base_image()

        factor = self.scale * PATCH_SIZE
        if self.shape_name in SHAPES:
            # Instead of using pygame's smoothscale to scale the image, scale the polygon instead.
            scaled_shape = [(v[0]*factor,  v[1]*factor) for v in SHAPES[self.shape_name]]
            pg.draw.polygon(base_image, self.color, scaled_shape, 0)
        return base_image

    def create_blank_base_image(self):
        # Give the agent a larger Surface (by sqrt(2)) to work with since it may rotate.
        surface_size = XY((self.rect.width, self.rect.height))*SQRT_2
        blank_base_image = Surface(surface_size)
        # This sets the rectangle to be transparent.
        # Otherwise it would be black and would cover nearby agents.
        # Even though it's a method of Surface, it can also take a Surface parameter.
        # If the Surface parameter is not given, PyCharm complains.
        # noinspection PyArgumentList
        blank_base_image = blank_base_image.convert_alpha()
        blank_base_image.fill((0, 0, 0, 0))
        return blank_base_image

    def current_patch(self) -> Patch:
        row_col: RowCol = (self.center_pixel).pixel_to_row_col()
        patch = World.patches_array[row_col.row, row_col.col]
        return patch

    def distance_to(self, other):
        wrap = not SimEngine.gui_get('Bounce?')
        dist = (self.center_pixel).distance_to(other.center_pixel, wrap)
        return dist

    def draw(self, shape_name=None):
        # No point in rotating circles or nodes. Only rotate SHAPES.
        if self.shape_name in SHAPES:
            self.image = pgt.rotate(self.base_image, -self.heading)
            self.rect = self.image.get_rect(center=self.center_pixel)
        super().draw(shape_name=self.shape_name)

    def face_xy(self, xy: Pixel_xy):
        new_heading = (self.center_pixel).heading_toward(xy)
        self.set_heading(new_heading)

    def forward(self, speed=1):
        velocity = heading_and_speed_to_velocity(self.heading, speed)
        self.set_velocity(velocity)
        self.move_by_velocity()

    def heading_toward(self, target):
        """ The heading required to face the target """
        from_pixel = self.center_pixel
        to_pixel = target.center_pixel
        return from_pixel.heading_toward(to_pixel)

    def in_links(self):
        return [lnk for lnk in World.links if lnk.directed and lnk.agent_2 is self]

    def move_by_dxdy(self, dxdy: Velocity):
        """
        Move to self.center_pixel + (dx, dy)
        """
        new_center_pixel_unwrapped = self.center_pixel + dxdy
        # Wrap around the grid of pixels.
        new_center_pixel_wrapped = new_center_pixel_unwrapped.wrap()
        self.move_to_xy(new_center_pixel_wrapped)

    def move_by_velocity(self):
        if SimEngine.gui_get('Bounce?'):
            new_velocity = self.bounce_off_screen_edge(self.velocity)
            if self.velocity != new_velocity:
                self.set_velocity(new_velocity)
        self.move_by_dxdy(self.velocity)

    def move_to_patch(self, patch):
        self.move_to_xy(patch.center_pixel)

    def move_to_xy(self, xy: Pixel_xy):
        """
        Remove this agent from the list of agents at its current patch.
        Move this agent to its new patch with center_pixel xy.
        Add this agent to the list of agents in its new patch.
        """
        current_patch: Patch = self.current_patch()
        current_patch.remove_agent(self)
        self.set_center_pixel(xy)
        new_patch = self.current_patch()
        new_patch.add_agent(self)

    def out_links(self):
        return [lnk for lnk in World.links if lnk.directed and lnk.agent_1 is self]

    def set_center_pixel(self, xy: Pixel_xy):
        self.center_pixel: Pixel_xy = xy.wrap()
        # Set the center point of this agent's rectangle.
        self.rect.center = (self.center_pixel - Agent.half_patch_pixel).round()

    def set_color(self, color):
        self.color = color
        self.base_image = self.create_base_image()

    def set_heading(self, heading):
        # Keep heading an int in range(360)
        self.heading = int(round(heading))

    def turn_left(self, delta_angles):
        self.turn_right(-delta_angles)

    def turn_right(self, delta_angles):
        self.set_heading(utils.normalize_360(self.heading + delta_angles))

    def set_velocity(self, velocity):
        self.velocity = velocity
        self.face_xy(self.center_pixel + velocity)

    def undirected_links(self):
        return [lnk for lnk in self.all_links() if not lnk.directed]


class Turtle(Agent):
    """ In case you want to call agents Turtles. """
    pass


# The Pylogo fuction that starts the simulation
from core.sim_engine import SimEngine


def PyLogo(world_class=World, caption=None, gui_left_upper=None, gui_right_upper=None,
           agent_class=Agent, patch_class=Patch, auto_setup=False,
           patch_size=11, board_rows_cols=(51, 51), clear=None, bounce=None, fps=None):
    if gui_left_upper is None:
        gui_left_upper = []
    if caption is None:
        caption = utils.extract_class_name(world_class)
    sim_engine = SimEngine(gui_left_upper, caption=caption, gui_right_upper=gui_right_upper,
                           patch_size=patch_size, board_rows_cols=board_rows_cols, clear=clear, bounce=bounce, fps=fps)
    gui.WINDOW.read(timeout=10)

    the_world = world_class(patch_class, agent_class)

    gui.WINDOW.read(timeout=10)
    sim_engine.top_loop(the_world, auto_setup=auto_setup)
