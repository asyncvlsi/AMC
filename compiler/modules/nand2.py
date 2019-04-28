import design
import debug
import utils
from tech import GDS,layer

class nand2(design.design):
    """
    A single nand2 cell. This module implements the
    single 2 input nand cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["A", "B", "Z", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("nand2", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "nand2", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "nand2")
        debug.info(2, "Create nand2")

        self.width = nand2.width
        self.height = nand2.height
        self.pin_map = nand2.pin_map
        
