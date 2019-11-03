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
from vector import vector
from pinv import pinv
from write_complete import write_complete
from nor2 import nor2
from nand2 import nand2
from utils import ceil

class write_complete_array(design.design):
    """ Dynamically generated write complete array circuitry. """

    def __init__(self, columns, word_size, name="write_complete_array"):
        design.design.__init__(self, name )
        debug.info(1, "Creating {0}".format(name))

        self.wc = write_complete()
        self.add_mod(self.wc)

        self.nor2 = nor2()
        self.add_mod(self.nor2)

        self.cols = columns
        self.w_size = word_size
        self.w_per_row = columns / word_size
        
        if self.w_per_row == 1:
            self.width = self.cols * self.wc.width 
            self.height = self.wc.height
        
        if self.w_per_row == 2:
            self.inv = pinv()
            self.add_mod(self.inv)

            #6*self.m_pitch("m1") : vdd, gnd, en, wc0, wc1, space
            self.width= self.cols*self.wc.width+self.inv.width+self.nor2.width+6*self.m_pitch("m1")
            self.height= self.wc.height + 6*self.m_pitch("m1")
        
        if self.w_per_row == 4:
            self.nand2 = nand2()
            self.add_mod(self.nand2)

            #8*self.m_pitch("m1") : vdd, gnd, en, wc0, wc1, wc2, wc3, space
            self.width= self.cols*self.wc.width+self.nand2.width+self.nor2.width+8*self.m_pitch("m1")
            self.height= 2*self.nor2.height + 9*self.m_pitch("m1")
        
        if self.w_per_row > 4:
            debug.error("more than 4 way column mux is not supported!",-1)
        
        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for write_complete array, order of the pins is important """
        
        for i in range(0, self.cols, self.w_size):
            self.add_pin("bl[{0}]".format(i))
            self.add_pin("br[{0}]".format(i))
        self.add_pin_list(["en", "write_complete", "vdd", "gnd"])

    def create_layout(self):
        """ Create modules for instantiation and then route 
            BL/BR in write_complete_array must be pitch-match with BL/BR in bitcell_array. 
            therefore, extra gates are placed on the left side of write_complete_array at 
            negative X direction. wc_x_shift is the shift in negative X. """        
        self.wc_x_shift= 0
        
        self.add_write_complete()
        if self.w_per_row >1:
            self.create_gate_array()
        self.add_layout_pins()        

    def add_write_complete(self):
        """ Creating the write_complete arary """
        
        bl_pin = self.wc.get_pin("bl")            
        br_pin = self.wc.get_pin("br")
        self.wc_inst={}
        
        for i in range(0,self.cols,self.w_size):

            wc_position = vector(i*self.wc.width, 0)

            if (self.w_size == 1 and i%2):
                mirror = "MY"
                wc_position = vector(i*self.wc.width+self.wc.width, 0)
            else:
                mirror = "R0" 
            name = "wc{0}".format(i/self.w_size)
            self.wc_inst[i]=self.add_inst(name=name,      
                                          mod=self.wc, 
                                          offset=wc_position,
                                          mirror = mirror)
            
            bl_offset = self.wc_inst[i].get_pin("bl").ll()
            br_offset = self.wc_inst[i].get_pin("br").ll()
            
            if self.w_per_row==1:
                self.connect_inst(["bl[{0}]".format(i),"br[{0}]".format(i), 
                                   "en", "write_complete", "vdd", "gnd"])
            else:
                self.connect_inst(["bl[{0}]".format(i),"br[{0}]".format(i), 
                                   "en", "wc[{0}]".format(i/self.w_size), "vdd", "gnd"])

            self.add_layout_pin(text="bl[{0}]".format(i), 
                                layer=bl_pin.layer, 
                                offset=bl_offset, 
                                width=contact.m1m2.width, 
                                height=contact.m1m2.width)
            self.add_layout_pin(text="br[{0}]".format(i), 
                                layer=br_pin.layer, 
                                offset= br_offset, 
                                width=contact.m1m2.width, 
                                height=contact.m1m2.width)

    def create_gate_array(self):
        """ Creating nor2+inv for words_per_row==2 and nor2+nand2 for words_per_row==4 """
        
        # Adding central metal2 bus for wc[i], vdd and gnd connections
        for i in range(self.w_per_row+2):
            self.add_rect(layer= "metal2", 
                          offset= (-(i+3)*self.m_pitch("m1"),self.m_pitch("m1")), 
                          width= contact.m1m2.width, 
                          height= self.height-self.m_pitch("m1"))
        
        if self.w_per_row == 2:
            nor2_offset = vector(-(self.w_per_row+5)*self.m_pitch("m1"), self.m_pitch("m1"))
            self.wc_nor2_inst=self.add_inst(name="wc_nor2", 
                                            mod=self.nor2, 
                                            offset=nor2_offset, 
                                            mirror="MY")
            self.connect_inst(["wc[0]","wc[1]", "Z", "vdd", "gnd"])

            inv_offset = vector(-self.nor2.width-(self.w_per_row+5)*self.m_pitch("m1"), self.m_pitch("m1")) 
            self.wc_inv_inst=self.add_inst(name="wc_inv",  
                                           mod=self.inv, 
                                           offset=inv_offset, 
                                           mirror="MY")
            self.connect_inst(["Z","write_complete", "vdd", "gnd"])

            # connect nor2 inputs to central metal2 bus
            pin_list=["A", "B", "gnd", "vdd"]
            for i in pin_list:
                nor_pin = self.wc_nor2_inst.get_pin(i)
                self.add_rect(layer="metal1", 
                              offset= nor_pin.ll(), 
                              width= -nor_pin.lx()-(pin_list.index(i)+3)*self.m_pitch("m1"), 
                              height= self.m1_width)
                self.add_via_center(self.m1_stack,[-(pin_list.index(i)+3)*self.m_pitch("m1")+\
                                                  0.5*contact.m1m2.width, nor_pin.lc().y], rotate=90)

            # Connect nor2 output to inv input
            nor2_Z = self.wc_nor2_inst.get_pin("Z")
            inv_input = self.wc_inv_inst.get_pin("A")
            self.inv_output = self.wc_inv_inst.get_pin("Z")
            self.add_path("metal1",[inv_input.lc(), nor2_Z.lc()])

            # Connect write_complete output to central metal2 bus
            for i in range(0,self.cols,self.w_size):
                wc_pos = self.wc_inst[i].get_pin("write_complete").uc()
                y_pos = wc_pos.y+(i/self.w_size+2)*self.m_pitch("m1")
                self.add_wire(self.m1_stack,[wc_pos, (wc_pos.x, y_pos), 
                                            (-(i/self.w_size+3)*self.m_pitch("m1"), y_pos)])
                self.add_via_center(self.m1_stack, (-(i/self.w_size+3)*self.m_pitch("m1")+\
                                                    0.5*contact.m1m2.width,y_pos), rotate=90)

            # Connect write_complete vdd and gnd to nor2 vdd and gnd
            vdd_pos = self.wc_inst[0].get_pin("vdd")
            nor2_vdd=self.wc_nor2_inst.get_pin("vdd")
            self.add_path("metal1",[nor2_vdd.lc(), 
                                   (-2*self.m_pitch("m1"), nor2_vdd.lc().y),
                                   (-2*self.m_pitch("m1"), vdd_pos.lc().y),
                                   (self.cols*self.wc.width, vdd_pos.lc().y)])
            gnd_pos = vector(-5*self.m_pitch("m1"), self.wc_inst[0].get_pin("gnd").lc().y)
            self.add_path("metal1",[gnd_pos,(self.cols*self.wc.width, gnd_pos.y)])
            self.add_via_center(self.m1_stack,
                               [-5*self.m_pitch("m1")+0.5*contact.m1m2.width, gnd_pos.y], rotate=90)
            
            self.wc_x_shift=self.inv.width+self.nor2.width+(self.w_per_row+5)*self.m_pitch("m1")

        if self.w_per_row == 4:
            nor2_Z={}
            self.nor2_vdd={}
            self.nor2_gnd={}
            for i in range(2):
                nor2_offset = vector(-(self.w_per_row+5)*self.m_pitch("m1"), i*(self.nor2.height+\
                                     2*max(self.well_space, self.implant_space, 
                                     (contact.m1m2.width+contact.m1m2.height)))+self.m_pitch("m1"))
                self.wc_nor2_inst=self.add_inst(name="wc_nor2_{0}".format(i), 
                                                mod=self.nor2, 
                                                offset=nor2_offset, 
                                                mirror ="MY")
                self.connect_inst(["wc[{0}]".format(2*i),"wc[{0}]".format(2*i+1),
                                   "Z[{0}]".format(i),"vdd","gnd"])
                
                # connect nor2 pins to central metal2 bus
                pin_list=["A", "B"]
                for j in pin_list:
                    nor_pin = self.wc_nor2_inst.get_pin(j)
                    self.add_rect(layer="metal1", 
                                  offset= nor_pin.ll(), 
                                  width= -nor_pin.lx()-(2*i+3+pin_list.index(j))*self.m_pitch("m1"), 
                                  height= self.m1_width)
                    self.add_via_center(self.m1_stack,[-(2*i+3+pin_list.index(j))*self.m_pitch("m1")+\
                                                      0.5*contact.m1m2.width, nor_pin.lc().y],rotate=90)
                self.nor2_gnd[i] = self.wc_nor2_inst.get_pin("gnd")
                self.add_rect(layer="metal1", 
                              offset= self.nor2_gnd[i].ll(), 
                              width= -self.nor2_gnd[i].lx()-7*self.m_pitch("m1"), 
                              height= self.m1_width)
                self.add_via_center(self.m1_stack, [-7*self.m_pitch("m1")+0.5*contact.m1m2.width, 
                                                    self.nor2_gnd[i].lc().y], rotate=90)

                self.nor2_vdd[i] = self.wc_nor2_inst.get_pin("vdd")
                self.add_rect(layer="metal1", 
                              offset= self.nor2_vdd[i].ll(), 
                              width= -self.nor2_vdd[i].lx()-8*self.m_pitch("m1"), 
                              height= self.m1_width)
                self.add_via_center(self.m1_stack, [-8*self.m_pitch("m1")+0.5*contact.m1m2.width,
                                                    self.nor2_vdd[i].lc().y], rotate=90)
                
                nor2_Z[i] = self.wc_nor2_inst.get_pin("Z")
            
            # Add nand2 gate
            nand2_offset = vector(-self.nor2.width- (self.w_per_row + 5)*self.m_pitch("m1")-\
                           max(self.m_pitch("m1")+self.m1_width,self.well_space,self.implant_space),self.m_pitch("m1")) 
            self.wc_nand2_inst2=self.add_inst(name="wc_nand2", 
                                              mod=self.nand2, 
                                              offset=nand2_offset, 
                                              mirror = "MY")
            self.connect_inst(["Z[1]","Z[0]", "write_complete", "vdd", "gnd"])
            
            # Connect nor2 output to nand2 inputs
            nand2_A_input = self.wc_nand2_inst2.get_pin("A").lc()
            nand2_B_input = self.wc_nand2_inst2.get_pin("B").lc()
            nand2_vdd = self.wc_nand2_inst2.get_pin("vdd").lc()
            nand2_gnd = self.wc_nand2_inst2.get_pin("gnd").lc()
            
            self.add_path("metal1",[self.nor2_vdd[0].lc(), nand2_vdd])
            self.add_path("metal1",[self.nor2_gnd[0].lc(), nand2_gnd])
            self.add_path("metal1",[nor2_Z[0].ll(),nand2_B_input])
            self.add_wire(self.m1_stack,[nor2_Z[1].lc(),
                                        (nand2_offset.x+0.5*self.m1_width, nor2_Z[1].lc().y), 
                                        (nand2_offset.x+0.5*self.m1_width, nand2_A_input.y), 
                                         nand2_A_input])

            # Connect write_complete output to central metal2 bus
            for i in range(0,self.cols,self.w_size):
                wc_pos = self.wc_inst[i].get_pin("write_complete").uc()
                y_pos = max(nor2_Z[1].lc().y,wc_pos.y)+i/self.w_size*self.m_pitch("m1")+self.m1_space
                self.add_wire(self.m1_stack,[wc_pos, (wc_pos.x, y_pos), 
                                            (-(i/self.w_size+3)*self.m_pitch("m1"), y_pos)])
                self.add_via_center(self.m1_stack,(-(i/self.w_size+3)*self.m_pitch("m1")+\
                                                   0.5*contact.m1m2.width,y_pos), rotate=90)

            # Connect write_complete vdd and gnd to nor2 vdd and gnd
            vdd_pos = self.wc_inst[0].get_pin("vdd")
            self.add_path("metal1",[self.nor2_vdd[0].lc(), 
                                   (-2*self.m_pitch("m1"), self.nor2_vdd[0].lc().y),
                                   (-2*self.m_pitch("m1"), vdd_pos.lc().y),
                                   (self.cols*self.wc.width, vdd_pos.lc().y)])
            gnd_pos = self.wc_inst[0].get_pin("gnd")
            self.add_path("metal1",[self.nor2_gnd[1].lc(), 
                                   (-2*self.m_pitch("m1"), self.nor2_gnd[1].lc().y),
                                   (-2*self.m_pitch("m1"), gnd_pos.lc().y),
                                   (self.cols*self.wc.width, gnd_pos.lc().y)])

            self.wc_x_shift=self.nand2.width+self.nor2.width+(self.w_per_row+6)*self.m_pitch("m1")+\
                            max(self.m_pitch("m1")+self.m1_width,self.well_space,self.implant_space)

    def add_layout_pins(self):
        """ Adding vdd, gnd, en and write_complete pins """
        
        if self.w_per_row == 1:
            vdd_offset = self.wc_inst[0].get_pin("vdd")
            gnd_offset = self.wc_inst[0].get_pin("gnd")
            en_offset =self.wc_inst[0].get_pin("en")
            wc_pin = self.wc_inst[0].get_pin("write_complete")

            self.add_layout_pin(text="vdd", 
                                layer=self.m1_pin_layer, 
                                offset=vdd_offset.ll(), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[vdd_offset.lc(), (self.cols*self.wc.width, vdd_offset.lc().y)])

            self.add_layout_pin(text="gnd", 
                                layer=self.m1_pin_layer, 
                                offset=gnd_offset.ll(), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[gnd_offset.lc(), (self.cols*self.wc.width, gnd_offset.lc().y)])
            
            self.add_layout_pin(text="en",  
                                layer=self.m1_pin_layer, 
                                offset=en_offset.ll(),  
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[en_offset.lc(), (self.cols*self.wc.width, en_offset.lc().y)])
            
            self.add_layout_pin(text="write_complete", 
                                layer=self.m2_pin_layer, 
                                offset= wc_pin.ll(), 
                                width=self.m2_width, 
                                height=self.m2_width)

        if self.w_per_row == 2:
            vdd_offset = vector(self.wc_inv_inst.lx(), self.height)
            gnd_offset = vector(self.wc_inv_inst.lx(), self.height-self.m_pitch("m1"))
            en_offset = vector(self.wc_inv_inst.lx(), self.height-2*self.m_pitch("m1"))
            
            self.add_layout_pin(text="vdd", 
                                layer=self.m1_pin_layer, 
                                offset=(vdd_offset.x, vdd_offset.y-0.5*self.m1_width), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[vdd_offset, (self.cols*self.wc.width, vdd_offset.y)])
            self.add_via_center(self.m1_stack, (-6*self.m_pitch("m1")+0.5*contact.m1m2.width, 
                                                vdd_offset.y), rotate=90)

            self.add_layout_pin(text="gnd", 
                                layer=self.m1_pin_layer, 
                                offset=(gnd_offset.x, gnd_offset.y-0.5*self.m1_width), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[gnd_offset, (self.cols*self.wc.width, gnd_offset.y)])
            self.add_via_center(self.m1_stack, (-5*self.m_pitch("m1")+0.5*contact.m1m2.width, 
                                                gnd_offset.y), rotate=90)

            self.add_layout_pin(text="en",  
                                layer=self.m1_pin_layer, 
                                offset=(self.wc_inv_inst.lx(), en_offset.y-0.5*self.m1_width),   
                                width=self.m1_width, 
                                height=self.m1_width)
            en_pin=self.wc_inst[0].get_pin("en")
            self.add_wire(self.m1_stack,[(self.wc_inv_inst.lx(), en_offset.y),
                                         (-self.m_pitch("m1"),en_offset.y),
                                         (-self.m_pitch("m1"), en_pin.lc().y),
                                         (self.cols*self.wc.width, en_pin.lc().y)])

            self.add_layout_pin(text="write_complete", 
                                layer=self.m2_pin_layer, 
                                offset=(self.inv_output.lx()+self.m1_space,self.inv_output.by()), 
                                width=self.m2_width, 
                                height=self.m2_width)
            self.add_rect(layer="metal2", 
                          offset= (self.inv_output.lx()+self.m1_space, self.inv_output.by()), 
                          width=self.m2_width, 
                          height=self.height - self.inv_output.by())
                       
        if self.w_per_row == 4:
            vdd_offset = vector(self.wc_nand2_inst2.lx(), self.height)
            gnd_offset = vector(self.wc_nand2_inst2.lx(), self.height-self.m_pitch("m1"))
            en_offset = vector(self.wc_nand2_inst2.lx(), self.height-2*self.m_pitch("m1"))
            wc_offset = self.wc_nand2_inst2.get_pin("Z")
            
            self.add_layout_pin(text="vdd", 
                                layer=self.m1_pin_layer, 
                                offset=(vdd_offset.x, vdd_offset.y-0.5*self.m1_width), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[vdd_offset, (self.cols*self.wc.width, vdd_offset.y)])
            self.add_via_center(self.m1_stack, (-8*self.m_pitch("m1")+0.5*contact.m1m2.width, 
                                                vdd_offset.y), rotate=90)

            self.add_layout_pin(text="gnd", 
                                layer=self.m1_pin_layer, 
                                offset=(gnd_offset.x, gnd_offset.y-0.5*self.m1_width), 
                                width=self.m1_width, 
                                height=self.m1_width)
            self.add_path("metal1",[gnd_offset, (self.cols*self.wc.width, gnd_offset.y)])
            self.add_via_center(self.m1_stack, (-7*self.m_pitch("m1")+0.5*contact.m1m2.width, 
                                                gnd_offset.y), rotate=90)

            self.add_layout_pin(text="en", 
                                layer=self.m1_pin_layer, 
                                offset=(en_offset.x, en_offset.y-0.5*self.m1_width), 
                                width=self.m1_width, 
                                height=self.m1_width)
            en_pin=self.wc_inst[0].get_pin("en")
            self.add_wire(self.m1_stack,[en_offset, (en_pin.lx()-self.m_pitch("m1"), en_offset.y),
                                        (-self.m_pitch("m1"), en_pin.lc().y),
                                        (self.cols*self.wc.width, en_pin.lc().y)])

            self.add_layout_pin(text="write_complete", 
                                layer=self.m2_pin_layer, 
                                offset= (wc_offset.lx()-0.5*self.m2_width,wc_offset.by()), 
                                width=self.m2_width, 
                                height=self.m2_width)
            self.add_wire(self.m1_stack,[(wc_offset.lc().x, self.height),wc_offset.lc(),
                                         (wc_offset.lc().x+ self.m_pitch("m1"),wc_offset.lc().y )])
