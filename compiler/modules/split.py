""" This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301, USA.
"""

import design
import debug
import utils
from tech import GDS,layer

class split(design.design):
    """
    This module implements the single split cell used in the design. It
    is a hand-made cell, so the layout and netlist should be available in
    the technology library.
    split for input address, input data, and some control signals when num of banks is greater than one
    """

    pin_names = ["D", "Q", "en1_S", "en2_S", "reset", "S", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("split", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "split", GDS["unit"])

    def __init__(self):
        design.design.__init__(self, "split")
        debug.info(2, "Create split")

        self.width = split.width
        self.height = split.height
        self.pin_map = split.pin_map

