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
from math import log
from vector import vector
from pinv import pinv
from nor3 import nor3
from nand2 import nand2
from utils import ceil
from hierarchical_predecode2x4 import hierarchical_predecode2x4 as pre2x4

class split_merge_control(design.design):
    """ Dynamically generated Control logic for the split and merge circuitry """

    def __init__(self, num_banks, name="split_merge_control"):
        """ Constructor """
        
        self.name= name
        design.design.__init__(self, self.name)
        debug.info(1, "Creating {}".format(self.name))

        self.num_banks= num_banks
        self.create_layout()
        self.offset_all_coordinates()
        #self.translate_all(vector(0, -self.via_shift("v1")))

        sizes= self.find_highest_coords()
        self.width= sizes[0]
        self.height= sizes[1]

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_offsets()
        self.add_layout_pins()
        self.add_modules()
        self.route_modules()

    def add_pins(self):
        """ Add pins for split_merge_control module, order of the pins is important """
        
        self.add_pin_list(["r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"])
        for i in range(self.num_banks):
            self.add_pin_list(["ack{0}".format(i),"ack_b{0}".format(i)])
        self.add_pin_list(["pre_ack", "pre_wack", "pre_rack", "rw_merge", "ack_b"])
        for i in range(int(log(self.num_banks,2))):
            self.add_pin("addr[{0}]".format(i))
        for i in range(self.num_banks):
            self.add_pin("sel[{0}]".format(i))
        self.add_pin_list(["S", "vdd", "gnd"])

    def create_modules(self):
        """ Add all the required modules """

        self.nor3 = nor3()
        self.add_mod(self.nor3)

        self.nand2 = nand2()
        self.add_mod(self.nand2)

        self.inv= pinv()
        self.add_mod(self.inv)
        
        self.inv2= pinv(size=2)
        self.add_mod(self.inv2)

        self.inv5= pinv(size= 5)
        self.add_mod(self.inv5)

        if self.num_banks == 4:
            self.pre2_4= pre2x4()
            self.add_mod(self.pre2_4)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, determine the size of vias etc """
        
        # This a an offset shift between gates to avoid short, well DRC, implant DRC
        self.off_shift= max(2*self.m_pitch("m1"), self.implant_space+contact.m1m2.width,
                            self.well_space+contact.m1m2.width)

        # Defining the width of horizontal tracks based on the num_inv and the gap between inv gates
        if self.num_banks == 2:
            self.horizontal_width= (8+self.num_banks)*self.inv.height +\
                                   4*self.off_shift + contact.m1m2.width
        if self.num_banks == 4:
            self.horizontal_width= self.pre2_4.height+ (9+self.num_banks)*self.inv.height +\
                                   4*self.off_shift + contact.m1m2.width

    def add_modules(self):
        """ Place all the gates """
        
        self.add_bank_decoder()
        self.add_Mrw_gate()
        self.add_ack_b_invs()
        self.add_pre_ctrl_inv()
    
    def route_modules(self):
        """ Route all the gates """
        
        self.route_bank_decoder()
        self.route_Mrw_gate()
        self.route_ack_b_invs()
        self.route_rack_b_inv()
        self.route_vdd_gnd()

    def create_in_out_rails(self, pin_off, pin_name):
        """ for each input or output there is a metal2 rail with its pin name """
        
        self.add_rect(layer ="metal2",
                      offset=pin_off,
                      width=self.horizontal_width,
                      height=self.m2_width)
        self.add_layout_pin(text=pin_name,
                            layer =self.m2_pin_layer,
                            offset=pin_off,
                            width=self.m2_width,
                            height=self.m2_width)

    def add_layout_pins(self):
        """ Add all input and output Pins (Order of pins matters)"""

        self.ctrl_bus_names= ["r", "w",  "rw", "ack", "rack", "rreq", "wreq", "wack"]
        self.merge_ctrl_bus_names= ["ack_b", "pre_ack", "rw_merge", "pre_rack", "pre_wack"]

        ctrl_size= len(self.ctrl_bus_names)
        merge_size= len(self.merge_ctrl_bus_names)
        addr_size=int(log(self.num_banks,2))
        
        self.ctrl_bus_off={}
        self.bank_ctrl_bus_off={}
        self.merge_ctrl_bus_off={}
        self.bank_addr_off={}
        self.bank_sel_off={}
        
        for i in range(ctrl_size):
            self.ctrl_bus_off[i]= vector(-0.5*contact.m1m2.width, i*self.m_pitch("m1"))
            self.create_in_out_rails(self.ctrl_bus_off[i],self.ctrl_bus_names[i])
        
        for i in range(self.num_banks):
            self.bank_ctrl_bus_names= ["ack{0}".format(self.num_banks-1-i), 
                                       "ack_b{0}".format(self.num_banks-1-i)]
            bank_ctrl_size=len(self.bank_ctrl_bus_names)
            for j in range(bank_ctrl_size):
                self.bank_ctrl_bus_off[i,j]= vector(-0.5*contact.m1m2.width, 
                                                   (ctrl_size+i*bank_ctrl_size+j)*self.m_pitch("m1"))
                self.create_in_out_rails(self.bank_ctrl_bus_off[i,j],self.bank_ctrl_bus_names[j]) 

        for i in range(merge_size):
            self.merge_ctrl_bus_off[i]= vector(-0.5*contact.m1m2.width, (i+ctrl_size+bank_ctrl_size*\
                                               self.num_banks)*self.m_pitch("m1"))
            self.create_in_out_rails(self.merge_ctrl_bus_off[i], self.merge_ctrl_bus_names[i])
        
        for i in range(addr_size):
            self.bank_addr_off[i]= vector(-0.5*contact.m1m2.width, (i+ctrl_size+bank_ctrl_size*\
                                          self.num_banks+merge_size)*self.m_pitch("m1"))
            self.create_in_out_rails(self.bank_addr_off[i], "addr[{0}]".format(i))

        for i in range(self.num_banks):
            if self.num_banks==2:
                name="sel[{0}]".format(self.num_banks-i-1)
            if self.num_banks==4:
                name="sel[{0}]".format(i)
            self.bank_sel_off[i]= vector(-0.5*contact.m1m2.width, 
                                        (i+ctrl_size+bank_ctrl_size*self.num_banks+ \
                                         addr_size+merge_size)*self.m_pitch("m1"))
            self.create_in_out_rails(self.bank_sel_off[i], name)

        self.vdd_offset= vector(-0.5*contact.m1m2.width, (ctrl_size+ bank_ctrl_size*self.num_banks+\
                                addr_size+self.num_banks+merge_size)*self.m_pitch("m1"))
        self.gnd_offset= vector(self.vdd_offset.x, self.vdd_offset.y+self.m_pitch("m1"))
        self.S_offset= vector(self.gnd_offset.x, self.gnd_offset.y+self.m_pitch("m1"))
        self.gate_y_off= self.S_offset.y + self.m_pitch("m1")

        self.create_in_out_rails(self.S_offset, "S")
        self.create_in_out_rails(self.vdd_offset, "vdd")
        self.create_in_out_rails(self.gnd_offset, "gnd")

    def add_bank_decoder(self):
        """ Add the inverter (num_banks=2) or 2:4 decoder (num_banks=4) for bank_sel signals """

        if self.num_banks == 2:
            dec_off= (self.inv.height, self.gate_y_off)        
            self.dec_inst=self.add_inst(name="decoder_inv", 
                                        mod=self.inv, 
                                        offset=dec_off, 
                                        rotate=90)
            self.connect_inst(["addr[0]", "pre_sel[0]", "vdd", "gnd"])

        if self.num_banks == 4:
            dec_off= (self.pre2_4.height, self.gate_y_off)        
            self.dec_inst=self.add_inst(name="decoder_2x4", 
                                        mod=self.pre2_4, 
                                        offset=dec_off, 
                                        rotate=90)
            temp= []
            temp.extend(["addr[0]","addr[1]","pre_sel[0]","pre_sel[1]","pre_sel[2]","pre_sel[3]"])
            temp.extend([ "vdd", "gnd"])
            self.connect_inst(temp)

        self.nand2_inst ={}
        self.dec_inv_inst ={}
        
        for i in range(self.num_banks):
            if i%2:
                mirror= "MX"
                nand_off= vector(self.dec_inst.rx()+(i+1)*self.nand2.height+self.off_shift,
                                 self.gate_y_off+self.nand2.width+self.inv5.width)
            else:
                mirror= "R0"
                nand_off= vector(self.dec_inst.rx()+i*self.nand2.height+self.off_shift,
                                 self.gate_y_off+self.nand2.width+self.inv5.width)
            self.nand2_inst[i]=self.add_inst(name="decoder_nand2_{0}".format(i), 
                                             mod=self.nand2, 
                                             offset=nand_off, 
                                             rotate=270,
                                             mirror= mirror )
            temp= []
            if self.num_banks == 2:
                if i%2:
                    temp.extend(["addr[0]", "S", "to_sel[1]", "vdd", "gnd"])
                else:
                    temp.extend(["pre_sel[0]", "S", "to_sel[0]", "vdd", "gnd"])

            if self.num_banks == 4:
                temp.extend(["pre_sel[{0}]".format(i), "S", "to_sel[{0}]".format(i), "vdd", "gnd"])
            self.connect_inst(temp)

            self.dec_inv_inst[i]=self.add_inst(name="decoder_inv_{0}".format(i), 
                                               mod=self.inv5, 
                                               offset=nand_off-vector(0, self.nand2.width), 
                                               rotate=270,
                                               mirror= mirror )
            self.connect_inst(["to_sel[{0}]".format(i), "sel[{0}]".format(i), "vdd", "gnd"])

    def add_Mrw_gate(self):
        """ Add nor3 and inverter for r, w and rw inputs and Mrw output"""

        nor_off= vector(self.nand2_inst[self.num_banks-1].rx()+self.inv.height+self.off_shift,
                             self.gate_y_off)
        self.nor_inst=self.add_inst(name="nor", 
                                    mod=self.nor3, 
                                    offset=nor_off,
                                    mirror= "R0",
                                    rotate=90)
        self.connect_inst(["r", "w", "rw", "Mnor", "vdd", "gnd"])
        
        inv_off= vector(self.nor_inst.rx(), self.gate_y_off + self.nor3.width)
        self.inv_inst=self.add_inst(name="inv", 
                                    mod=self.inv, 
                                    offset=inv_off,
                                    mirror= "R0",
                                    rotate=90)
        self.connect_inst(["Mnor", "rw_merge", "vdd", "gnd"])

    def add_ack_b_invs(self):
        """ Add row of inverter for ack0:3 inputs and ack_b0:3 output"""
        self.ack_b_bank_inst={}
        for i in range(self.num_banks):
            if i%2:
                ack_b_off= vector(self.nor_inst.rx()+(i+1)*self.inv.height+self.off_shift,
                                  self.gate_y_off)
                mirror ="R0"
            else:
                ack_b_off= vector(self.nor_inst.rx()+i*self.inv.height+self.off_shift, 
                                       self.gate_y_off)
                mirror ="MX"
            self.ack_b_bank_inst[i]=self.add_inst(name="ack_b_bank_inv{0}".format(i), 
                                                  mod=self.inv5, 
                                                  offset=ack_b_off,
                                                  mirror= mirror,
                                                  rotate=90)
            self.connect_inst(["ack{0}".format(i), "ack_b{0}".format(i), "vdd", "gnd"])

    def add_pre_ctrl_inv(self):
        """ Add inverter for rreq input and ack_b output"""

        self.pre_ack_b_inst={}
        for i in range(3):
            pre_ack_b_off= vector(self.ack_b_bank_inst[self.num_banks-1].rx()+ \
                                  self.inv.height+self.off_shift, self.gate_y_off+i*self.inv2.width)

            if i==2:
                mod = self.inv5
            else:
                mod = self.inv2

            self.pre_ack_b_inst[i]=self.add_inst(name="pre_ack_b_inv{0}".format(i), 
                                                 mod=mod, 
                                                 offset=pre_ack_b_off,
                                                 mirror= "R0",
                                                 rotate=90)
            if i==0:
                self.connect_inst(["pre_ack", "ackx0", "vdd", "gnd"])
            if i==1:
                self.connect_inst(["ackx0", "ackx1", "vdd", "gnd"])
            if i==2:
                self.connect_inst(["ackx1", "ack", "vdd", "gnd"])
        

        self.add_path("metal1", [self.pre_ack_b_inst[1].get_pin("A").uc(), self.pre_ack_b_inst[0].get_pin("Z").lc()])
        self.add_path("metal1", [self.pre_ack_b_inst[2].get_pin("A").uc(), self.pre_ack_b_inst[1].get_pin("Z").lc()])
        ack_b_off= vector(pre_ack_b_off.x, self.gate_y_off)
        self.ack_b_inst=self.add_inst(name="ack_b_inv", 
                                      mod=self.inv2, 
                                      offset=ack_b_off,
                                      mirror= "MX",
                                      rotate=90)
        self.connect_inst(["ack", "ack_b", "vdd", "gnd"])

        self.rack_b_inst={}
        for i in range(3):
            rack_b_off= vector(ack_b_off.x+2*self.inv.height, self.gate_y_off+i*self.inv2.width)
            if i==2:
                mod = self.inv5
            else:
                mod = self.inv2

            self.rack_b_inst[i]=self.add_inst(name="rack_b_inv{0}".format(i), 
                                              mod=mod, 
                                              offset=rack_b_off,
                                              mirror= "R0",
                                              rotate=90)
            if i==0:
                self.connect_inst(["pre_rack", "rack0", "vdd", "gnd"])
            if i==1:
                self.connect_inst(["rack0", "rack1", "vdd", "gnd"])
            if i==2:
                self.connect_inst(["rack1", "rack", "vdd", "gnd"])
        self.add_path("metal1", [self.rack_b_inst[1].get_pin("A").uc(), self.rack_b_inst[0].get_pin("Z").lc()])
        self.add_path("metal1", [self.rack_b_inst[2].get_pin("A").uc(), self.rack_b_inst[1].get_pin("Z").lc()])
        
        
        self.wack_b_inst={}
        for i in range(3):
            wack_b_off= vector(rack_b_off.x, self.gate_y_off+i*self.inv2.width)
            if i==2:
                mod = self.inv5
            else:
                mod = self.inv2

            self.wack_b_inst[i]=self.add_inst(name="wack_b_inv{0}".format(i), 
                                              mod=mod, 
                                              offset=wack_b_off,
                                              mirror= "MX",
                                              rotate=90)
            if i==0:
                self.connect_inst(["pre_wack", "wack0", "vdd", "gnd"])
            if i==1:
                self.connect_inst(["wack0", "wack1", "vdd", "gnd"])
            if i==2:
                self.connect_inst(["wack1", "wack", "vdd", "gnd"])
        self.add_path("metal1", [self.wack_b_inst[1].get_pin("A").uc(), self.wack_b_inst[0].get_pin("Z").lc()])
        self.add_path("metal1", [self.wack_b_inst[2].get_pin("A").uc(), self.wack_b_inst[1].get_pin("Z").lc()])

    def cxn_inv_output(self, pin1, pin2):
        """ Connecting the output of inv to coresponding rail with metal3
            Adding Via2 at the inv out and rail for connection """
        
        #This is the extra space needed to ensure DRC rules to the m1/m2 contacts
        m1m2_m2m3_fix= 0.5*(contact.m2m3.width - contact.m1m2.width)
        contact_xshift= 0.5*self.m2_width+m1m2_m2m3_fix
        contact_yshift= m1m2_m2m3_fix+self.m1_width+contact.m2m3.height

        self.add_path("metal3",[pin1, (pin1.x, pin2.y)])
        self.add_via(self.m2_stack,(pin1.x-contact_xshift, pin2.y-m1m2_m2m3_fix-self.via_shift("v1")))
        self.add_via(self.m2_stack,(pin1.x-contact_xshift, pin1.y-contact_yshift-self.via_shift("v1")))

    def cxn_gate_input(self, pin1, pin2):
        """ Connecting the input(s) of gates to coresponding rail with metal1
            Adding Via1 at the rail for connection """ 
        
        self.add_path("metal1",[(pin1.x, pin1.y-self.m1_width), (pin1.x, pin2.y)],
                      width=self.m1_width)
        self.add_via(self.m1_stack,(pin1.x-0.5*self.m2_width, pin2.y-self.via_shift("v1")))


    def route_bank_decoder(self):
        """ Route the inverter or 2:4 decoder """
        
        if self.num_banks == 2:
            for i in range(self.num_banks):
                
                inv_out_off= self.dec_inv_inst[i].get_pin("Z").uc()
                inv_in_off= self.dec_inv_inst[i].get_pin("A").uc()
                nand2_out_off= self.nand2_inst[i].get_pin("Z").uc()
                nand2_A_off= self.nand2_inst[i].get_pin("A").uc()
                nand2_vdd_off= vector(self.nand2_inst[i].get_pin("vdd").uc().x, 
                                      self.nand2_inst[i].get_pin("vdd").uc().y+0.5*self.m1_width)

                if i%2:
                    dec_out_off= self.dec_inst.get_pin("Z").uc()
                    inv_in_xoff= self.dec_inv_inst[i].get_pin("A").rx()

                    self.add_wire(self.m1_rev_stack,
                                  [dec_out_off,
                                  (dec_out_off.x,self.nand2_inst[i].uy()+(i+2)*self.m_pitch("m1")),
                                  (nand2_A_off.x,self.nand2_inst[i].uy()+(i+2)*self.m_pitch("m1")),
                                   nand2_A_off])
                else:
                    dec_out_off= self.dec_inst.ur()
                    inv_in_xoff= self.dec_inv_inst[i].get_pin("A").lx()
                    self.cxn_gate_input(self.dec_inst.get_pin("A").uc(),self.bank_addr_off[i])
                    
                    self.add_via(self.m1_stack,(self.dec_inst.rx()+self.m_pitch("m1")-\
                                                0.5*contact.m1m2.width, self.bank_addr_off[i].y-self.via_shift("v1")))

                    self.add_wire(self.m1_rev_stack,
                                  [(dec_out_off.x+self.m_pitch("m1"), self.bank_addr_off[i].y),
                                  (dec_out_off.x+self.m_pitch("m1"), 
                                   self.nand2_inst[i].uy()+(i+2)*self.m_pitch("m1")),
                                  (nand2_A_off.x, self.nand2_inst[i].uy()+(i+2)*self.m_pitch("m1")),
                                   nand2_A_off])
                
                nand2_B= self.nand2_inst[i].get_pin("B").uc()
                inv_in_yoff= self.dec_inv_inst[i].get_pin("A").uc().y
                self.add_path("metal1", [nand2_out_off,(inv_in_xoff, inv_in_yoff)])
                
                self.cxn_gate_input(inv_out_off, self.bank_sel_off[i])
                self.cxn_inv_output(nand2_B,self.S_offset)
                self.add_via(self.m1_stack, (nand2_B.x-0.5*self.m1_width, nand2_B.y-self.via_shift("v1")))
                self.add_rect_center(layer="metal2", 
                                     offset=nand2_B, 
                                     width=contact.m1m2.width, 
                                     height=2*self.m_pitch("m1"))

        if self.num_banks == 4:
            #route inputs of 2:4 decoder to input addr rails
            for i in range(int(log(self.num_banks,2))):
                if i%2:
                    decoder_input_offset= vector(self.dec_inst.lx()+self.nand2.get_pin("B").lc().y, 
                                                 self.dec_inst.get_pin("in[{0}]".format(i)).uy())
                else:
                    decoder_input_offset= vector(self.dec_inst.lx()+self.nand2.get_pin("A").lc().y, 
                                                 self.dec_inst.get_pin("in[{0}]".format(i)).uy())
                self.cxn_gate_input(decoder_input_offset, self.bank_addr_off[i])

            #route outputs of 2:4 decoder to nand2 gates
            for i in range(self.num_banks):
                dec_out_off= vector(self.dec_inst.get_pin("out[{0}]".format(i)).uc().x, 
                                    self.dec_inst.get_pin("out[{0}]".format(i)).lc().y)
                inv_out_off= self.dec_inv_inst[i].get_pin("Z").uc()
                nand2_out_off= self.nand2_inst[i].get_pin("Z").uc()
                nand2_A_off= self.nand2_inst[i].get_pin("A").uc()
                if i%2:
                    inv_in_xoff= self.dec_inv_inst[i].get_pin("A").rx()
                else:
                    inv_in_xoff= self.dec_inv_inst[i].get_pin("A").lx()
                
                nand2_B= self.nand2_inst[i].get_pin("B").uc()
                inv_in_yoff= self.dec_inv_inst[i].get_pin("A").uc().y
                nand2_vdd_off= vector(self.nand2_inst[i].get_pin("vdd").uc().x, 
                                      self.nand2_inst[i].get_pin("vdd").uc().y+0.5*self.m1_width)
                
                self.add_path("metal1", [nand2_out_off,(inv_in_xoff, inv_in_yoff)])
                self.cxn_gate_input(inv_out_off, self.bank_sel_off[i])
                self.cxn_inv_output(nand2_B,self.S_offset)
                self.add_via(self.m1_stack, (nand2_B.x-0.5*self.m1_width, nand2_B.y-self.via_shift("v1")))
                self.add_rect_center(layer="metal2", 
                                     offset=nand2_B, 
                                     width=contact.m1m2.width, 
                                     height=2*self.m_pitch("m1"))

                self.add_path("metal1", [dec_out_off, 
                                        (dec_out_off.x, dec_out_off.y+(i+1)*self.m_pitch("m1")),
                                        (nand2_A_off.x, dec_out_off.y+(i+1)*self.m_pitch("m1")), 
                                         nand2_A_off])

    def route_Mrw_gate(self):
        """ Route r, w and rw input pins and Mrw output pin"""
        
        # Connecting input r, w and rw to NOR3 inputs A, B and C
        in_pin= ["A", "B", "C"]
        pin= ["r", "w", "rw"]
        for i in range(3):
            self.cxn_gate_input(self.nor_inst.get_pin(in_pin[i]).uc(), 
                                self.ctrl_bus_off[self.ctrl_bus_names.index(pin[i])])

        # Connecting Output of NOR3 gate to input of inv
        nor_inv_in_off =self.inv_inst.get_pin("A").uc()
        nor_out_off= self.nor_inst.get_pin("Z").uc()
        self.add_path("metal1", [nor_out_off, nor_inv_in_off])
        
        # Connecting Output of inv to Mrw pin
        self.cxn_inv_output(self.inv_inst.get_pin("Z").uc(), 
                            self.merge_ctrl_bus_off[self.merge_ctrl_bus_names.index("rw_merge")])

    def route_ack_b_invs(self):
        """ Route ack0:3 input pins and ack_b0:3 output pins"""
        
        # Connecting input ack0:3 to inverter input A
        for i in range(self.num_banks):
            self.cxn_gate_input(self.ack_b_bank_inst[i].get_pin("A").uc(),
                                self.bank_ctrl_bus_off[i,0]) 
            self.cxn_inv_output(self.ack_b_bank_inst[i].get_pin("Z").uc(), 
                                self.bank_ctrl_bus_off[i,1])
    
    def route_rack_b_inv(self):
        """ Route pre_rack input pin and rack output pin"""
        
        # Connecting input rreq to inverter input A
        modules1 =[self.pre_ack_b_inst[0], self.wack_b_inst[0], self.rack_b_inst[0]]
        modules2 =[self.pre_ack_b_inst[2], self.wack_b_inst[2], self.rack_b_inst[2]]
        pre_pin =["pre_ack", "pre_wack", "pre_rack"]
        pin =["ack", "wack", "rack"]
        for j in range(3):
            self.cxn_gate_input(modules1[j].get_pin("A").uc(), 
                                self.merge_ctrl_bus_off[self.merge_ctrl_bus_names.index(pre_pin[j])])
            self.cxn_inv_output(modules2[j].get_pin("Z").uc(), 
                                self.ctrl_bus_off[self.ctrl_bus_names.index(pin[j])])

        mod= self.ack_b_inst
        self.cxn_gate_input(mod.get_pin("A").uc(), 
                            self.ctrl_bus_off[self.ctrl_bus_names.index("ack")])
        self.cxn_inv_output(mod.get_pin("Z").uc(), 
                            self.merge_ctrl_bus_off[self.merge_ctrl_bus_names.index("ack_b")])

    def route_vdd_gnd(self):
        """ Route vdd and gnd pins of all the gates to vdd and gnd pin"""

        if self.num_banks == 4:
             for vdd_pin in (self.dec_inst.get_pins("vdd")):
                 self.cxn_gate_input(vdd_pin.uc(), self.vdd_offset)
             
             for gnd_pin in (self.dec_inst.get_pins("gnd")):
                 self.cxn_gate_input(gnd_pin.uc(), self.gnd_offset)

        if self.num_banks == 2:
             self.cxn_gate_input(self.dec_inst.get_pin("vdd").uc(), self.vdd_offset)
             self.cxn_gate_input(self.dec_inst.get_pin("gnd").uc(), self.gnd_offset)
       
        power_pins= ["vdd", "gnd"]
        for i in range(2):
            vdd_y_off= vector(0, self.vdd_offset.y+i*self.m_pitch("m1"))
            self.cxn_gate_input(self.nor_inst.get_pin(power_pins[i]).uc(), vdd_y_off)

            for j in range(self.num_banks):
                 vdd_y_off= vector(0, self.vdd_offset.y+i*self.m_pitch("m1"))
                 self.cxn_gate_input(self.ack_b_bank_inst[j].get_pin(power_pins[i]).uc(),vdd_y_off)
                 self.cxn_gate_input(self.nand2_inst[j].get_pin(power_pins[i]).uc(), vdd_y_off)

            for mod in [self.pre_ack_b_inst[0], self.ack_b_inst, self.wack_b_inst[0], self.rack_b_inst[0]]:
                vdd_y_off= vector(0, self.vdd_offset.y+i*self.m_pitch("m1"))
                self.cxn_gate_input(mod.get_pin(power_pins[i]).uc(), vdd_y_off)
