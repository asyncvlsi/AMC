# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
from vector import vector
from globals import OPTS
from pinv import pinv
from nand2 import nand2

class driver(design.design):
    """ Creates an array of drivers (nand2 + inv) to drive the control signals with Go """

    def __init__(self, rows, inv_size = 1, name = "driver"):
        design.design.__init__(self, name)
        
        self.nand2 = nand2()
        self.add_mod(self.nand2)

        self.rows = rows
        self.inv_size = inv_size
        self.name = name
        
        self.inv = pinv(size=self.inv_size)
        self.add_mod(self.inv)

        self.height = self.inv.height * self.rows
        
        self.add_pins()
        self.add_driver()

    def add_pins(self):
        """ Add pins for driver_array, order of the pins is important """
        
        for i in range(self.rows):
            self.add_pin("in[{0}]".format(i))
        for i in range(self.rows):
            self.add_pin("out[{0}]".format(i))
        self.add_pin_list(["en", "vdd","gnd"])

    def add_driver(self):
        """ Add nand2 + inv cells"""
        
        self.x_offset1 = 7*self.m1_space
        self.x_offset2 = self.x_offset1 + self.nand2.width
        self.width = self.x_offset2 + self.inv.width
        
        self.add_layout_pin(text="gnd", 
                            layer=self.m1_pin_layer, 
                            offset=[self.x_offset1, -0.5*contact.m1m2.width], 
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)


        for row in range(self.rows):
            name_nand = "driver_nand{}".format(row)
            name_inv2 = "driver_inv{}".format(row)

            #flipping the cell to share vdd/gnd rail
            if (row % 2):
                y_offset = self.inv.height*(row + 1)
                inst_mirror = "MX"
                pin_name = "gnd"
            else:
                y_offset = self.inv.height*row
                inst_mirror = "R0"
                pin_name = "vdd"

            nand2_offset=[self.x_offset1, y_offset]
            inv2_offset=[self.x_offset2, y_offset]
            base_offset = vector(self.width, y_offset)

            yoffset = (row + 1) * self.inv.height - 0.5 * contact.m1m2.width
            self.add_layout_pin(text=pin_name, 
                                layer=self.m1_pin_layer, 
                                offset=[self.x_offset1, yoffset], 
                                width=contact.m1m2.width, 
                                height=contact.m1m2.width)
            # add nand 2
            nand_inst=self.add_inst(name=name_nand, 
                                    mod=self.nand2, 
                                    offset=nand2_offset, 
                                    mirror=inst_mirror)
            self.connect_inst(["en", "in[{0}]".format(row), "net[{0}]".format(row), "vdd", "gnd"])
            
            # add inv
            inv2_inst=self.add_inst(name=name_inv2, 
                                    mod=self.inv, 
                                    offset=inv2_offset, 
                                    mirror=inst_mirror)
            self.connect_inst(["net[{0}]".format(row), "out[{0}]".format(row), "vdd", "gnd"])

            # en connection
            a_pin = nand_inst.get_pin("A")
            a_pos = a_pin.lc()
            clk_offset = vector(self.m1_width + 2*self.m1_space ,a_pos.y)
            self.add_segment_center(layer="metal1", start=clk_offset, end=a_pos)
            self.add_via_center(self.m1_stack, clk_offset, rotate=90)

            # Nand2 out to inv input
            zr_pos = nand_inst.get_pin("Z").lc()
            al_pos = inv2_inst.get_pin("A").lc()
            # ensure the bend is in the middle 
            mid1_pos = vector(0.5*(zr_pos.x+al_pos.x), zr_pos.y)
            mid2_pos = vector(0.5*(zr_pos.x+al_pos.x), al_pos.y)
            self.add_path("metal1", [zr_pos, mid1_pos, mid2_pos, al_pos])

            # output each OUT on the right
            out_pin = inv2_inst.get_pin("Z")
            self.add_layout_pin(text="out[{0}]".format(row), 
                                layer=out_pin.layer, 
                                offset=out_pin.ll(),
                                width=self.m1_width,
                                height=self.m1_width)

            # connect the decoder input pin to nand2 B
            b_pin = nand_inst.get_pin("B")
            self.add_layout_pin(text="in[{0}]".format(row), 
                                layer=out_pin.layer, 
                                offset=b_pin.ll(), 
                                width=self.m1_width,
                                height=self.m1_width)

        # Wordline enable connection
        en_pin=self.add_rect(layer="metal2", 
                             offset=[2*self.m1_space,0], 
                             width=self.m2_width, 
                             height=self.height)
        en_pin=self.add_layout_pin(text="en", 
                                   layer=self.m2_pin_layer, 
                                   offset=[2*self.m1_space,0], 
                                   width=self.m2_width, 
                                   height=self.m2_width)
