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
from math import ceil
from tech import spice
from vector import vector
from nand2 import nand2
from pinv import pinv
from flipflop import flipflop


class frequency_divider(design.design):
    """ Dynamically generated a frequency divider"""

    def __init__(self, name="frequency_divider"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))
        
        self.create_layout()
        
        self.width= self.ff_clk3.rx() + 10*self.m_pitch("m1")
        self.height=self.ff_clk3.uy() + 4*self.m_pitch("m1")
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.add_modules()
        self.connect_modules()
        self.connect_vdd_gnd()
        self.add_layout_pins()
        
    def add_pins(self):
        """ Adds pins for oscillator module """
        
        self.add_pin_list(["in", "clk", "clk1", "clk2", "clk3", "reset", "vdd", "gnd"])
    
    def create_modules(self):
        """ construct all the required modules """
        
        self.nand2 = nand2()
        self.add_mod(self.nand2)
        
        self.inv1 = pinv(size=1)
        self.add_mod(self.inv1)

        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)

        self.ff = flipflop()
        self.add_mod(self.ff)
        
    def add_modules(self):
        """ Add modules """

        self.rst_inv=self.add_inst(name="rst_inv",
                                   mod=self.inv1,
                                   offset=(0, 0))
        self.connect_inst(["reset", "reset_bar", "vdd", "gnd"])
        
        self.rst_nand=self.add_inst(name="rst_nand",
                                    mod=self.nand2,
                                    offset=self.rst_inv.lr())
        self.connect_inst(["in", "reset_bar", "clk_b", "vdd", "gnd"])
        
        self.clk_inv=self.add_inst(name="clk_inv",
                                   mod=self.inv5,
                                   offset=self.rst_nand.lr())
        self.connect_inst(["clk_b", "clk", "vdd", "gnd"])
        
        
        self.ff_div=self.add_inst(name="ff_div",
                                  mod=self.ff,
                                  offset=self.clk_inv.lr()+vector(3*self.m_pitch("m1"), 0))
        self.connect_inst(["a", "clk_div", "a", "clk", "vdd", "gnd"])
        
        self.div_inv=self.add_inst(name="div_inv",
                                   mod=self.inv1,
                                   offset=self.ff_div.lr()+vector(3*self.m_pitch("m1"), 0))
        self.connect_inst(["clk_div", "clk_div_b", "vdd", "gnd"])
        
        self.ff_clk2=self.add_inst(name="ff_clk2",
                                  mod=self.ff,
                                  offset=self.div_inv.lr()+vector(2*self.m_pitch("m1"), 0))
        self.connect_inst(["clk_div_b", "clk2", "clk1", "clk", "vdd", "gnd"])
        
        self.ff_clk3=self.add_inst(name="ff_clk3",
                                  mod=self.ff,
                                  offset=self.ff_clk2.ul()+vector(0, self.ff.height),
                                  mirror="MX")
        self.connect_inst(["clk_div", "clk3", "clk3_b", "clk", "vdd", "gnd"])


    def connect_modules(self):
        """ make connections for input and outputs of ff_div, ff_clk2 and ff_clk3  """
        
        #connect reset_bar to input B of rst_nand
        pos1=self.rst_inv.get_pin("Z").lc()
        pos2=self.rst_nand.get_pin("B").lc()
        self.add_path("metal1", [pos1, pos2])


        #connect clk to input clk of ff_div
        pos1= self.clk_inv.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos4=self.ff_div.get_pin("clk").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        #connect input and out_bar of ff_div together
        pos1=self.ff_div.get_pin("in").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.ff_div.uy()+self.m_pitch("m1"))
        pos6=self.ff_div.get_pin("out_bar").lc()
        pos4=vector(self.ff_div.rx()+self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])
        
        #connect out of ff_div to input of div_inv
        pos1=self.div_inv.get_pin("A").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos4=self.ff_div.get_pin("out").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

        #connect out of div_inv to input of ff_clk2
        pos1=self.div_inv.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=self.ff_clk2.get_pin("in").lc()
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])

        #connect out of ff_div to input of ff_clk3
        pos1=self.div_inv.get_pin("A").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos4=self.ff_clk3.get_pin("in").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        #connect clk of ff_div to clk of ff_clk2 and ff_clk3
        pos1=self.ff_div.get_pin("clk").lc()
        pos2=self.ff_clk2.get_pin("clk").lc()
        self.add_path("metal1", [pos1, pos2])
        
        pos3=vector(pos2.x-2*self.m_pitch("m1"), pos2.y)
        pos5=self.ff_clk3.get_pin("clk").lc()
        pos4=vector(pos3.x, pos5.y)
        self.add_wire(self.m1_stack, [pos2, pos3, pos4, pos5])

    def connect_vdd_gnd(self):
        """ Connect vdd and gnd of all modules together and to power pins"""

        pins=["vdd", "gnd"]
        
        #connect vdd and gnd of other modules to vdd and gnd pins
        modules=[self.clk_inv, self.ff_clk2]
        for i in range(2):
            off =vector(-(i+5)*self.m_pitch("m1"), 0)
            self.add_rect(layer="metal2",
                          offset= off,
                          width=self.m2_width,
                          height=self.ff_clk3.uy())
            self.add_layout_pin(text=pins[i],
                                layer=self.m2_pin_layer,
                                offset=off,
                                width=self.m2_width,
                                height=self.m2_width)


            for mod in modules:
                off1=vector(off.x, mod.get_pin(pins[i]).lc().y-0.5*self.m1_width)
                width=mod.get_pin(pins[i]).lc().x-off.x
                self.add_rect(layer="metal1",
                              offset=off1,
                              width=width,
                              height=self.m1_width)
                self.add_via(self.m1_stack, off1)

        #connect gnd of ff_clk3 to gnd pin
        pos1=self.ff_clk3.get_pin("gnd").lc()
        pos2=(-6*self.m_pitch("m1"), pos1.y)
        self.add_path("metal1", [pos1, pos2])
        self.add_via(self.m1_stack, pos2)

        #connect vdd of div_inv to vdd of ff_clk3
        pos1=self.div_inv.get_pin("vdd").lc()
        pos2=self.ff_clk2.get_pin("vdd").lc()
        self.add_wire(self.m1_stack, [pos1, pos2])
        self.add_via(self.m1_stack, pos1)

    def add_layout_pins(self):
        

        self.min_xoff=-6*self.m_pitch("m1")

        #reset pin
        pos2=self.rst_inv.get_pin("A").lc()
        pos1=vector(self.min_xoff, pos2.y)
        self.add_path("metal1", [pos1,pos2])
        self.add_layout_pin(text="reset",
                            layer=self.m1_pin_layer,
                            offset=pos1-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #input pin
        pos2=self.rst_nand.get_pin("A").ll()+vector(0.5*contact.m1m2.height, 0)
        pos1=vector(pos2.x, -0.5*contact.m1m2.width)
        self.add_path("metal2", [pos1,pos2])
        self.add_via(self.m1_stack, pos2+vector(0.5*contact.m1m2.height, 0), rotate=90)
        self.add_layout_pin(text="in",
                            layer=self.m2_pin_layer,
                            offset=pos1-vector(0.5*self.m1_width,0),
                            width=self.m2_width,
                            height=self.m2_width)

        #clk pin
        pos1=vector(self.min_xoff, self.clk_inv.uy()+2*self.m_pitch("m1"))
        pos2=vector(self.clk_inv.rx()-self.m1_space-0.5*self.m2_width, pos1.y)
        pos3=vector(pos2.x, self.clk_inv.get_pin("Z").by())
        self.add_wire(self.m1_stack, [pos1,pos2,pos3])
        self.add_layout_pin(text="clk",
                            layer=self.m1_pin_layer,
                            offset=pos1-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #clk1 pin
        pos1=vector(self.min_xoff, self.ff_clk3.uy()+2*self.m_pitch("m1"))
        pos2=vector(self.ff_clk2.rx()+self.m_pitch("m1"), pos1.y)
        pos4=self.ff_clk2.get_pin("out_bar").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1,pos2,pos3, pos4])
        self.add_layout_pin(text="clk1",
                            layer=self.m1_pin_layer,
                            offset=pos1-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #clk2 pin
        pos1=vector(self.min_xoff, self.ff_clk3.uy()+3*self.m_pitch("m1"))
        pos2=vector(self.ff_clk2.rx()+2*self.m_pitch("m1"), pos1.y)
        pos4=self.ff_clk2.get_pin("out").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1,pos2,pos3, pos4])
        self.add_layout_pin(text="clk2",
                            layer=self.m1_pin_layer,
                            offset=pos1-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)
        #clk3 pin
        pos1=vector(self.min_xoff, self.ff_clk3.uy()+4*self.m_pitch("m1"))
        pos2=vector(self.ff_clk3.rx()+3*self.m_pitch("m1"), pos1.y)
        pos4=self.ff_clk3.get_pin("out").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1,pos2,pos3, pos4])
        self.add_layout_pin(text="clk3",
                            layer=self.m1_pin_layer,
                            offset=pos1-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)
    
