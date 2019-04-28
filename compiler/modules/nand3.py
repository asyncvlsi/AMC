import design
import debug
import utils
from tech import GDS,layer

class nand3(design.design):
    """
    A single nand3 cell. This module implements the
    single 3 input nand3 cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["A", "B", "C", "Z", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("nand3", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "nand3", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "nand3")
        debug.info(2, "Create nand3")

        self.width = nand3.width
        self.height = nand3.height
        self.pin_map = nand3.pin_map
        
