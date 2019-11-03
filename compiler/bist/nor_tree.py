# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA. (See LICENSE for licensing information)


import design
import debug
import contact
import math
from tech import drc, parameter, spice
from vector import vector
from nor2 import nor2
from nor3 import nor3
from pinv import pinv

class nor_tree(design.design):
    """ Dynamically generated nor tree with nor+inverter"""

    def __init__(self, size, name="nor_tree"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.size = size
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.determine_gates()
        self.add_layout_pins()
        self.height= self.nor2.height + self.m_pitch("m1")
        
    def add_pins(self):
        """ Adds pins for nor_tree module """
        
        for i in range(self.size-1):
            self.add_pin("in{0}".format(i))
        self.add_pin_list(["out", "vdd", "gnd"])

    def create_modules(self):
        """ Adds all the required modules """
        
        self.inv = pinv(size=1)
        self.add_mod(self.inv)
        
        self.nor2 = nor2()
        self.add_mod(self.nor2)
        
        self.nor3 = nor3()
        self.add_mod(self.nor3)

    def determine_gates(self):
        """Determines the number of nor2 and nor3 needed based on the number of inputs"""
        
        self.nor_inst={}
        self.inv_inst={}
        if (self.size == 3):
            self.add_nor2()
            self.width= self.nor2.width + self.m_pitch("m1")+0.5*self.m2_width
        elif (self.size == 4):
            self.add_nor3()
            self.width= self.nor3.width + 3*self.m_pitch("m1")+0.5*self.m2_width
        elif (self.size > 4):
            self.add_nor_tree()
            self.width= (self.size-3)*(self.nor2.width+self.inv.width) + \
                         self.nor2.width + self.m_pitch("m1")+0.5*self.m2_width
        
        #This is a contact/via shift to avoid DRC violation
        self.via_co_shift= 0.5*abs(contact.poly.width-contact.m1m2.width)

    def add_nor2(self):
        """ Place the nor2 gates """
        
        self.nor_inst[0]= self.add_inst(name="nor2", mod=self.nor2, offset=(0,0))
        self.connect_inst(["in0", "in1", "out", "vdd", "gnd"])

    def add_nor3(self):
        """ Place the nor3 gates """
        
        self.nor_inst[0]= self.add_inst(name="nor3", mod=self.nor3, offset=(0,0))
        self.connect_inst(["in0", "in1", "in2", "out", "vdd", "gnd"])


    def add_nor_tree(self):
        """ Place the nor_tree """
        
        for i in range(self.size-3):
            x_off = i*(self.nor2.width+self.inv.width)
            self.nor_inst[i]= self.add_inst(name="nor2_{0}".format(i), mod=self.nor2,
                                            offset=(x_off,0))
            if i == 0:
                self.connect_inst(["in0", "in1", "z0", "vdd", "gnd"])
            else:
                self.connect_inst(["out{0}".format(i-1), "in{0}".format(i+1), 
                                   "z{0}".format(i), "vdd", "gnd"])

            self.inv_inst[i]= self.add_inst(name="inv_{0}".format(i), mod=self.inv,
                                            offset=(x_off+self.nor2.width,0))
            self.connect_inst(["z{0}".format(i), "out{0}".format(i), "vdd", "gnd"])
        
        self.nor_inst[self.size-3]= self.add_inst(name="nor2_{0}".format(self.size-3),
                                                  mod=self.nor2,
                                                  offset=(self.inv_inst[self.size-4].rx(),0))
        self.connect_inst(["out{0}".format(self.size-4), "in{0}".format(self.size-2), 
                           "out", "vdd", "gnd"])

    def add_layout_pins(self):
        """ Add input, output and power pins """
        
        # Add first input pin
        module = self.nor_inst[0]
        A_off= module.get_pin("A")
        mid_pos = vector(module.lx()-self.m_pitch("m1"), A_off.lc().y)
        pos2 = vector(module.lx(), A_off.lc().y)
        self.add_path("metal2", [(mid_pos.x,-self.m_pitch("m1")), mid_pos, pos2])
        self.add_via(self.m1_stack, (module.lx()+self.via_shift("v1"),A_off.by()), rotate=90) 
        
        in0_off=(module.lx()-self.m_pitch("m1")-0.5*self.m2_width,-self.m_pitch("m1"))
        self.add_layout_pin(text="in0",
                            layer=self.m2_pin_layer,
                            offset=in0_off,
                            width=self.m2_width,
                            height=self.m2_width)

        # Add second to last input pins
        if self.size == 4:
            pins = ["B", "C"]
            for i in range(2):
                nor_off= module.get_pin(pins[i])
                mid_pos = vector(module.lx()-(i+2)*self.m_pitch("m1"), nor_off.lc().y)
                pos2 = vector(module.lx(), nor_off.lc().y)
                self.add_path("metal2", [(mid_pos.x,-self.m_pitch("m1")), mid_pos, pos2])
                self.add_via(self.m1_stack, (module.lx()+self.via_shift("v1"),nor_off.by()), rotate=90) 
                
                in_off=(module.lx()-(i+2)*self.m_pitch("m1")-0.5*self.m2_width,-self.m_pitch("m1"))
                self.add_layout_pin(text="in{0}".format(i+1),
                                     layer=self.m2_pin_layer,
                                     offset=in_off,
                                     width=self.m2_width,
                                     height=self.m2_width)

        else:
            for i in range(self.size-2):
                xoff = self.nor_inst[i].lx()
                B_off= self.nor_inst[i].get_pin("B")
                self.add_path("metal2", [(xoff,-self.m_pitch("m1")), 
                                         (xoff, B_off.by()+contact.m1m2.width)])
                self.add_via(self.m1_stack, (xoff+contact.m1m2.height, B_off.by()), rotate=90)
                
                in_off=(xoff-0.5*self.m2_width,-self.m_pitch("m1"))
                self.add_layout_pin(text="in{0}".format(i+1),
                                    layer=self.m2_pin_layer,
                                    offset=in_off,
                                    width=self.m2_width,
                                    height=self.m2_width)


            for i in range(self.size-3):
                A_off= self.nor_inst[i+1].get_pin("A")
                inv_Z_off= self.inv_inst[i].get_pin("Z")
                height = abs(A_off.by()-inv_Z_off.by()) + self.m1_width
                self.add_rect(layer="metal1", 
                              offset=(A_off.lx(), min(A_off.by(), inv_Z_off.by())),
                              width=self.m1_width,
                              height=height)

        # Add output pin
        if self.size == 4:
            nor_Z_off= module.get_pin("Z")
        else:
            nor_Z_off= self.nor_inst[self.size-3].get_pin("Z")
        self.add_layout_pin(text="out",
                            layer=self.m1_pin_layer,
                            offset=nor_Z_off.ll(),
                            width=self.m1_width,
                            height=self.m1_width)

        # Add vdd and gnd pins
        nor_vdd_off= module.get_pin("vdd").ll()
        nor_gnd_off= module.get_pin("gnd").ll()
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=nor_vdd_off,
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        self.add_layout_pin(text="gnd",
                            layer=self.m1_pin_layer,
                            offset=nor_gnd_off,
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
