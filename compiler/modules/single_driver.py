# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA. (See LICENSE for licensing information)



import design
import debug
import utils
from tech import GDS,layer

class single_driver(design.design):
    """
    A single single_driver cell. This module implements the
    single single_driver cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["in0", "in1", "out", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("single_driver", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "single_driver", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "single_driver")
        debug.info(2, "Create single_driver")

        self.width = single_driver.width
        self.height = single_driver.height
        self.pin_map = single_driver.pin_map
        
