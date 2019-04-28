import design
import debug
import utils
from tech import GDS,layer

class nor2(design.design):
    """
    A single nor2 cell. This module implements the
    single 2 input nor2 cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["A", "B", "Z", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("nor2", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "nor2", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "nor2")
        debug.info(2, "Create nor2")

        self.width = nor2.width
        self.height = nor2.height
        self.pin_map = nor2.pin_map
        
