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

class decode_stage_4_4(design.design):
    """
    A single decode_stage_4_4 cell. This module implements the
    decode_stage cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    This cell is used in the design of heirarchical decoder.
    """

    pin_names = ["in0", "in1", "in2", "in3", "out0", "out1", "out2", "out3", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("decode_stage_4_4", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "decode_stage_4_4", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "decode_stage_4_4")
        debug.info(2, "Create decode_stage_4_4")

        self.width = decode_stage_4_4.width
        self.height = decode_stage_4_4.height
        self.pin_map = decode_stage_4_4.pin_map
        
