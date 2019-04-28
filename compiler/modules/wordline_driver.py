import design
import debug
import utils
from tech import GDS,layer

class wordline_driver(design.design):
    """
    A single wordline_driver cell. This module implements the
    single wordline_driver cell used in the design. It is a hand-made cell, so
    the layout and netlist should be available in the technology library.
    """

    pin_names = ["in0", "in1", "in2", "in3", "out0", "out1", "out2", "out3", "en", "vdd", "gnd"]
    (width,height) = utils.get_libcell_size("wordline_driver", GDS["unit"], layer["boundary"])
    pin_map = utils.get_libcell_pins(pin_names, "wordline_driver", GDS["unit"])
    

    def __init__(self):
        design.design.__init__(self, "wordline_driver")
        debug.info(2, "Create wordline_driver")

        self.width = wordline_driver.width
        self.height = wordline_driver.height
        self.pin_map = wordline_driver.pin_map
        
