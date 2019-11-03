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
from nor_tree import nor_tree
from xor2 import xor2
from nor2 import nor2
from nand2 import nand2
from nand3 import nand3
from pinv import pinv
from flipflop import flipflop
from ptx import ptx
from tgate_array import tgate_array
from tech import info, layer, drc
from utils import ceil

class lfsr(design.design):
    """ Dynamically generated forward and reverse LFSR for input-size > 2"""

    def __init__(self, size, name="lfsr"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.size = size
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.compute_polynomials()
        self.create_modules()
        self.setup_layout_constants()
        self.add_modules()
        self.connect_modules()
        self.width= self.max_xoff-self.ctrl_xoff[3]+self.m_pitch("m1")
        self.height= self.max_yoff - self.min_yoff + 6*self.m_pitch("m1")

    def add_pins(self):
        """ Adds pins for lfsr module """
        
        for i in range(self.size):
            self.add_pin("addr{0}".format(i))
        self.add_pin_list(["up_down", "reset", "test", "done", "clk", "vdd", "gnd"])

    def create_modules(self):
        """ Construct all the required modules """
        
        self.nor_tree = nor_tree(size=self.size, name="lfsr_nor_tree")
        self.add_mod(self.nor_tree)

        self.ff = flipflop()
        self.add_mod(self.ff)
        
        self.xor2 = xor2()
        self.add_mod(self.xor2)
        
        self.nor2 = nor2()
        self.add_mod(self.nor2)
        
        self.tgate_array = tgate_array(self.size)
        self.add_mod(self.tgate_array)
        
        self.nand2 = nand2()
        self.add_mod(self.nand2)
        
        self.nand3 = nand3()
        self.add_mod(self.nand3)
        
        self.inv = pinv(size=1)
        self.add_mod(self.inv)

        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)
        
        self.pmos = ptx(tx_type="pmos", min_area = True, dummy_poly=False)
        self.add_mod(self.pmos)

        self.nmos = ptx(tx_type="nmos", min_area = False, dummy_poly=False)
        self.add_mod(self.nmos)

    def setup_layout_constants(self):
        """ Setup layout offsets, spaces, etc """

        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.gap= max(self.implant_space, self.well_space, 2*self.m_pitch("m1"))
        self.ygap= self.gap + self.m_pitch("m1")
        
        #Thsi is to share Drain & Source contacts of initializer MOSes
        self.nmos_overlap = self.nmos.get_pin("D").lx() - self.nmos.get_pin("S").lx()

    def compute_polynomials(self):
        """ Set the forward and reverse feedback polynomials for LFSRs. 
            reverse LFSR has to have a characteristic polynomial that is 
            the reciprocal characteristic polynomial of the forward LFSR."""
        
        if self.size == 3:
            self.forward = [2, 0]
            self.reverse=  [2, 1]
        if self.size == 4:
            self.forward = [3, 0]
            self.reverse=  [3, 2]
        if self.size == 5:
            self.forward = [3, 0]
            self.reverse=  [4, 2]
        if self.size == 6:
            self.forward = [5, 0]
            self.reverse=  [5, 4]
        if self.size == 7:
            self.forward = [6, 0]
            self.reverse=  [6, 5]
        if self.size == 8:
            self.forward = [6, 5, 4, 0]
            self.reverse=  [7, 5, 4, 3]
        if self.size == 9:
            self.forward = [5, 0]
            self.reverse=  [8, 4]
        if self.size == 10:
            self.forward = [7, 0]
            self.reverse=  [9, 6]
        if self.size == 11:
            self.forward = [9, 0]
            self.reverse=  [10, 8]
        if self.size == 12:
            self.forward = [4, 10, 11, 0]
            self.reverse=  [11, 10, 9,  3]
        if self.size == 13:
            self.forward = [8, 11, 12, 0]
            self.reverse=  [12, 11, 10, 7]
        if self.size == 14:
            self.forward = [2, 12, 13, 0]
            self.reverse=  [13, 12, 11, 1]
        if self.size == 15:
            self.forward = [14, 0]
            self.reverse=  [14, 13]
        if self.size == 16:
            self.forward = [4, 13, 15, 0]
            self.reverse=  [15, 14, 12, 3]
        if self.size == 17:
            self.forward = [14, 0]
            self.reverse=  [16, 13]
        if self.size == 18:
            self.forward = [11, 0]
            self.reverse=  [17, 10]
        if self.size == 19:
            self.forward = [14, 17, 18, 0]
            self.reverse=  [18, 17, 16, 13]
        if self.size == 20:
            self.forward = [17, 0]
            self.reverse=  [19, 16]
        if self.size > 20:
            debug.error("Invalid number of inputs! size less than 20 are allowed :(",-1)

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_flipflops()
        self.add_nor_tree()
        self.add_xor_gates(self.forward, self.reverse)
        self.add_init_moses()
        self.add_reset_test_gate()
        self.add_forward_reverse_selection_gates()
        self.add_tgate_array()
        self.add_lfsr_complete_gates()
    
    def connect_modules(self):
        """ Route modules """

        self.connect_nor_tree_to_ff()
        self.connect_nor_tree_to_xor(self.forward, self.reverse)
        self.connect_xor_to_ff(self.forward, self.reverse)
        self.add_layout_pins()
        self.connect_pmos_to_ff()
        self.connect_nmos_to_ff()
        self.connect_pmos_to_reset_b()
        self.connect_nmos_r_to_reset()
        self.connect_nmos_f_to_init()
        self.add_well_contacts()
        self.connect_reset_test_gate()
        self.connect_forward_gate()
        self.connect_ff_to_out_pins()
        self.connect_tgate_array_to_ff()
        self.connect_tgate_array_to_up_down()
        self.connect_lfsr_complete_gates()
        self.connect_vdd_gnd()
    
    def add_flipflops(self):
        """ Place flipflop gates """
        
        self.ff_up={}
        self.ff_down={}
        for i in range(self.size):
            #FFs for forward lfsr
            self.ff_up[self.size-1-i]= self.add_inst(name="ff_up{0}".format(self.size-1-i),
                                                     mod=self.ff,
                                                     offset=(i*self.ff.width,0))
            self.connect_inst(["Q_f{0}".format(self.size-i), "Q_f{0}".format(self.size-1-i), 
                               "Q_bar_f{0}".format(self.size-1-i), "clk_forward", "vdd", "gnd"])
            
        for i in range(self.size):
            #FFs for reverse lfsr
            self.ff_down[i]= self.add_inst(name="ff_down{0}".format(i),
                                           mod=self.ff,
                                           offset=(i*self.ff.width,0),
                                           mirror= "MX")
            if i == 0:
                self.connect_inst(["Q_r{0}".format(self.size), "Q_r{0}".format(i), 
                                   "Q_bar_r{0}".format(i), "clk_reverse", "vdd", "gnd"])
            else:
                self.connect_inst(["Q_r{0}".format(i-1), "Q_r{0}".format(i), 
                                   "Q_bar_r{0}".format(i), "clk_reverse", "vdd", "gnd"])

    def add_nor_tree(self):
        """ Place nor_tree """
        
        #nor_tree for forward lfsr
        offset=(0,self.ff.height+(self.size+2)*self.m_pitch("m2"))
        self.nor_tree_up= self.add_inst(name="nor_tree_up", mod=self.nor_tree,
                                        offset=offset)
        temp=[]
        for i in range(self.size-1, 0, -1):
            temp.append("Q_f{0}".format(i))
        temp.extend(["u_f0", "vdd", "gnd"])
        self.connect_inst(temp)

        #nor_tree for reverse lfsr
        offset = (0,-self.ff.height-(self.size+2)*self.m_pitch("m2"))
        self.nor_tree_down= self.add_inst(name="nor_tree_down", mod=self.nor_tree,
                                          offset= offset, mirror="MX")
        temp=[]
        for i in range(0, self.size-1, 1):
            temp.append("Q_r{0}".format(i))
        temp.extend(["u_d0", "vdd", "gnd"])
        self.connect_inst(temp)
    
    def add_xor_gates(self, forward, reverse):
        """ Place xor gates at the positions indicated by polynomials"""
        
        #xor for forward lfsr
        self.xor_up={}
        self.xor_down={}
        for i in forward:
            n = forward.index(i)
            offset = self.nor_tree_up.lr()+vector(n*self.xor2.width+(n+1)*self.gap, self.m_pitch("m1"))
            self.xor_up[n]= self.add_inst(name="xor_up{}".format(n), mod=self.xor2,
                                               offset=offset)
            if i == 0:
                self.connect_inst(["Q_f0", "u_f{}".format(n), "Q_f{}".format(self.size), "vdd", "gnd"])

            else:
                self.connect_inst(["Q_f{0}".format(i), "u_f{}".format(n), "u_f{}".format(n+1), "vdd", "gnd"])
        
        #xor for reverse lfsr
        for i in reverse:
            n = reverse.index(i)
            offset = self.nor_tree_down.ur()+vector(n*self.xor2.width+(n+1)*self.gap, -self.m_pitch("m1"))
            self.xor_down[n]= self.add_inst(name="xor_down{}".format(n), mod=self.xor2,
                                                 offset=offset, mirror="MX")
            if n == len(forward)-1:
                self.connect_inst(["Q_r{}".format(i), "u_d{}".format(n), "Q_r{}".format(self.size), "vdd", "gnd"])
            else:
                self.connect_inst(["Q_r{}".format(i), "u_d{}".format(n), "u_d{}".format(n+1), "vdd", "gnd"])

    
    def add_init_moses(self):
        """ Add initialize transistors to set the values of FFs at reset and when LFSR flips"""
        
        #PMOS for first reverse FF to set to vdd
        x_off=-(self.size+5)*self.m_pitch("m1")
        y_off= self.xor_down[1].by()
        self.nmos_r={}
        self.nmos_f={}
        self.init_pmos = self.add_inst(name="init_pmos_r0",mod=self.pmos,
                                       offset=(x_off, y_off),rotate=90)
        self.connect_inst(["Q_r0", "reset_b", "vdd", "vdd"])
        
        #NMOS for reverse FFs to set to gnd
        for i in range(2*(self.size-1)-1):
            x_off= self.init_pmos.rx()
            y_off=self.init_pmos.uy()+i*self.nmos_overlap + 4*self.well_extend_active
            self.nmos_r[i] = self.add_inst(name="init_nmos_r{0}".format(i),mod=self.nmos,
                                           offset=(x_off, y_off),rotate=90)
            if i%2:
                self.connect_inst(["gnd", "reset", "Q_r{0}".format(i+1-int((i-1)/2)), "gnd"])
            else:
                self.connect_inst(["Q_r{0}".format(i+1-int(i/2)), "reset", "gnd", "gnd"])
    
        #NMOS for forward FFs to set to gnd
        for i in range(2*(self.size-1)):
            x_off= self.init_pmos.rx()
            y_off=max(self.nmos_r[2*(self.size-1)-2].uy(),self.ff_down[0].by())+i*self.nmos_overlap
            
            if info["tx_dummy_poly"]:
                y_off = y_off+self.poly_space
            self.nmos_f[i] = self.add_inst(name="init_nmos_f{0}".format(i),mod=self.nmos,
                                           offset=(x_off, y_off),rotate=90)
            if i%2:
                self.connect_inst(["gnd", "init", "Q_f{0}".format(i-int((i-1)/2)), "gnd"])
            else:
                self.connect_inst(["Q_f{0}".format(i-int(i/2)), "init", "gnd", "gnd"])
    
        if info["tx_dummy_poly"]:
            self.dummy_poly=[]
            self.dummy_poly.append(self.init_pmos.ll()+vector(0, 0))
            self.dummy_poly.append(self.init_pmos.ul() -vector(0, self.poly_width))
            self.dummy_poly.append(self.nmos_r[0].ll()+vector(0, 0))
            self.dummy_poly.append(self.nmos_r[2*(self.size-1)-2].ul() -vector(0, self.poly_width))
            self.dummy_poly.append(self.nmos_f[2*(self.size-1)-1].ul() -vector(0, self.poly_width))
            self.dummy_poly.append(self.nmos_f[0].ll()+vector(0, 0))
            for i in self.dummy_poly:
                self.add_rect(layer="poly",
                              offset=i,
                              height=self.poly_width,
                              width=ceil(drc["minarea_poly_merge"]/self.poly_width))
    
    def add_reset_test_gate(self):
        """ Add AND gate to gate clk with test signal"""
        
        x_off= self.init_pmos.rx()-self.nand2.width-self.inv.width
        y_off= self.nmos_f[2*(self.size-1)-1].uy()+self.well_space+self.m_pitch("m1")+self.inv.height
        
        self.reset_inv = self.add_inst(name="reset_inv",mod=self.inv,
                                       offset=(x_off, y_off),mirror="MX")
        self.connect_inst(["reset", "reset_b", "vdd", "gnd"])
        
        y_off = self.reset_inv.uy() + self.gap + contact.m1m2.width
        self.init_nand = self.add_inst(name="init_nand",mod=self.nand2,
                                       offset=(x_off, y_off))
        self.connect_inst(["up_down_b", "done", "k", "vdd", "gnd"])
        
        self.init_inv = self.add_inst(name="init_inv",mod=self.inv,
                                      offset=(x_off+self.nand2.width, y_off))
        self.connect_inst(["k", "init", "vdd", "gnd"])
        
        y_off = self.init_inv.uy() + self.gap + contact.m1m2.width
        self.test_nand = self.add_inst(name="test_nand",mod=self.nand3,
                                       offset=(x_off, y_off))
        self.connect_inst(["test", "clk", "reset_b", "z_test", "vdd", "gnd"])
        
        self.test_inv = self.add_inst(name="test_inv",mod=self.inv,
                                      offset=(x_off+self.nand3.width, y_off))
        self.connect_inst(["z_test", "clk_in", "vdd", "gnd"])


    def add_forward_reverse_selection_gates(self):
        """ Add AND gates for forward/reverse selection"""
        
        #2 input nand + inv for forward lfsr
        x_off= self.init_pmos.rx() - self.nand2.width - self.inv5.width
        y_off= self.test_inv.uy()+self.nand2.height+self.well_space+contact.m1m2.width+self.m_pitch("m1")
        
        self.forward_nand = self.add_inst(name="forward_nand", mod=self.nand2,
                                          offset=(x_off, y_off), mirror="MX")
        self.connect_inst(["up_down", "clk_in", "z_forward1", "vdd", "gnd"])
        
        self.forward_inv = self.add_inst(name="forward_inv", mod=self.inv5,
                                         offset=(x_off+self.nand2.width, y_off),
                                         mirror="MX")
        self.connect_inst(["z_forward1", "clk_forward", "vdd", "gnd"])

        #2 input nand + inv for reverse lfsr
        x_off= self.forward_nand.lx()
        y_off= self.forward_nand.uy()
        y_off1=y_off+2*self.inv.height+self.well_space+2*self.m_pitch("m1")
        
        self.reverse_inv1 = self.add_inst(name="reverse_inv1", mod=self.inv,
                                          offset=(x_off,y_off1), mirror="MX")
        self.connect_inst(["up_down", "up_down_b", "vdd", "gnd"])

        self.reverse_nand = self.add_inst(name="reverse_nand", mod=self.nand2,
                                          offset=(x_off, y_off))
        self.connect_inst(["up_down_b", "clk_in", "z_reverse1", "vdd", "gnd"])
        
        self.reverse_inv = self.add_inst(name="reverse_inv", mod=self.inv5,
                                         offset=(x_off+self.nand2.width, y_off))
        self.connect_inst(["z_reverse1", "clk_reverse", "vdd", "gnd"])
    
    def add_tgate_array(self):
        """ Add array of T gates for forward/reverse output selection"""
        
        self.tgate_xoff = max(self.ff_up[0].rx(), self.xor_up[len(self.forward)-1].rx()+self.m2_space)
        y_off = self.xor_down[1].by() + self.m_pitch("m2")
        off=(self.tgate_xoff+(2*self.size+3)*self.m_pitch("m2"), y_off)
        
        self.tgate_ary= self.add_inst(name="tgate_array", mod=self.tgate_array, offset=off)
        temp=[]
        for i in range(self.size):
            temp.extend(["Q_r{0}".format(i), "Q_f{0}".format(i), "addr{0}".format(i)])
        temp.extend(["up_down", "up_down_b", "vdd", "gnd"])    
        self.connect_inst(temp)

        height= max(self.xor_up[1].uy(),self.tgate_ary.uy())-self.xor_down[1].by()
        for i in range(2*self.size):
            off1= vector(self.tgate_xoff+(i+3)*self.m_pitch("m2"), y_off)
            self.add_rect(layer="metal2", 
                          offset=off1, 
                          width=contact.m1m2.width, 
                          height=height)

    def add_lfsr_complete_gates(self):
        """ Add array of nor2 + inv gates for "done" output detection"""
        
        x_off = self.tgate_ary.rx()+(self.size+6)*self.m_pitch("m2")
        self.nor2_inst={}
        self.inv_inst={}
        
        for i in range(self.size-1):
            off1=(x_off, self.xor_down[1].by() + i * (self.inv.height+self.ygap))
            self.nor2_inst[i]= self.add_inst(name="nor2{0}".format(i), mod=self.nor2,
                                             offset=off1)

            if i==0: 
                self.connect_inst(["addr1", "addr0", "addr_zb{0}".format(i), "vdd", "gnd"])
            if i == self.size-2:
                self.connect_inst(["addr{0}".format(i+1), "addr_z{0}".format(i-1), "done", "vdd", "gnd"])
            if 0 < i < self.size-2:
                self.connect_inst(["addr{0}".format(i+1), "addr_z{0}".format(i-1), "addr_zb{0}".format(i), "vdd", "gnd"])
        
        for i in range(self.size-2):
            off2=(x_off+self.nor2.width, self.xor_down[1].by() + i * (self.inv.height+self.ygap))

            self.inv_inst[i]= self.add_inst(name="inv{0}".format(i), mod=self.inv,
                                            offset=off2)
            self.connect_inst(["addr_zb{0}".format(i), "addr_z{0}".format(i), "vdd", "gnd"])


    def connect_lfsr_complete_gates(self):
        """ connect array of nor2 + inv gates for "done" output detection"""

        pin=self.nor2_inst[0].get_pin("B").lc()
        x_off = self.tgate_ary.rx()+self.m_pitch("m2")
        self.add_path("metal1", [(x_off, pin.y) , pin])
        self.add_via_center(self.m1_stack, (x_off, pin.y))
        
        for i in range(self.size-1):
            pin=self.nor2_inst[i].get_pin("A").lc()
            x_off = self.tgate_ary.rx()+(i+2)*self.m_pitch("m2")
            self.add_path("metal3", [(x_off, pin.y) , pin])
            self.add_via_center(self.m2_stack, (x_off, pin.y))
            self.add_via_center(self.m1_stack, (pin.x-0.5*contact.m1m2.width, pin.y))
            self.add_via_center(self.m2_stack, (pin.x-0.5*contact.m1m2.width, pin.y))
            self.add_rect(layer="metal2", 
                          offset=(pin.x-contact.m1m2.width, pin.y), 
                          width=contact.m1m2.width, 
                          height=ceil(self.m2_minarea/contact.m1m2.width))

        for i in range(self.size-2):
            pos1=self.inv_inst[i].get_pin("Z").lc()
            pos2=vector(pos1.x+self.m_pitch("m2"), pos1.y)
            pos3=vector(pos2.x, self.inv_inst[i].uy()+self.m_pitch("m1"))
            pos6=self.nor2_inst[i+1].get_pin("B").lc()
            pos4=vector(pos6.x-self.m_pitch("m1"), pos3.y)
            pos5=vector(pos6.x-self.m_pitch("m1"), pos6.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])
        

    def connect_tgate_array_to_ff(self):
        """ Connect output of FFs to inputs of tgate_array"""
        
        #connections for forward lfsr
        max_xoff = self.ff_up[self.size-1].get_pin("out").lx()
        for i in range(self.size):
            y_off = self.ff_up[i].uy()+(i+1)*self.m_pitch("m2")
            x_off = self.tgate_xoff+(1+2*self.size-2*i)*self.m_pitch("m2")
            self.add_path("metal3", [(max_xoff, y_off ), (x_off, y_off)])
            self.add_via_center(self.m2_stack, (x_off+0.5*contact.m2m3.width, y_off)) 

        #connections for reverse lfsr
        for i in range(self.size):
            y_off = self.ff_down[i].by()-(i+1)*self.m_pitch("m2")
            x_off = self.tgate_xoff+(2*i+1+3)*self.m_pitch("m2")
            self.add_path("metal3", [(max_xoff, y_off ), (x_off, y_off)])
            self.add_via_center(self.m2_stack, (x_off+0.5*contact.m2m3.width, y_off)) 

        #connections for tgate array
        for i in range(self.size):
            off1 = self.tgate_ary.get_pin("in1{0}".format(i)).lc()
            off2 = self.tgate_ary.get_pin("in2{0}".format(i)).lc()
            x_off = self.tgate_xoff+(4+2*i)*self.m_pitch("m2")
            self.add_path("metal1", [(x_off, off1.y), off1])
            self.add_path("metal1", [(x_off-self.m_pitch("m2"), off2.y), off2])
            self.add_via_center(self.m1_stack, (x_off+0.5*contact.m1m2.width, off1.y))
            self.add_via_center(self.m1_stack, (x_off-self.m_pitch("m2")+0.5*contact.m1m2.width, off2.y)) 

    def connect_tgate_array_to_up_down(self):
        """ Connect up_down and up_down_b to tgate_array"""
        
        pins=["up_down", "up_down_b"]
        x_off1=[self.ctrl_xoff[1], self.reverse_inv1.get_pin("Z").lc().x+self.m_pitch("m1")]
        y_off1= self.reverse_inv1.get_pin("Z").lc().y
        for i in range(2):
            pos1= (x_off1[i], y_off1)
            pos2= (x_off1[i], self.max_yoff + (i+1)*self.m_pitch("m1"))
            pos4=self.tgate_ary.get_pin(pins[i]).uc()
            pos3=(pos4.x, self.max_yoff + (i+1)*self.m_pitch("m1"))
            self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4] )

    def connect_nor_tree_to_ff(self):
        """ Connect output of FFs to inputs of nor_tree"""
        
        self.yoff_f={}
        #connections for forward lfsr
        for i in range(self.size):
            self.yoff_f[self.size-1-i] = self.ff_up[i].uy()+(i+1)*self.m_pitch("m2")
            pos1= (0, self.yoff_f[self.size-1-i] )
            pos2= (self.ff.width*self.size, self.yoff_f[self.size-1-i])
            self.add_path("metal3", [pos1, pos2])
            
            if i < self.size-1:
                nor_tree_in_off =self.nor_tree_up.get_pin("in{0}".format(i)).uc() 
                self.add_path("metal2",[nor_tree_in_off, (nor_tree_in_off.x, self.yoff_f[self.size-1-i])])
                self.add_via_center(self.m2_stack, (nor_tree_in_off.x, self.yoff_f[self.size-1-i])) 
        
            ff_out_off = self.ff_up[self.size-1-i].get_pin("out").lr()
            self.add_path("metal2",[ff_out_off, (ff_out_off.x, self.yoff_f[self.size-1-i])])
            self.add_via_center(self.m2_stack, (ff_out_off.x, self.yoff_f[self.size-1-i])) 
        
        self.yoff_r={}
        #connections for reverse lfsr
        for i in range(self.size):
            self.yoff_r[i] = self.ff_down[i].by()-(i+1)*self.m_pitch("m2")
            self.add_path("metal3", [(0, self.yoff_r[i] ), (self.ff.width*self.size, self.yoff_r[i])])
            
            if i < self.size-1:
                nor_tree_in_off =self.nor_tree_down.get_pin("in{0}".format(i)).uc() 
                self.add_path("metal2",[nor_tree_in_off, (nor_tree_in_off.x, self.yoff_r[i])])
                self.add_via_center(self.m2_stack, (nor_tree_in_off.x, self.yoff_r[i])) 
        
            ff_out_off = self.ff_down[i].get_pin("out").ur()
            self.add_path("metal2",[ff_out_off, (ff_out_off.x, self.yoff_r[i])])
            self.add_via_center(self.m2_stack, (ff_out_off.x, self.yoff_r[i])) 


    def connect_nor_tree_to_xor(self, forward, reverse):
        """ Connect output of nor_tree to input B of first XOR
            Connect output of i XOR to inputs of i+1 XOR"""
        
        #connections for forward lfsr
        pos1=self.nor_tree_up.get_pin("out")
        pos2=self.xor_up[0].get_pin("B").lc()
        mid_pos1 = vector(pos1.rx()+2*self.m1_width, pos1.lc().y)
        mid_pos2 = vector(mid_pos1.x, min(pos1.lc().y, pos2.y))
        self.add_path("metal1", [pos1.lc(),mid_pos1,mid_pos2,pos2])
        
        for i in range(len(forward)-1):
            pos1=self.xor_up[i].get_pin("Z")
            pos2=self.xor_up[i+1].get_pin("B")
            mid_pos1=vector(pos1.rx(), min(pos1.lc().y, pos2.lc().y))
            self.add_path("metal1", [(pos1.rx()-0.5*self.m1_width,pos1.lc().y), mid_pos1, pos2.lc()])
        
        for i in forward:
            n = forward.index(i)
            pos3=self.xor_up[n].get_pin("A").lc()
            pos4=vector(self.xor_up[n].get_pin("A").lx()-0.5*contact.m1m2.width, pos3.y)
            left_bend=[]
            right_bend=[]
            for j in range(self.size):
                pin = self.ff_up[j].get_pin("in").lc().x
                if abs(pos3.x - pin) < self.m_pitch("m2"):
                    if pos3.x < pin: 
                         left_bend.append(i) 
                    else:
                         right_bend.append(i) 

            if i in left_bend or right_bend:                     
                pos5=vector(pos4.x, self.xor_up[n].by()-self.m_pitch("m1"))
                if i in left_bend:
                    pos6=vector(pos3.x-2*self.m_pitch("m2"), pos5.y)
                if i in right_bend:
                    pos6=vector(pos5.x+2*self.m_pitch("m2"), pos5.y)
                pos7=vector(pos6.x, self.yoff_f[i])
                self.add_wire(self.m1_stack, [pos3, pos4, pos5, pos6, pos7])
                self.add_via_center(self.m2_stack, pos7)
            else:
                pos4=vector(self.xor_up[n].get_pin("A").lx()-0.5*contact.m1m2.width, pos3.y)
                pos5=vector(pos4.x, self.yoff_f[i])
                self.add_wire(self.m1_stack, [pos3, pos4, pos5])
                self.add_via_center(self.m2_stack, pos5)

        #connections for reverse lfsr
        pos1=self.nor_tree_down.get_pin("out")
        pos2=self.xor_down[0].get_pin("B").lc()
        mid_pos1=vector(pos1.rx()+2*self.m1_width, pos1.lc().y,)
        mid_pos2=vector(mid_pos1.x, max(pos1.lc().y, pos2.y))
        self.add_path("metal1", [pos1.lc(), mid_pos1, mid_pos2, pos2])

        for i in range(len(reverse)-1):
            pos1=self.xor_down[i].get_pin("Z")
            pos2=self.xor_down[i+1].get_pin("B")
            mid_pos1=vector(pos1.rx(), max(pos1.lc().y, pos2.lc().y))
            self.add_path("metal1", [(pos1.rx()-0.5*self.m1_width,pos1.lc().y), mid_pos1, pos2.lc()])
        
        for i in reverse:
            n = reverse.index(i)
            pos3=self.xor_down[n].get_pin("A").lc()
            pos4=vector(self.xor_down[n].get_pin("A").lx()-0.5*contact.m1m2.width, pos3.y)
            left_bend=[]
            right_bend=[]
            for j in range(self.size):
                pin = self.ff_down[j].get_pin("in").lc().x
                if abs(pos3.x - pin) < self.m_pitch("m2"):
                    if pos3.x < pin: 
                         left_bend.append(i) 
                    else:
                         right_bend.append(i) 

            if i in left_bend or right_bend:                     
                pos5=vector(pos4.x, self.xor_down[n].uy()+self.m_pitch("m1"))
                if i in left_bend:
                    pos6=vector(pos3.x-2*self.m_pitch("m2"), pos5.y)
                if i in right_bend:
                    pos6=vector(pos5.x+2*self.m_pitch("m2"), pos5.y)
                pos7=vector(pos6.x, self.yoff_r[i])
                self.add_wire(self.m1_stack, [pos3, pos4, pos5, pos6, pos7])
                self.add_via_center(self.m2_stack, pos7)
            else:
                pos5=vector(pos4.x, self.yoff_r[i])
                self.add_wire(self.m1_stack, [pos3, pos4, pos5])
                self.add_via_center(self.m2_stack, pos5)


    def connect_xor_to_ff(self, forward, reverse):
        """ Connect output of last XOR to input of first flipflop"""
        
        #connections for forward lfsr
        k = len(reverse)-1
        pin = self.xor_up[k].get_pin("Z")
        pos1=vector(pin.rx()+0.5*self.m2_width, pin.uc().y)
        pos2=vector(pos1.x,self.ff_up[self.size-1].uy()+(self.size+1)*self.m_pitch("m2"))
        pos3=vector(self.ff_up[self.size-1].lx()-self.m_pitch("m1"), pos2.y)
        pos4=self.ff_up[self.size-1].get_pin("in").lc()+vector(self.m_pitch("m1"),0) 
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])
        self.add_via_center(self.m1_stack, (pos1.x, pos1.y-0.5*self.m1_width-self.via_shift("v1")))
        self.add_via_center(self.m2_stack, pos4, rotate=90)

        #connections for reverse lfsr
        pin = self.xor_down[k].get_pin("Z")
        pos1=vector(pin.rx()+0.5*self.m2_width, pin.uc().y)
        pos2=vector(pos1.x,self.ff_down[0].by()-(self.size+1)*self.m_pitch("m2"))
        pos3=vector(self.ff_down[0].lx()-self.m_pitch("m1"), pos2.y)
        pos4=self.ff_down[0].get_pin("in").lc()+vector(self.m_pitch("m1"),0)
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])
        self.add_via_center(self.m1_stack, (pos1.x, pos1.y-0.5*self.m1_width-self.via_shift("v1")))
        self.add_via_center(self.m2_stack, pos4, rotate=90)

        
    def add_layout_pins(self):
        """ Add output and power layout pins"""

        self.max_yoff = max(self.reverse_inv1.uy(), self.nor2_inst[self.size-2].uy(), 
                            self.tgate_ary.uy(), self.xor_up[1].uy())
        self.min_yoff = self.xor_down[1].by() - 2*self.m_pitch("m1")
        
        for i in range(self.size):
            x_off =self.tgate_ary.rx()
            y_off=self.tgate_ary.get_pin("out{0}".format(i)).lc().y
            pos1= (x_off+(i+1)*self.m_pitch("m2"), self.tgate_ary.by())
            pos2= (x_off+(i+1)*self.m_pitch("m2"),self.max_yoff)
            self.add_path("metal2", [pos1, pos2], width=contact.m1m2.width)
            self.add_path("metal1", [(x_off, y_off), (x_off+(i+1)*self.m_pitch("m2"), y_off)])
            self.add_via_center(self.m1_stack , (x_off+(i+1)*self.m_pitch("m2"), y_off))
            off=(x_off+(i+1)*self.m_pitch("m2")-0.5*self.m2_width, self.max_yoff-self.m2_width)
            self.add_layout_pin(text="addr{0}".format(i), 
                                layer=self.m2_pin_layer, 
                                offset=off,
                                width=self.m2_width,
                                height=self.m2_width)
            
        
        self.max_xoff = self.inv_inst[0].rx()+self.m_pitch("m1")
        pin =self.nor2_inst[self.size-2].get_pin("Z")
        self.add_path("metal1", [pin.lc(), (self.max_xoff, pin.lc().y)])
        self.add_layout_pin(text="done", 
                                layer=self.m1_pin_layer, 
                                offset=(self.max_xoff-self.m1_width, pin.by()),
                                width=self.m1_width,
                                height=self.m1_width)

        
        pin=["reset", "up_down", "vdd", "gnd"]
        self.ctrl_xoff={}
        for i in range(4):
            self.ctrl_xoff[i] = x_off = self.reverse_inv1.lx()-(i+2)* self.m_pitch("m1")
            self.add_path("metal2",[(x_off,self.xor_down[1].by()), 
                                    (x_off, self.max_yoff)] )

        for i in range(3):
            pin_off=(self.ctrl_xoff[i+1]-0.5*self.m2_width, self.max_yoff-self.m2_width)
            self.add_layout_pin(text=pin[i+1], 
                                layer=self.m2_pin_layer, 
                                offset=pin_off,
                                width=self.m2_width,
                                height=self.m2_width)
        
        
        pos2=self.reset_inv.get_pin("A").lc()
        pos1= (self.ctrl_xoff[3], pos2.y)
        self.add_path("metal1", [pos1,pos2])
        self.add_layout_pin(text="reset", 
                            layer=self.m1_pin_layer, 
                            offset=(self.ctrl_xoff[3], self.reset_inv.get_pin("A").by()),
                            width=self.m1_width,
                            height=self.m1_width)

        self.add_layout_pin(text="test", 
                            layer=self.m1_pin_layer, 
                            offset=(self.ctrl_xoff[3], self.test_nand.get_pin("A").by()),
                            width=self.m1_width,
                            height=self.m1_width)
        
        self.add_layout_pin(text="clk", 
                            layer=self.m1_pin_layer, 
                            offset=(self.ctrl_xoff[3],self.test_nand.get_pin("B").by()),
                            width=self.m1_width,
                            height=self.m1_width)

        #second set of power pins on right side of layout
        pin=["vdd", "gnd"]
        for i in range(2):
            self.ctrl_xoff[i+4] = x_off = self.tgate_xoff+(i+1)* self.m_pitch("m1")
            pos1=(x_off,self.xor_down[1].by())
            pos2=(x_off, self.max_yoff+contact.m1m2.width)
            self.add_path(layer="metal2",coordinates=[pos1,pos2], width=contact.m1m2.width )


    def connect_pmos_to_ff(self):
        """ Connect initial pmos to flipflop inputs"""
        
        self.out_xoff={}
        height1 = max(self.nmos_r[2*(self.size-1)-2].uy(), self.ff_down[0].by())-self.m_pitch("m2")
        height2 = max(self.nmos_f[2*(self.size-1)-1].uy(), self.nor_tree_up.by())
        for i in range(self.size):
            self.out_xoff[i]= x_off = -(i+4)* self.m_pitch("m1")
            self.add_path("metal2",[(x_off, self.xor_down[1].by()), 
                                    (x_off, height1)], width=contact.m1m2.width)
            self.add_path("metal2",[(x_off, self.nmos_f[0].by()), 
                                    (x_off, height2)], width=contact.m1m2.width)
        
        #First reverse ff is initialized with vdd
        pin=self.init_pmos.get_pin("S").lc()
        self.add_path ("metal1", [pin, (self.out_xoff[0], pin.y)])
        self.add_via_center(self.m1_stack,(self.out_xoff[0], pin.y))
        pin=self.init_pmos.get_pin("D").lc()
        self.add_path ("metal1", [pin, (self.ctrl_xoff[2], pin.y)])
        self.add_via_center(self.m1_stack,(self.ctrl_xoff[2], pin.y))


    def connect_nmos_to_ff(self):
        """ Connect initial nmos to flipflop inputs"""
        
        #second to last reverse ffs are initialized with gnd
        for i in range(2*(self.size-1)-1):
            if i%2:
                pin=self.nmos_r[i].get_pin("D").lc()
                self.add_path ("metal1", [pin, (self.out_xoff[int((i-1)/2)+2], pin.y)])
                self.add_via_center(self.m1_stack,(self.out_xoff[int((i-1)/2)+2], pin.y) )
                pin=self.nmos_r[i].get_pin("S").lc()
                self.add_path ("metal1", [pin, (self.ctrl_xoff[3], pin.y)])
                self.add_via_center(self.m1_stack,(self.ctrl_xoff[3], pin.y) )
            
            else: 
                pin=self.nmos_r[i].get_pin("S").lc()
                self.add_path ("metal1", [pin, (self.out_xoff[int(i/2)+1], pin.y)])
                self.add_via_center(self.m1_stack,(self.out_xoff[int(i/2)+1], pin.y) )
                pin=self.nmos_r[i].get_pin("D").lc()
                self.add_path ("metal1", [pin, (self.ctrl_xoff[3], pin.y)])
                self.add_via_center(self.m1_stack,(self.ctrl_xoff[3], pin.y) )
        
        #first to last forward ffs are initialized with gnd
        for i in range(2*(self.size-1)):
            if i%2:
                pin=self.nmos_f[i].get_pin("D").lc()
                self.add_path ("metal1", [pin, (self.out_xoff[int((i-1)/2)+1], pin.y)])
                self.add_via_center(self.m1_stack,(self.out_xoff[int((i-1)/2)+1], pin.y))
                pin=self.nmos_f[i].get_pin("S").lc()
                self.add_path ("metal1", [pin, (self.ctrl_xoff[3], pin.y)])
                self.add_via_center(self.m1_stack,(self.ctrl_xoff[3], pin.y))
            
            else: 
                pin=self.nmos_f[i].get_pin("S").lc()
                self.add_path ("metal1", [pin, (self.out_xoff[int(i/2)], pin.y)])
                self.add_via_center(self.m1_stack,(self.out_xoff[int(i/2)], pin.y) )
                pin=self.nmos_f[i].get_pin("D").lc()
                self.add_path ("metal1", [pin, (self.ctrl_xoff[3], pin.y)])
                self.add_via_center(self.m1_stack,(self.ctrl_xoff[3], pin.y) )


    def connect_pmos_to_reset_b(self):
        """ Connect gate of initial pmos to reset_b"""
        
        pos1 = self.reset_inv.get_pin("Z").lc()
        pos2 = vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.init_pmos.by())
        pos4 = vector(self.init_pmos.lx()-self.m_pitch("m1")-self.poly_space+contact.poly.height, 
                      pos3.y-2*contact.poly.width+0.5*self.m1_width)
        self.add_wire (self.m1_stack, [pos1, pos2, pos3, pos4])

        pos3=vector(pos2.x, self.reset_inv.uy()+self.m_pitch("m1"))
        pos6=self.test_nand.get_pin("C").lc()
        pos4=vector(self.forward_nand.lx()-self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x,pos6.y)
        self.add_wire (self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])

        pos1=pin=self.init_pmos.get_pin("G").lc()
        pos2=vector(self.init_pmos.lx()-self.m_pitch("m1")-self.poly_space, pos1.y)
        pos22=vector(pos2.x, self.init_pmos.get_pin("G").uc().y)
        pos3= vector(pos2.x, self.init_pmos.by()-2*contact.poly.width)
        pos6 = vector(pos3.x+0.5*contact.poly.first_layer_height+self.via_shift("co"), pos3.y)
        
        
        self.add_path("poly", [pos1, pos2])
        self.add_path("poly", [pos22, pos3], width =contact.poly.first_layer_height )
        self.add_contact(self.poly_stack, pos6, rotate=90)
        self.add_via(self.m1_stack, (pos6.x+contact.m1m2.height, pos6.y), rotate=90)
        self.add_rect(layer="metal2", 
                      offset=pos3, 
                      width=ceil(self.m2_minarea/contact.m1m2.width), 
                      height=contact.m1m2.width)
        
        
    def connect_nmos_r_to_reset(self):
        """ Connect gates of all initial reverse nmoses to reset input"""
        
        self.x_off = self.nmos_r[0].lx()-2*self.m_pitch("m1")-self.well_enclose_active
        for i in range(2*(self.size-1)-1):
            pin=self.nmos_r[i].get_pin("G").lc()
            self.add_path ("poly", [pin, (self.x_off, pin.y)])
       
        
        pos1=(self.x_off, self.nmos_r[2*(self.size-1)-2].get_pin("G").uc().y)
        pos2=(self.x_off, self.nmos_r[0].by()+drc["extra_to_poly"])
        self.add_path ("poly", [pos1,pos2], width=contact.poly.first_layer_height)
        
        #add poly_contact at gate and connect gate to reset rail
        y_off=self.nmos_r[0].by()+drc["extra_to_poly"]
        pos1=(self.x_off-0.5*contact.poly.width, y_off+0.5*contact.poly.height)
        pos2=(self.ctrl_xoff[0], y_off+0.5*contact.poly.height)
        self.add_path ("metal1", [pos1,pos2])
        self.add_contact(self.poly_stack, 
                        (self.x_off-0.5*contact.poly.first_layer_height, y_off-self.via_shift("co")))
        self.add_via_center(self.m1_stack, pos2)
        

    def connect_nmos_f_to_init(self):
        """ Connect gates of all initial forward nmoses to init pin"""
        
        #connect all the gates together with poly
        self.x_off = self.nmos_f[0].lx()-2*self.m_pitch("m1")-self.well_enclose_active
        for i in range(2*(self.size-1)):
            pin=self.nmos_f[i].get_pin("G").lc()
            self.add_path ("poly", [pin, (self.x_off, pin.y)])
        
        pos1=(self.x_off, self.nmos_f[2*(self.size-1)-1].get_pin("G").uc().y)
        pos2=(self.x_off, self.nmos_f[0].by()+drc["extra_to_poly"])
        self.add_path ("poly", [pos1,pos2], width=contact.poly.first_layer_height)
        
        #add poly_contact at gate and connect gate to reset rail
        xoff= self.x_off-0.5*contact.poly.first_layer_height
        y_off=self.nmos_f[0].by()+drc["extra_to_poly"]
        self.add_contact(self.poly_stack, (xoff, y_off-self.via_shift("co")))
        pos1=self.init_inv.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.reset_inv.by()-self.m_pitch("m1"))
        pos4=vector(self.reset_inv.rx()-self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, y_off+0.5*contact.poly.height)
        pos6=vector(self.x_off, pos5.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos6])

    def add_well_contacts(self):
        """ Add both nwell and pwell contacts with implant layer"""

        
        #add implant and well layers for initial nmos & pmos and well contacts
        x_shift = self.x_off-self.m_pitch("m1")-2*self.implant_enclose_poly
        width = self.init_pmos.rx() - x_shift + self.implant_enclose_poly

        width3=self.init_pmos.height+ self.implant_enclose_poly  + 2*self.m_pitch("m1")
        width2 = width - width3
        off0= vector(x_shift, self.init_pmos.by() - 2*self.m_pitch("m1"))
        off1= vector(off0.x, self.init_pmos.uy()+self.well_extend_active+drc["extra_to_poly"])
        off2 =vector(off0.x, self.nmos_r[0].by())
        off3 =vector(off0.x, self.init_pmos.by() - 2*self.m_pitch("m1"))
        off4 =vector(self.init_pmos.lx()-2*self.m_pitch("m1"), self.init_pmos.by() - 2*self.m_pitch("m1")) 
        
        height0=self.init_pmos.uy()+self.well_extend_active-self.init_pmos.by() + 2*self.m_pitch("m1")+drc["extra_to_poly"]
        height1=self.nmos_f[2*(self.size-1)-1].uy() - self.init_pmos.uy()-self.well_extend_active+drc["extra_to_poly"]
        height2=self.nmos_f[2*(self.size-1)-1].uy() - self.nmos_r[0].by()+2*drc["extra_to_poly"]
        height3=self.nmos_r[0].by()-self.init_pmos.uy()-drc["extra_to_poly"]-self.well_extend_active
        
        if info["has_nwell"]:
            self.add_rect(layer="nwell", offset=off0, width = width, height=height0)
        
        if info["has_pwell"]:
            self.add_rect(layer="pwell", offset=off1, width = width, height=height1)
        
        if info["has_nimplant"]:
            self.add_rect(layer="nimplant", offset=off2, width = width, height=height2)
            self.add_rect(layer="nimplant", offset=off3, width = width2, height=height0)

        if info["has_pimplant"]:
            self.add_rect(layer="pimplant", offset=off1, width = width, height=height3)
            self.add_rect(layer="pimplant", offset=off4, width=width3, height=height0)
        
        #add well contact for nmoses
        pcontact_off = self.init_pmos.ul()+vector(0, 2*self.well_extend_active)
        self.add_contact(("active", "contact", "metal1"), pcontact_off, rotate=90)

        #add well contact for pmos
        ncontact_off = vector(off0.x+self.well_enclose_active, self.init_pmos.by())
        self.add_contact(("active", "contact", "metal1"), ncontact_off)
        
        #add  active layer for min_arae active rule
        pactive_off = pcontact_off-vector(contact.active.height, 0)
        nactive_off = ncontact_off
        self.add_rect(layer="active", 
                      offset=pactive_off, 
                      width=ceil(self.active_minarea/contact.active.width), 
                      height=contact.active.width)
        self.add_rect(layer="active", 
                      offset=nactive_off, 
                      width=contact.active.width, 
                      height=ceil(self.active_minarea/contact.active.width))

        self.add_rect(layer="extra_layer", 
                      layer_dataType = layer["extra_layer_dataType"], 
                      offset=off1, 
                      width=width, 
                      height=height3-drc["extra_to_poly"])
        self.add_rect(layer="extra_layer", 
                      layer_dataType = layer["extra_layer_dataType"], 
                      offset=off0, 
                      width=width-width3, 
                      height=height0)

        vt_offset=self.init_pmos.ll()-vector(0, 2*self.m_pitch("m1"))
        vt_height = self.pmos.width+2*self.m_pitch("m1")+drc["extra_to_poly"]
        self.add_rect(layer="vt",
                      offset=vt_offset,
                      layer_dataType = layer["vt_dataType"],
                      width=self.pmos.height,
                      height=vt_height)
        self.add_rect(layer="vt",
                      offset=self.nmos_r[0].ll(),
                      layer_dataType = layer["vt_dataType"],
                      width=self.nmos.height,
                      height=self.nmos_f[2*(self.size-1)-1].uy()-self.nmos_r[0].by())
        
        #connect pwell contact to gnd
        pos1=vector(self.init_pmos.lx(), self.init_pmos.uy()+2*self.well_extend_active+0.5*self.m1_width)
        pos2=vector(self.ctrl_xoff[3], pos1.y)
        self.add_path ("metal1", [pos1, pos2], width=contact.m1m2.width)
        self.add_via_center(self.m1_stack, pos2)
        
        #connect nwell contact to vdd
        pos1 = vector(nactive_off.x+0.5*self.m1_width,nactive_off.y)
        pos2 = vector(pos1.x, self.init_pmos.get_pin("D").uy())
        self.add_path ("metal1", [pos1, pos2], width=contact.m1m2.width)

    def connect_reset_test_gate(self):
        """ Connect terminals of test gate to corresponding input"""
        
        pin= ["A", "B"]
        for i in range(2):
            pos1 = self.test_nand.get_pin(pin[i]).lc()
            pos2=(self.ctrl_xoff[3], pos1.y)
            self.add_path ("metal1", [pos1, pos2])
            #self.add_via_center(self.m1_stack, pos2)
        
        self.add_path ("metal1", [self.test_nand.get_pin("Z").lc(),
                                  self.test_inv.get_pin("A").lc()])    
        pos1 = self.reset_inv.get_pin("A").lc()
        pos2=(self.ctrl_xoff[0], pos1.y)
        self.add_path ("metal1", [pos1, pos2])
        self.add_via_center(self.m1_stack, pos2)
    
    def connect_forward_gate(self):
        """ Connect terminals of forward-reverse selection gate to corresponding input"""
        
        mod= [self.forward_nand, self.reverse_nand]
        ff= [self.ff_up[0], self.ff_down[self.size-1]]
        for i in range(2):
            pos1 = mod[i].get_pin("B").lc()
            pos2=(pos1.x-self.m_pitch("m1"), pos1.y)
            self.add_path ("metal1", [pos1, pos2])
            self.add_via_center(self.m1_stack, pos2)

        pos1=self.reverse_nand.get_pin("B").lc()-vector(self.m_pitch("m1"),0)
        pos2=vector(pos1.x, self.forward_nand.by() - self.m_pitch("m1"))
        pos4 =self.test_inv.get_pin("Z").lc()
        pos3 = vector(pos4.x+self.m_pitch("m1"), pos2.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

        mod= [self.forward_nand, self.reverse_inv1]
        for i in range(2):
            pos1 = mod[i].get_pin("A").lc()
            pos2=(self.ctrl_xoff[1], pos1.y)
            self.add_path ("metal1", [pos1, pos2])
            self.add_via_center(self.m1_stack, pos2)

        #connect input A of init_nand to up_down_b
        pos1=self.reverse_inv1.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.reverse_inv1.by()-self.m_pitch("m1"))
        pos4=vector(self.reverse_nand.get_pin("A").uc().x, pos3.y)
        pos5=self.reverse_nand.get_pin("A").uc()
        pos6=self.init_nand.get_pin("A").lc()
        self.add_wire(self.m1_stack, [pos1,pos2,pos3,pos4,pos6])
        self.add_via_center(self.m1_stack, pos5)
        
        #connect input B of init_nand to done
        pin=self.nor2_inst[self.size-2].get_pin("Z")
        pos1=vector(pin.rx(), pin.lc().y)
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.max_yoff+3*self.m_pitch("m1"))
        pos4=vector(self.forward_nand.lx()-6*self.m_pitch("m1"), pos3.y)
        pos5=self.init_nand.get_pin("B").lc()
        self.add_wire(self.m1_stack, [pos1,pos2,pos3,pos4,pos5])

        mod= [self.forward_inv, self.reverse_inv]
        for i in range(2):
            pos3 = mod[i].get_pin("Z").lc()
            pos4=vector(-(i+2)*self.m_pitch("m1"), pos3.y)
            pos5=vector(pos4.x, ff[i].get_pin("clk").lc().y)
            pos6=ff[i].get_pin("clk").lc()
            if (pos3.y - pos5.y < 2*self.m_pitch("m1")):
                self.add_path ("metal1", [pos3, pos4, pos5, pos6])
            else:
                self.add_wire (self.m1_stack, [pos3, pos4, pos5, pos6])

        self.add_path ("metal1", [self.forward_nand.get_pin("Z").lc(), 
                                  self.forward_inv.get_pin("A").lc()])    
        self.add_path ("metal1", [self.reverse_nand.get_pin("Z").lc(), 
                                  self.reverse_inv.get_pin("A").lc()])    

    def connect_ff_to_out_pins(self):
        """ Connect flipflop inputs to output pins"""
        
        #reverse lfsr
        for i in range(self.size-1, -1, -1):
            x_off=-(4+i)*self.m_pitch("m1")
            y_off=self.ff_down[0].by()-(i+1)*self.m_pitch("m2")
            self.add_path("metal3", [(self.ff_down[self.size-1].rx(), y_off), (x_off,y_off)])
            self.add_via_center(self.m2_stack, (x_off,y_off))
        
        #forward lfsr
        for i in range(self.size-2, -1, -1):
            x_off=-(5+i)*self.m_pitch("m1")
            y_off=self.ff_up[0].uy()+(self.size-1-i)*self.m_pitch("m2")
            self.add_path("metal3", [(self.ff_up[self.size-2].rx(), y_off), (x_off,y_off)])
            self.add_via_center(self.m2_stack, (x_off,y_off))

        x_off=-4*self.m_pitch("m1")
        y_off=self.ff_up[0].uy()+self.size*self.m_pitch("m2")
        self.add_path("metal3", [(self.ff_up[self.size-1].rx(), y_off), (x_off,y_off)])
        self.add_via_center(self.m2_stack, (x_off,y_off))

    def connect_vdd_gnd(self):
        """ Connect gnd and vdd of all gate to vdd/gnd input pins"""
        
        pins=["vdd", "gnd"]
        
        modules1=[self.reset_inv, self.test_nand, self.init_nand, 
                  self.forward_nand, self.reverse_nand, self.reverse_inv1]
        for mod in modules1:
            for pin in pins:
                pos1=mod.get_pin(pin).lc()
                pos2=(self.ctrl_xoff[pins.index(pin)+2], pos1.y)
                self.add_path("metal1", [pos1, pos2])
                self.add_via_center(self.m1_stack, (self.ctrl_xoff[pins.index(pin)+2],pos1.y), rotate=90)
        
        modules2=[self.xor_up[0],self.xor_down[0],self.ff_up[0], self.ff_down[0]]
        for mod in modules2:
            for pin in pins:
                pos1=mod.get_pin(pin).lc()
                pos2=(self.ctrl_xoff[pins.index(pin)+4], pos1.y)
                self.add_path("metal1", [pos1,pos2])
                self.add_via_center(self.m1_stack, (self.ctrl_xoff[pins.index(pin)+4],pos1.y), rotate=90)

        yoff = self.tgate_ary.get_pin("vdd").uy()
        for pin in pins:
            if (yoff> self.ff_up[0].uy() and yoff < self.xor_up[0].by()-2*self.m1_width):
                pos1=self.tgate_ary.get_pin(pin).lc()
                pos2=vector(self.ctrl_xoff[pins.index(pin)+4]+0.5*self.m1_width, pos1.y)
                pos4=self.ff_up[0].get_pin(pin).lc()
                pos3=vector(pos2.x,  pos4.y)
                self.add_path("metal1", [pos1, pos2, pos3, pos4])

            elif yoff < self.ff_down[0].by()-self.m1_width:
                pos1=self.tgate_ary.get_pin(pin).lc()
                pos2=vector(self.ctrl_xoff[pins.index(pin)+4]+0.5*self.m1_width, pos1.y)
                pos4=self.ff_down[0].get_pin(pin).lc()
                pos3=vector(pos2.x,  pos4.y)
                self.add_path("metal1", [pos1, pos2, pos3, pos4])
            
            else:
                pos1=self.tgate_ary.get_pin(pin).lc()
                self.add_path("metal3", [pos1, (self.ctrl_xoff[pins.index(pin)+4], pos1.y)])
                self.add_via_center(self.m1_stack, pos1, rotate=90)
                self.add_via_center(self.m2_stack, pos1, rotate=90)
                self.add_via_center(self.m2_stack, (self.ctrl_xoff[pins.index(pin)+4],pos1.y))
                self.add_rect_center(layer="metal2", 
                                     offset=pos1,
                                     width=ceil(self.m2_minarea/contact.m1m2.width), 
                                     height=contact.m1m2.width)

        for pin in pins:
            pos1=self.xor_up[0].get_pin(pin)
            pos2=self.nor_tree_up.get_pin(pin)
            mid_pos1=(self.nor_tree_up.rx(), pos1.lc().y)
            self.add_path("metal1", [pos1.lc(), mid_pos1, pos2.lc()], width=contact.m1m2.width)
            
            pos3=self.xor_down[0].get_pin(pin)
            pos4=self.nor_tree_down.get_pin(pin)
            mid_pos3=(self.nor_tree_down.rx(), pos3.lc().y)
            self.add_path("metal1", [pos3.lc(), mid_pos3, pos4.lc()], width=contact.m1m2.width)

        for i in range(2):
            x_off = self.nor2_inst[0].lx()-(i+4)*self.m_pitch("m2")
            self.add_path("metal2", [(x_off, self.min_yoff) , (x_off, self.max_yoff)])
        
        for j in range(self.size-1):
            for i in range(2):
                pin = self.nor2_inst[j].get_pin(pins[i]).lc()
                x_off = self.nor2_inst[j].lx()-(4+i)*self.m_pitch("m2")
                self.add_path("metal1", [(x_off, pin.y) , pin])
                self.add_via_center(self.m1_stack, (x_off, pin.y))

        for i in range(2):
            x_off1 = self.nor2_inst[j].lx()-(4+i)*self.m_pitch("m2")
            x_off2 = self.ctrl_xoff[i+4]
            x_off3 = self.ctrl_xoff[i+2]
            y_off1 = self.xor_down[0].by()
            y_off2 = self.min_yoff - i*self.m_pitch("m1")
            self.add_wire(self.m1_stack, [(x_off1, y_off1) , (x_off1, y_off2) , 
                                          (x_off2, y_off2), (x_off2, y_off1)])
            self.add_wire(self.m1_stack, [(x_off3, y_off1) , (x_off3, y_off2) , 
                                          (x_off2, y_off2), (x_off2, y_off1)])
            
