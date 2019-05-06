""" This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301, USA.
"""
import design
import debug
import contact
import math
from tech import drc, parameter, spice
from vector import vector
from driver import driver
from pinv import pinv
from nor3 import nor3
from replica_bitline import replica_bitline
from pull_up_pull_down import pull_up_pull_down 

class bank_control_logic(design.design):
    """ Dynamically generated Control logic for the a single Bank """

    def __init__(self, num_rows, num_subanks, two_level_bank=True, name="bank_control_logic"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.num_rows = num_rows
        self.num_subanks = num_subanks
        self.two_level_bank = two_level_bank
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_offsets()
        self.add_modules()
        self.height= self.rbl.ul().y - self.min_off_y + self.m_pitch("m1")
        
        #Pin_width coresponds to the position of the last instance with its connections
        if self.num_subanks > 1:
            # data_ready_inst + 4*m1_pitch for connections
            self.pin_width = self.dr_inst.lr().x + 4*self.m_pitch("m1")
        else:
            if self.two_level_bank:
                # rreq_merge_inv_inst + 3*m1_pitch for connections
                self.pin_width = self.rreq_mrg_inv1_inst.lr().x + 3*self.m_pitch("m1")
            else:
                # decoder_enable_inst + 1*m1_pitch for connections
                self.pin_width = self.dec_en_inst.lr().x + self.m_pitch("m1")

        #replica_bitline_inst + + 5*m1_pitch for connections
        self.pin_width = max(self.replica_bitline.height+5*self.m_pitch("m1"), self.pin_width) 
        
        #total width= pin_width + 3*m1_pitch for spaces for both sides
        self.width = self.pin_width + 3*self.m_pitch("m1")
        self.add_layout_pins()

    def add_pins(self):
        """ Adds pins for control logic module """
        
        self.add_pin_list(["reset", "r", "w", "rw", "ack", "rack", "rreq"])
        if self.two_level_bank:
            self.add_pin("rreq_merge")
        self.add_pin_list(["wreq", "wack"])
        for i in range(self.num_subanks):
            self.add_pin("write_complete[{0}]".format(i))
        for i in range(self.num_subanks):
            self.add_pin("data_ready[{0}]".format(i))
        if self.num_subanks>1:
            for i in range(self.num_subanks):
                self.add_pin("go[{0}]".format(i))
        self.add_pin_list(["sen", "wen", "pchg", "decoder_enable", "vdd", "gnd"])

    def create_modules(self):
        """ Adds all the required modules """
        
        self.nor3 = nor3()
        self.add_mod(self.nor3)
        
        self.inv = pinv(size=1)
        self.add_mod(self.inv)
        
        self.inv2 = pinv(size=2)
        self.add_mod(self.inv2)

        
        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)

        self.u_gate = pull_up_pull_down(num_nmos=2, num_pmos=2, nmos_size=2, pmos_size=3, 
                                        vdd_pins=["S0"], gnd_pins=["S0", "D1"])
        self.add_mod(self.u_gate)

        self.wen_gate = pull_up_pull_down(num_nmos=4, num_pmos=2, nmos_size=2, pmos_size=3, 
                                          vdd_pins=["S0"], gnd_pins=["D3"])
        self.add_mod(self.wen_gate)
        
        self.sen_gate = pull_up_pull_down(num_nmos=3, num_pmos=2, nmos_size=2, pmos_size=3, 
                                          vdd_pins=["S0"], gnd_pins=["D2"])
        self.add_mod(self.sen_gate)

        self.ack_gate = pull_up_pull_down(num_nmos=6, num_pmos=4, nmos_size=2, pmos_size=3, 
                                          vdd_pins=["S0", "D3"], gnd_pins=["D2"])
        self.add_mod(self.ack_gate)

        self.rack_gate = pull_up_pull_down(num_nmos=3, num_pmos=3, nmos_size=1, pmos_size=4, 
                                           vdd_pins=["S0", "D2"], gnd_pins=["S0"])
        self.add_mod(self.rack_gate)

        self.wack_gate = pull_up_pull_down(num_nmos=3, num_pmos=3, nmos_size=2, pmos_size=3, 
                                           vdd_pins=["S0", "D2"], gnd_pins=["S0"])
        self.add_mod(self.wack_gate)
        
        if self.num_subanks > 1:
            gnd_pins =["S0"]
            for i in range(self.num_subanks/2):
                gnd_pins.append("D{0}".format(4*i+3))
        
            self.wc_gate = pull_up_pull_down(num_nmos=2*self.num_subanks, num_pmos=1, 
                                            nmos_size=1, pmos_size=2, 
                                            vdd_pins=["S0"], gnd_pins=gnd_pins)
            self.add_mod(self.wc_gate)

            self.dr_gate = pull_up_pull_down(num_nmos=2*self.num_subanks, num_pmos=1, 
                                             nmos_size=1, pmos_size=2, 
                                             vdd_pins=["S0"], gnd_pins=gnd_pins)
            self.add_mod(self.dr_gate)

        delay_stages = 1
        delay_fanout = 1 
        # replica bitline load is 20% of main bitline load
        bitcell_loads = int(math.ceil(self.num_rows / 5.0))
        self.replica_bitline = replica_bitline(delay_stages, delay_fanout, bitcell_loads)
        self.add_mod(self.replica_bitline)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """

        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.gap= max(self.implant_space,self.well_space,self.m_pitch("m1"))
        
        # Y-offset of input/output pins above the gates
        v_shift = self.inv5.width+2*self.inv2.width+self.ack_gate.width+self.well_space
        if self.num_subanks > 1:
            v_shift = max(v_shift, self.inv.width + self.wc_gate.width)
        self.wen_off_y = v_shift+2*self.m_pitch("m2")
        self.pchg_off_y = self.wen_off_y+self.m_pitch("m2")
        self.reset_bar_off_y = self.pchg_off_y+self.m_pitch("m2")
        if self.num_subanks > 1:
            self.comp_off_y = self.reset_bar_off_y            
        self.rblk_off_y = self.U_off_y = self.reset_bar_off_y+self.m_pitch("m2")
        self.sen_off_y = self.U_off_y+self.m_pitch("m2")
        self.vdd_off_y = self.sen_off_y+self.m_pitch("m2")
        self.gnd_off_y = self.vdd_off_y+self.m_pitch("m2")
        
        # Y-offset of input/output pins blow the gates
        self.r_off_y = -2*self.m_pitch("m2")
        self.wc_off_y = self.r_off_y-self.m_pitch("m2")
        self.rw_off_y = self.wc_off_y-self.m_pitch("m2")
        self.dr_off_y = self.rw_off_y-self.m_pitch("m2")
        self.ack_off_y = self.dr_off_y-self.m_pitch("m2")
        self.wack_off_y = self.ack_off_y
        self.rreq_off_y = self.wack_off_y-self.m_pitch("m2")
        self.data_ready_off_y = self.rreq_off_y-self.m_pitch("m2")
        self.w_off_y = self.data_ready_off_y-self.num_subanks*self.m_pitch("m2")
        self.write_comp_off_y = self.w_off_y-self.m_pitch("m2")
        self.rack_off_y = self.write_comp_off_y-self.num_subanks*self.m_pitch("m2")
        self.reset_off_y = self.rack_off_y
        self.go_off_y = self.reset_off_y-self.m_pitch("m2")
        self.dec_en_off_y = self.wack_off_y
        self.min_off_y = self.go_off_y-self.num_subanks*self.m_pitch("m2")

    def add_modules(self):
        """ Place the gates """
        
        self.add_reset_gate()
        self.add_pchg_gate()
        self.add_u_gate()
        self.add_wen_gate()
        self.add_sen_gate()
        self.add_ack_gate()
        self.add_rack_gate()
        self.add_wack_gate()
        self.add_dec_en_gate()
        if self.two_level_bank:
            self.add_rreq_merge_enable()
        else:
            self.rreq_mrg_inv1_inst_lr_x=self.wack_inst.lr().x+2*self.inv.height+2*self.m_pitch("m1")
        if self.num_subanks > 1: 
            self.add_WC_OR_gate()
            self.add_DR_OR_gate()
        self.add_rbl(0)

    def add_layout_pins(self):
        """ Routing pins to modules input and output"""
        
        self.add_input_rw_pin()
        self.add_input_w_pin()
        self.add_input_r_pin()
        self.add_input_reset_pin()
        self.add_input_wreq_pin()
        self.add_input_rreq_pin()
        self.add_input_dr_pins()
        self.add_input_wc_pins()
        if self.num_subanks > 1: 
            self.add_input_go_pin()
        self.add_output_ack_pin()
        self.add_output_wen_pin()
        self.add_output_wack_pin()
        self.add_output_pchg_pin()
        self.add_output_rack_pin()
        self.add_output_dec_en_pin()
        self.add_U_routing()
        self.add_output_sen_pin()
        self.add_rbl_routing()
        self.route_vdd_gnd()

    def add_m1H_minarea(self, pin):
        """ Adds horizontal metal1 rail in active contact position to avoid DRC min_area"""
        
        self.add_rect_center(layer="metal1",
                             offset=pin,
                             width=self.m1_minarea/contact.m1m2.height,
                             height=contact.m1m2.height)

    def add_m1V_minarea(self, pin):
        """ Adds vertical metal1 rail in active contact position to avoid DRC min_area"""

        self.add_rect_center(layer="metal1",
                             offset=pin,
                             width=contact.m1m2.width,
                             height=self.m1_minarea/contact.m1m2.width)

    def add_m1P_minarea(self, pin, y_off, gap):
        """ Adds vertical metal1 rail in poly contact position to avoid DRC min_area"""

        self.add_rect_center(layer="metal1",
                             offset=(pin.x+0.5*contact.m1m2.width, y_off-gap),
                             width=contact.m1m2.width,
                             height=self.m1_minarea/contact.m1m2.width)

    def add_Zpath(self, pin1, pin2, gap):
        """ Adds a Z connection in m1 between pins (pin1.y> pin2.y) with mid position at pin1.y-gap"""

        self.add_path("metal1",[pin1.uc(), (pin1.uc().x, pin1.lc().y-gap), 
                               (pin2.uc().x, pin1.lc().y-gap), pin2.uc()])
    def add_Zwire(self, pin1, pin2, gap):
        """ Adds a Z connection (m1+via1+m2) between pins (pin1.y> pin2.y) 
            with mid position at pin1.y-gap"""

        self.add_wire(self.m1_rev_stack,[pin1.uc(), (pin1.uc().x, pin1.lc().y-gap), 
                                        (pin2.uc().x, pin1.lc().y-gap), pin2.uc()])

    def add_reset_gate(self):
        """ Adds the inverter for reset signal """

        rst_inv_off= (self.inv.height,0)        
        self.rst_inv_inst=self.add_inst(name="reset_inv", 
                                        mod=self.inv, 
                                        offset=rst_inv_off, 
                                        rotate=90)
        self.connect_inst(["reset", "reset_bar", "vdd", "gnd"])

        # Input and output offset
        self.rst_in_off=self.rst_inv_inst.get_pin("A")
        self.rst_out_off=self.rst_inv_inst.get_pin("Z")


    def add_pchg_gate(self):
        """ Adds the nor3 + inv for pchg signal """

        # adding a contact.m1m2.width space due to bounding box being at the middle of vdd/gnd rails 
        pchg_off= (self.inv.height+self.gap+contact.m1m2.width,0)
        self.pchg_inst=self.add_inst(name="pchg_gate", 
                                     mod=self.nor3, 
                                     offset=pchg_off, 
                                     mirror="MX", 
                                     rotate=90)
        self.connect_inst(["r", "rw", "w", "pre_pchg", "vdd", "gnd"])

        # Adding an inverter above nor3 gate
        pchg_inv_off= (self.inv.height+self.gap+contact.m1m2.width, self.nor3.width)        
        self.pchg_inv_inst=self.add_inst(name="pchg_inv", 
                                         mod=self.inv5, 
                                         offset=pchg_inv_off, 
                                         mirror="MX", 
                                         rotate=90)
        self.connect_inst(["pre_pchg", "pchg", "vdd", "gnd"])

        # output offset
        self.pchg_off=self.pchg_inv_inst.get_pin("Z")
        
        # Connecting nor3 output to inverter input
        self.add_path("metal1",[self.pchg_inst.get_pin("Z").uc(), 
                                self.pchg_inv_inst.get_pin("A").uc()])

    def add_u_gate(self):
        """Adds pull_up_pull_down network for u-gate """

        #add 2*m1_pitch for 2 connections of u_gate
        u_off= (self.pchg_inv_inst.lr().x + self.u_gate.height + 2*self.m_pitch("m1"), 0)
        self.u_inst=self.add_inst(name="u_gate", 
                                  mod=self.u_gate, 
                                  offset=u_off, 
                                  mirror="R0", 
                                  rotate=90)
        temp = []
        temp.extend(["gnd", "reset", "u", "ack", "gnd"])
        temp.extend(["vdd", "pre_pchg", "net_u_1", "ack", "u", "vdd", "gnd"])
        self.connect_inst(temp)
        
        #input & output offset
        self.u_rst_in_off=self.u_inst.get_pin("Gn0")
        self.u_out_off = self.u_inst.get_pin("Dn0")
        self.u_pre_pchg_in_off=self.u_inst.get_pin("Gp0")
        self.u_ack_in_off=self.u_inst.get_pin("Gp1")
        
        #Connecting poly-gates that are driven by same signal
        self.add_path("poly", [self.u_inst.get_pin("Gn1").uc(), self.u_inst.get_pin("Gp1").uc()])
        
        #Adding a Z connection for output node
        self.add_Zpath(self.u_inst.get_pin("Dn0"), self.u_inst.get_pin("Dp1"), self.m_pitch("m1"))
        
        #Extending the implant to cover poly contact
        self.add_rect(layer="pimplant",
                      offset=self.u_inst.ul(),
                      width=self.u_inst.height,
                      height=contact.poly.height+self.implant_enclose_poly)

        #Adding min_area metal1 for active contacts with no connections and in poly_contact positions
        self.add_m1V_minarea(self.u_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.u_inst.get_pin("Sp0").cc())
        self.add_m1H_minarea(self.u_inst.get_pin("Dn1").cc())
        self.add_m1H_minarea(self.u_inst.get_pin("Sn0").cc())
        self.add_m1P_minarea(self.u_inst.get_pin("Gp0").lc(), self.u_inst.ll().y,0)
        self.add_m1P_minarea(self.u_inst.get_pin("Gn0").lr(), self.u_inst.ul().y, 0) 

    def add_wen_gate(self):
        """ Adds the pull_up_pull_down network for wen-gate """
        
        #add 3*m1_pitch for 3 connections of wen_gate
        wen_off= (self.u_inst.lr().x+3*self.m_pitch("m1"),0)
        self.wen_inst=self.add_inst(name="wen_gate", 
                                    mod=self.wen_gate, 
                                    offset=wen_off, 
                                    mirror="MX", 
                                    rotate=90)
        temp = []
        temp.extend(["net_wen_2", "w", "pre_wen", "rw", "net_wen_3", "rack", "net_wen_2", "u", "gnd"])
        temp.extend(["vdd", "w", "net_wen_1", "rw", "pre_wen", "vdd", "gnd"])
        self.connect_inst(temp)

        #adding 0.5*con.m1m2.width to share vdd rail
        wen_inv_off= (wen_off[0] + 0.5*contact.m1m2.width, self.wen_gate.width)        
        self.wen_inv_inst=self.add_inst(name="delay_wen_inv", 
                                        mod=self.inv5, 
                                        offset=wen_inv_off, 
                                        mirror="MX", 
                                        rotate=90)
        self.connect_inst(["pre_wen", "wen", "vdd", "gnd"])
        
        #input & output offset
        self.wen_w_in_off=self.wen_inst.get_pin("Gp0")
        self.wen_rw_in_off=self.wen_inst.get_pin("Gp1")
        self.wen_rack_in_off=self.wen_inst.get_pin("Gn2")
        self.wen_u_in_off=self.wen_inst.get_pin("Gn3")
        self.wen_out_off=self.wen_inv_inst.get_pin("Z")
        
        #Connecting poly-gates that are driven by same signal
        self.add_path("poly", [self.wen_inst.get_pin("Gn0").uc(), self.wen_inst.get_pin("Gp0").uc()])
        self.add_path("poly", [self.wen_inst.get_pin("Gn1").uc(), self.wen_inst.get_pin("Gp1").uc()])
        
        #Adding a Z connection for output node
        self.add_Zpath(self.wen_inst.get_pin("Dn0"),self.wen_inst.get_pin("Dp1"),self.m_pitch("m1")) 

        #Connecting the output node to inv input
        self.add_path("metal1",[self.wen_inst.get_pin("Dn0").uc(),self.wen_inv_inst.get_pin("A").lc()])
        
        #Adding a Z connection for active contact connections
        self.add_Zwire(self.wen_inst.get_pin("Sn0"), self.wen_inst.get_pin("Dn2"),self.m_pitch("m1"))
        
        #Connecting the vdd of inv to wen_inst, gnd is connected by abutment
        self.add_path("metal1", [self.wen_inst.get_pin("vdd").uc(), 
                                 self.wen_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1V_minarea(self.wen_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.wen_inst.get_pin("Sp0").cc())
        self.add_m1H_minarea(self.wen_inst.get_pin("Dn1").cc())
        self.add_m1H_minarea(self.wen_inst.get_pin("Dn3").cc())
        self.add_m1P_minarea(self.wen_inst.get_pin("Gn3").lc(), self.wen_inst.ll().y,0)

    def add_sen_gate(self):
        """ Adds the pull_up_pull_down network for sen-gate """

        #-con.m1m2.width to share vdd between sen and wen gates
        sen_off= (self.wen_inst.lr().x+self.sen_gate.height-contact.m1m2.width,0)
        self.sen_inst=self.add_inst(name="sen_gate", 
                                    mod=self.sen_gate, 
                                    offset=sen_off, 
                                    mirror="R0", 
                                    rotate=90)
        temp = []
        temp.extend(["net_sen_2", "r", "pre_rblk", "rw", "net_sen_2", "u", "gnd"])
        temp.extend(["vdd", "r", "net_sen_1", "rw", "pre_rblk", "vdd", "gnd"])
        self.connect_inst(temp)
        
        #-0.5*con.m1m2.width to share vdd
        sen_inv_off= (sen_off[0]-0.5*contact.m1m2.width, self.sen_gate.width)        
        self.sen_inv_inst=self.add_inst(name="delay_sen_inv", 
                                        mod=self.inv5, 
                                        offset=sen_inv_off, 
                                        mirror="R0", 
                                        rotate=90)
        self.connect_inst(["pre_rblk", "rblk", "vdd", "gnd"])

        #input & output offsets
        self.sen_r_in_off=self.sen_inst.get_pin("Gn0")
        self.sen_rw_in_off=self.sen_inst.get_pin("Gn1")
        self.sen_u_in_off=self.sen_inst.get_pin("Gn2")
        self.sen_out_off=self.sen_inv_inst.get_pin("Z")

        #Connecting poly-gates that are driven by same signal
        self.add_path("poly", [self.sen_inst.get_pin("Gn0").uc(), self.sen_inst.get_pin("Gp0").uc()])
        self.add_path("poly", [self.sen_inst.get_pin("Gn1").uc(), self.sen_inst.get_pin("Gp1").uc()])
        
        #Adding a Z connection for output node
        self.add_Zpath(self.sen_inst.get_pin("Dp1"),self.sen_inst.get_pin("Dn0"),-self.m_pitch("m1"))
        
        #Connecting the output node to inv input
        self.add_path("metal1",[self.sen_inst.get_pin("Dn0").uc(),self.sen_inv_inst.get_pin("A").lc()])

        #Adding a Z connection for active contact connections
        self.add_Zwire(self.sen_inst.get_pin("Sn0"),self.sen_inst.get_pin("Dn1"),self.m_pitch("m1"))
        
        #Connecting the vdd of inv to sen_inst, gnd is connected by abutment
        self.add_path("metal1", [self.sen_inst.get_pin("vdd").uc(),
                                 self.sen_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)  
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1H_minarea(self.sen_inst.get_pin("Dn2").cc())
        self.add_m1H_minarea(self.sen_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.sen_inst.get_pin("Sp0").cc())
        self.add_m1P_minarea(self.sen_inst.get_pin("Gn2").ll(),self.sen_inst.ll().y,contact.poly.height)
        
    def add_ack_gate(self):
        """" Adds the pull_up_pull_down network for ack-gate """

        #add 6*m1_pitch for 6 connections of ack_gate
        ack_off= (self.sen_inst.lr().x+6*self.m_pitch("m1"),0)
        self.ack_inst=self.add_inst(name="ack_gate", 
                                    mod=self.ack_gate, 
                                    offset=ack_off, 
                                    mirror="MX", 
                                    rotate=90)
        temp = []
        temp.extend(["ack1", "pchg", "net_ack3", "r", "net_ack4", "rack"])
        temp.extend(["gnd", "wack", "net_ack5", "w", "net_ack3", "rw", "net_ack5"])
        temp.extend(["vdd", "pchg", "net_ack1", "wack", "net_ack2", "rack"])
        temp.extend(["ack1", "reset_bar", "vdd", "vdd", "gnd"])
        self.connect_inst(temp)
        
        # 0.5*con.m1m2.width for vdd sharing
        ack_inv_off1= (ack_off[0]+0.5*contact.m1m2.width, self.ack_gate.width+self.gap)        
        self.ack_inv_inst1=self.add_inst(name="delay_ack_inv1", 
                                   mod=self.inv2, 
                                   offset=ack_inv_off1, 
                                   mirror="MX", 
                                   rotate=90)
        self.connect_inst(["ack1", "ack2", "vdd", "gnd"])
        ack_inv_off2= (ack_inv_off1[0], ack_inv_off1[1]+self.inv2.width)
        self.ack_inv_inst2=self.add_inst(name="delay_ack_inv2", 
                                   mod=self.inv2, 
                                   offset=ack_inv_off2, 
                                   mirror="MX", 
                                   rotate=90)
        self.connect_inst(["ack2", "pre_ack", "vdd", "gnd"])
        ack_inv_off= (ack_inv_off2[0], ack_inv_off2[1]+self.inv2.width)
        self.ack_inv_inst=self.add_inst(name="delay_ack_inv", 
                                   mod=self.inv5, 
                                   offset=ack_inv_off, 
                                   mirror="MX", 
                                   rotate=90)
        self.connect_inst(["pre_ack", "ack", "vdd", "gnd"])
        
        #input & output offset
        self.ack_pchg_in_off=self.ack_inst.get_pin("Gn0")
        self.ack_r_in_off=self.ack_inst.get_pin("Gn1")
        self.ack_rack_in_off=self.ack_inst.get_pin("Gn2")
        self.ack_wack_in_off2=self.ack_inst.get_pin("Gn3")
        self.ack_w_in_off=self.ack_inst.get_pin("Gn4")
        self.ack_rw_in_off=self.ack_inst.get_pin("Gn5")
        self.ack_wack_in_off1=self.ack_inst.get_pin("Gp1")
        self.ack_reset_bar_in_off = self.ack_inst.get_pin("Gp3")
        self.ack_out_off=self.ack_inv_inst.get_pin("Z").lr()-vector(0,0.5*self.m2_width)

        #Connecting poly-gates that are driven by same signal
        self.add_path("poly", [self.ack_inst.get_pin("Gn0").uc(),self.ack_inst.get_pin("Gp0").uc()])
        self.add_path("poly", [self.ack_inst.get_pin("Gn2").uc(),self.ack_inst.get_pin("Gp2").uc()])

        #Adding a Z connection for active contact connections
        self.add_Zwire(self.ack_inst.get_pin("Dn0"),self.ack_inst.get_pin("Dn4"),-self.m_pitch("m2"))
        self.add_Zpath(self.ack_inst.get_pin("Dn3"),self.ack_inst.get_pin("Dn5"),self.m_pitch("m1")) 

        #Adding a Z connection for output node
        self.add_Zpath(self.ack_inst.get_pin("Sn0"), self.ack_inst.get_pin("Dp2"),self.m_pitch("m1")) 
        
        #Connecting output of ack_inst to inv input
        self.add_path("metal1",[self.ack_inst.get_pin("Sn0").uc(),
                               (self.ack_inv_inst1.get_pin("A").lr()-vector(0,0.5*self.m1_width))])
        self.add_path("metal1",[self.ack_inv_inst1.get_pin("Z").uc(),
                               self.ack_inv_inst2.get_pin("A").lc()])
        self.add_path("metal1",[self.ack_inv_inst2.get_pin("Z").uc(),
                                self.ack_inv_inst.get_pin("A").lc()])
        
        #Connecting the vdd of inv to ack_inst vdd, gnd is connected by abutment
        self.add_path("metal1", [self.ack_inst.get_pin("vdd").uc(), 
                                 self.ack_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)

        #Extending the implant to cover poly contact
        self.add_rect(layer="pimplant",
                      offset=self.ack_inst.ul(),
                      width=self.ack_inst.height,
                      height=self.gap)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1V_minarea(self.ack_inst.get_pin("Sp0").cc())
        self.add_m1V_minarea(self.ack_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.ack_inst.get_pin("Dp1").cc())
        self.add_m1V_minarea(self.ack_inst.get_pin("Dp3").cc())
        self.add_m1H_minarea(self.ack_inst.get_pin("Dn1").cc())
        self.add_m1V_minarea((self.ack_inst.get_pin("Dn2").uc() + vector(0, self.m1_width)))
        self.add_m1P_minarea(self.ack_inst.get_pin("Gn0").lc(), self.ack_inst.ll().y,self.m1_width)
        self.add_m1P_minarea(self.ack_inst.get_pin("Gn3").lc(),self.ack_inst.ll().y,0)
        self.add_m1P_minarea(self.ack_inst.get_pin("Gn1").lc(),self.ack_inst.ul().y,-self.m1_width)
        self.add_m1P_minarea(self.ack_inst.get_pin("Gn3").lc(),self.ack_inst.ul().y,-self.m1_width)
        self.add_m1H_minarea(self.ack_inv_inst.get_pin("Z").uc())
        
    def add_rack_gate(self):
        """" Adds the pull_up_pull_down network for rack-gate """

        #add 4*m1_pitch for 4 connections of rack_gate
        rack_off= (self.ack_inst.lr().x+self.rack_gate.height+4*self.m_pitch("m1"),0)
        self.rack_inst=self.add_inst(name="rack_gate", 
                                     mod=self.rack_gate, 
                                     offset=rack_off, 
                                     mirror="R0", 
                                     rotate=90)
        temp = []
        if self.num_subanks > 1:
            temp.extend(["gnd", "u", "net_rack2", "rreq", "net_rack3", "data_ready", "rack1"])
        else:
            temp.extend(["gnd", "u", "net_rack2", "rreq", "net_rack3", "data_ready[0]", "rack1"])

        temp.extend(["vdd", "u", "net_rack1","rreq", "rack1","reset_bar", "vdd"])
        temp.extend(["vdd", "gnd"])
        self.connect_inst(temp)

        # -0.5*con.m1m2.width for vdd sharing
        rack_inv_off1= (rack_off[0]-0.5*contact.m1m2.width, self.rack_gate.width+self.gap)        
        self.rack_inv_inst1=self.add_inst(name="delay_rack_inv1", 
                                    mod=self.inv2, 
                                    offset=rack_inv_off1, 
                                    mirror="R0", 
                                    rotate=90)
        self.connect_inst(["rack1", "rack2", "vdd", "gnd"])
        rack_inv_off2= (rack_inv_off1[0], rack_inv_off1[1]+self.inv2.width)        
        self.rack_inv_inst2=self.add_inst(name="delay_rack_inv2", 
                                    mod=self.inv2, 
                                    offset=rack_inv_off2, 
                                    mirror="R0", 
                                    rotate=90)
        self.connect_inst(["rack2", "pre_rack", "vdd", "gnd"])

        rack_inv_off= (rack_inv_off2[0], rack_inv_off2[1]+self.inv2.width)        
        self.rack_inv_inst=self.add_inst(name="delay_rack_inv", 
                                    mod=self.inv5, 
                                    offset=rack_inv_off, 
                                    mirror="R0", 
                                    rotate=90)
        self.connect_inst(["pre_rack", "rack", "vdd", "gnd"])
        
        #input & output offset
        self.rack_u_in_off = self.rack_inst.get_pin("Gp0")
        self.rack_rreq_in_off= self.rack_inst.get_pin("Gp1")
        self.rack_rst_b_in_off= self.rack_inst.get_pin("Gp2")
        self.rack_dr_in_off = self.rack_inst.get_pin("Gn2")
        self.rack_out_off=self.rack_inv_inst.get_pin("Z").bc()-vector(0,0.5*self.m2_width)

        #Connecting poly-gates that are driven by same signal
        self.add_path("poly",[self.rack_inst.get_pin("Gn0").uc(),self.rack_inst.get_pin("Gp0").uc()])
        self.add_path("poly",[self.rack_inst.get_pin("Gn1").uc(),self.rack_inst.get_pin("Gp1").uc()])
        
        #Adding a Z connection for output node
        self.add_Zpath(self.rack_inst.get_pin("Dn2"),self.rack_inst.get_pin("Dp1"),self.m_pitch("m1"))

        #Connecting output of rack_inst to inv input
        self.add_Zpath(self.rack_inst.get_pin("Dn2"),self.rack_inv_inst1.get_pin("A"),-self.m_pitch("m1"))
        self.add_path("metal1", [self.rack_inv_inst1.get_pin("Z").uc(),self.rack_inv_inst2.get_pin("A").lc()])
        self.add_path("metal1", [self.rack_inv_inst2.get_pin("Z").uc(),self.rack_inv_inst.get_pin("A").lc()])
        
        #Connecting the vdd and gnd of inv to rack_inst
        self.add_path("metal1", [self.rack_inst.get_pin("vdd").uc(),
                                self.rack_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)
        self.add_path("metal1", [self.rack_inst.get_pin("gnd").uc(),
                                 self.rack_inv_inst.get_pin("gnd").lc()], width=contact.m1m2.width)
        
        #Extending the implant to cover poly contact
        self.add_rect(layer="pimplant",
                      offset=self.rack_inst.ul(),
                      width=self.rack_inst.height,
                      height=self.gap)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1V_minarea(self.rack_inst.get_pin("Sp0").cc())
        self.add_m1V_minarea(self.rack_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.rack_inst.get_pin("Dp2").cc())
        self.add_m1V_minarea(self.rack_inst.get_pin("Sn0").cc())
        self.add_m1V_minarea(self.rack_inst.get_pin("Dn0").cc()-vector(0, self.m1_width))
        self.add_m1H_minarea(self.rack_inst.get_pin("Dn1").cc())
        self.add_m1P_minarea(self.rack_inst.get_pin("Gp0").lc(), self.rack_inst.ll().y,0)
        self.add_m1P_minarea(self.rack_inst.get_pin("Gp2").lc(), self.rack_inst.ll().y,0)
        self.add_m1P_minarea(self.rack_inst.get_pin("Gn2").lc(), self.rack_inst.ul().y,0)
        self.add_m1H_minarea(self.rack_inv_inst.get_pin("Z").uc())
        
    def add_wack_gate(self):
        """" Adds the pull_up_pull_down network for wack-gate """

        #add 5*m1_pitch for 5 connections of wack_gate
        wack_off= (self.rack_inst.lr().x+5*self.m_pitch("m1"),0)
        self.wack_inst=self.add_inst(name="wack_gate", 
                                     mod=self.wack_gate, 
                                     offset=wack_off, 
                                     mirror="MX", 
                                     rotate=90)
        temp = []
        if self.num_subanks > 1:
            temp.extend(["gnd", "u", "net_wack2", "wreq", "net_wack3", "write_complete", "wack1"])
        else:
            temp.extend(["gnd","u","net_wack2", "wreq", "net_wack3", "write_complete[0]","wack1"])
        temp.extend(["vdd", "u", "net_wack1", "wreq", "wack1", "reset_bar", "vdd"])
        temp.extend(["vdd", "gnd"])
        self.connect_inst(temp)

        # -0.5*con.m1m2.width for vdd sharing
        wack_inv_off1= (self.wack_inst.lr().x-self.inv.height-0.5*contact.m1m2.width,
                       self.wack_gate.width+self.gap)        
        self.wack_inv_inst1=self.add_inst(name="delay_wack_inv1", 
                                         mod=self.inv2, 
                                         offset=wack_inv_off1, 
                                         mirror="MX", 
                                         rotate=90)
        self.connect_inst(["wack1", "wack2", "vdd", "gnd"])
        wack_inv_off2= (wack_inv_off1[0], wack_inv_off1[1]+self.inv2.width)        
        self.wack_inv_inst2=self.add_inst(name="delay_wack_inv2", 
                                         mod=self.inv2, 
                                         offset=wack_inv_off2, 
                                         mirror="MX", 
                                         rotate=90)
        self.connect_inst(["wack2", "pre_wack", "vdd", "gnd"])
        wack_inv_off= (wack_inv_off2[0], wack_inv_off2[1]+self.inv2.width)        
        self.wack_inv_inst=self.add_inst(name="delay_wack_inv", 
                                         mod=self.inv5, 
                                         offset=wack_inv_off, 
                                         mirror="MX", 
                                         rotate=90)
        self.connect_inst(["pre_wack", "wack", "vdd", "gnd"])
        
        #input & output offset
        self.wack_u_in_off = self.wack_inst.get_pin("Gn0")
        self.wack_wc_in_off = self.wack_inst.get_pin("Gn2")
        self.wack_wreq_in_off = self.wack_inst.get_pin("Gp1")
        self.wack_rst_b_in_off = self.wack_inst.get_pin("Gp2")
        self.wack_out_off=self.wack_inv_inst.get_pin("Z").bc()-vector(0,self.m2_width)

        #Connecting poly-gates that are driven by same signal
        self.add_path("poly",[self.wack_inst.get_pin("Gn0").uc(),self.wack_inst.get_pin("Gp0").uc()])
        self.add_path("poly",[self.wack_inst.get_pin("Gn1").uc(),self.wack_inst.get_pin("Gp1").uc()])
        
        #Adding a Z connection for output node
        self.add_Zpath(self.wack_inst.get_pin("Dn2"),self.wack_inst.get_pin("Dp1"),self.m_pitch("m1"))
        
        #Connecting output of wack_inst to inv input
        pos1=(self.wack_inv_inst1.get_pin("A").bc()-vector(0,0.5*self.m1_width))
        pos2=(self.wack_inv_inst1.lr().x-self.m_pitch("m1"),pos1[1])
        pos3=(pos2[0],self.wack_inst.get_pin("Dn2").uc().y)
        self.add_path("metal1", [self.wack_inv_inst1.get_pin("A").uc(),
                                 pos1, pos2, pos3, self.wack_inst.get_pin("Dn2").ul()])
        self.add_path("metal1", [self.wack_inv_inst1.get_pin("Z").uc(),self.wack_inv_inst2.get_pin("A").lc()])
        self.add_path("metal1", [self.wack_inv_inst2.get_pin("Z").uc(),self.wack_inv_inst.get_pin("A").lc()])
        
        #Connecting the vdd and gnd of inv to wack_inst
        self.add_path("metal1", [self.wack_inst.get_pin("vdd").uc(), 
                                 self.wack_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)
        self.add_path("metal1", [self.wack_inst.get_pin("gnd").uc(), 
                                 self.wack_inv_inst.get_pin("gnd").lc()], width=contact.m1m2.width)
        
        #Extending the implant to cover poly contact
        self.add_rect(layer="pimplant",
                      offset=self.wack_inst.ul(),
                      width=self.wack_inst.height,
                      height=self.gap)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1V_minarea(self.wack_inst.get_pin("Sp0").cc())
        self.add_m1V_minarea(self.wack_inst.get_pin("Dp0").cc())
        self.add_m1V_minarea(self.wack_inst.get_pin("Dp2").cc())
        self.add_m1V_minarea(self.wack_inst.get_pin("Sn0").cc())
        self.add_m1V_minarea(self.wack_inst.get_pin("Dn0").cc())
        self.add_m1H_minarea(self.wack_inst.get_pin("Dn1").cc())
        self.add_m1P_minarea(self.wack_inst.get_pin("Gn2").lc(),self.wack_inst.ul().y,0)
        self.add_m1P_minarea(self.wack_inst.get_pin("Gp0").lc(),self.wack_inst.ll().y,0)
        self.add_m1P_minarea(self.wack_inst.get_pin("Gp2").lc(),self.wack_inst.ll().y,0)
        self.add_m1H_minarea(self.wack_inv_inst.get_pin("Z").uc())

    def add_dec_en_gate(self):
        """ Adds delays for decode_enable signals """

        #add 4*m1_pitch for 4 connections of decoder_enable_gate + 0.5*con.m1m2.width for vdd sharing
        delay_inv_off= (self.wack_inst.lr().x+4*self.m_pitch("m1")+\
                        0.5*contact.m1m2.width, self.inv5.width)        
        self.dec_en_inst=self.add_inst(name="decoder_enable_inv", 
                                       mod=self.inv5, 
                                       offset=delay_inv_off, 
                                       mirror="R0", 
                                       rotate=270)
        self.connect_inst(["pchg", "decoder_enable", "vdd", "gnd"])

        #input & output offset
        self.dec_en_in_off=self.dec_en_inst.get_pin("A")
        self.dec_en_out_off=self.dec_en_inst.get_pin("Z")

    def add_rreq_merge_enable(self):
        """ Adds buffer for rreq signal of dout merge array when two_level_bank"""

        #add 4*m1_pitch for 4 connections of rreq_gate + 0.5*con.m1m2.width for vdd sharing
        rreq_mrg_inv_off= (self.wack_inst.lr().x+ 2* self.inv.height+4*self.m_pitch("m1")+\
                           0.5*contact.m1m2.width,self.inv5.width)        
        self.rreq_mrg_inv1_inst=self.add_inst(name="rreq_merge_inv_0", 
                                              mod=self.inv5, 
                                              offset=rreq_mrg_inv_off, 
                                              mirror="MX", 
                                              rotate=270)
        self.connect_inst(["pre_rreq", "rreq_merge", "vdd", "gnd"])
        
        self.rreq_mrg_inv2_inst=self.add_inst(name="rreq_merge_inv_1", 
                                              mod=self.inv, 
                                              offset=rreq_mrg_inv_off+vector(0,self.inv.width), 
                                              mirror="MX", 
                                              rotate=270)
        self.connect_inst(["rreq", "pre_rreq", "vdd", "gnd"])

        rreq_mrg_in_off=self.rreq_mrg_inv2_inst.get_pin("A")
        rreq_mrg_out_off=self.rreq_mrg_inv1_inst.get_pin("Z")
        
        #Connecting output of rreq_inv2 to rreq_inv2 input
        self.add_path("metal1", [self.rreq_mrg_inv1_inst.get_pin("A").uc(),
                                 self.rreq_mrg_inv2_inst.get_pin("Z").lc()])

        self.add_path("metal1", [rreq_mrg_out_off.uc(),(rreq_mrg_out_off.uc().x, self.min_off_y)])
        
        self.add_layout_pin(text="rreq_merge",
                            layer=self.m1_pin_layer,
                            offset=(rreq_mrg_out_off.ll().x, self.min_off_y),
                            width=self.m1_width,
                            height=self.m1_width)
        
        pos1=rreq_mrg_in_off.uc()+vector(0,self.m_pitch("m1"))
        pos2=(self.rreq_mrg_inv2_inst.lr().x+self.m_pitch("m1"),pos1[1])
        pos3=(pos2[0], self.rreq_off_y)
        self.add_wire(self.m1_rev_stack, [rreq_mrg_in_off.uc(),pos1, pos2, pos3]) 
        
        self.add_via(self.m1_stack,(pos2[0],self.rreq_off_y), rotate=90)
                           
        # Calculating the offset for next cell
        self.rreq_mrg_inv1_inst_lr_x = self.rreq_mrg_inv1_inst.lr().x+2*self.m_pitch("m1")
    
    def add_WC_OR_gate(self):
        """" Adds the pull_up_pull_down network for write_complete-gate """

        #add 2*m1_pitch for 2 connections of write_complete_gate
        wc_off= (self.rreq_mrg_inv1_inst_lr_x+self.wc_gate.height+2*self.m_pitch("m1"),
                 self.wc_gate.width)
        self.wc_inst=self.add_inst(name="write_complete_gate", 
                                   mod=self.wc_gate, 
                                   offset=wc_off, 
                                   mirror="MX", 
                                   rotate=270)
        temp = []
        for i in range(self.num_subanks/2):
            temp.extend(["gnd", "write_complete[{0}]".format(2*i), "net[{0}]".format(2*i), 
                         "go[{0}]".format(2*i), "pre_WC", "write_complete[{0}]".format(2*i+1), 
                         "net[{0}]".format(2*i+1), "go[{0}]".format(2*i+1)])
        temp.extend(["gnd"])
        temp.extend(["vdd", "pchg", "pre_WC", "vdd", "gnd"])
        self.connect_inst(temp)
        
        # -0.5*con.m1m2.width for vdd sharing
        wc_inv_off= (wc_off[0]-0.5*contact.m1m2.width, self.wc_gate.width)        
        self.wc_inv_inst=self.add_inst(name="write_complete_inv", 
                                       mod=self.inv, 
                                       offset=wc_inv_off, 
                                       mirror="R0", 
                                       rotate=90)
        self.connect_inst(["pre_WC", "write_complete", "vdd", "gnd"])
        
        #input & output offset
        self.wc_off=self.wc_inv_inst.get_pin("Z")
        self.WC_pchg_off = self.wc_inst.get_pin("Gp0")
        self.WC_off={}
        self.wc_go_off={}
        for i in range(self.num_subanks):
            self.WC_off[i] = self.wc_inst.get_pin("Gn{0}".format(2*i))
            self.wc_go_off[i] = self.wc_inst.get_pin("Gn{0}".format(2*i+1))

        Dn_contact={}
        for i in range(self.num_subanks/2):
            Dn_contact[i] = self.wc_inst.get_pin("Dn{0}".format(4*i+1))
        
        for i in range(self.num_subanks/2 - 1):
            self.add_Zpath(Dn_contact[i], Dn_contact[i+1], -1.5*self.m_pitch("m1"))

        #Adding a Z connection for output node
        Dp_contact = self.wc_inst.get_pin("Dp0").uc()
        self.add_path("metal1", [Dn_contact[self.num_subanks/2-1].uc(), Dp_contact])
        
        #Connecting output of wc_inst to inv input
        self.add_path("metal1", [Dp_contact, self.wc_inv_inst.get_pin("A").uc()])
        
        #Connecting the vdd of inv to wc_inst, gnd is connected by abutment
        self.add_path("metal1", [self.wc_inst.get_pin("vdd").uc(), 
                                 self.wc_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1H_minarea(self.wc_inst.get_pin("Sp0").cc())
        self.add_m1V_minarea(self.wc_inst.get_pin("Sn0").cc())
        self.add_m1V_minarea(self.wc_inst.get_pin("Dn{0}".format(2*self.num_subanks-1)).cc())
        self.add_m1P_minarea(self.wc_inst.get_pin("Sp0").ll(),self.wc_inst.ul().y,self.m_pitch("m1"))
        for i in range(2*self.num_subanks-1):
            self.add_m1V_minarea(self.wc_inst.get_pin("Dn{0}".format(i)).cc())

    def add_DR_OR_gate(self):
        """" Adds the pull_up_pull_down network for write_complete-gate """

        #add a gap for well/implant spacing between write_complete and data_ready gate
        dr_off= (self.wc_inst.lr().x+self.dr_gate.height+self.gap, self.dr_gate.width)
        self.dr_inst=self.add_inst(name="data_ready_gate", 
                                   mod=self.dr_gate, 
                                   offset=dr_off, 
                                   mirror="MX", 
                                   rotate=270)
        temp = []
        for i in range(self.num_subanks/2):
            temp.extend(["gnd", "data_ready[{0}]".format(2*i), "net[{0}]".format(2*i+self.num_subanks), 
                         "go[{0}]".format(2*i), "pre_DR","data_ready[{0}]".format(2*i+1), 
                         "net[{0}]".format(2*i+1+self.num_subanks), "go[{0}]".format(2*i+1)])
        temp.extend(["gnd"])
        temp.extend(["vdd", "pchg", "pre_DR", "vdd", "gnd"])
        self.connect_inst(temp)
        
        # -0.5*con.m1m2.width for vdd sharing
        dr_inv_off= (dr_off[0]-0.5*contact.m1m2.width, self.dr_gate.width)        
        self.dr_inv_inst=self.add_inst(name="data_ready_inv", 
                                       mod=self.inv, 
                                       offset=dr_inv_off, 
                                       mirror="R0", 
                                       rotate=90)
        self.connect_inst(["pre_DR", "data_ready", "vdd", "gnd"])
        
        #input & output offset
        self.dr_off=self.dr_inv_inst.get_pin("Z")
        self.DR_pchg_off = self.dr_inst.get_pin("Gp0")
        self.DR_off={}
        self.dr_go_off={}
        for i in range(self.num_subanks):
            self.DR_off[i] = self.dr_inst.get_pin("Gn{0}".format(2*i))
            self.dr_go_off[i] = self.dr_inst.get_pin("Gn{0}".format(2*i+1))

        Dn_contact={}
        for i in range(self.num_subanks/2):
            Dn_contact[i] = self.dr_inst.get_pin("Dn{0}".format(4*i+1))
        
        for i in range(self.num_subanks/2 - 1):
            self.add_Zpath(Dn_contact[i], Dn_contact[i+1], -1.5*self.m_pitch("m1"))

        #Adding a Z connection for output node
        Dp_contact = self.dr_inst.get_pin("Dp0").uc()
        self.add_path("metal1", [Dn_contact[self.num_subanks/2-1].uc(), Dp_contact])
        
        #Connecting output of dr_inst to inv input
        self.add_path("metal1", [Dp_contact, self.dr_inv_inst.get_pin("A").uc()])
        
        #Connecting the vdd of inv to dr_inst, gnd is connected by abutment
        self.add_path("metal1", [self.dr_inst.get_pin("vdd").uc(), 
                                 self.dr_inv_inst.get_pin("vdd").lc()], width=contact.m1m2.width)
        
        #Adding min_area metal1 for active contacts with no connections and poly_contact positions
        self.add_m1H_minarea(self.dr_inst.get_pin("Sp0").cc())
        self.add_m1V_minarea(self.dr_inst.get_pin("Sn0").cc())
        self.add_m1V_minarea(self.dr_inst.get_pin("Dn{0}".format(2*self.num_subanks-1)).cc())
        self.add_m1P_minarea(self.dr_inst.get_pin("Sp0").ll(),self.dr_inst.ul().y,self.m_pitch("m1"))
        for i in range(2*self.num_subanks-1):
            self.add_m1V_minarea(self.dr_inst.get_pin("Dn{0}".format(i)).cc())

    def add_rbl(self,y_off):
        """ Adds the replica bitline """
        
        #adding the replica bitline above the last pin (gnd) + one m1_pitch space
        rbl_off= (self.replica_bitline.height, self.gnd_off_y+self.m_pitch("m1"))
        self.rbl=self.add_inst(name="replica_bitline", 
                               mod=self.replica_bitline,
                               offset=rbl_off,
                               rotate=90)
        self.connect_inst(["rblk", "sen", "vdd", "gnd"])
        
        #input & output offset
        self.rblk_in_off=self.rbl.get_pin("en").lc()
        self.rblk_out_off=self.rbl.get_pin("out").lc()
        
    def add_input_rw_pin(self):
        """ Adds the input rw pin """

        pchg_B = self.pchg_inst.get_pin("B").ul()
        self.add_layout_pin(text="rw", 
                            layer=self.m1_pin_layer, 
                            offset=(pchg_B.x, self.min_off_y), 
                            width=self.m1_width)
        
        self.add_rect(layer="metal2", 
                      offset=(pchg_B.x, self.rw_off_y), 
                      width=self.ack_rw_in_off.uc().x- pchg_B.x,
                      height = contact.m1m2.width)

        self.add_via(self.m1_stack,(pchg_B.x, self.rw_off_y))
        
        self.add_path("metal1",[self.pchg_inst.get_pin("B").uc(), 
                               (self.pchg_inst.get_pin("B").uc().x, self.min_off_y)])
        
        # wen-gate rw-input connection
        self.add_path("poly",[self.wen_rw_in_off.uc(), (self.wen_rw_in_off.uc().x, 0)])
        self.add_contact(self.poly_stack,(self.wen_rw_in_off.ll().x, 0))
        self.add_path("metal1",[(self.wen_rw_in_off.ll().x+0.5*contact.poly.width, 0),
                                (self.wen_rw_in_off.ll().x+0.5*contact.poly.width, self.rw_off_y)])
        self.add_via(self.m1_stack,(self.wen_rw_in_off.ll().x, self.rw_off_y))
        
        # sen-gate rw-input connection
        self.add_path("poly",[self.sen_rw_in_off.uc(), (self.sen_rw_in_off.uc().x, 0)])
        self.add_contact(self.poly_stack, (self.sen_rw_in_off.ll().x,0))
        self.add_path("metal1",[(self.sen_rw_in_off.ll().x+0.5*contact.poly.width,0), 
                                (self.sen_rw_in_off.ll().x+0.5*contact.poly.width, self.rw_off_y)])
        self.add_via(self.m1_stack, (self.sen_rw_in_off.ll().x, self.rw_off_y))

        # ack-gate rw-input connection
        self.add_path("poly",[self.ack_rw_in_off.uc(),(self.ack_rw_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack,(self.ack_rw_in_off.ll().x, -self.m_pitch("m1")))
        self.add_path("metal1",[(self.ack_rw_in_off.ll().x+0.5*contact.poly.width,-self.m_pitch("m1")), 
                                (self.ack_rw_in_off.ll().x+0.5*contact.poly.width,self.rw_off_y)])
        self.add_via(self.m1_stack, (self.ack_rw_in_off.ll().x, self.rw_off_y))

    def add_input_w_pin(self):
        """ Adds the input w pin """

        # pchg-gate w-input connection
        pchg_C = self.pchg_inst.get_pin("C").ul()
        self.add_layout_pin(text="w", 
                            layer=self.m1_pin_layer, 
                            offset=(pchg_C.x, self.min_off_y), 
                            width=self.m1_width)
        self.add_rect(layer="metal2", 
                      offset=(pchg_C.x,self.w_off_y), 
                      width=self.ack_w_in_off.uc().x- pchg_C.x + self.poly_to_active,
                      height = contact.m1m2.width)
        
        self.add_via(self.m1_stack, (pchg_C.x, self.w_off_y))
        self.add_path("metal1",[self.pchg_inst.get_pin("C").uc(), 
                               (self.pchg_inst.get_pin("C").uc().x, self.min_off_y)])

        # wen-gate w-input connection
        self.add_path("poly",[self.wen_w_in_off.uc(), (self.wen_w_in_off.uc().x,0)])
        self.add_contact(self.poly_stack, (self.wen_w_in_off.ll().x, 0))
        self.add_path("metal1",[(self.wen_w_in_off.ll().x+0.5*contact.poly.width, 0), 
                                (self.wen_w_in_off.ll().x+0.5*contact.poly.width, self.w_off_y)])
        self.add_via(self.m1_stack, (self.wen_w_in_off.ll().x, self.w_off_y))

        # ack-gate w-input connection
        pos1= self.ack_w_in_off.uc()
        pos2=(pos1[0],self.ack_w_in_off.uc().y-0.5*contact.active.height-self.well_enclose_active)
        pos3=(self.ack_w_in_off.uc().x+self.poly_to_active,pos2[1])
        pos4=(pos3[0], 0)
        self.add_path("poly", [pos1, pos2, pos3, pos4])
        self.add_contact(self.poly_stack, (self.ack_w_in_off.ll().x+self.poly_to_active, 0))
        
        pos1=(self.ack_w_in_off.ll().x+self.poly_to_active+0.5*contact.poly.width,0)
        pos2=(pos1[0],self.w_off_y)
        self.add_path("metal1",[pos1, pos2])
        self.add_via(self.m1_stack, (self.ack_w_in_off.ll().x+self.poly_to_active, self.w_off_y))

    def add_input_r_pin(self):
        """ Adds the input r pin """
        
        # pchg-gate r-input connection
        pchg_A = self.pchg_inst.get_pin("A").ul()
        self.add_layout_pin(text="r", 
                            layer=self.m1_pin_layer, 
                            offset=(pchg_A.x,self.min_off_y), 
                            width=self.m1_width)
        self.add_rect(layer="metal2",
                      offset=(pchg_A.x,self.r_off_y), 
                      width=self.ack_inst.ll().x-2*self.m_pitch("m1")-pchg_A.x,
                      height = contact.m1m2.width)
        self.add_via(self.m1_stack, (pchg_A.x, self.r_off_y))
        self.add_path("metal1",[self.pchg_inst.get_pin("A").uc(),
                               (self.pchg_inst.get_pin("A").uc().x, self.min_off_y)])
        
        # sen-gate r-input connection
        self.add_path("poly",[self.sen_r_in_off.uc(), (self.sen_r_in_off.uc().x,0)])
        self.add_contact(self.poly_stack, (self.sen_r_in_off.ll().x, 0))

        self.add_path("metal1",[(self.sen_r_in_off.ll().x+0.5*contact.poly.width, 0), 
                                (self.sen_r_in_off.ll().x+0.5*contact.poly.width, self.r_off_y)])
        self.add_via(self.m1_stack, (self.sen_r_in_off.ll().x, self.r_off_y))

        # ack-gate r-input connection
        self.add_path("poly",[self.ack_r_in_off.uc(), 
                             (self.ack_r_in_off.uc().x, self.ack_inst.ul().y)])
        self.add_contact(self.poly_stack,(self.ack_r_in_off.ll().x, 
                                          self.ack_inst.ul().y-contact.poly.height))
        self.add_via(self.m1_stack, (self.ack_r_in_off.ll().x, 
                                     self.ack_inst.ul().y-contact.m1m2.height))

        pos1=(self.ack_r_in_off.uc().x, self.ack_inst.ul().y-0.5*self.m2_width)
        pos2=(self.ack_inst.ll().x-2*self.m_pitch("m1"), pos1[1])
        pos3=(pos2[0], self.r_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width,self.r_off_y), rotate=90)

    def add_input_reset_pin(self):
        """ Adds the input reset pin """

        self.add_layout_pin(text="reset", 
                            layer=self.m1_pin_layer, 
                            offset=(self.rst_in_off.ll().x, self.min_off_y), 
                            width=self.m1_width)
        # reset-gate reset input 
        self.add_path("metal1",[self.rst_in_off.uc(), (self.rst_in_off.uc().x,self.min_off_y)])
        
        # U-gate reset input 
        self.add_rect(layer="metal2", 
                      offset=(self.rst_in_off.uc().x, self.reset_off_y), 
                      width=self.u_inst.lr().x+self.m_pitch("m1")-self.rst_in_off.uc().x,
                      height = contact.m1m2.width)
        self.add_via(self.m1_stack, (self.rst_in_off.uc().x,self.reset_off_y))
        self.add_path("poly",[self.u_rst_in_off.uc(), 
                             (self.u_rst_in_off.uc().x,self.u_gate.width+contact.poly.height)])
        self.add_contact(self.poly_stack, 
                         (self.u_rst_in_off.lr().x, self.u_gate.width))
        self.add_via(self.m1_stack, (self.u_rst_in_off.lr().x, self.u_gate.width))
        
        pos1=(self.u_rst_in_off.lr().x, self.u_gate.width+0.5*self.m2_width)
        pos2=(self.u_inst.lr().x+self.m_pitch("m1"), pos1[1])
        pos3=(pos2[0], self.reset_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0], self.reset_off_y))

        # reset-gate reset_bar connection
        self.add_rect(layer="metal2", 
                      offset=(self.rst_out_off.uc().x,self.reset_bar_off_y), 
                      width=self.wack_inst.lr().x+self.m_pitch("m1")-self.rst_out_off.uc().x,
                      height = contact.m1m2.width)

        self.add_via(self.m1_stack, (self.rst_out_off.ll().x,self.reset_bar_off_y))
        self.add_path("metal1",[self.rst_out_off.uc(),
                               (self.rst_out_off.uc().x,self.reset_bar_off_y)])

        # ack-gate reset_bar connection
        self.add_path("poly",[self.ack_reset_bar_in_off.uc(), (self.ack_reset_bar_in_off.uc().x, 0)])
        self.add_contact(self.poly_stack, (self.ack_reset_bar_in_off.ll().x, 0))
        self.add_via(self.m1_stack, (self.ack_reset_bar_in_off.ll().x, 0))

        pos1=(self.ack_reset_bar_in_off.uc().x,0.5*self.m2_width)
        pos2=(self.ack_inst.ll().x-self.m_pitch("m1"), pos1[1])
        pos3=(pos2[0], self.reset_bar_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.reset_bar_off_y))

        # rack-gate reset_bar connection
        self.add_path("poly",[self.rack_rst_b_in_off.uc(), 
                             (self.rack_rst_b_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack,(self.rack_rst_b_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.rack_rst_b_in_off.ll().x, -self.m_pitch("m1")))
        
        pos1= (self.rack_rst_b_in_off.uc().x,-self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.rack_inst.ll().x-self.m_pitch("m1"),pos1[1])
        pos3= (pos2[0], self.reset_bar_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.reset_bar_off_y))

        # wack-gate reset_bar connection
        self.add_path("poly",[self.wack_rst_b_in_off.uc(),(self.wack_rst_b_in_off.uc().x, -self.m_pitch("m1"))])
        self.add_contact(self.poly_stack,(self.wack_rst_b_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.wack_rst_b_in_off.ll().x, -self.m_pitch("m1")))
        
        pos1= (self.wack_rst_b_in_off.uc().x, -self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.wack_inst.lr().x+self.m_pitch("m1"),pos1[1])
        pos3= (pos2[0], self.reset_bar_off_y)
        self.add_wire(self.m1_rev_stack,[pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.reset_bar_off_y))
    
    def add_input_wreq_pin(self):
        """ Adds the output wreq pin """

        self.add_layout_pin(text="wreq", 
                            layer=self.m1_pin_layer, 
                            offset=(self.wack_wreq_in_off.ll().x,self.min_off_y), 
                            width=self.m1_width,
                            height=self.m1_width)
        # wack-gate wreq connection
        self.add_path("poly",[self.wack_wreq_in_off.uc(), (self.wack_wreq_in_off.uc().x, 0)])
        self.add_contact(self.poly_stack,(self.wack_wreq_in_off.ll().x, 0))
        self.add_path("metal1",[(self.wack_wreq_in_off.ll().x+0.5*self.m1_width, contact.poly.height), 
                                (self.wack_wreq_in_off.ll().x+0.5*self.m1_width, self.min_off_y)])

    def add_input_rreq_pin(self):
        """ Adds the output rreq pin """

        # rack-gate rreq connection
        self.add_layout_pin(text="rreq", 
                            layer=self.m1_pin_layer, 
                            offset=(self.rack_rreq_in_off.ll().x, self.min_off_y), 
                            width=self.m1_width)
        
        self.add_path("poly",[self.rack_rreq_in_off.uc(), (self.rack_rreq_in_off.uc().x,0)])
        self.add_contact(self.poly_stack,(self.rack_rreq_in_off.uc().x-0.5*contact.poly.width, 0))
        self.add_path("metal1",[(self.rack_rreq_in_off.uc().x, 0), 
                                (self.rack_rreq_in_off.uc().x, self.min_off_y)])

        self.add_rect(layer="metal2",
                      offset= (self.rack_rreq_in_off.uc().x, self.rreq_off_y),
                      width= self.pin_width-self.rack_rreq_in_off.uc().x-self.m_pitch("m1"),
                      height=self.m2_width)
        self.add_via(self.m1_stack, (self.rack_rreq_in_off.uc().x,self.rreq_off_y))


    def add_input_dr_pins(self):
        """ Adds the input data_reay pins """

        if self.num_subanks > 1:
            for i in range(self.num_subanks):
                self.add_path("poly",[self.DR_off[i].uc(), 
                                     (self.DR_off[i].uc().x, -self.m_pitch("m1"))])
                self.add_contact(self.poly_stack,
                                 (self.DR_off[i].ll().x,-self.m_pitch("m1")))

                x_off=self.DR_off[i].ll().x+0.5*contact.poly.width
                self.add_path("metal1",[(x_off, -self.m_pitch("m1")),
                                        (x_off, self.data_ready_off_y- i*self.m_pitch("m2"))])
                self.add_via(self.m1_stack, (self.DR_off[i].uc().x+self.m1_width,
                                             self.data_ready_off_y- i*self.m_pitch("m2")), rotate=90)

                self.add_rect(layer="metal2", 
                              offset=(-self.m_pitch("m1"),
                                      self.data_ready_off_y- i*self.m_pitch("m2")),
                              width=self.width,
                              height = contact.m1m2.width)
                self.add_layout_pin(text="data_ready[{0}]".format(i), 
                                    layer=self.m2_pin_layer, 
                                    offset=(-self.m_pitch("m1"),
                                            self.data_ready_off_y - i*self.m_pitch("m2")),
                                    width=contact.m1m2.width,
                                    height = contact.m1m2.width)

        else:
                self.add_rect(layer="metal2", 
                              offset=(-self.m_pitch("m1"),self.dr_off_y), 
                              width=self.dec_en_inst.lr().x,
                              height = contact.m1m2.width)
                self.add_layout_pin(text="data_ready[0]", 
                                    layer=self.m2_pin_layer, 
                                    offset=(-self.m_pitch("m1"),self.dr_off_y), 
                                    width= contact.m1m2.width,
                                    height = contact.m1m2.width)
        
        # Add data_ready input
        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"),self.dr_off_y), 
                      width=self.pin_width, 
                      height = contact.m1m2.width)
        self.add_path("poly",[self.rack_dr_in_off.uc(), 
                             (self.rack_dr_in_off.uc().x, self.rack_inst.ul().y+self.m1_width)])
        self.add_contact(self.poly_stack,(self.rack_dr_in_off.ll().x, 
                                          self.rack_inst.ul().y+self.m1_width-contact.poly.height))
        self.add_via(self.m1_stack, (self.rack_dr_in_off.ll().x, 
                                      self.rack_inst.ul().y+self.m1_width-contact.m1m2.height))

        pos1= (self.rack_dr_in_off.uc().x, self.rack_inst.ul().y+self.m1_width-0.5*self.m2_width)
        pos2= (self.rack_inst.ll().x-2*self.m_pitch("m1"),pos1[1])
        pos3= (pos2[0],self.dr_off_y)
        self.add_wire(self.m1_rev_stack,[pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0], self.dr_off_y))
        
        # Add data_ready-gate output
        if self.num_subanks > 1:
            x_off = self.dr_inst.lr().x+2*self.m_pitch("m1")
            self.add_via(self.m1_stack, (x_off, self.dr_off_y))
            self.add_wire(self.m1_rev_stack,[self.dr_off.uc(),
                           (self.dr_off.uc().x, self.comp_off_y+0.5*self.m2_width ), 
                           (x_off, self.comp_off_y+0.5*self.m2_width),
                           (x_off, self.dr_off.uc().y),(x_off, self.dr_off_y)])

    def add_input_wc_pins(self):
        """ Adds the input write_complete pins """

        if self.num_subanks > 1:
            for i in range(self.num_subanks):
                self.add_path("poly",[self.WC_off[i].uc(),(self.WC_off[i].uc().x,-self.m_pitch("m1"))])
                self.add_contact(self.poly_stack, (self.WC_off[i].ll().x,-self.m_pitch("m1")))

                x_off = self.WC_off[i].ll().x+0.5*contact.poly.width
                self.add_path("metal1",[(x_off,-self.m_pitch("m1")), 
                                        (x_off,self.write_comp_off_y- i*self.m_pitch("m2"))])
                self.add_via(self.m1_stack, (self.WC_off[i].uc().x+self.m1_width,
                                             self.write_comp_off_y- i*self.m_pitch("m2")), rotate=90)

                self.add_rect(layer="metal2", 
                              offset=(-self.m_pitch("m1"),
                                       self.write_comp_off_y-i*self.m_pitch("m2")),
                              width=self.width,
                              height = contact.m1m2.width)
                self.add_layout_pin(text="write_complete[{0}]".format(i), 
                                    layer=self.m2_pin_layer, 
                                    offset=(-self.m_pitch("m1"),
                                            self.write_comp_off_y-i*self.m_pitch("m2")),
                                    width=contact.m1m2.width,
                                    height = contact.m1m2.width)
        else:
                self.add_rect(layer="metal2", 
                                    offset=(-self.m_pitch("m1"),self.wc_off_y), 
                                    width=self.dec_en_inst.lr().x,
                                    height = contact.m1m2.width)
                self.add_layout_pin(text="write_complete[0]", 
                                    layer=self.m2_pin_layer, 
                                    offset=(-self.m_pitch("m1"),self.wc_off_y), 
                                    width=contact.m1m2.width,
                                    height = contact.m1m2.width)

        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"),self.wc_off_y), 
                      width=self.pin_width, 
                      height = contact.m1m2.width)
        self.add_path("poly",[self.wack_wc_in_off.uc(),
                             (self.wack_wc_in_off.uc().x,self.wack_inst.ul().y)])
        self.add_contact(self.poly_stack, 
                         (self.wack_wc_in_off.ll().x,self.wack_inst.ul().y-contact.poly.height))
        self.add_via(self.m1_stack, (self.wack_wc_in_off.ll().x,
                                     self.wack_inst.ul().y-contact.m1m2.height))

        pos1= (self.wack_wc_in_off.uc().x, self.wack_inst.ul().y-0.5*self.m2_width)
        pos2= (self.wack_inst.lr().x+2*self.m_pitch("m1"), pos1[1])
        pos3= (pos2[0], self.wc_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.wc_off_y))
        
        # Add write_complete-gate output
        if self.num_subanks > 1:
            x_off =  self.wc_inst.ll().x-self.m_pitch("m1")
            self.add_via(self.m1_stack, (x_off, self.wc_off_y))
            self.add_wire(self.m1_rev_stack,
                          [self.wc_off.uc(), (self.wc_off.uc().x, self.comp_off_y+0.5*self.m2_width), 
                          (x_off, self.comp_off_y+0.5*self.m2_width),
                          (x_off, self.wc_off.uc().y), (x_off, self.wc_off_y)])

    def add_input_go_pin(self):
        """ Adds the input go pin """
        for i in range(self.num_subanks):
             self.add_rect(layer="metal2", 
                           offset=(-self.m_pitch("m1"),self.go_off_y-i*self.m_pitch("m1")), 
                           width=self.width,
                           height=contact.m1m2.width)
             self.add_layout_pin(text="go[{0}]".format(i), 
                                 layer=self.m2_pin_layer, 
                                 offset=(-self.m_pitch("m1"),self.go_off_y-i*self.m_pitch("m1")), 
                                 width=contact.m1m2.width,
                                 height=contact.m1m2.width)

             self.add_path("poly",[self.wc_go_off[i].uc(),(self.wc_go_off[i].uc().x, 0)])
             self.add_contact(self.poly_stack, (self.wc_go_off[i].ll().x,0))

             x_off = self.wc_go_off[i].ll().x+0.5*contact.poly.width
             self.add_path("metal1",[(x_off,0),(x_off, self.go_off_y-i*self.m_pitch("m1"))])
              
             self.add_via(self.m1_stack, (self.wc_go_off[i].uc().x,
                                          self.go_off_y-i*self.m_pitch("m1")), rotate=90)

             self.add_path("poly",[self.dr_go_off[i].uc(),(self.dr_go_off[i].uc().x, 0)])
             self.add_contact(self.poly_stack,(self.dr_go_off[i].ll().x,0))

             x_off = self.dr_go_off[i].ll().x+0.5*contact.poly.width
             self.add_path("metal1",[(x_off,0),(x_off, self.go_off_y-i*self.m_pitch("m1"))])
              
             self.add_via(self.m1_stack, (self.dr_go_off[i].uc().x,
                                          self.go_off_y-i*self.m_pitch("m1")), rotate=90)

    def add_output_ack_pin(self):
        """ Adds the output ack pin """
        
        #ack-gate output connection
        x_off=self.ack_inst.ll().x-4*self.m_pitch("m1")
        self.add_layout_pin(text="ack", 
                            layer=self.m1_pin_layer, 
                            offset=(x_off-0.5*self.m1_width,self.min_off_y), 
                            width=self.m1_width)
        self.add_wire(self.m1_rev_stack, [self.ack_out_off, 
                                         (x_off, self.ack_out_off.y), (x_off, self.min_off_y)])
        
        self.add_via(self.m1_stack, (x_off-0.5*self.m1_width, self.ack_off_y))
        self.add_rect(layer="metal2", 
                      offset=(self.u_ack_in_off.uc().x,self.ack_off_y), 
                      width=x_off-self.u_ack_in_off.uc().x,
                      height = contact.m1m2.width)

        #u-gate ack input connection
        self.add_path("poly",[self.u_ack_in_off.uc(),(self.u_ack_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack, (self.u_ack_in_off.ll().x,-self.m_pitch("m1")))
        x_off = self.u_ack_in_off.ll().x+0.5*contact.poly.width
        self.add_path("metal1", [(x_off,-self.m_pitch("m1")), (x_off, self.ack_off_y)])
        self.add_via(self.m1_stack, (self.u_ack_in_off.ll().x, self.ack_off_y))
        

    def add_output_wen_pin(self):
        """ Adds the output wen pin """
        
        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"),self.wen_off_y), 
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="wen", 
                            layer=self.m2_pin_layer, 
                            offset=(-self.m_pitch("m1"),self.wen_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        # wen-gate output connection
        self.add_via(self.m1_stack, (self.wen_out_off.ur().x,self.wen_off_y), rotate=90)
        self.add_path("metal1",[self.wen_out_off.uc(), (self.wen_out_off.uc().x,self.wen_off_y)])

    def add_output_wack_pin(self):
        """ Adds the output wack pin """
        # wack-gate output connection
        x_off = self.wack_inst.lr().x+3*self.m_pitch("m1")
        self.add_layout_pin(text="wack", 
                            layer=self.m1_pin_layer, 
                            offset=(x_off-0.5*self.m1_width,self.min_off_y), 
                            width=self.m1_width,
                            height=self.m1_width)

        self.add_wire(self.m1_rev_stack,
                      [self.wack_out_off, (x_off,self.wack_out_off.y), (x_off,self.min_off_y)])
        self.add_via(self.m1_stack, (x_off,self.wack_off_y))
        
        # ack-gate wack connection
        self.add_rect(layer="metal2", 
                      offset=(self.ack_wack_in_off1.uc().x, self.wack_off_y), 
                      width=x_off-self.ack_wack_in_off1.uc().x,
                      height = contact.m1m2.width)
        
        self.add_path("poly",[self.ack_wack_in_off1.uc(), (self.ack_wack_in_off1.uc().x,0)])
        self.add_contact(self.poly_stack, (self.ack_wack_in_off1.ll().x,0))
        self.add_path("metal1",[(self.ack_wack_in_off1.ll().x+0.5*contact.poly.width,0),
                                (self.ack_wack_in_off1.ll().x+0.5*contact.poly.width,self.wack_off_y)])
        self.add_via(self.m1_stack, (self.ack_wack_in_off1.ll().x,self.wack_off_y))
        
        self.add_path("poly",[self.ack_wack_in_off2.uc(), 
                             (self.ack_wack_in_off2.uc().x, self.ack_inst.ul().y)])
        self.add_contact(self.poly_stack, 
                         (self.ack_wack_in_off2.ll().x, self.ack_inst.ul().y-contact.poly.height))
        self.add_via(self.m1_stack, (self.ack_wack_in_off2.ll().x, 
                                     self.ack_inst.ul().y-contact.m1m2.height))
        pos1= (self.ack_wack_in_off2.ll().x, self.ack_inst.ul().y-0.5*self.m2_width)
        pos2= (self.ack_inst.lr().x+self.m_pitch("m1"), pos1[1])
        pos3= (pos2[0], self.wack_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0], self.wack_off_y))

    def add_output_pchg_pin(self):
        """ Adds the output pchg pin """

        self.add_rect(layer="metal2",
                      offset=(-self.m_pitch("m1"),self.pchg_off_y), 
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="pchg", 
                            layer=self.m2_pin_layer,
                            offset=(-self.m_pitch("m1"),self.pchg_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
        # Add u-gate pchg input 
        pchg_nor3_off=vector(self.pchg_inst.get_pin("Z").lc().x, self.pchg_inst.get_pin("Z").uc().y)
        self.add_path("poly",[self.u_pre_pchg_in_off.uc(), (self.u_pre_pchg_in_off.uc().x,0)])
        self.add_contact(self.poly_stack, (self.u_pre_pchg_in_off.ll().x, 0))
        self.add_via(self.m1_stack, (self.u_pre_pchg_in_off.ll().x, 0))
        
        pos1= (self.u_pre_pchg_in_off.ll().x, 0.5*self.m2_width)
        pos2= (self.u_inst.ll().x-self.m_pitch("m1"), pos1[1])
        pos3= (pos2[0], pchg_nor3_off.y)
        pos4= (pchg_nor3_off.x+self.m1_width, pos3[1])
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3, pos4])
        self.add_via(self.m1_stack,(pos4[0]+contact.m1m2.height,pos3[1]-contact.m1m2.width),rotate=90)
        
        #Route the pchg rail
        self.add_via(self.m1_stack, (self.pchg_off.lr().x, self.pchg_off_y), rotate=90)
        self.add_path("metal1",[self.pchg_off.uc(), (self.pchg_off.uc().x,self.pchg_off_y)])

        # ack-gate pchg-input connection
        self.add_path("poly",[self.ack_pchg_in_off.uc(),
                             (self.ack_pchg_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack, (self.ack_pchg_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.ack_pchg_in_off.ll().x, -self.m_pitch("m1")))

        
        pos1= (self.ack_pchg_in_off.uc().x, -self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.ack_inst.ll().x-3*self.m_pitch("m1"), pos1[1])
        pos3= (pos2[0], self.pchg_off_y)
        self.add_wire(self.m1_rev_stack,[pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]+0.5*self.m1_width, self.pchg_off_y), rotate=90)
        
        # decoder_enable_gate pchg-input connection
        self.add_via(self.m1_stack, (self.dec_en_in_off.ur().x, self.pchg_off_y), rotate=90)
        self.add_path("metal1",[self.dec_en_in_off.uc(),(self.dec_en_in_off.uc().x,self.pchg_off_y)])

        if self.num_subanks > 1:
            # write_complete-gate pchg-input connection
            self.add_path("poly",[self.WC_pchg_off.uc(),
                                 (self.WC_pchg_off.uc().x,self.wc_inst.ul().y-contact.poly.height)])
            self.add_contact(self.poly_stack, 
                             (self.WC_pchg_off.ur().x,self.wc_inst.ul().y-2*contact.poly.height))
            self.add_via(self.m1_stack, (self.WC_pchg_off.ur().x, 
                                         self.wc_inst.ul().y-2*contact.poly.height))

            self.add_wire(self.m1_rev_stack, [(self.WC_pchg_off.ur().x,
                          self.wc_inst.ul().y-contact.poly.height-0.5*self.m2_width), 
                          (self.wc_inst.ll().x-2*self.m_pitch("m1"),
                          self.wc_inst.ul().y-contact.poly.height-0.5*self.m2_width),
                          (self.wc_inst.ll().x-2*self.m_pitch("m1"),self.pchg_off_y)])
            self.add_via(self.m1_stack, (self.wc_inst.ll().x-2*self.m_pitch("m1")+0.5*self.m1_width,
                                          self.pchg_off_y), rotate=90)
            
            # Data_ready-gate pchg-input connection
            self.add_path("poly",[self.DR_pchg_off.uc(),(self.DR_pchg_off.uc().x,
                                  self.dr_inst.ul().y-contact.poly.height)])
            off= (self.DR_pchg_off.lr().x,self.dr_inst.ul().y-2*contact.poly.height)
            self.add_contact(self.poly_stack, off)
            self.add_via(self.m1_stack, off)

            pos1= (self.DR_pchg_off.lr().x, self.dr_inst.ul().y-contact.poly.height-0.5*self.m2_width)
            pos2= (self.dr_inst.lr().x+self.m_pitch("m1"), pos1[1])
            pos3= (pos2[0], self.pchg_off_y)
            self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
            self.add_via(self.m1_stack, (pos2[0]+0.5*self.m1_width,self.pchg_off_y), rotate=90)

    def add_output_rack_pin(self):
        """ Adds the input rack pin """
        
        # rack-gate output connection
        x_off = self.rack_inst.lr().x+2*self.m_pitch("m1")-0.5*self.m1_width
        self.add_layout_pin(text="rack", 
                            layer=self.m1_pin_layer, 
                            offset=(x_off, self.min_off_y), 
                            width=self.m1_width)
        self.add_via(self.m1_stack, (x_off,self.rack_off_y))
        self.add_wire(self.m1_rev_stack,
                      [self.rack_out_off,
                      (self.rack_inst.lr().x+2*self.m_pitch("m1"),self.rack_out_off.y), 
                      (self.rack_inst.lr().x+2*self.m_pitch("m1"),self.min_off_y)])

        # wen-gate rack-input connection
        self.add_rect(layer="metal2",
                      offset=(self.wen_rack_in_off.uc().x+self.poly_to_active, self.rack_off_y), 
                      width=x_off-self.wen_rack_in_off.uc().x-self.poly_to_active,
                      height = contact.m1m2.width)
        
        pos1= self.wen_rack_in_off.uc()
        pos2=(pos1[0], self.wen_rack_in_off.uc().y-0.5*contact.active.height-self.well_enclose_active)
        pos3= (self.wen_rack_in_off.uc().x+self.poly_to_active,pos2[1])
        pos4= (pos3[0],0)
        self.add_path("poly",[pos1, pos2, pos3, pos4])
        
        self.add_contact(self.poly_stack, (self.wen_rack_in_off.ll().x+self.poly_to_active,0))
        
        x_off =  self.wen_rack_in_off.ll().x + self.poly_to_active + 0.5*contact.poly.width
        self.add_path("metal1", [(x_off, 0), (x_off, self.rack_off_y)])
        
        self.add_via(self.m1_stack,(x_off-0.5*contact.poly.width, self.rack_off_y))

        # ack-gate rack-input connection
        self.add_path("poly",[self.ack_rack_in_off.uc(), (self.ack_rack_in_off.uc().x, 0)])
        self.add_contact(self.poly_stack,(self.ack_rack_in_off.ll().x, 0))
        self.add_path("metal1",[(self.ack_rack_in_off.ll().x+0.5*contact.poly.width, 0), 
                      (self.ack_rack_in_off.ll().x+0.5*contact.poly.width,self.rack_off_y)])
        self.add_via(self.m1_stack, (self.ack_rack_in_off.ll().x,self.rack_off_y))


    def add_output_dec_en_pin(self):
        """ Adds the output decoder_enable pin """

        self.add_rect(layer="metal2", 
                      offset=(self.dec_en_out_off.ul().x, self.dec_en_off_y), 
                      width=self.width-self.dec_en_out_off.uc().x-self.m_pitch("m1"),
                      height=contact.m1m2.width)
        self.add_layout_pin(text="decoder_enable", 
                            layer=self.m2_pin_layer, 
                            offset=(self.dec_en_out_off.ul().x, self.dec_en_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        self.add_path("metal1",[self.dec_en_out_off.uc(),
                               (self.dec_en_out_off.uc().x,self.dec_en_off_y)])
        self.add_via(self.m1_stack, (self.dec_en_out_off.ul().x,self.dec_en_off_y))
    
    def add_U_routing(self):
        """ Routes the u signal """

        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"), self.U_off_y), 
                      width=self.pin_width, 
                      height = contact.m1m2.width)
        self.add_via(self.m1_stack, (self.u_out_off.uc().x-0.5*contact.m1m2.width,self.U_off_y))
        self.add_path("metal1",[self.u_out_off.uc(), (self.u_out_off.uc().x,self.U_off_y)])
        
        # wen-gate u-input connection
        self.add_path("poly",[self.wen_u_in_off.uc(),(self.wen_u_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack, (self.wen_u_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.wen_u_in_off.ll().x, -self.m_pitch("m1")))
        
        pos1= (self.wen_u_in_off.uc().x, -self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.wen_inst.ll().x-self.m_pitch("m1"),pos1[1])
        pos3= (pos2[0], self.U_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m2_width, self.U_off_y))
        
        # sen-gate u-input connection
        pos1 = self.sen_u_in_off.uc()
        pos2= (pos1[0], self.sen_u_in_off.uc().y-0.5*contact.active.height-self.well_enclose_active)
        pos3= (self.sen_u_in_off.uc().x-self.poly_to_active, pos2[1])
        pos4= (pos3[0], -self.m_pitch("m1"))
        self.add_path("poly",[pos1, pos2, pos3, pos4])
        
        x_off = self.sen_u_in_off.ll().x-self.poly_to_active
        self.add_contact(self.poly_stack, (x_off, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (x_off, -self.m_pitch("m1")))
        
        pos1= (self.sen_u_in_off.ll().x-self.poly_to_active, -self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.sen_inst.lr().x+self.m_pitch("m1"), pos1[1])
        pos3= (pos2[0], self.U_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width,self.U_off_y))
        
        # rack-gate u-input connection
        self.add_path("poly",[self.rack_u_in_off.uc(),
                             (self.rack_u_in_off.uc().x, -self.m_pitch("m1"))])
        self.add_contact(self.poly_stack, (self.rack_u_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.rack_u_in_off.ll().x, -self.m_pitch("m1")))

        pos1=(self.rack_u_in_off.uc().x, -self.m_pitch("m1")+0.5*self.m2_width)
        pos2=(self.rack_inst.lr().x+self.m_pitch("m1"), pos1[1])
        pos3=(pos2[0], self.U_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.U_off_y))
        
        # wack-gate u-input connection
        self.add_path("poly",[self.wack_u_in_off.uc(),
                             (self.wack_u_in_off.uc().x,-self.m_pitch("m1"))])
        self.add_contact(self.poly_stack,(self.wack_u_in_off.ll().x, -self.m_pitch("m1")))
        self.add_via(self.m1_stack, (self.wack_u_in_off.ll().x, -self.m_pitch("m1")))

        pos1= (self.wack_u_in_off.uc().x,-self.m_pitch("m1")+0.5*self.m2_width)
        pos2= (self.wack_inst.ll().x-self.m_pitch("m1"),pos1[1])
        pos3= (pos2[0], self.U_off_y)
        self.add_wire(self.m1_rev_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, (pos2[0]-0.5*self.m1_width, self.U_off_y))
 
    def add_output_sen_pin(self):
        """ Adds the output sen pin """

        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"),self.sen_off_y), 
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="sen", 
                            layer=self.m2_pin_layer, 
                            offset=(-self.m_pitch("m1"),self.sen_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        x_off = self.pin_width+2*self.m_pitch("m1")
        self.add_wire(self.m1_rev_stack,
                      [(self.rblk_out_off.x-self.m1_width-contact.m1m2.width, self.rblk_out_off.y), 
                      (x_off, self.rblk_out_off.y), (x_off, self.sen_off_y)])
        self.add_via(self.m1_stack, (x_off-0.5*self.m1_width, self.sen_off_y), rotate=90)

    def add_rbl_routing(self):
        """ Routes the rbl input, output and power signals """
        
        self.add_path("metal1",[self.sen_out_off.uc(), (self.sen_out_off.uc().x, self.rblk_in_off.y), 
                                self.rblk_in_off])

    def route_vdd_gnd(self):
        """ Adds the vdd and gnd pins """

        self.add_rect(layer="metal2",
                      offset=(-self.m_pitch("m1"), self.vdd_off_y), 
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="vdd",
                            layer=self.m2_pin_layer,
                            offset=(-self.m_pitch("m1"), self.vdd_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        self.add_rect(layer="metal2", 
                      offset=(-self.m_pitch("m1"), self.gnd_off_y), 
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="gnd",
                            layer=self.m2_pin_layer, 
                            offset=(-self.m_pitch("m1"), self.gnd_off_y), 
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        #vdd connection of rbl
        vdd_0 = self.rbl.get_pins("vdd")[0]
        vdd_1 = self.rbl.get_pins("vdd")[1]
        self.add_wire(self.m1_rev_stack,[vdd_0.lc(),
                     (vdd_0.lc().x+2*self.m_pitch("m1"), vdd_0.lc().y),
                     (vdd_0.lc().x+2*self.m_pitch("m1"), vdd_1.lc().y),
                     vdd_1.lc(), (self.pin_width, vdd_1.lc().y),(self.pin_width, self.vdd_off_y)])
        self.add_via(self.m1_stack, (vdd_0.lc().x+contact.m1m2.width, vdd_0.ll().y))
        self.add_via(self.m1_stack, (vdd_1.lc().x+contact.m1m2.width, vdd_1.ll().y))
        self.add_via(self.m1_stack, (self.pin_width-0.5*self.m1_width, self.vdd_off_y))

        #gnd connection of rbl
        gnd_0= self.rbl.get_pin("gnd")
        x_off= self.pin_width+self.m_pitch("m1")
        self.add_wire(self.m1_rev_stack,[gnd_0.lc(),(x_off,gnd_0.lc().y),(x_off,self.gnd_off_y)])
        self.add_via(self.m1_stack,(x_off-0.5*self.m1_width,self.gnd_off_y))
        self.add_via(self.m1_stack,(gnd_0.lc().x+contact.m1m2.width, gnd_0.ll().y))
                
        gates_list = [self.rst_inv_inst, self.pchg_inst, self.u_inst, self.wen_inst, self.sen_inst, 
                      self.ack_inst, self.rack_inv_inst, self.wack_inv_inst, self.dec_en_inst]
        if self.num_subanks > 1:
            gates_list.extend([self.wc_inst, self.dr_inst])
        if self.two_level_bank:
            gates_list.extend([self.rreq_mrg_inv2_inst])
        for inst in gates_list:
            for gnd_pin in inst.get_pins("gnd"):
                self.add_rect(layer="metal1", 
                              offset=gnd_pin.ll(), 
                              width=contact.m1m2.width, 
                              height=self.gnd_off_y-gnd_pin.ll().y)
                self.add_via(self.m1_stack, (gnd_pin.uc().x-0.5*contact.m1m2.width, self.gnd_off_y))

            for vdd_pin in inst.get_pins("vdd"):
                self.add_rect(layer="metal1", 
                              offset=vdd_pin.ll(), 
                              width=contact.m1m2.width, 
                              height=self.vdd_off_y-vdd_pin.ll().y)
                self.add_via(self.m1_stack, (vdd_pin.uc().x-0.5*contact.m1m2.width, self.vdd_off_y))
        self.add_rect(layer="nimplant",
                      offset=(-0.5*contact.m1m2.width,-self.m_pitch("m1")-self.implant_enclose_poly),
                      width=self.pin_width,
                      height=self.m_pitch("m1")+self.implant_enclose_poly)
