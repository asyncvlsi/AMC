""" BSD 3-Clause License
    Copyright (c) 2018-2019 Regents of the University of California and The Board
    of Regents for the Oklahoma Agricultural and Mechanical College
    (acting for and on behalf of Oklahoma State University)
    All rights reserved.
"""


import design
import debug
from vector import vector
from precharge import precharge

class precharge_array(design.design):
    """ Array of dynamically generated precharge cells to charge all bitlines. """

    def __init__(self, columns, name="precharge_array"):
        design.design.__init__(self, name)
        debug.info(1, "Creating {0}".format(name))

        self.columns = columns

        self.pc_cell = precharge()
        self.add_mod(self.pc_cell)

        self.width = self.columns * self.pc_cell.width
        self.height = self.pc_cell.height

        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for precharge_array, order of the pins is important """
        
        for i in range(self.columns):
            self.add_pin("bl[{0}]".format(i))
            self.add_pin("br[{0}]".format(i))
        self.add_pin_list(["en", "vdd"])

    def create_layout(self):
        self.add_insts()
        self.connect_rails()

    def add_insts(self):
        """Creates a precharge array by horizontally tiling the precharge cell"""

        for i in range(self.columns):
            name = "pre_column_{0}".format(i)
            offset = vector(self.pc_cell.width * i, 0)
            inst=self.add_inst(name=name, mod=self.pc_cell, offset=offset)
            bl_pin = inst.get_pin("bl")
            self.add_layout_pin(text="bl[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset=bl_pin.ll(), 
                                width=self.m2_width, 
                                height=bl_pin.height())
            br_pin = inst.get_pin("br") 
            self.add_layout_pin(text="br[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset=br_pin.ll(), 
                                width=self.m2_width, 
                                height=bl_pin.height())
            self.connect_inst(["bl[{0}]".format(i), "br[{0}]".format(i), "en", "vdd"])
    
    def connect_rails(self):
        """Add vdd and en rails across the array"""

        self.add_layout_pin(text="vdd", 
                            layer=self.m1_pin_layer, 
                            offset=self.pc_cell.get_pin("vdd").ll(), 
                            width=self.m1_width, 
                            height=self.m1_width)
        self.add_layout_pin(text="en", 
                            layer=self.m1_pin_layer, 
                            offset=self.pc_cell.get_pin("en").ll(), 
                            width=self.m1_width, 
                            height=self.m1_width)
