# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import utils
from tech import GDS,layer

class replica_bitcell(design.design):
    """
    A single replica bit 6T cell. 
    This module implements the single replica memory cell used in the design. It
    is a hand-made cell, so the layout and netlist should be available in
    the technology library.
    A replica memory cell is a hard-wired memory cell that always stores "0"
    """

    pin_names = ["bl", "br", "wl", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("replica_cell_6t", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "replica_cell_6t", GDS["unit"])

    def __init__(self):
        design.design.__init__(self, "replica_cell_6t")
        debug.info(2, "Create replica bitcell object")

        self.width = replica_bitcell.width
        self.height = replica_bitcell.height
        self.pin_map = replica_bitcell.pin_map
