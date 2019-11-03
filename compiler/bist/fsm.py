
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
from tech import info, layer, drc
from pinv import pinv
from nand2 import nand2
from nand3 import nand3
from nor2 import nor2
from nor3 import nor3
from ptx import ptx
from flipflop import flipflop
from delay_chain import delay_chain
from utils import ceil

class fsm(design.design):
    """ Dynamically generated finite state machin for March C test"""

    def __init__(self, name="finite-state-machine"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.add_modules()
        self.connect_modules()
        self.add_layout_pins()
        self.width= self.max_xoff - self.min_xoff
        self.height=self.height1+10*self.m_pitch("m1")+self.dc_inst.height

    def add_pins(self):
        """ Adds all pins of data pattern module """
        
        self.add_pin_list(["lfsr", "comp", "reset", "fin", "err", "up_down", "data_enable",     
                           "r", "w", "clk", "clk3", "clk2", "vdd", "gnd"])

    def create_modules(self):
        """ construct all the required modules """
        
        self.inv = pinv()
        self.add_mod(self.inv)

        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)

        self.nand2 = nand2()
        self.add_mod(self.nand2)
        
        self.nand3 = nand3()
        self.add_mod(self.nand3)
        
        self.nor2 = nor2()
        self.add_mod(self.nor2)
        
        self.nor3 = nor3()
        self.add_mod(self.nor3)
        
        self.ff = flipflop()
        self.add_mod(self.ff)

        self.nmos = ptx(tx_type="nmos", min_area = True, dummy_poly=True)
        self.add_mod(self.nmos)
        
        self.fanout_list=[]
        for i in range(6):
            self.fanout_list.append(1)

        self.dc=delay_chain(fanout_list=self.fanout_list, name="delay_chain3")
        self.add_mod(self.dc)
        
        #These are gaps between neighbor cell to avoid well/implant DRC violation
        self.ygap = max(self.well_space, self.implant_space, self.m_pitch("m1"))+contact.m1m2.width
        self.yshift = vector(0,self.ygap+self.m_pitch("m1"))
        
        self.xgap = 2*self.m_pitch("m1")
        self.xshift = vector(3*self.m_pitch("m1"),0)
        
        #offset for vdd and gnd pin
        self.vdd_xoff = -6*self.m_pitch("m1")
        self.gnd_xoff = -7*self.m_pitch("m1")
        
        #width of vertical m2 bus for connections
        self.vbus_width = 15*self.m_pitch("m1")
        
        #width of horizontal m1 bus for connections
        self.hbus_width = 14*self.m_pitch("m1")

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_flipflops()
        self.add_reset_gates()
        self.add_delay_chain()
        self.add_stage0_gates()
        self.add_stage1_gates()
        self.add_stage2_gates()
        self.add_err_gates()
        self.add_finish_gates()
        self.add_up_down_gates()
        self.add_data_gates()
        self.add_read_write_gates()

    def connect_modules(self):
        """ Route modules """
        
        self.add_connection_rails()
        self.connect_reset_gates_to_rails()
        self.connect_init_mos()
        self.connect_input_inv_to_rails()
        self.reset_inverter_connections()
        self.connect_reset_gates_to_ff()
        self.connect_stage0_gates_to_rails()
        self.connect_stage1_gates_to_rails()
        self.connect_stage2_gates_to_rails()
        self.connect_err_gates_to_rails()
        self.connect_finish_updown_data_gates_to_rails()
        self.connect_ff_gates_inputs()
        self.connect_read_write_gates_to_rails()
    
    def add_flipflops(self):
        """ Place 3 FFs for 8 states in FSM """
        
        self.ff_inst={}
        self.init_mos={}
        for i in range(3):
            if i%2:
                mirror="MX"
                yoff=(i+1)*self.ff.height
                nyoff = yoff - (i%2)*self.nmos.width 
                if info["tx_dummy_poly"]:
                    nyoff = nyoff +0.5*self.poly_width 

            else:
                mirror="R0"
                yoff=i*self.ff.height
                nyoff = i*self.ff.height
                if info["tx_dummy_poly"]:
                    nyoff = nyoff - 0.5*self.poly_width

            self.ff_inst[i]= self.add_inst(name="ff{0}".format(i), mod=self.ff,
                                           offset=(0,yoff), mirror=mirror)
            self.connect_inst(["d{0}".format(i),"sx{0}".format(i),"sx_b{0}".format(i),"clk3","vdd","gnd"])
            
            self.init_mos[i]=self.add_inst(name="init_mos{}".format(i), mod=self.nmos,
                                           offset=(self.ff.width+self.nmos.height, nyoff),
                                           rotate=90)
            self.connect_inst(["sx{0}".format(i),"reset", "gnd", "gnd"])
    
    def connect_init_mos(self):
        """ Connect terminals of initialize nmos"""
        for i in range(3):
            if i%2:
                gnd_pin = "D"
                ff_pin= "S"
            else:
                gnd_pin = "S"
                ff_pin= "D"

            #Connect Source of initialize mos to gnd
            pos1=self.init_mos[i].get_pin(gnd_pin).uc()
            pos2=(pos1.x, self.ff_inst[i].get_pin("gnd").by())
            self.add_path("metal1", [pos1, pos2], width=contact.active.height)
            
            #Connect Drain of initialize mos to output of FF
            pos1=self.init_mos[i].get_pin(ff_pin).uc()
            pos2=(pos1.x, self.ff_inst[i].get_pin("out").lc().y)
            self.add_path("metal1", [pos1, pos2], width=contact.active.height)
            
            #Add poly contacts and via1 at gate position of initialize mos
            pos1=self.init_mos[i].get_pin("G").lc()
            pos2=vector(self.init_mos[i].rx()+1.5*contact.poly.width, pos1.y)
            pos3=vector(pos2.x+contact.poly.second_layer_width, pos1.y)
            self.add_path("poly", [pos1, pos2])
            self.add_via_center(self.poly_stack, pos2)
            self.add_via_center(self.m1_stack, pos3)
            
            #Add metal1 to satisfy min_area 
            width=3*contact.m1m2.width
            height=max(ceil(self.m1_minarea/width), contact.m1m2.height, contact.poly.height)
            self.add_rect_center(layer="metal1", 
                                 offset=pos2+vector(0.5*contact.poly.width,0), 
                                 width=width, 
                                 height=height)
                                                       

        #Connect Gate of initialize mos to reset
        pos1=vector(pos3.x, self.init_mos[0].get_pin("G").lc().y)
        pos2=vector(pos1.x, self.reset_inv.uy()+self.m_pitch("m1"))
        pos3=vector(self.reset_inv.lx()-2*self.m_pitch("m1"), pos2.y)
        pos5=self.reset_inv.get_pin("A").lc()
        pos4=vector(pos3.x, pos5.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
        
        #Add Well and implant layer plus one well contact for all initialize mos
        width=self.nmos.height+4*self.m_pitch("m1")
        height=self.ff_inst[2].uy() - self.init_mos[0].by()
        if info["has_pwell"]:
            self.add_rect(layer="pwell", offset=self.init_mos[0].ll(), 
                          width=width, height=height)
        if info["has_nimplant"]:
            self.add_rect(layer="nimplant", offset=self.init_mos[0].ll(), 
                          width=self.nmos.height+self.m_pitch("m1"), height=height)
        
        well_contact_off=vector(self.init_mos[1].rx()+2*self.m_pitch("m1"), 
                                self.ff_inst[1].get_pin("gnd").lc().y)
        self.add_via_center(("active", "contact", "metal1"), well_contact_off)
        
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant", offset=(well_contact_off.x-self.m_pitch("m1"), 0), 
                          width=3*self.m_pitch("m1"), height=height)
    
        #Add active to satisfy min_area
        self.add_rect_center(layer="active", 
                             offset=well_contact_off, 
                             width=contact.active.width, 
                             height=ceil(self.active_minarea/contact.active.width))

        #Add extra layer of well-contact
        extra_off = well_contact_off-vector(self.m_pitch("m1"), self.m_pitch("m1")) 
        extra_width=2*self.m_pitch("m1")
        extra_height = max(ceil(self.extra_minarea/extra_width), 2*self.m_pitch("m1"))
        self.add_rect(layer="extra_layer", 
                      layer_dataType = layer["extra_layer_dataType"], 
                      offset=extra_off, 
                      width=extra_width, 
                      height=extra_height)
        
        #Add VT to satisfy min_area
        self.add_rect(layer="vt",
                      offset=self.init_mos[0].ll(),
                      layer_dataType = layer["vt_dataType"],
                      width=self.nmos.height+4*self.m_pitch("m1"),
                      height=self.nmos.width)

        if info["tx_dummy_poly"]:
            for i in range(3):
                width=ceil(drc["minarea_poly_merge"]/self.poly_width)
                pos1=vector(self.nmos.dummy_poly_offset1.y-width, self.nmos.dummy_poly_offset1.x)
                pos2=vector(self.nmos.dummy_poly_offset2.y-width, self.nmos.dummy_poly_offset2.x)
                self.add_rect(layer="poly", offset=self.init_mos[i].lr()+pos1, width=width, height=self.poly_width)
                self.add_rect(layer="poly", offset=self.init_mos[i].lr()+pos2, width=width, height=self.poly_width)
    
    
    def add_reset_gates(self):
        """ Add 3 AND gates on right side of FFs to gate the output of FFs with reset_bar
            Add 2 AND gates above FFs to gate the 'comp', 'lfsr' inputs with reset_bar """        
        
        self.reset_inv=self.add_inst(name="reset_inv", mod=self.inv,
                                     offset=(0,3*self.ff.height+self.ygap))
        self.connect_inst(["reset", "reset_bar", "vdd", "gnd"])
        
        self.rst_nand={}
        self.rst_inv={}
        for i in range(3):
            if i%2:
                mirror="MX"
                y_off=(i+1)*self.ff.height
            else:
                mirror="R0"
                y_off=i*self.ff.height

            self.rst_nand[i]=self.add_inst(name="rst_nand{0}".format(i), mod=self.nand2,
                                           offset=(self.init_mos[i].rx()+4*self.m_pitch("m1"),y_off),
                                           mirror = mirror)
            self.connect_inst(["reset_bar", "sx{0}".format(i), "s_b{0}".format(i), "vdd", "gnd"])
            
            self.rst_inv[i]=self.add_inst(name="rst_inv{0}".format(i),
                                           mod=self.inv5,
                                           offset=(self.rst_nand[i].rx(), y_off),
                                           mirror = mirror)
            self.connect_inst(["s_b{0}".format(i), "s{0}".format(i), "vdd", "gnd"])

        pins = ["comp", "lfsr", "comp_err_b", "lfsr_done_b", "comp_err", "lfsr_done"]
        for i in range(2):
            if i%2:
                mirror="MX"
                y_off=self.reset_inv.uy()+2*self.ygap+2*self.inv.height
            else:
                mirror="R0"
                y_off=self.reset_inv.uy()+2*self.ygap

            self.rst_nand[i+3]=self.add_inst(name="rst_nand{0}".format(i+3), mod=self.nand2,
                                             offset=(self.rst_nand[i].lx(),y_off),
                                             mirror = mirror)
            self.connect_inst(["reset_bar", pins[i], pins[i+2], "vdd", "gnd"])
            
            self.rst_inv[i+3]=self.add_inst(name="rst_inv{0}".format(i+3), mod=self.inv,
                                            offset=(self.rst_nand[i+3].rx(), y_off),
                                            mirror = mirror)
            self.connect_inst([pins[i+2], pins[i+4], "vdd", "gnd"])
    
 
    def add_delay_chain(self):
        """ Add delay chain for clk input to match the delay with clk3 & clk2 """        
        
        self.dc_inst=self.add_inst(name="delay_chain", mod=self.dc,
                                   offset=(0,-4*self.m_pitch("m1")-self.dc.height))
        self.connect_inst(["clk", "clk_d", "vdd", "gnd"])

    def add_stage0_gates(self):
        """ Add gates for combinational logic of S0 FF"""
        
        self.gate00=self.add_inst(name="gate00", mod=self.nor2,
                                  offset=self.rst_inv[2].ur()+vector(self.vbus_width,0))
        self.connect_inst(["s1", "comp_err_b", "L0", "vdd", "gnd"])

        self.gate01=self.add_inst(name="gate01", mod=self.nor3,
                                  offset=self.gate00.ul()+self.yshift)
        self.connect_inst(["L0", "s_b0", "s_b2", "L1", "vdd","gnd"])
        
        self.gate01_inv=self.add_inst(name="gate01_inv", mod=self.inv,
                                      offset=self.gate01.lr())
        self.connect_inst(["L1", "L2", "vdd", "gnd"])
        
        self.gate02=self.add_inst(name="gate02", mod=self.nor2,
                                  offset=(self.gate01.ul()+vector(0,self.ygap)))
        self.connect_inst(["s_b2", "comp_err_b", "L7", "vdd", "gnd"])

        self.gate03=self.add_inst(name="gate03", mod=self.nand3,
                                  offset=(self.gate02.ul()+vector(0,self.ygap)))
        self.connect_inst(["s_b0", "s_b1", "lfsr_done", "L8", "vdd", "gnd"])

        self.gate04=self.add_inst(name="gate04", mod=self.nor2,
                                  offset=self.gate03.lr()+self.xshift)
        self.connect_inst(["L7", "L8", "L9", "vdd", "gnd"])
        
        self.gate04_inv=self.add_inst(name="gate04_inv", mod=self.inv,
                                      offset=self.gate04.lr())
        self.connect_inst(["L9", "L10", "vdd", "gnd"])
        
        self.gate05=self.add_inst(name="gate05", mod=self.nand2,
                                  offset=(self.gate03.ul()+vector(0,self.ygap)))
        self.connect_inst(["s0","lfsr_done_b", "L3", "vdd", "gnd"])
        
        self.gate06=self.add_inst(name="gate06", mod=self.nand3,
                                  offset=self.gate05.ul()+self.yshift)
        self.connect_inst(["s_b0", "s1", "lfsr_done", "L4", "vdd", "gnd"])
        
        self.gate07=self.add_inst(name="gate07", mod=self.nand2,
                                  offset=self.gate06.lr()+self.xshift)
        self.connect_inst(["L3", "L4", "L5","vdd", "gnd"])

        self.gate08=self.add_inst(name="gate08", mod=self.nand3,
                                  offset=self.gate06.ul()+self.yshift)
        self.connect_inst(["L5", "s_b2", "comp_err_b", "L6", "vdd", "gnd"])

        self.gate09=self.add_inst(name="gate09", mod=self.nand3,
                                  offset=self.gate04_inv.lr()+self.xshift)
        self.connect_inst(["L2", "L10", "L6", "d0", "vdd", "gnd"])

    def add_stage1_gates(self):
        """ Add gates for combinational logic of S1 FF"""
        
        self.gate10=self.add_inst(name="gate10", mod=self.nor2,
                                  offset=(self.gate09.rx()+self.vbus_width, self.hbus_width))
        self.connect_inst(["s2","s_b0","o0","vdd","gnd"])

        self.gate11=self.add_inst(name="gate11", mod=self.nor2,
                                  offset=self.gate10.ul()+self.yshift)
        self.connect_inst(["o0","s_b1","o1","vdd","gnd"])

        self.gate12=self.add_inst(name="gate12", mod=self.nor2,
                                  offset=self.gate11.ul()+vector(0,self.ygap))
        self.connect_inst(["s0","s1","o2","vdd","gnd"])

        self.gate13=self.add_inst(name="gate13", mod=self.nor2,
                                  offset=self.gate12.lr()+self.xshift)
        self.connect_inst(["o2","s2","o3","vdd","gnd"])

        self.gate14=self.add_inst(name="gate14", mod=self.nor2,
                                  offset=self.gate12.ul()+vector(0,self.ygap+2*self.m_pitch("m1")))
        self.connect_inst(["o3","s2","o4","vdd","gnd"])
        
        self.gate15=self.add_inst(name="gate15", mod=self.nor2,
                                  offset=self.gate14.ul()+self.yshift)
        self.connect_inst(["o4","comp_err_b","o5","vdd","gnd"])

        self.gate16=self.add_inst(name="gate16", mod=self.nor2,
                                  offset=self.gate15.lr()+self.xshift)
        self.connect_inst(["o1","o5","o11","vdd","gnd"])

        self.gate17=self.add_inst(name="gate17", mod=self.nand3,
                                 offset=self.gate15.ul()+vector(0,self.ygap))
        self.connect_inst(["s0", "s_b1", "lfsr_done", "o6","vdd","gnd"])
        
        self.gate17_inv=self.add_inst(name="gate17_inv", mod=self.inv,
                                      offset=self.gate17.lr())
        self.connect_inst(["o6", "o7","vdd","gnd"])

        self.gate18=self.add_inst(name="gate18", mod=self.nand2,
                                  offset=self.gate17.ul()+vector(0,self.ygap))
        self.connect_inst(["lfsr_done_b", "s_b2","o8","vdd","gnd"])

        self.gate19=self.add_inst(name="gate19", mod=self.nand2,
                                  offset=self.gate18.ul()+vector(0,self.ygap))
        self.connect_inst(["s0","s1", "o9","vdd","gnd"])

        self.gate110=self.add_inst(name="gate110", mod=self.nor2,
                                   offset=self.gate19.lr()+self.xshift)
        self.connect_inst(["o8","o9","o10","vdd","gnd"])

        self.gate111=self.add_inst(name="gate111", mod=self.nor2,
                                   offset=self.gate110.lr()+self.xshift)
        self.connect_inst(["o7","o10","o12","vdd","gnd"])

        self.gate112=self.add_inst(name="gate112", mod=self.nand2,
                                   offset=self.gate111.lr()+self.xshift)
        self.connect_inst(["o11","o12","d1","vdd","gnd"])
    
    def add_stage2_gates(self):
        """ Add gates for combinational logic of S2 FF"""
        
        self.gate20=self.add_inst(name="gate20", mod=self.nor2,
                                 offset=(self.gate112.rx()+self.vbus_width, self.hbus_width))
        self.connect_inst(["s0","s1","n0","vdd","gnd"])

        self.gate23=self.add_inst(name="gate23",mod=self.nor3,
                                  offset=self.gate20.ul()+self.yshift)
        self.connect_inst(["n0", "s2", "comp_err_b", "n3","vdd","gnd"])

        self.gate21=self.add_inst(name="gate21",mod=self.nand2,
                                  offset=self.gate23.ul()+vector(0,self.ygap))
        self.connect_inst(["s_b2", "lfsr_done", "n2","vdd","gnd"])

        self.gate22=self.add_inst(name="gate22",mod=self.nand2,
                                  offset=self.gate21.ul()+self.yshift)
        self.connect_inst(["s0","s1","n1","vdd","gnd"])

        self.gate24=self.add_inst(name="gate24",mod=self.nor2,
                                  offset=self.gate21.lr()+vector(self.xgap,0))
        self.connect_inst(["n2","n1","n4", "vdd","gnd"])

        self.gate25=self.add_inst(name="gate25",mod=self.nor3,
                                  offset=self.gate24.lr()+self.xshift)
        self.connect_inst(["n3","n4","s2", "n5", "vdd","gnd"])

        self.inv2_inst=self.add_inst(name="inv20",mod=self.inv,
                                     offset=self.gate25.lr())
        self.connect_inst(["n5","d2","vdd","gnd"])

    def add_err_gates(self):
        """ Add gates for combinational logic of "err" output """
        
        self.gate_err0=self.add_inst(name="gate_err0", mod=self.nand3,
                                     offset=self.gate22.ul()+vector(0,self.ygap))
        self.connect_inst(["s2", "s1","s_b0", "q0","vdd","gnd"])

        self.gate_err1=self.add_inst(name="gate_err1", mod=self.nor2,
                                     offset=self.gate_err0.ul()+self.yshift)
        self.connect_inst(["s0", "s1", "q1","vdd","gnd"])

        self.gate_err2=self.add_inst(name="gate_err2", mod=self.nor2,
                                     offset=self.gate_err1.ul()+self.yshift)
        self.connect_inst(["q1", "s2", "q2","vdd","gnd"])

        self.gate_err3=self.add_inst(name="gate_err3", mod=self.nor2,
                                     offset=self.gate_err2.ul()+self.yshift)
        self.connect_inst(["q2", "s2", "q3","vdd","gnd"])

        self.gate_err4=self.add_inst(name="gate_err4", mod=self.nor2,
                                     offset=self.gate_err3.lr()+self.xshift)
        self.connect_inst(["q3", "comp_err_b", "q4","vdd","gnd"])
        
        self.gate_err4_inv=self.add_inst(name="gate_err4_inv", mod=self.inv,
                                         offset=self.gate_err4.lr())
        self.connect_inst(["q4","q5","vdd","gnd"])

        self.gate_err5=self.add_inst(name="gate_err5", mod=self.nand2,
                                     offset=self.gate_err4_inv.lr()+self.xshift)
        self.connect_inst(["q0", "q5", "err","vdd","gnd"])

    def add_finish_gates(self):
        """ Add gates for combinational logic of "fin" output """
        
        xoff=self.inv2_inst.rx()+self.m_pitch("m1")
        self.gate_fin0=self.add_inst(name="gate_fin0", mod=self.nand2,
                                     offset=(xoff+self.vbus_width,self.hbus_width))
        self.connect_inst(["lfsr_done", "comp_err_b", "m0","vdd","gnd"])

        self.gate_fin1=self.add_inst(name="gate_fin1", mod=self.nand2,
                                     offset=self.gate_fin0.ul()+self.yshift)
        self.connect_inst(["m0","s_b1", "m1","vdd","gnd"])

        self.gate_fin2=self.add_inst(name="gate_fin2", mod=self.nand3,
                                     offset=self.gate_fin1.ul()+self.yshift)
        self.connect_inst(["m1", "s0", "s2", "m2","vdd","gnd"])
        
        self.inv_finish_inst=self.add_inst(name="inv_finish", mod=self.inv,
                                           offset=self.gate_fin2.lr())
        self.connect_inst(["m2","fin","vdd","gnd"])

    def add_up_down_gates(self):
        """ Add gates for combinational logic of "up_down" output """
        
        self.gate_updown0=self.add_inst(name="gate_updown0", mod=self.nand3,
                                        offset=self.gate_fin2.ul()+vector(0,self.ygap))
        self.connect_inst(["s0","s1", "s_b2", "x0", "vdd","gnd"])
        
        self.gate_updown1=self.add_inst(name="gate_updown1", mod=self.nand2,
                                        offset=self.gate_updown0.ul()+self.yshift)
        self.connect_inst(["x0", "s_b2", "up_down","vdd","gnd"])

    def add_data_gates(self):
        """ Add gates for combinational logic of "data_enable" output """
        

        self.gate_data1=self.add_inst(name="gate_data1", mod=self.nand2,
                                      offset=self.gate_updown1.ul()+self.yshift)
        self.connect_inst(["s_b2", "s0", "data1_b","vdd","gnd"])
        
        self.gate_data2=self.add_inst(name="inv_data", mod=self.inv,
                                      offset=self.gate_data1.lr())
        self.connect_inst(["data1_b","data_enable","vdd","gnd"])

    def add_read_write_gates(self):
        """ Add gates for combinational logic of "r" and "w" outputs """
        
        #W
        xoff=max(self.inv_finish_inst.rx(),self.gate_updown0.rx())+8*self.m_pitch("m1")
        self.gate_w0=self.add_inst(name="w0", mod=self.nand2,
                                   offset=(xoff+self.vbus_width, self.hbus_width))
        self.connect_inst(["s_b0", "s_b1", "f2", "vdd","gnd"])
        
        self.gate_w1=self.add_inst(name="w1", mod=self.nand2,
                                   offset=self.gate_w0.ul()+self.yshift)
        self.connect_inst(["f2", "s2", "f3", "vdd","gnd"])

        self.gate_w2=self.add_inst(name="w2", mod=self.nand3,
                                   offset=self.gate_w1.ul()+self.yshift)
        self.connect_inst(["f3", "clk2", "clk_d", "f4", "vdd","gnd"])

        self.gate_w3=self.add_inst(name="w3", mod=self.inv,
                                   offset=self.gate_w2.lr())
        self.connect_inst(["f4", "w", "vdd","gnd"])

        #R
        self.gate_r0=self.add_inst(name="r0", mod=self.nand2,
                                   offset=self.gate_w2.ul()+vector(0,self.ygap))
        self.connect_inst(["s_b2", "s0", "f6", "vdd","gnd"])
        
        self.gate_r1=self.add_inst(name="r1", mod=self.nand2,
                                   offset=self.gate_r0.ul()+self.yshift)
        self.connect_inst(["s1", "s_b2", "f7", "vdd","gnd"])
        
        self.gate_r2=self.add_inst(name="r2", mod=self.nand2,
                                    offset=self.gate_r1.ul()+vector(0,self.ygap))
        self.connect_inst(["s_b1", "s2", "f8", "vdd","gnd"])
        
        self.gate_r3=self.add_inst(name="r3", mod=self.nand3,
                                   offset=self.gate_r1.lr()+self.xshift)
        self.connect_inst(["f6", "f7", "f8", "f9", "vdd","gnd"])
        
        self.gate_r4=self.add_inst(name="r4", mod=self.nand3,
                                   offset=self.gate_r2.ul()+self.yshift)
        self.connect_inst(["f9", "clk3", "clk_d", "f10", "vdd","gnd"])

        self.gate_r5=self.add_inst(name="r5", mod=self.inv,
                                   offset=self.gate_r4.lr())
        self.connect_inst(["f10", "r", "vdd","gnd"])
        
    def add_connection_rails(self):
        """ Add 12 rails (5 signal & their complement + vdd & gnd) in metal2 
            for each stage and connect all rails together with metal1"""
        
        self.rail = []
        stage = []
        off=[self.rst_inv[0].rx(), self.gate09.rx(), self.gate112.rx(), self.inv2_inst.rx(), 
             max(self.inv_finish_inst.rx(), self.gate_updown0.rx())+3*self.m_pitch("m1")]
        
        self.height1=max(self.gate_r5.uy(), self.gate_data1.uy(),  
                         self.gate08.uy(), self.gate19.uy(), self.gate_err3.uy())
        
        for i in range(len(off)):
            for j in range(12):
                stage.append(off[i]+(j+2)*self.m_pitch("m1"))
                self.add_rect(layer="metal2", 
                              offset=(off[i]+(j+2)*self.m_pitch("m1"), 0),
                              width=contact.m1m2.width,
                              height=self.height1+5*self.m_pitch("m1"))
                self.add_via(self.m1_stack, (off[i]+(j+2)*self.m_pitch("m1"), 
                                             j*self.m_pitch("m1")-self.via_shift("v1")))
            self.rail.append(stage)
            stage=[]
        
        for j in range(12):
            self.add_rect(layer="metal1", 
                          offset=(off[0]+(j+2)*self.m_pitch("m1"), j*self.m_pitch("m1")),
                          width=off[-1]-off[0],
                          height=self.m1_width)

    def connect_reset_gates_to_rails(self):
        """ Connect output of reset gates to middle rails """

        pins=["Z", "A"]
        for i in range(3):
            pos1=self.rst_inv[i].get_pin("Z").lc()
            pos2=vector(self.rail[0][2*i], pos1.y)
            self.add_path("metal1",[pos1, pos2])
            self.add_via_center(self.m1_stack, (pos2.x+0.5*contact.m1m2.width, pos2.y)) 

            if i%2:
                y_off=self.rst_inv[i].by()-self.m_pitch("m1")
            else:
                y_off=self.rst_inv[i].uy()+self.m_pitch("m1")
            
            pin=self.rst_inv[i].get_pin("A")
            pos3=vector(pin.rx()-2*self.m1_width, pin.lc().y)
            pos4=vector(pos3.x, y_off)
            pos5=vector(self.rail[0][2*i+1], pos4.y)
            
            self.add_via_center(self.m1_stack, pos3)
            self.add_wire(self.m1_stack,[pos3, pos4, pos5])
            self.add_via_center(self.m1_stack, (pos5.x+0.5*contact.m1m2.width, pos5.y)) 

    def connect_input_inv_to_rails(self):
        """ Connect input and output of comp_err and lsfr_done inverters to middle rails """

        power_pins=["vdd", "gnd"]
        for i in range(2):
            pos1=self.rst_inv[3+i].get_pin("Z")
            pos2=vector(self.rail[0][6+2*i], pos1.lc().y)
            self.add_path("metal3", [(pos1.rx()-self.m1_space-contact.m2m3.width, pos1.lc().y), pos2])
            self.add_via_center(self.m2_stack, (pos2.x+0.5*contact.m1m2.width, pos2.y))
            pin=self.rst_inv[3+i].get_pin("A")
            pos3=vector(pin.lx()-0.5*contact.m1m2.width, pin.lc().y)
            
            if i %2:
                pos5=vector(pos3.x, self.rst_inv[3+i].get_pin("gnd").lc().y+self.m_pitch("m1"))
                self.add_via(self.m2_stack, pos1.ul()-vector(contact.m2m3.width, 
                                                      contact.m2m3.height-self.via_shift("v2")))
            else:
                pos5=vector(pos3.x, self.rst_inv[3+i].get_pin("gnd").lc().y-self.m_pitch("m1"))
                self.add_via(self.m2_stack, pos1.ll()-vector(contact.m2m3.width,self.via_shift("v2")))
            
            pos6=vector(self.rail[0][7+2*i], pos5.y)
            self.add_wire(self.m2_rev_stack,[pos3, pos5, pos6] )
            self.add_via_center(self.m1_stack, pos3)
            self.add_via_center(self.m2_stack, (pos6.x+0.5*contact.m1m2.width, pos6.y))

            for j in range(2):
                pos1=self.rst_inv[3+i].get_pin(power_pins[j]).lc()
                pos2=vector(self.vdd_xoff-j*self.m_pitch("m1"), pos1.y)
                self.add_path("metal1",[pos1, pos2])
                self.add_via_center(self.m1_stack, (pos2.x+0.5*contact.m1m2.width, pos2.y))

    def reset_inverter_connections(self):
        """ Connect input, output and power of reset inverter """
        
        modules=[self.reset_inv, self.dc_inst]
        power_pins=["vdd", "gnd"]
        xoffset=[self.vdd_xoff, self.gnd_xoff]
        
        #connect vdd and gnd of reset_inv and clk_inv to rails
        for mod in modules:
            for (i,off) in zip(power_pins, xoffset):
                pos1=mod.get_pin(i).lc()
                pos2 = vector(off, pos1.y)
                self.add_path("metal1",[pos1, pos2])
                self.add_via_center(self.m1_stack, (pos2.x+0.5*contact.m1m2.width, pos2.y))
        
        #connect output of reset inverter to input 'B' of nand2 gates
        pos1=self.reset_inv.get_pin("Z").lc()
        pos2=vector(self.init_mos[0].rx()+3*self.m_pitch("m1"), pos1.y)
        self.add_path("metal1", [pos1, pos2])
        self.add_via_center(self.m1_stack, pos2)
        for i in range(5):
            pos3=self.rst_nand[i].get_pin("A").lc()
            pos4=vector(pos2.x, pos3.y)
            self.add_wire(self.m1_stack, [pos2, pos3, pos4])

    def connect_reset_gates_to_ff(self):
        """ Connect output and power of FF to reset gates"""
        
        for i in range(3):
            #connect output of rst_inv to input of FF
            pin=self.ff_inst[i].get_pin("out")
            pos1=vector(pin.rx(), pin.lc().y)
            pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
            pos4=self.rst_nand[i].get_pin("B").lc()
            pos3=vector(pos2.x+self.m_pitch("m1"), pos4.y)
            self.add_path("metal1", [pos1, pos2, pos3, pos4])
            
            #connect gnd of rst_inv to gnd of FF
            self.add_path("metal1", [self.rst_inv[i].get_pin("gnd").lc(), 
                                     self.ff_inst[i].get_pin("gnd").lc()])
            
            #connect vdd of rst_inv to vdd of FF
            pos3=vector(self.ff_inst[i].rx(), self.ff_inst[i].get_pin("vdd").lc().y)
            pin=self.rst_nand[i].get_pin("vdd")
            pos1=vector(pin.lx()+0.5*self.m1_width, pin.lc().y)
            pos2=vector(pos1.x, pos3.y)
            self.add_path("metal1", [pos1, pos2, pos3])

        for i in range(3):
            pins = ["vdd", "gnd"]
            for j in range(2):
                pos1=self.ff_inst[i].get_pin(pins[j]).lc()
                pos2 = vector(self.vdd_xoff-j*self.m_pitch("m1"), pos1.y)
                self.add_path("metal1",[pos1, pos2])
                self.add_via_center(self.m1_stack, (pos2.x+0.5*contact.m1m2.width, pos2.y))

    def connect_pin_to_rail(self, gate, pin, rail_off):
        """ Connect pin 'pin' of gate 'gate' to rail at offset 'rail_off' """
        
        self.add_path("metal1", [gate.get_pin(pin).lc(), (rail_off, gate.get_pin(pin).lc().y)])
        xoff = rail_off+contact.m1m2.width+self.via_shift("v1")
        yoff=  gate.get_pin(pin).by()
        self.add_via(self.m1_stack, (xoff,yoff), rotate=90)

    def connect_out_to_in(self, out_gate, in_gate, in_pin):
        """ Connect output pin of a gate to input pin of other gate with a Z-path """
        
        outpin=vector(out_gate.get_pin("Z").rx(), out_gate.get_pin("Z").lc().y)
        inpin=vector(in_gate.get_pin(in_pin).lx(), in_gate.get_pin(in_pin).lc().y)
        if (abs(outpin.y - inpin.y) > self.inv.height):
            self.add_wire(self.m1_stack, [outpin, (inpin.x-self.m_pitch("m1"), outpin.y),
                                         (inpin.x-self.m_pitch("m1"), inpin.y), inpin])
        else:
            self.add_path("metal1", [outpin, (outpin.x+self.m_pitch("m1"), outpin.y),
                                     (outpin.x+self.m_pitch("m1"), inpin.y), inpin])

    def s_connection(self, pin1, pin_name, pin2):
        """ Connect pin1 to pin2 with an S-shape wire"""
        
        pos1=pin1.get_pin(pin_name).lc()
        pos2=vector(pos1.x-self.m1_width, pos1.y)
        pos3=vector(pos2.x, pin1.by()-self.m_pitch("m1"))
        pos5=vector(pin2.get_pin("Z").rx(), pin2.get_pin("Z").lc().y)
        pos4=vector(pos5.x+self.m_pitch("m1"), pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
        
    def connect_stage0_gates_to_rails(self):
        """ Connect input pins of stage1 gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate00, "A", self.rail[0][2])
        self.connect_pin_to_rail(self.gate00, "B", self.rail[0][7])
        self.connect_pin_to_rail(self.gate01, "B", self.rail[0][1])
        self.connect_pin_to_rail(self.gate01, "C", self.rail[0][5])
        self.connect_pin_to_rail(self.gate02, "A", self.rail[0][5])
        self.connect_pin_to_rail(self.gate02, "B", self.rail[0][7])
        self.connect_pin_to_rail(self.gate03, "A", self.rail[0][1])
        self.connect_pin_to_rail(self.gate03, "B", self.rail[0][3])
        self.connect_pin_to_rail(self.gate03, "C", self.rail[0][8])
        self.connect_pin_to_rail(self.gate05, "A", self.rail[0][0])
        self.connect_pin_to_rail(self.gate05, "B", self.rail[0][9])
        self.connect_pin_to_rail(self.gate06, "A", self.rail[0][1])
        self.connect_pin_to_rail(self.gate06, "B", self.rail[0][2])
        self.connect_pin_to_rail(self.gate06, "C", self.rail[0][8])
        self.connect_pin_to_rail(self.gate08, "B", self.rail[0][5])
        self.connect_pin_to_rail(self.gate08, "C", self.rail[0][7])
        self.connect_out_to_in(self.gate05, self.gate07, "A")
        self.connect_out_to_in(self.gate06, self.gate07, "B")
        self.connect_out_to_in(self.gate02, self.gate04, "A")
        self.connect_out_to_in(self.gate03, self.gate04, "B")
        self.connect_out_to_in(self.gate01_inv, self.gate09, "A")
        self.connect_out_to_in(self.gate08, self.gate09, "C")
        self.connect_out_to_in(self.gate04_inv, self.gate09, "B")
        self.s_connection(self.gate01, "A", self.gate00)
        self.s_connection(self.gate08, "A", self.gate07)
        
        for gate in [self.gate00, self.gate01, self.gate02, self.gate04, 
                     self.gate05, self.gate07, self.gate08, self.gate09]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[0][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[0][11])

    def connect_stage1_gates_to_rails(self):
        """ Connect input pins of stage1 gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate10, "A", self.rail[1][4])
        self.connect_pin_to_rail(self.gate10, "B", self.rail[1][1])
        self.connect_pin_to_rail(self.gate11, "B", self.rail[1][3])
        self.connect_pin_to_rail(self.gate12, "A", self.rail[1][0])
        self.connect_pin_to_rail(self.gate12, "B", self.rail[1][2])
        self.connect_pin_to_rail(self.gate14, "B", self.rail[1][4])
        self.connect_pin_to_rail(self.gate15, "B", self.rail[1][7])
        self.connect_pin_to_rail(self.gate17, "A", self.rail[1][0])
        self.connect_pin_to_rail(self.gate17, "B", self.rail[1][3])
        self.connect_pin_to_rail(self.gate17, "C", self.rail[1][8])
        self.connect_pin_to_rail(self.gate18, "A", self.rail[1][9])
        self.connect_pin_to_rail(self.gate18, "B", self.rail[1][5])
        self.connect_pin_to_rail(self.gate19, "A", self.rail[1][0])
        self.connect_pin_to_rail(self.gate19, "B", self.rail[1][2])
        self.connect_out_to_in(self.gate11, self.gate16, "A")
        self.connect_out_to_in(self.gate12, self.gate13, "A")
        self.connect_out_to_in(self.gate15, self.gate16, "B")
        self.connect_out_to_in(self.gate18, self.gate110, "A")
        self.connect_out_to_in(self.gate19, self.gate110, "B")
        self.connect_out_to_in(self.gate17_inv, self.gate111, "A")
        self.connect_out_to_in(self.gate110, self.gate111, "B")
        self.connect_out_to_in(self.gate16, self.gate112, "A")
        self.connect_out_to_in(self.gate111, self.gate112, "B")
        self.s_connection(self.gate11, "A", self.gate10)
        self.s_connection(self.gate14, "A", self.gate13)
        self.s_connection(self.gate15, "A", self.gate14)

        for gate in [self.gate10, self.gate11, self.gate13, self.gate14, 
                     self.gate16, self.gate17, self.gate18, self.gate112]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[1][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[1][11])
        
        #connect input B of gate13 to s2 (self.rail[1][4])
        pos1=vector(self.rail[1][4], self.gate12.uy()+self.m_pitch("m1"))
        pos2=vector(self.gate12.rx()+self.m_pitch("m1"), pos1.y)
        pos3=self.gate13.get_pin("B").lc()
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, pos1)

    def connect_stage2_gates_to_rails(self):
        """ Connect input pins of stage2 gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate20, "A", self.rail[2][0])
        self.connect_pin_to_rail(self.gate20, "B", self.rail[2][2])
        self.connect_pin_to_rail(self.gate21, "A", self.rail[2][5])
        self.connect_pin_to_rail(self.gate21, "B", self.rail[2][8])
        self.connect_pin_to_rail(self.gate22, "A", self.rail[2][0])
        self.connect_pin_to_rail(self.gate22, "B", self.rail[2][2])
        self.connect_pin_to_rail(self.gate23, "B", self.rail[2][4])
        self.connect_pin_to_rail(self.gate23, "C", self.rail[2][7])
        self.connect_out_to_in(self.gate21, self.gate24, "A")
        self.connect_out_to_in(self.gate22, self.gate24, "B")
        self.connect_out_to_in(self.gate23, self.gate25, "A")
        self.connect_out_to_in(self.gate24, self.gate25, "B")
        self.s_connection(self.gate23, "A", self.gate20)
        
        for gate in [self.gate20, self.gate21, self.gate22, self.gate23, self.gate25]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[2][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[2][11])
        
        #connect input C of gate25 to s2 (self.rail[2][4])
        pos1=vector(self.rail[2][4], self.gate22.by()-self.m_pitch("m1"))
        pos2=vector(self.gate25.lx()-self.m_pitch("m1"), pos1.y)
        pos3=self.gate25.get_pin("C").lc()
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        self.add_via(self.m1_stack, pos1)

    def connect_err_gates_to_rails(self):
        """ Connect input pins of error and data gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate_err0, "A", self.rail[2][4])
        self.connect_pin_to_rail(self.gate_err0, "B", self.rail[2][2])
        self.connect_pin_to_rail(self.gate_err0, "C", self.rail[2][1])
        self.connect_pin_to_rail(self.gate_err1, "A", self.rail[2][0])
        self.connect_pin_to_rail(self.gate_err1, "B", self.rail[2][2])
        self.connect_pin_to_rail(self.gate_err2, "B", self.rail[2][4])
        self.connect_pin_to_rail(self.gate_err3, "B", self.rail[2][4])
        self.connect_out_to_in(self.gate_err3, self.gate_err4, "A")
        self.connect_out_to_in(self.gate_err4_inv, self.gate_err5, "B")
        self.connect_out_to_in(self.gate_err0, self.gate_err5, "A")
        self.s_connection(self.gate_err2, "A", self.gate_err1)
        self.s_connection(self.gate_err3, "A", self.gate_err2)
        
        for gate in [self.gate_err0, self.gate_err1, self.gate_err2, self.gate_err5 ]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[2][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[2][11])

        #connect input B of gate_err4 to comp_err_b (self.rail[2][7])
        pos1=vector(self.rail[2][7], self.gate_err3.uy()+self.m_pitch("m1"))
        pos2=vector(self.gate_err3.rx()+self.m_pitch("m1"), pos1.y)
        pos3=self.gate_err4.get_pin("B").lc()
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        self.add_via_center(self.m1_stack, pos1+vector(0.5*contact.m1m2.width, 0), rotate=90)
    
    def connect_finish_updown_data_gates_to_rails(self):
        """ Connect input pins of finish and up_down gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate_fin0, "A", self.rail[3][8])
        self.connect_pin_to_rail(self.gate_fin0, "B", self.rail[3][7])
        self.connect_pin_to_rail(self.gate_fin1, "B", self.rail[3][3])
        self.connect_pin_to_rail(self.gate_fin2, "B", self.rail[3][0])
        self.connect_pin_to_rail(self.gate_fin2, "C", self.rail[3][4])
        self.connect_pin_to_rail(self.gate_updown0, "A", self.rail[3][0])
        self.connect_pin_to_rail(self.gate_updown0, "B", self.rail[3][2])
        self.connect_pin_to_rail(self.gate_updown0, "C", self.rail[3][5])
        self.connect_pin_to_rail(self.gate_updown1, "B", self.rail[3][5])
        self.connect_pin_to_rail(self.gate_data1, "A", self.rail[3][5])
        self.connect_pin_to_rail(self.gate_data1, "B", self.rail[3][0])
        self.s_connection(self.gate_fin1, "A", self.gate_fin0)
        self.s_connection(self.gate_fin2, "A", self.gate_fin1)
        self.s_connection(self.gate_updown1, "A", self.gate_updown0)

        for gate in [self.gate_fin0, self.gate_fin1, self.gate_fin2, self.gate_updown0,  
                     self.gate_updown1, self.gate_data1]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[3][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[3][11])

    def connect_read_write_gates_to_rails(self):
        """ Connect input pins of read and write gates to middle rails. order of rails: 
            0:s0, 1:s_b0, 2:s1, 3:s_b1, 4:s2, 5:s_b2, 6:comp_err, 7:comp_err_b, 
            8:lfsr_done, 9:lfsr_done_b, 10:vdd, 11:gnd """
        
        self.connect_pin_to_rail(self.gate_w0, "A", self.rail[4][1])
        self.connect_pin_to_rail(self.gate_w0, "B", self.rail[4][3])
        self.connect_pin_to_rail(self.gate_w1, "B", self.rail[4][4])
        self.connect_pin_to_rail(self.gate_r0, "A", self.rail[4][5])
        self.connect_pin_to_rail(self.gate_r0, "B", self.rail[4][0])
        self.connect_pin_to_rail(self.gate_r1, "A", self.rail[4][2])
        self.connect_pin_to_rail(self.gate_r1, "B", self.rail[4][5])
        self.connect_pin_to_rail(self.gate_r2, "A", self.rail[4][3])
        self.connect_pin_to_rail(self.gate_r2, "B", self.rail[4][4])
        self.s_connection(self.gate_w1, "A", self.gate_w0)
        self.s_connection(self.gate_w2, "A", self.gate_w1)
        self.connect_out_to_in(self.gate_r0, self.gate_r3, "A")
        self.connect_out_to_in(self.gate_r1, self.gate_r3, "B")
        self.connect_out_to_in(self.gate_r2, self.gate_r3, "C")
        self.s_connection(self.gate_r4, "A", self.gate_r3)
        for gate in [self.gate_w0, self.gate_w1, self.gate_w2, self.gate_r0,    
                     self.gate_r2, self.gate_r3, self.gate_r4, self.gate_r5]:
            self.connect_pin_to_rail(gate, "vdd", self.rail[4][10])
            self.connect_pin_to_rail(gate, "gnd", self.rail[4][11])

        #connect input B of gate_w2 to clk2
        pos3=vector(-8*self.m_pitch("m1"), self.height1+3*self.m_pitch("m1"))
        pos6=self.gate_w2.get_pin("B").lc()
        pos4=vector(pos6.x-3*self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos3, pos4, pos5, pos6])
        self.add_layout_pin(text="clk2",
                            offset=pos3-vector(0, 0.5*self.m1_width),
                            layer=self.m1_pin_layer,
                            width=self.m1_width,
                            height=self.m1_width)

        #connect input B of gate_r4 to clk3
        pos1=self.ff_inst[0].get_pin("clk").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.height1+2*self.m_pitch("m1"))
        pos6=self.gate_r4.get_pin("B").lc()
        pos4=vector(pos6.x-4*self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])

        #connect input C of gate_w2 and gate_r4 to clk_d (delay_chain output)
        pos1=self.dc_inst.get_pin("out").lc()
        pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.dc_inst.by()-self.m_pitch("m1"))
        pos6=self.gate_r4.get_pin("C").lc()
        pos4=vector(pos6.x-5*self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])

        pos7=self.gate_w2.get_pin("C").lc()
        pos8=vector(pos4.x, pos7.y)
        self.add_wire(self.m1_stack, [pos4, pos7, pos8])

    def connect_ff_gates_inputs(self):
        """  Connect output of stage0, stage1 and stage2 to to 
             ff_inst[0], ff_inst[1] and ff_inst[2] 'in' input, respectively. """
        
        modules=[self.gate09, self.gate112, self.inv2_inst]
        for i in range(3):
            pos1=vector(modules[i].get_pin("Z").rx(), modules[i].get_pin("Z").lc().y)
            pos2=vector(pos1.x+2*self.m1_width, pos1.y)
            pos3=vector(pos2.x, -(i+1)*self.m_pitch("m1"))
            pos5=self.ff_inst[i].get_pin("in").lc()
            pos4=vector(pos5.x-(i+2)*self.m_pitch("m1"), pos3.y)
            
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
    
    def add_layout_pins(self):
        """ Adds all input, ouput and power pins"""

        self.min_xoff=self.ff_inst[0].lx()-8*self.m_pitch("m1")
        self.max_xoff = max(self.gate_r3.rx(), self.gate_r5.rx()) + self.m_pitch("m1")
        
        #Add output pin "comp" and "lfsr"
        pin_names = ["comp" , "lfsr"]
        for i in range(2):
            pin =self.rst_nand[3+i].get_pin("B")
            self.add_path("metal1", [(self.min_xoff, pin.lc().y), pin.lc()])
            self.add_layout_pin(text=pin_names[i],
                                layer=self.m1_pin_layer,
                                offset=(self.min_xoff, pin.by()),
                                width=self.m1_width,
                                height=self.m1_width)

        #Add input pin "reset"
        pin= self.reset_inv.get_pin("A")
        self.add_path("metal1", [pin.lc(), (self.min_xoff, pin.lc().y) ])
        self.add_layout_pin(text="reset",
                            layer=self.m1_pin_layer,
                            offset=(self.min_xoff, pin.by()),
                            width=self.m1_width,
                            height=self.m1_width)

        #Connect clk pin of all FFs together and Add input pin "clk3"
        for i in range(3):
            pos1=self.ff_inst[i].get_pin("clk").lc()
            pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
            pos3=vector(pos2.x, self.ff_inst[2].get_pin("clk").lc().y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_via_center(self.m1_stack, pos3, rotate=90)
        

        #Add clk pin
        pos4=vector(self.min_xoff, self.dc_inst.get_pin("in").lc().y)
        self.add_path("metal1", [pos4, self.dc_inst.get_pin("in").lc()])
        self.add_layout_pin(text="clk",
                            layer=self.m1_pin_layer,
                            offset=(pos4.x, pos4.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)
        
        pos4=vector(self.min_xoff, self.ff_inst[0].get_pin("clk").lc().y)
        self.add_path("metal1", [pos4, self.ff_inst[0].get_pin("clk").lc()])
        self.add_layout_pin(text="clk3",
                            layer=self.m1_pin_layer,
                            offset=(pos4.x, pos4.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #Add output pin "data_enable", "up_down" and "finish"
        pins=["data_enable","up_down", "fin"]
        module=[self.gate_data2, self.gate_updown1, self.inv_finish_inst]
        for i in range(3):
            pos1=vector(module[i].get_pin("Z").rx(), module[i].get_pin("Z").lc().y)
            pos2=vector(module[2].get_pin("Z").rx()+(i+1)*self.m_pitch("m1"), pos1.y)
            pos3=vector(pos2.x, self.height1+5*self.m_pitch("m1"))
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_layout_pin(text=pins[i],
                                layer=self.m2_pin_layer,
                                offset=(pos3.x-0.5*self.m2_width, pos3.y-self.m2_width),
                                width=self.m2_width,
                                height=self.m2_width)

        #Add output pin "err"
        pos1=vector(self.gate_err5.get_pin("Z").rx(), self.gate_err5.get_pin("Z").lc().y)
        pos2=vector(pos1.x+self.m1_width, pos1.y)
        pos3=vector(pos2.x, self.height1+5*self.m_pitch("m1"))
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        self.add_layout_pin(text="err",
                            layer=self.m2_pin_layer,
                            offset=(pos3.x-0.5*self.m2_width, pos3.y-self.m2_width),
                            width=self.m2_width,
                            height=self.m2_width)

        #Add output read-write pins
        pin_list=["r", "w" ]
        module_list=[self.gate_r5, self.gate_w3]
        for (pin,mod) in zip(pin_list, module_list):
            pos1=mod.get_pin("Z").lc()
            pos2=vector(self.max_xoff, pos1.y)
            self.add_path("metal1", [pos1, pos2])
            self.add_layout_pin(text=pin,
                                layer=self.m1_pin_layer,
                                offset=(self.max_xoff-self.m1_width, pos2.y-0.5*self.m1_width),
                                width=self.m1_width,
                                height=self.m1_width)

        #Add power pin "vdd" and "gnd"
        pin_off=[self.vdd_xoff, self.gnd_xoff]
        pin_names=["vdd", "gnd"]
        for i in range(2):
            y_off=self.height1+(5-i)*self.m_pitch("m1")
            self.add_path("metal1", [(pin_off[i],y_off), (self.rail[0][10+i], y_off)])
            self.add_via(self.m1_stack, (pin_off[i], y_off-0.5*self.m1_width-self.via_shift("v1")))
            self.add_via(self.m1_stack, (self.rail[0][10+i], y_off-0.5*self.m1_width-self.via_shift("v1")))
        
        for (off, name) in zip(pin_off, pin_names):
            self.add_rect(layer="metal2", 
                          offset=(off, self.dc_inst.by()), 
                          width=self.m2_width, 
                          height=self.height1+self.dc_inst.height+9*self.m_pitch("m1"))
            self.add_layout_pin(text=name,
                                layer=self.m2_pin_layer,
                                offset=(off, self.height1+5*self.m_pitch("m1")-self.m2_width),
                                width=self.m2_width,
                                height=self.m2_width)
