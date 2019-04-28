import design
import debug
import utils
from tech import GDS,layer

class merge(design.design):
    """
    This module implements the single merge cell used in the design. It
    is a hand-made cell, so the layout and netlist should be available in
    the technology library.
    merge for output data signals and some control signals when num of banks is greater than one
    """

    pin_names = ["D", "Q", "en1_M", "en2_M", "reset", "M", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("merge", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "merge", GDS["unit"])

    def __init__(self):
        design.design.__init__(self, "merge")
        debug.info(2, "Create merge")

        self.width = merge.width
        self.height = merge.height
        self.pin_map = merge.pin_map

