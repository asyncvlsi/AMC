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

class write_complete(design.design):
    """
    This module implements the single write complete cell used in the design. It
    is a hand-made cell, so the layout and netlist should be available in
    the technology library.
    """

    pin_names = ["bl", "br", "en", "write_complete", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("write_complete", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "write_complete", GDS["unit"])

    def __init__(self):
        design.design.__init__(self, "write_complete")
        debug.info(2, "Create write_complete")

        self.width = write_complete.width
        self.height = write_complete.height
        self.pin_map = write_complete.pin_map
