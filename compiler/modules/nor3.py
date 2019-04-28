import design
import debug
import utils
from tech import GDS,layer

class nor3(design.design):
    """
    A single nor3 cell. This module implements the
    single 3 input nor3 cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["A", "B", "C", "Z", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("nor3", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "nor3", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "nor3")
        debug.info(2, "Create nor3")

        self.width = nor3.width
        self.height = nor3.height
        self.pin_map = nor3.pin_map
        
