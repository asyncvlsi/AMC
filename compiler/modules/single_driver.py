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
        
