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
from vector import vector
from xor2 import xor2
from nand2 import nand2
from nand3 import nand3
from pinv import pinv
from nor_tree import nor_tree
from flipflop import flipflop
from ptx import ptx
from utils import ceil

class comparator(design.design):
    """ Dynamically generated comparator to comapre data-in and data-out in BIST """

    def __init__(self, size, name="comparator"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.size = size
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_constants()
        self.add_modules()
        self.connect_modules()
        self.add_layout_pins()
        self.width= max(self.xor_inst[self.size-1].rx(), self.inv_inst.rx())+\
                    4*self.m_pitch("m1")+self.m2_width
        self.height= self.nor_tree_inst.uy()+3*self.m_pitch("m1")+self.m2_width

    def add_pins(self):
        """ Adds pins for lfsr module """
        
        for i in range(self.size):
            self.add_pin("din{0}".format(i))
        for i in range(self.size):
            self.add_pin("dout{0}".format(i))
        self.add_pin_list(["err", "lfsr_done", "reset", "r", "clk", "vdd", "gnd"])

    def create_modules(self):
        """ construct all the required modules """
        
        self.flipflop = flipflop()
        self.add_mod(self.flipflop)
        
        self.xor2 = xor2()
        self.add_mod(self.xor2)

        self.nand2 = nand2()
        self.add_mod(self.nand2)

        self.nand3 = nand3()
        self.add_mod(self.nand3)
        
        self.inv = pinv()
        self.add_mod(self.inv)

        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)
        
        self.nor_tree=nor_tree(size=self.size+1, name="comparator_nor_tree")
        self.add_mod(self.nor_tree)

    def setup_layout_constants(self):
        """ Setup layout constants, spaces, etc """

        self.pin_off = 2*self.m_pitch("m1")
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.gap1= max(self.implant_space, self.well_space, self.m_pitch("m1"))+contact.m1m2.width
        self.gap2= self.gap1+2*self.m_pitch("m1")

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_flipflop()
        self.add_clk_gate()
        self.add_xor()
        self.add_nor_tree()

    def connect_modules(self):
        """ Route modules """

        self.connect_FF_to_XOR()
        self.connect_clk_to_FF()
        self.connect_XOR_to_nor_tree()
        self.connect_vdd_gnd()
    
    def add_flipflop(self):
        """ Place the flipflops """
        
        self.flipflop_inst={}
        x_shisht = self.inv.width+self.inv5.width+self.nand3.width+\
                   4*self.m_pitch("m1")-self.flipflop.width
        for i in range(self.size):
            off=(x_shisht+i*(self.flipflop.width+self.gap2),0)
            self.flipflop_inst[i]= self.add_inst(name="flipflop{0}".format(i),
                                                 mod=self.flipflop,
                                                 offset=off)
            self.connect_inst(["din{0}".format(i), "out{0}".format(i), "out_bar{0}".format(i), 
                               "clkin", "vdd", "gnd"])

    def add_clk_gate(self):
        """ Place the inv and nand3 for clk gateing with reset and lfsr_done signals """
        
        self.reset_inv_inst= self.add_inst(name="inv_reset",
                                           mod=self.inv,
                                           offset=(0,self.flipflop_inst[0].uy()+self.gap1))
        self.connect_inst(["reset", "reset_b", "vdd", "gnd"])

        off=self.reset_inv_inst.lr()+vector(4*self.m_pitch("m1"),0)
        self.reset_nand_inst= self.add_inst(name="nand3_reset",
                                            mod=self.nand3,
                                            offset=off)
        self.connect_inst(["reset_b", "lfsr_done", "clk", "q", "vdd", "gnd"])
        
        self.clk_inv_inst= self.add_inst(name="inv_clk",
                                         mod=self.inv5,
                                         offset=self.reset_nand_inst.lr())
        self.connect_inst(["q", "clkin", "vdd", "gnd"])
        
        pos2=self.reset_nand_inst.get_pin("A").lc()
        pos1=self.reset_inv_inst.get_pin("Z").lc()
        mid_pos=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        self.add_path("metal1", [pos1, mid_pos, pos2])
            
    def add_xor(self):
        """ Place the xor gates above flipflops """
        
        self.xor_inst={}
        for i in range(self.size):
            xoff = max(self.flipflop_inst[0].rx() , self.clk_inv_inst.rx()) + self.gap2
            yoff = self.flipflop_inst[0].uy()+self.gap1
            off = (xoff + i*(self.flipflop.width+self.gap2),yoff)
            self.xor_inst[i]= self.add_inst(name="xor{0}".format(i),
                                            mod=self.xor2,
                                            offset=off)
            self.connect_inst(["out{0}".format(i), "dout{0}".format(i), "z{0}".format(i), "vdd", "gnd"])
    
    def add_nor_tree(self):
        """ Place the nor-tree above xor gates """
        
        xoff=self.flipflop_inst[1].rx()+self.gap2
        yoff=self.xor_inst[0].uy()+(self.size+2)*self.m_pitch("m1")
        self.nor_tree_inst= self.add_inst(name="nor_tree",
                                           mod=self.nor_tree,
                                           offset=(xoff,yoff))
        temp=[]
        for i in range(self.size):
            temp.append("z{0}".format(i))
        
        temp.extend(["err_bar", "vdd", "gnd"])
        self.connect_inst(temp)
    
        off=(self.nor_tree_inst.rx(),self.nor_tree_inst.by()+self.m_pitch("m1"))
        self.inv_err= self.add_inst(name="inv_err", mod=self.inv, offset=off)
        self.connect_inst(["err_bar", "err1", "vdd", "gnd"])

        self.nand_err= self.add_inst(name="nand_err", mod=self.nand3,
                                     offset=self.inv_err.lr()+vector(self.gap2, 0))
        self.connect_inst(["reset_b", "err1", "r", "err_b", "vdd", "gnd"])


        self.inv_inst= self.add_inst(name="inv", mod=self.inv, offset=self.nand_err.lr())
        self.connect_inst(["err_b", "err", "vdd", "gnd"])
        
        pos1=self.inv_err.get_pin("Z").lc()
        pos2=(self.inv_err.rx()+self.m1_width, pos1.y)
        pos3=self.nand_err.get_pin("B").lc()
        self.add_path("metal1", [pos1,pos2, pos3])

        pos1=self.nand_err.get_pin("A").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.nand_err.uy()+self.m_pitch("m1"))
        pos5=self.reset_inv_inst.get_pin("Z").ll()-vector(0.5*self.m2_width, 0)
        pos4=vector(pos5.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])


    def connect_clk_to_FF(self):
        """ Connect output of clk_inv to clk pin of FF """
        pos1=self.clk_inv_inst.get_pin("Z").ll()-vector(0.5*self.m2_width, self.via_shift("v1"))
        pos3=vector(pos1.x, self.clk_inv_inst.uy()+5*self.m_pitch("m1"))
        pos4=vector(self.reset_inv_inst.lx()-self.m_pitch("m1"),pos3.y)
        pos6=self.flipflop_inst[self.size-1].get_pin("clk").lc()
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos3, pos4, pos5, pos6])

    def connect_FF_to_XOR(self):
        """ Connect FF output to input A of XOR """
        
        for i in range(self.size):
            pos1=self.flipflop_inst[i].get_pin("out").lc()
            pos2=vector(self.flipflop_inst[i].rx()+self.m_pitch("m1"), pos1.y)
            pos4=self.xor_inst[i].get_pin("A").lc()
            pos3=(pos2.x, pos4.y)
            self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4])
        
    def connect_XOR_to_nor_tree(self):
        """ Connect XOR output to inputs of nor_tree """
        
        for i in range(self.size):
            y_off=self.xor_inst[0].uy()+(i+1)*self.m_pitch("m1")
            self.add_path("metal1",[(self.xor_inst[0].lx(), y_off), 
                                    (self.xor_inst[self.size-1].rx(), y_off)])
            pos1=self.xor_inst[i].get_pin("Z")
            pos2=vector(pos1.rx(), y_off)
            self.add_path("metal2",[pos1.lr(),pos2])
            self.add_via_center(self.m1_stack, (pos1.rx(), pos1.lc().y))
            self.add_via_center(self.m1_stack, pos2)
            
            pos3=self.nor_tree_inst.get_pin("in{0}".format(i)).uc()
            pos4=vector(pos3.x, y_off)
            self.add_path("metal2", [pos3, pos4])
            self.add_via_center(self.m1_stack, pos4+vector(0, self.via_shift("v1")))

    def connect_vdd_gnd(self):
        """ Connect vdd and gnd of all modules to vdd and gnd pins """
        
        modules=[self.inv_inst, self.flipflop_inst[self.size-1], 
                 self.xor_inst[self.size-1], self.reset_nand_inst]
        pins=["vdd", "gnd"]
        
        for mod in modules:
            for i in range(2):
                pos1=mod.get_pin(pins[i]).lc()
                pos2=vector(self.reset_inv_inst.lx()-(3+i)*self.m_pitch("m1"), pos1.y)
                self.add_path("metal1", [pos1, pos2])
                self.add_via_center(self.m1_stack, (pos2.x+0.5*self.m2_width, pos2.y), rotate=90)
            

    def add_layout_pins(self):
        """ Adds all input, ouput and power pins"""
        
        #reset pin
        rst_pin = self.reset_inv_inst.get_pin("A")
        self.add_path("metal1", [(-4*self.m_pitch("m1"), rst_pin.lc().y), rst_pin.lc()])
        self.add_layout_pin(text="reset",
                            layer=self.m1_pin_layer,
                            offset=(-4*self.m_pitch("m1"), rst_pin.by()),
                            width=self.m1_width,
                            height=self.m1_width)
        #lfsr_done pin
        lfsr_pin = self.reset_nand_inst.get_pin("B")
        x_off = lfsr_pin.lc().x-self.m_pitch("m1")
        y_off = max(self.reset_nand_inst.uy(), self.xor_inst[0].uy())+self.m_pitch("m1")
        self.add_wire(self.m1_stack, [(-4*self.m_pitch("m1"), y_off), (x_off, y_off), 
                                      (x_off, lfsr_pin.lc().y), lfsr_pin.lc()])
        self.add_layout_pin(text="lfsr_done",
                            layer=self.m1_pin_layer,
                            offset=(-4*self.m_pitch("m1"), y_off-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #r pin
        pos1=self.nand_err.get_pin("C").lc()
        pos2=vector(pos1.x-2*self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.nand_err.uy()+2*self.m_pitch("m1"))
        pos4=vector(-4*self.m_pitch("m1"), pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        self.add_layout_pin(text="r",
                            layer=self.m1_pin_layer,
                            offset=pos4-vector(0, 0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #clk pin
        clk_pin = self.reset_nand_inst.get_pin("C")
        x_off = clk_pin.lc().x-2*self.m_pitch("m1")
        y_off = max(self.reset_nand_inst.uy(), self.xor_inst[0].uy())+2*self.m_pitch("m1")
        self.add_wire(self.m1_stack, [(-4*self.m_pitch("m1"), y_off), (x_off, y_off), 
                                      (x_off, clk_pin.lc().y), clk_pin.lc()])
        self.add_layout_pin(text="clk",
                            layer=self.m1_pin_layer,
                            offset=(-4*self.m_pitch("m1"), y_off-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)
        
        #din inputs to FFs
        for i in range(self.size):
            pos1=self.flipflop_inst[i].get_pin("in").lc()
            pin_off=vector(pos1.x-self.m_pitch("m1"), self.flipflop_inst[i].by()-self.m_pitch("m1"))
            self.add_wire(self.m1_stack, [pin_off,pos1])
            self.add_layout_pin(text="din{0}".format(i),
                                layer=self.m2_pin_layer,
                                offset=(pin_off.x-0.5*self.m2_width, pin_off.y),
                                width=self.m2_width,
                                height=self.m2_width)

        #dout inputs to XORs
        for i in range(self.size):
            pin=self.xor_inst[i].get_pin("B")
            pin_off=vector(pin.lc().x-self.m_pitch("m1"), self.nor_tree_inst.uy()+3*self.m_pitch("m1"))
            self.add_path("metal3", [pin_off, pin.lc()])
            self.add_rect_center(layer="metal2", 
                                 offset=(pin.lx()+0.5*self.m2_width,pin.uc().y),
                                 width=self.m2_width,
                                 height=self.m2_minarea/self.m2_width)
            self.add_via(self.m1_stack, (pin.lc()-vector(0, 0.5*self.m2_width)))
            self.add_via(self.m2_stack, (pin.lc()-vector(0, 0.5*self.m3_width)))
            self.add_layout_pin(text="dout{0}".format(i),
                                layer=self.m3_pin_layer,
                                offset=(pin_off.x-0.5*self.m3_width, pin_off.y-self.m3_width),
                                width=self.m3_width,
                                height=self.m3_width)
        #output pin
        pin=self.inv_inst.get_pin("Z")
        x_off = max(self.xor_inst[self.size-1].rx(), pin.rx())+self.m_pitch("m1")
        self.add_path("metal1", [pin.lc(), (x_off, pin.lc().y)])
        self.add_layout_pin(text="err",
                            layer=self.m1_pin_layer,
                            offset=(x_off-self.m1_width, pin.by()),
                            width=self.m1_width,
                            height=self.m1_width)

        #vdd & gnd pins
        pins=["vdd", "gnd"]
        height=self.nor_tree_inst.uy()-self.flipflop_inst[0].by()+self.m_pitch("m1")
        for i in range(2):
            off=(self.reset_inv_inst.lx()-(i+3)*self.m_pitch("m1"),-self.m_pitch("m1"))
            self.add_rect(layer="metal2",
                          offset=off,
                          width=self.m2_width,
                          height=height)
            self.add_layout_pin(text=pins[i],
                               layer=self.m2_pin_layer,
                               offset=off,
                               width=self.m2_width,
                               height=self.m2_width)
        
