# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import utils
from tech import GDS,layer

class sense_amp(design.design):
    """
    This module implements the single sense amp cell used in the design. It
    is a hand-made cell, so the layout and netlist should be available in
    the technology library.
    Sense amplifier to amplify the voltage swing on a  pair of bit-lines.
    """

    pin_names = ["bl", "br", "dout", "dout_bar", "en", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("sense_amp", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "sense_amp", GDS["unit"])

    def __init__(self):
        design.design.__init__(self, "sense_amp")
        debug.info(2, "Create sense_amp")

        self.width = sense_amp.width
        self.height = sense_amp.height
        self.pin_map = sense_amp.pin_map
