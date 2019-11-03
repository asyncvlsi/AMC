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


import sys
import datetime
import getpass
import design
import debug
import contact
from tech import drc
from vector import vector
from math import log
from globals import OPTS, print_time
from sync_interface_ctrl import sync_interface_ctrl
from din_latch import din_latch
from dout_latch import dout_latch
from ctrl_latch import ctrl_latch
from sram import sram
from utils import ceil
from bitcell import bitcell

class sync_sram(design.design):
    """ Add synchronous interface to SRAM"""

    def __init__(self, word_size, words_per_row, num_rows, num_subanks, 
                 branch_factors, bank_orientations, name="sync_sram"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.word_size = word_size
        self.w_per_row = words_per_row
        self.num_rows= num_rows
        self.num_subanks = num_subanks
        self.branch_factors= branch_factors
        self.num_outbanks = branch_factors[0]
        self.num_inbanks = branch_factors[1]
        self.bank_orientations = bank_orientations
        self.addr_size = int(log(self.w_per_row, 2)) + \
                         int(log(self.num_rows, 2)) + \
                         int(log(self.num_subanks, 2)) + \
                         int(log(self.num_outbanks, 2)) + \
                         int(log(self.num_inbanks, 2))
        self.create_layout()
        self.offset_all_coordinates()

        self.bitcell = bitcell()

        self.total_bits = self.num_rows*self.num_subanks*self.word_size*\
                          self.w_per_row*self.num_inbanks*self.num_outbanks
        efficiency = 100*((self.total_bits*self.bitcell.width*\
                      self.bitcell.height)/(self.width*self.height))

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_offsets()
        self.add_modules()
        self.connect_interface_to_sram()
        self.add_layout_pins()

    def add_pins(self):
        """ Adds pins, order of the pins is important """
        
        for i in range(self.word_size):
                self.add_pin("data_in[{0}]".format(i),"INPUT")
        for i in range(self.word_size):
                self.add_pin("data_out[{0}]".format(i),"OUTPUT")
        for i in range(self.addr_size):
            self.add_pin("addr[{0}]".format(i),"INPUT")
        self.add_pin_list(["reset", "r", "w",  "en", "clk"],"INPUT")
        self.add_pin("vdd","POWER")
        self.add_pin("gnd","GROUND")

    def create_modules(self):
        """ Create modules for instantiation """

        self.async_sram = sram(word_size=self.word_size, words_per_row=self.w_per_row, 
                               num_rows=self.num_rows, num_subanks=self.num_subanks, 
                               branch_factors=self.branch_factors, 
                               bank_orientations=self.bank_orientations, name="async_sram")
        self.add_mod(self.async_sram)

        self.din_latch = din_latch(size=self.word_size, name="din_latch")
        self.add_mod(self.din_latch)

        self.dout_latch = dout_latch(size=self.word_size, name="dout_latch")
        self.add_mod(self.dout_latch)
        
        self.addr_latch = din_latch(size=self.addr_size, name="addr_latch")
        self.add_mod(self.addr_latch)

        self.ctrl_latch = ctrl_latch(size=2, name="ctrl_latch")
        self.add_mod(self.ctrl_latch)
        
        self.sync_interface_ctrl = sync_interface_ctrl(name="sync_interface_ctrl")
        self.add_mod(self.sync_interface_ctrl)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.ygap= max(self.implant_space,self.well_space,3*self.m_pitch("m1"))

        #This is a contact/via shift to avoid DRC violation
        self.via_xshift= 0.5*abs(contact.m1m2.second_layer_width-self.m1_width)
        
        self.height= self.async_sram.height
        self.width = self.async_sram.width+self.sync_interface_ctrl.width+\
                     max(self.dout_latch.width,self.din_latch.width)+\
                     self.m_pitch("m1")*(2*self.word_size+self.addr_size+20)

    def add_modules(self):
        """ Place the modules """
        
        self.add_sram()
        self.add_din_latch_array()
        self.add_dout_latch_array()
        self.add_addr_latch_array()
        self.add_ctrl_latch_array()
        self.add_sync_interface_ctrl_logic()

    def connect_interface_to_sram(self):
        """ Connect all the modules to sram data, addr, ctrl bus """
        
        self.connect_data_latch()
        self.connect_addr_latch()
        self.connect_ctrl_latch()
        self.route_ctrl_lines()
        self.route_clk()
        self.route_power_lines()

    def add_sram(self):
        """ Place async SRAM """
        
        self.sram_inst=self.add_inst(name="async_sram", mod=self.async_sram, offset=(0, 0))
        temp =[]
        for i in range(self.word_size):
            temp.append("async_din[{0}]".format(i))
        for i in range(self.word_size):
            temp.append("async_dout[{0}]".format(i))
        for i in range(self.addr_size):
            temp.append("async_addr[{0}]".format(i))
        temp.extend(["reset", "async_r", "async_w",  "rw", "async_ack", 
                     "async_rack", "async_r", "async_w", "wack", "vdd", "gnd"])
        self.connect_inst(temp)
        
    def add_din_latch_array(self):
        """ Place din_latch array """

        yoff = max(self.sram_inst.get_pin("data_out[{}]".format(self.word_size-1)).by(),
                   self.sram_inst.get_pin("vdd").by())+self.m_pitch("m2")
        xoff=self.async_sram.width+(2*self.word_size+5)*self.m_pitch("m1")+self.din_latch.width
        
        self.din_latch=self.add_inst(name="din_latch", 
                                     mod=self.din_latch, 
                                     offset=(xoff,yoff),
                                     mirror="MY")
        temp =[]
        for i in range(self.word_size):
            temp.append("data_in[{0}]".format(i))
        for i in range(self.word_size):
            temp.append("async_din[{0}]".format(i))
        temp.extend(["clk", "din_en", "clk_b", "din_enb", "vdd", "gnd"])
        self.connect_inst(temp)


    def add_dout_latch_array(self):
        """ Place dout_latch array """

        xoff= self.async_sram.width+(2*self.word_size+5)*self.m_pitch("m1") 
        yoff=self.din_latch.uy()+10*self.m_pitch("m2")
        self.dout_latch=self.add_inst(name="dout_latch", 
                                          mod=self.dout_latch, 
                                          offset=(xoff,yoff))
        temp =[]
        for i in range(self.word_size):
            temp.append("async_dout[{0}]".format(i))
        for i in range(self.word_size):
            temp.append("data_out[{0}]".format(i))
        temp.extend(["async_rack", "rack_b","vdd", "gnd"])
        self.connect_inst(temp)

    def add_addr_latch_array(self):
        """ Place addr_latch array """

        xoff=-(self.addr_size+14)*self.m_pitch("m1")-self.addr_latch.width 
        yoff=self.sram_inst.get_pin("addr[0]").by()+0.5*self.m1_width-self.via_xshift
        self.addr_latch=self.add_inst(name="addr_latch", 
                                          mod=self.addr_latch, 
                                          offset=(xoff,yoff))
        temp =[]
        for i in range(self.addr_size):
            temp.append("addr[{0}]".format(i))
        for i in range(self.addr_size):
            temp.append("async_addr[{0}]".format(i))
        temp.extend(["clk", "din_en", "clk_b", "din_enb", "vdd", "gnd"])
        self.connect_inst(temp)

    def add_ctrl_latch_array(self):
        """ Place ctrl_latch array """

        xoff=-max(self.addr_latch.width,self.ctrl_latch.width)-\
              (self.addr_size+14)*self.m_pitch("m1") 
        yoff=self.addr_latch.uy()+self.ygap
        self.ctrl_latch=self.add_inst(name="ctrl_latch", 
                                      mod=self.ctrl_latch, 
                                      offset=(xoff,yoff))
        self.connect_inst(["r", "w", "async_r", "async_w", "clk", "ctrl_en", "vdd", "gnd"])
        
    def add_sync_interface_ctrl_logic(self):
        """ Place sync_interface_ctrl_logic """

        xoff=-max(self.addr_latch.width, self.sync_interface_ctrl.width)-\
             (self.addr_size+14)*self.m_pitch("m1") 
        yoff=self.ctrl_latch.uy()+self.ygap+2*self.m_pitch("m1")
        self.interface_ctrl=self.add_inst(name="sync_ctrl_logic", 
                                          mod=self.sync_interface_ctrl, 
                                          offset=(xoff,yoff))
        self.connect_inst(["clk", "clk_b", "en", "async_ack", "async_rack", "ctrl_en", 
                           "din_en", "din_enb", "rack_b", "vdd", "gnd"])

    def connect_data_latch(self):
        """ Connect din and dout latches to data buses"""
        
        for i in range(self.word_size):
            pos1 = self.din_latch.get_pin("sync_din[{0}]".format(i)).lc()
            pos2 = vector(self.din_latch.lx()-(i+3)*self.m_pitch("m1"), pos1.y)
            pos4 = self.sram_inst.get_pin("data_in[{}]".format(i)).lc()
            pos3 = vector(pos2.x, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        for i in range(self.word_size):
            pos1 = self.dout_latch.get_pin("async_dout[{0}]".format(i)).lc()
            pos2 = vector(self.dout_latch.lx()-(i+3+self.word_size)*self.m_pitch("m1"), pos1.y)
            pos4 = self.sram_inst.get_pin("data_out[{}]".format(i)).lc()
            pos3 = vector(pos2.x, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

    def connect_addr_latch(self):
        """ Connect addr latches to addr buses"""
        
        if (self.branch_factors[1] == 1 or self.branch_factors[0] != 1):
            for i in range(self.addr_size):
                pos1 = self.addr_latch.get_pin("sync_din[{0}]".format(i)).lc()
                pos2 = vector(self.addr_latch.rx()+(i+6)*self.m_pitch("m1"), pos1.y)
                pos4 = self.sram_inst.get_pin("addr[{}]".format(i)).lc()
                pos3 = vector(pos2.x, pos4.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        else:
            y_off = min(self.sram_inst.get_pin("addr[0]").by()-self.m_pitch("m1"), 
                        self.din_latch.by()-(2*self.word_size+2)*self.m_pitch("m1"))
            for i in range(self.addr_size):
                pos1 = self.addr_latch.get_pin("sync_din[{0}]".format(i)).lc()
                pos2 = vector(self.addr_latch.rx()+(i+6)*self.m_pitch("m1"), pos1.y)
                pos5 = self.sram_inst.get_pin("addr[{}]".format(i)).uc()
                pos3 = vector(pos2.x, y_off-i*self.m_pitch("m1"))
                pos4 = vector(pos5.x, pos3.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
    
    def connect_ctrl_latch(self):
        """ Connect addr latches to addr buses"""
        
        ctrl_pins = ["r", "w", "rreq", "wreq"]

        for i in range(4):

            if (self.branch_factors[1] == 1 or self.branch_factors[0] != 1): 
                y_off = self.sram_inst.get_pin(ctrl_pins[i]).lc().y
                pos6 = self.sram_inst.get_pin(ctrl_pins[i]).lc()
            else:    
                y_off = min(self.sram_inst.get_pin("addr[0]").by()-(self.addr_size+1)*self.m_pitch("m1"), 
                            self.din_latch.by()-(2*self.word_size+self.addr_size+2)*self.m_pitch("m1"))-\
                            i%2*self.m_pitch("m1")
                pos6 = self.sram_inst.get_pin(ctrl_pins[i]).uc()
            
            pos1 = self.ctrl_latch.get_pin("sync_in[{0}]".format(i%2)).uc()
            pos2 = vector(pos1.x, self.ctrl_latch.uy()+(i%2+1)*self.m_pitch("m1"))
            pos3 = vector(self.addr_latch.rx()+(i%2+10+self.addr_size)*self.m_pitch("m1"), pos2.y)
            pos4 = vector(pos3.x, y_off)
            pos5 = vector(pos6.x, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])
    
    def route_ctrl_lines(self):
        """ route ctrl lines between sync_interface_ctrl, asyn_sram and latches"""

        ack_xoff=self.interface_ctrl.rx()+(6+self.addr_size)*self.m_pitch("m1")
        rack_xoff = ack_xoff + self.m_pitch("m1")
        dout_en_xoff = ack_xoff + self.m_pitch("m1")
        ctrl_en_xoff = self.interface_ctrl.rx()+2*self.m_pitch("m1")
        din_en_xoff = ctrl_en_xoff + self.m_pitch("m1")
        din_enb_xoff = din_en_xoff + self.m_pitch("m1")
        
        # route ack between sram and sync_interface_ctrl
        if (self.branch_factors[1] == 1 or self.branch_factors[0] != 1):
            y_off = self.sram_inst.get_pin("ack").lc().y
            pos5 = self.sram_inst.get_pin("ack").lc()
        else:    
            y_off = min (self.sram_inst.get_pin("addr[0]").by()-(self.addr_size+3)*self.m_pitch("m1"), 
                         self.din_latch.by()-(2*self.word_size+4+self.addr_size)*self.m_pitch("m1"))
            pos5 = self.sram_inst.get_pin("ack").uc()
        
        pos1 = self.interface_ctrl.get_pin("ack").lc()
        pos2 = vector(ack_xoff, pos1.y)
        pos3= vector(pos2.x, y_off)
        pos4 = vector(pos5.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])

        # route rack between sram and sync_interface_ctrl
        if (self.branch_factors[1] == 1 or self.branch_factors[0] != 1): 
            y_off = self.sram_inst.get_pin("rack").lc().y
            pos6 = self.sram_inst.get_pin("rack").lc()
        else:    
            y_off = min (self.sram_inst.get_pin("addr[0]").by()-(self.addr_size+4)*self.m_pitch("m1"), 
                         self.din_latch.by()-(2*self.word_size+5+self.addr_size)*self.m_pitch("m1"))
            pos6 = self.sram_inst.get_pin("rack").uc()
        pos1 = self.interface_ctrl.get_pin("rack").lc()
        pos3 = vector(rack_xoff, pos1.y)
        pos4= vector(pos3.x, y_off)
        pos5 = vector(pos6.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos3, pos4, pos5, pos6])

        # route ctrl_en between ctrl_latch and sync_interface_ctrl
        pos1 = self.interface_ctrl.get_pin("ctrl_en").lc()
        pos2 = vector(ctrl_en_xoff, pos1.y)
        pos4 = self.ctrl_latch.get_pin("en").lc()
        pos3 = vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

        if self.branch_factors[1] == 1: 
            y_off =  self.din_latch.by()-8*self.m_pitch("m2")
        else:    
            y_off = min(self.sram_inst.get_pin("addr[0]").by()-3*self.m_pitch("m2"), 
                        self.din_latch.by()-3*self.m_pitch("m2"))

        # route din_en between addr_latch, din_latch and sync_interface_ctrl
        pos1 = self.interface_ctrl.get_pin("din_en").lc()
        pos2 = vector(din_en_xoff, pos1.y)
        pos3 = vector(pos2.x, self.addr_latch.by()-2*self.m_pitch("m1"))
        pos5 = self.addr_latch.get_pin("en").uc()
        pos4 = vector(pos5.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
        
        pos1 = self.addr_latch.get_pin("en").uc()
        pos2 = vector(pos1.x, y_off)
        pos4 = self.din_latch.get_pin("en").uc()
        pos3 = vector(pos4.x, pos2.y)
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])

        # route din_en_b between addr_latch, din_latch and sync_interface_ctrl
        pos1 = self.interface_ctrl.get_pin("din_en_b").lc()
        pos2 = vector(din_enb_xoff, pos1.y)
        pos3 = vector(pos2.x, self.addr_latch.by()-3*self.m_pitch("m1"))
        pos5 = self.addr_latch.get_pin("en_b").uc()
        pos4 = vector(pos5.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])

        pos1 = self.addr_latch.get_pin("en_b").uc()
        pos2 = vector(pos1.x, y_off-self.m_pitch("m2"))
        pos4 = self.din_latch.get_pin("en_b").uc()
        pos3 = vector(pos4.x, pos2.y)
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])
        
        off=(pos4.x-0.5*contact.m2m3.width, pos4.y-self.via_shift("v1")-self.metal3_enclosure_via2)
        self.add_via(self.m2_stack,off )
        
        off=(pos1.x-0.5*contact.m2m3.width, pos1.y-self.via_shift("v1")-self.metal3_enclosure_via2)
        self.add_via(self.m2_stack,off )

        # route dout_en between dout_latch and sync_interface_ctrl
        pin1 = ["rack", "rack_b"]
        pin2 = ["rack", "rack_b"]
        
        if self.branch_factors[1] == 1: 
            y_off =  self.din_latch.by()
        else:    
            y_off = min (self.sram_inst.get_pin("addr[0]").by()-self.m_pitch("m2"), 
                         self.din_latch.by()-self.m_pitch("m1"))
        for i in range(2):
            pos1 = self.interface_ctrl.get_pin(pin1[i]).lc()
            pos2 = vector(dout_en_xoff+ i*self.m_pitch("m1"), pos1.y)
            pos3 = vector(pos2.x, y_off-i*self.m_pitch("m2"))
            pos4 = vector(self.dout_latch.lx()-(2*self.word_size+3+i)*self.m_pitch("m1"), pos3.y)
            pos5 = vector(pos4.x, self.dout_latch.by() - (i+1)*self.m_pitch("m2"))
            pos7 = self.dout_latch.get_pin(pin2[i]).uc()
            pos6 = vector(pos7.x, pos5.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_wire(self.m2_rev_stack, [pos2, pos3, pos4, pos5, pos6, pos7])
            
            if self.dout_latch.get_pin(pin2[i]).layer == self.m3_pin_layer:
                off=(pos7.x-0.5*contact.m2m3.width, pos7.y-self.via_shift("v1")-self.metal3_enclosure_via2)
                self.add_via(self.m2_stack, off)

    def route_clk(self):
        """ route clk between sync_interface_ctrl and latches"""
        
        # route from sync_interface_ctrl to ctrl_latch
        pos1 = self.interface_ctrl.get_pin("clk").uc()
        pos3 = self.ctrl_latch.get_pin("clk").lc()
        pos2 = vector(pos1.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        
        off=self.interface_ctrl.get_pin("clk").ur()-vector(0, contact.m1m2.width)
        self.add_via(self.m1_stack, off, rotate=90)

        # route from sync_interface_ctrl to addr_latch
        pos1 = self.interface_ctrl.get_pin("clk").uc()
        pos2 = vector(pos1.x, self.addr_latch.by()-self.m_pitch("m1"))
        pos4 = self.addr_latch.get_pin("clk").uc()
        pos3 = vector(pos4.x, pos2.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

        # route from sync_interface_ctrl to ctrl_latch
        pos1 = self.interface_ctrl.get_pin("clk_b").lc()
        pos2 = vector(self.interface_ctrl.rx()+5*self.m_pitch("m1"), pos1.y)
        pos3 = vector(pos2.x, self.addr_latch.by()-4*self.m_pitch("m1"))
        pos5 = self.addr_latch.get_pin("clk_b").uc()
        pos4 = vector(pos5.x, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])

        if self.branch_factors[1] == 1: 
            y_off = self.din_latch.by()-10*self.m_pitch("m2")
        else:    
            y_off = min(self.sram_inst.get_pin("addr[0]").by()-5*self.m_pitch("m2"), 
                        self.din_latch.by()-5*self.m_pitch("m2"))

        # route clk from addr_latch to din_latch
        pos1 = self.addr_latch.get_pin("clk").uc()
        pos2 = vector(pos1.x, y_off)
        pos4 = self.din_latch.get_pin("clk").uc()
        pos3 = vector(pos4.x, pos2.y)
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])

        # route clk_b from addr_latch to din_latch
        pos1 = self.addr_latch.get_pin("clk_b").uc()
        pos2 = vector(pos1.x, y_off-self.m_pitch("m2"))
        pos4 = self.din_latch.get_pin("clk_b").uc()
        pos3 = vector(pos4.x, pos2.y)
        self.add_wire(self.m2_rev_stack, [pos1, pos2, pos3, pos4])
        
        off=(pos4.x-0.5*contact.m2m3.width,pos4.y-self.via_shift("v1")-self.metal3_enclosure_via2)
        self.add_via(self.m2_stack, off)
        
        off=(pos1.x-0.5*contact.m2m3.width, pos1.y-self.via_shift("v1")-self.metal3_enclosure_via2)
        self.add_via(self.m2_stack, off)

    def route_power_lines(self):
        """ route ctrl lines between sync_interface_ctrl, asyn_sram and latches"""
        
        # route vdd and gnd between sram and sync interface pieces
        power_pins = ["vdd", "gnd"]
        for i in range(2):
            pin_list=[]
            for pin in self.din_latch.get_pins(power_pins[i]):
                pin_list.append(pin)
            for pin in self.dout_latch.get_pins(power_pins[i]):
                pin_list.append(pin)

            for pin in pin_list:
                pos1 = pin.lc()
                pos2 = vector(self.din_latch.lx()-i*self.m_pitch("m1"), pos1.y)
                pos4 = self.sram_inst.get_pin(power_pins[i]).lc()
                pos3 = vector(pos2.x, pos4.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

            pin_list=[]
            for pin in self.addr_latch.get_pins(power_pins[i]):
                pin_list.append(pin)
            for pin in self.interface_ctrl.get_pins(power_pins[i]):
                pin_list.append(pin)
            for pin in self.ctrl_latch.get_pins(power_pins[i]):
                pin_list.append(pin)

            for pin in pin_list:
                pos1 = pin.lc()
                pos2 = vector(self.addr_latch.rx()+i*self.m_pitch("m1"), pos1.y)
                pos4 = self.sram_inst.get_pin(power_pins[i]).lc()
                pos3 = vector(pos2.x, pos4.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
    
    def add_layout_pins(self):
        """ Add final data, addr, ctrl and power synchronous pins """

        for i in range(self.word_size):
            pin_off = self.din_latch.get_pin("async_din[{0}]".format(i)).lr()-vector(self.m1_width, 0)
            self.add_layout_pin(text="data_in[{0}]".format(i),
                                layer=self.m1_pin_layer,
                                offset=pin_off,
                                width=self.m1_width,
                                height=self.m1_width)

        for i in range(self.word_size):
            pin_off = self.dout_latch.get_pin("sync_dout[{0}]".format(i)).lr()-vector(self.m1_width, 0)
            self.add_layout_pin(text="data_out[{0}]".format(i),
                                layer=self.m1_pin_layer,
                                offset=pin_off,
                                width=self.m1_width,
                                height=self.m1_width)

        for i in range(self.addr_size):
            pin_off = self.addr_latch.get_pin("async_din[{0}]".format(i)).ll()
            self.add_layout_pin(text="addr[{0}]".format(i),
                                layer=self.m1_pin_layer,
                                offset=pin_off,
                                width=self.m1_width,
                                height=self.m1_width)

        ctrl_pins = ["r", "w"]
        for i in range(2):
            pin_off = self.ctrl_latch.get_pin("async_in[{0}]".format(i)).ul()-vector(0, self.m1_width)
            self.add_layout_pin(text=ctrl_pins[i],
                                layer=self.m2_pin_layer,
                                offset=pin_off,
                                width=self.m2_width,
                                height=self.m2_width)

        ctrl_pins = ["clk", "en"]
        for i in range(2):
            pin_off = self.interface_ctrl.get_pin(ctrl_pins[i]).ll()
            self.add_layout_pin(text=ctrl_pins[i],
                                layer=self.m1_pin_layer,
                                offset=pin_off,
                                width=self.m1_width,
                                height=self.m1_width)

        power_pins = ["vdd", "gnd", "reset"]
        for i in range(3):
            pin_off = self.sram_inst.get_pin(power_pins[i])
            self.add_layout_pin(text=power_pins[i],
                                layer=pin_off.layer,
                                offset=pin_off.ll(),
                                width=self.m1_width,
                                height=self.m1_width)
    
    def sp_write(self, sp_name):
        """ Write the entire spice of the object to the file """
        sp = open(sp_name, 'w')

        sp.write("**************************************************\n")
        sp.write("* AMC generated memory.\n")
        sp.write("* Number of Words: {}\n".format(self.total_bits/self.word_size))
        sp.write("* Word Size: {}\n".format(self.word_size))
        sp.write("* Number of Banks: {}\n".format(self.num_inbanks*self.num_outbanks))
        sp.write("**************************************************\n")        
        usedMODS = list()
        self.sp_write_file(sp, usedMODS)
        del usedMODS
        sp.close()


    def save_output(self):
        """ Save all the output files while reporting time to do it as well. """

        # Save the standar spice file
        start_time = datetime.datetime.now()
        spname = OPTS.output_path + self.name + ".sp"
        print("\n SP: Writing to {0}".format(spname))
        self.sp_write(spname)
        print_time("Spice writing", datetime.datetime.now(), start_time)

        # Save the extracted spice file if requested
        if OPTS.use_pex:
            start_time = datetime.datetime.now()
            sp_file = OPTS.output_path + "temp_pex.sp"
            calibre.run_pex(self.name, gdsname, spname, output=sp_file)
            print_time("Extraction", datetime.datetime.now(), start_time)
        else:
            # Use generated spice file for characterization
            sp_file = spname
        
        # Write the layout
        start_time = datetime.datetime.now()
        gdsname = OPTS.output_path + self.name + ".gds"
        print("\n GDS: Writing to {0}".format(gdsname))
        self.gds_write(gdsname)
        print_time("GDS", datetime.datetime.now(), start_time)

        # Create a LEF physical model
        start_time = datetime.datetime.now()
        lefname = OPTS.output_path + self.name + ".lef"
        print("\n LEF: Writing to {0}".format(lefname))
        self.lef_write(lefname)
        print_time("LEF", datetime.datetime.now(), start_time)

        # Write a verilog model
        start_time = datetime.datetime.now()
        vname = OPTS.output_path + self.name + ".v"
        print("\n Verilog: Writing to {0}".format(vname))
        self.verilog_write(vname)
        print_time("Verilog", datetime.datetime.now(), start_time)
        
        # Characterize the design
        if OPTS.characterize:
            start_time = datetime.datetime.now()        
            from characterizer import lib
            print("\n LIB: Characterizing... ")
            if OPTS.spice_name!="":
                print("Performing simulation-based characterization with {}".format(OPTS.spice_name))
            if OPTS.trim_netlist:
                print("Trimming netlist to speed up characterization.")
            lib.lib(out_dir=OPTS.output_path, sram=self)
            print_time("Characterization", datetime.datetime.now(), start_time)
