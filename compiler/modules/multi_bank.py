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


import sys
import getpass
import design
import debug
import contact
from math import log
from vector import vector
from bank import bank
from split_array import split_array
from merge_array import merge_array
from split_merge_control import split_merge_control

class multi_bank(design.design):
    """ Dynamically generated multi bank (1, 2 or 4) asynchronous SRAM with split and merge arrays"""

    def __init__(self, word_size, words_per_row, num_rows, num_subanks, num_banks, orientation, 
                 two_level_bank, name):
        design.design.__init__(self, name)

        self.w_size= word_size
        self.w_per_row= words_per_row
        self.num_rows= num_rows
        self.num_subanks= num_subanks
        self.num_banks= num_banks
        
        # banks can be stacked or placed in an horizontal direction (set to "H" or "V")
        self.orien= orientation

        # If two_level_bank, second level of split and merge cells will be added
        self.two_level_bank= two_level_bank
        
        self.compute_sizes()
        self.add_pins()
        self.create_layout()
        self.offset_all_coordinates()

    def compute_sizes(self):
        """ Compute the address sizes """
        
        self.row_addr_size= int(log(self.num_rows, 2))
        self.col_addr_size= int(log(self.num_subanks, 2))
        self.column_mux_addr_size= int(log(self.w_per_row, 2))
        self.bank_addr_size= self.col_addr_size + self.row_addr_size + self.column_mux_addr_size
        self.addr_size= self.bank_addr_size + int(log(self.num_banks, 2))
        
    def add_pins(self):
        """ Add pins for multi-bank, order of the pins is important """

        for i in range(self.w_size):
            self.add_pin("din[{0}]".format(i))
        for i in range(self.w_size):
            self.add_pin("dout[{0}]".format(i))
        for i in range(self.addr_size):
            self.add_pin("addr[{0}]".format(i))
        self.add_pin_list(["reset","r","w","rw","ack","rack","rreq","wreq","wack"])
        if (self.num_banks > 1 and self.two_level_bank):
            self.add_pin_list(["S","ack_merge","rw_en1_S","rw_en2_S","Mack_S","Mrack_S", "Mwack_S"])
        self.add_pin_list(["vdd", "gnd"])

    def create_layout(self):
        """ Layout creation """
        
        self.create_modules()

        if self.num_banks == 1:
            self.add_single_bank_modules()
        elif self.num_banks == 2:
            self.add_two_bank_modules()
            if self.two_level_bank:
                self.create_split_merge()
        elif self.num_banks == 4:
            self.add_four_bank_modules()
            if self.two_level_bank:
                self.create_split_merge()
        else:
            debug.error("Invalid number of banks! only 1, 2 and 4 banks are allowed :)",-1)

    def create_split_merge(self):
        """ Create and routes the outter (second-level) split and merge modules """

        self.add_split_merge_cells()
        self.route_data_split_merge()
        self.route_addr_ctrl_split_merge()
        self.route_split_cells_powers_and_selects()

    def create_modules(self):
        """ Create all the modules that will be used """

        # Create the bank module (up to four are instantiated)
        # With only one bank, there is no split and merge, hence, two_level is off
        if self.num_banks ==1:
            two_level_bank=False  
        else:
            two_level_bank=True
        self.bank= bank(word_size=self.w_size, words_per_row=self.w_per_row,
                        num_rows=self.num_rows, num_subanks=self.num_subanks, 
                        two_level_bank=two_level_bank, name="bank")
        self.add_mod(self.bank)

        if self.num_banks >1:
            self.sp_mrg_ctrl= split_merge_control(num_banks=self.num_banks)
            self.add_mod(self.sp_mrg_ctrl)

        if self.two_level_bank:
            self.dsplit_ary= split_array(name="outter_data_split_array", 
                                         word_size=self.w_size, 
                                         words_per_row=self.w_per_row)
            self.add_mod(self.dsplit_ary)

            self.dmerge_ary= merge_array(name="outter_data_merge_array", 
                                         word_size=self.w_size, 
                                         words_per_row=self.w_per_row)
            self.add_mod(self.dmerge_ary)
        
            self.addr_split_ary= split_array(name="outter_addr_split_array", 
                                             word_size=self.addr_size, 
                                             words_per_row=1)
            self.add_mod(self.addr_split_ary)

            # 5: R, W, RW, WREQ, RREQ
            self.ctrl_split_ary= split_array(name="outter_ctrl_split_array", 
                                             word_size=5, 
                                             words_per_row=1)
            self.add_mod(self.ctrl_split_ary)


            self.ctrl_mrg_cell= merge_array(name="outter_ctrl_merge_cell", 
                                            word_size=1, 
                                            words_per_row=1)
            self.add_mod(self.ctrl_mrg_cell)


    def add_bank(self, bank_num, position, x_flip, y_flip):
        """ Place a bank at the given position with orientations """

        # x_flip ==  1 --> no flip in x_axis
        # x_flip == -1 --> flip in x_axis
        # y_flip ==  1 --> no flip in y_axis
        # y_flip == -1 --> flip in y_axis

        # x_flip and y_flip are used for position translation

        if x_flip == -1 and y_flip == -1:
            bank_rotation= 180
        else:
            bank_rotation= 0

        if x_flip == y_flip:
            bank_mirror= "R0"
        elif x_flip == -1:
            bank_mirror= "MX"
        elif y_flip == -1:
            bank_mirror= "MY"
        else:
            bank_mirror= "R0"
            
        bank_inst=self.add_inst(name="bank{0}".format(bank_num),
                                mod=self.bank,
                                offset=position,
                                mirror=bank_mirror,
                                rotate=bank_rotation)
        temp= []
        if (self.num_banks > 1 and self.two_level_bank):
            for i in range(self.num_subanks):
                for j in range(self.w_size):
                    temp.append("din_split[{0}]".format(j))
            for i in range(self.num_subanks):
                for j in range(self.w_size):
                    temp.append("dout_merge[{0}]".format(j))
            for i in range(self.bank_addr_size):
                temp.append("addr_split[{0}]".format(i))
        else:
            for i in range(self.num_subanks):
                for j in range(self.w_size):
                    temp.append("din[{0}]".format(j))
            for i in range(self.num_subanks):
                for j in range(self.w_size):
                    temp.append("dout[{0}]".format(j))
            for i in range(self.bank_addr_size):
                temp.append("addr[{0}]".format(i))
        
        if self.num_banks ==1:
            temp.extend(["reset", "r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"])
        
        if (self.num_banks > 1 and not self.two_level_bank):
            temp.extend(["reset", "r", "w", "rw", "pre_ack", "pre_rack", "rreq", "wreq", "pre_wack"])
            temp.extend(["sel[{0}]".format(bank_num), "ack{0}".format(bank_num)]) 
            temp.extend(["ack_b{0}".format(bank_num), "ack_b", "rw_merge", "rreq", "wreq"])
        
        if (self.num_banks > 1 and self.two_level_bank):
            temp.extend(["reset", "r_split", "w_split", "rw_split", "pre_ack", "pre_rack"])
            temp.extend(["rreq_split", "wreq_split", "pre_wack", "sel[{0}]".format(bank_num)])
            temp.extend(["ack{0}".format(bank_num), "ack_b{0}".format(bank_num), "ack_b"])
            temp.extend(["rw_merge", "rreq_split", "wreq_split"])

        temp.extend(["vdd", "gnd"])
        self.connect_inst(temp)
        return bank_inst

    def compute_bus_sizes(self):
        """ Compute the independent bus widths shared between two and four bank SRAMs """
        
        #8 : ("r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack")
        self.control_size= 8
        
        #5:("Mrack","rreq_b","Mwack","Mack","rw_merge") + "ack0:3_b", "wack0:3_b", "ack0:3", "wack0:3"
        self.merge_split_size= 5+ 2*self.num_banks
        
        # Vertical address + control + merge_split + one-hot bank select + reset+ vdd + gnd + S bus
        self.num_v_line= self.addr_size + self.control_size + self.merge_split_size+ self.num_banks+4
        self.v_bus_width= self.m_pitch("m1")*self.num_v_line
        self.bnk_to_bus_gap= 2*self.m3_width
        self.bnk_to_bnk_gap= 2*self.m3_width
        
        # Horizontal data bus size ( input and output data)
        self.num_h_line= self.w_size
        self.data_bus_height= self.m_pitch("m1")*self.num_h_line
        
        if self.orien == "H":
            self.data_bus_width= 2*(self.bank.width + self.bnk_to_bus_gap)+ self.sp_mrg_ctrl.height
        if self.orien == "V":
            self.data_bus_width= self.bank.width + self.bnk_to_bus_gap+ \
                                  max(self.sp_mrg_ctrl.height, 2*self.w_size*self.m_pitch("m1"))
            if self.num_banks == 4:
                if ((2*self.w_size+2)*self.m_pitch("m1")>self.sp_mrg_ctrl.height-self.v_bus_width) :
                    self.data_bus_width= self.data_bus_width+ (2*self.w_size+2)*self.m_pitch("m1")-\
                                         self.sp_mrg_ctrl.height+self.v_bus_width
        
        self.power_rail_height= self.m1_width
        self.pow_rail_pitch= self.m_pitch("m1")
        self.power_rail_width= self.data_bus_width

    def add_single_bank_modules(self):
        """ Adds a single bank SRAM """
        
        # No orientation or offset
        self.bank_inst= self.add_bank(0, [0, 0], 1, 1)
        self.add_single_bank_pins()
        self.width= self.bank.width
        self.height= self.bank.height

    def add_two_bank_modules(self):
        """ Adds the moduels and the buses for a two bank SRAM. """
        
        self.compute_two_bank_offsets()
        self.add_two_banks()
        self.add_busses()
        self.route_banks()
    
    def add_four_bank_modules(self):
        """ Adds the modules and the buses for a four bank SRAM. """

        self.compute_four_bank_offsets()
        self.add_four_banks()
        self.add_busses()
        self.route_banks()
    
    def compute_two_bank_offsets(self):
        """ Compute the overall offsets for a two bank SRAM buses"""

        self.compute_bus_sizes()
        #Find the location of ack_merge which is the last pin in ctrl logic of bank
        self.bank_ack_mrg_off=self.bank.get_pin("ack_merge").by() + self.m_pitch("m1")
        
        if (self.sp_mrg_ctrl.height >= self.v_bus_width):
            v_off =abs(self.sp_mrg_ctrl.height-self.v_bus_width)

        else:
            v_off= 0

        if self.orien == "H":
            self.v_bus_height= self.bank_ack_mrg_off + self.bnk_to_bus_gap + \
                               2*(self.data_bus_height+self.pow_rail_pitch)+self.m_pitch("m1")
            self.din1_bus_off= vector(0, 2*self.pow_rail_pitch)
            self.v_bus_off= vector(self.bank.width+self.bnk_to_bus_gap+v_off, 0)
            self.pow_rail_1_off= vector(0, 0)
        
        if self.orien == "V":
            self.v_bus_height= self.bank_ack_mrg_off+ self.bank.height + \
                                2*(self.bnk_to_bus_gap + self.data_bus_height + \
                                self.pow_rail_pitch + self.m_pitch("m1"))
            self.din1_bus_off= vector(-v_off, self.bank.height+self.bnk_to_bus_gap+\
                                      2*self.pow_rail_pitch)
            self.v_bus_off= vector(0,0)
            self.pow_rail_1_off= vector(-v_off, self.bank.height+self.bnk_to_bus_gap)
        
        self.reset_off= self.v_bus_off
        self.addr_bus1_off=  self.reset_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.S_off= self.addr_bus1_off.scale(1,0) +vector(self.bank_addr_size*self.m_pitch("m1"),0)
        self.gnd_off= self.S_off.scale(1,0) +vector(self.m_pitch("m1"),0)
        self.vdd_off= self.gnd_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.sel_bus_off= self.vdd_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.addr_bus2_off= self.sel_bus_off.scale(1,0) + vector(self.num_banks*self.m_pitch("m1"),0)
        self.spl_mrg_ctrl_bus_off=  self.addr_bus2_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.spl_mrg_in_off= self.spl_mrg_ctrl_bus_off.scale(1,0) + vector(5*self.m_pitch("m1"),0)
        self.ctrl_bus_off= self.spl_mrg_in_off.scale(1,0) + \
                            vector(2*self.m_pitch("m1")*self.num_banks,0)
        self.dout1_bus_off= vector(self.din1_bus_off.x,self.din1_bus_off.y + self.data_bus_height)

    def compute_four_bank_offsets(self):
        """ Compute the overall offsets for a four bank SRAM """
        
        self.compute_bus_sizes()
        #Find the location of ack_merge which is the last pin in ctrl logic of bank
        self.bank_ack_mrg_off=self.bank.get_pin("ack_merge").by() + self.m_pitch("m1")

        if (self.sp_mrg_ctrl.height >= self.v_bus_width):
            v_off =abs(self.sp_mrg_ctrl.height-self.v_bus_width)
        else:
            v_off= 0
        
        if self.orien == "H":
            self.v_bus_height= self.bank_ack_mrg_off+self.bank.height + \
                                2*(self.bnk_to_bus_gap + self.data_bus_height + \
                                self.pow_rail_pitch + self.m_pitch("m1")) 
            self.pow_rail_1_off= vector(0, self.bank.height + self.bnk_to_bus_gap)
            self.din1_bus_off= vector(0, self.pow_rail_1_off.y + 2*self.pow_rail_pitch)
            self.dout1_bus_off= vector(0, self.din1_bus_off.y + self.data_bus_height)
            self.v_bus_off= vector(self.bank.width+self.bnk_to_bus_gap+v_off,0)
            
        if self.orien == "V":
            if ((2*self.w_size+2)*self.m_pitch("m1")>self.sp_mrg_ctrl.height-self.v_bus_width):
                v_off = v_off + (2*self.w_size+2)*self.m_pitch("m1")-self.sp_mrg_ctrl.height+self.v_bus_width

            self.v_bus_height =self.bank_ack_mrg_off+ 3*self.bank.height + \
                               4*(self.bnk_to_bus_gap + self.data_bus_height + \
                               self.pow_rail_pitch + self.m_pitch("m1") ) + self.bnk_to_bnk_gap
            self.pow_rail_1_off= vector(-v_off,self.bank.height + self.bnk_to_bus_gap)
            self.din1_bus_off= vector(-v_off,self.pow_rail_1_off.y + 2*self.pow_rail_pitch)
            self.dout1_bus_off= vector(-v_off,self.din1_bus_off.y + self.data_bus_height)
            self.pow_rail_2_off= vector(-v_off,3*(self.bank.height + self.bnk_to_bus_gap) +\
                                 self.bnk_to_bnk_gap + 2*(self.data_bus_height +self.pow_rail_pitch))
            self.din2_bus_off= vector(-v_off,self.pow_rail_2_off.y + 2*self.pow_rail_pitch)
            self.dout2_bus_off= vector(-v_off,self.din2_bus_off.y + self.data_bus_height)
            self.v_bus_off= vector(0, 0)

        self.reset_off= self.v_bus_off
        self.addr_bus1_off= self.reset_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.S_off= self.addr_bus1_off.scale(1,0) +vector(self.bank_addr_size*self.m_pitch("m1"),0)
        self.gnd_off= self.S_off.scale(1,0) +vector(self.m_pitch("m1"),0)
        self.vdd_off= self.gnd_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.sel_bus_off= self.vdd_off.scale(1,0) + vector(self.m_pitch("m1"),0)
        self.addr_bus2_off= self.sel_bus_off.scale(1,0) + vector(self.num_banks*self.m_pitch("m1"),0)
        self.spl_mrg_ctrl_bus_off= self.addr_bus2_off.scale(1,0) + vector(2*self.m_pitch("m1"),0)
        self.spl_mrg_in_off= self.spl_mrg_ctrl_bus_off.scale(1,0) + vector(5*self.m_pitch("m1"),0)
        self.ctrl_bus_off=self.spl_mrg_in_off.scale(1,0)+vector(2*self.m_pitch("m1")*self.num_banks,0)

    def add_two_banks(self):
        
        if self.orien == "H":
            # Placement of bank 0 (left)
            self.bank_pos_1= vector(self.bank.width, 2*self.data_bus_height + \
                                    self.bnk_to_bus_gap+ 2*self.pow_rail_pitch)
            self.bank_inst=[self.add_bank(1, self.bank_pos_1, 1, -1)]

            # Placement of bank 1 (right)
            x_off= self.bank.width+max(self.sp_mrg_ctrl.height,self.v_bus_width)+2*self.bnk_to_bus_gap
            self.bank_pos_0= vector(x_off, self.bank_pos_1.y)
            self.bank_inst.append(self.add_bank(0, self.bank_pos_0, 1, 1))
            self.width= self.bank_inst[1].rx() + self.m_pitch("m1")

        if self.orien == "V":
            # Placement of bank 0 (bottom)
            x_off= self.v_bus_width + self.bnk_to_bus_gap
            self.bank_pos_0= vector(x_off,self.bank.height)
            self.bank_inst=[self.add_bank(0, self.bank_pos_0, -1, 1)]

            # Placement of bank 1 (top)
            y_off= self.bank.height +2*(self.data_bus_height+self.bnk_to_bus_gap+self.pow_rail_pitch)
            self.bank_pos_1= vector(self.bank_pos_0.x, y_off)
            self.bank_inst.append(self.add_bank(1, self.bank_pos_1, 1, 1))

            if (self.sp_mrg_ctrl.height >= self.v_bus_width):
                self.width= self.bank_inst[1].rx() + (self.sp_mrg_ctrl.height-self.v_bus_width) + \
                            self.m_pitch("m1")
                
            else:
                self.width= self.bank_inst[1].rx() + self.m_pitch("m1")
            

        sp_mrg_ctrl_off= vector(self.v_bus_off.x+self.v_bus_width -contact.m1m2.height,
                                self.v_bus_off.y+ self.v_bus_height-self.m1_width)
        # Rotate 90, to pitch-patch in and outs and also poly-silicon goes in one direction
        self.sp_mrg_ctrl_inst= self.add_inst(name="split_merge_control", 
                                              mod=self.sp_mrg_ctrl, 
                                              offset=sp_mrg_ctrl_off,
                                              mirror= "R0",
                                              rotate= 90)
        temp =[]
        if self.two_level_bank:
            temp.extend(["r_split","w_split","rw_split","ack_merge","rack_merge",
                         "rreq_split","wreq_split","wack_merge"])
        else:
            temp.extend(["r","w","rw","ack","rack","rreq","wreq","wack"])
        for i in range(self.num_banks):
            temp.extend(["ack{0}".format(i), "ack_b{0}".format(i)])
        temp.extend(["pre_ack", "pre_wack", "pre_rack", "rw_merge"])        
        if self.two_level_bank:
            temp.extend(["ack_b", "addr_split[{0}]".format(self.addr_size-1)])
        else:
            temp.extend(["ack_b", "addr[{0}]".format(self.addr_size-1)])
        
        if self.two_level_bank:
            temp.extend(["sel[0]", "sel[1]", "S", "vdd", "gnd"])
        else:
            temp.extend(["sel[0]", "sel[1]", "vdd", "vdd", "gnd"])
        
        self.connect_inst(temp)
        
        self.height= max(self.bank_inst[1].uy(), self.sp_mrg_ctrl_inst.uy())

    def add_four_banks(self):
        """ Adds four banks based on orientation """
        
        if self.orien == "H":
            # Placement of bank 3 (upper left)
            self.bank_pos_3= vector(self.bank.width,self.bank.height + 2*self.data_bus_height + \
                                     2*self.bnk_to_bus_gap + 2*self.pow_rail_pitch)
            self.bank_inst=[self.add_bank(3, self.bank_pos_3, 1, -1)]
            
            # Placement of bank 2 (upper right)
            x_off= self.bank.width+max(self.sp_mrg_ctrl.height,self.v_bus_width)+2*self.bnk_to_bus_gap
            self.bank_pos_2= vector(x_off, self.bank_pos_3.y)
            self.bank_inst.append(self.add_bank(2, self.bank_pos_2, 1, 1))

            # Placement of bank 1 (bottom left)
            y_off= self.bank.height
            self.bank_pos_1= vector(self.bank_pos_3.x, y_off)
            self.bank_inst.append(self.add_bank(1, self.bank_pos_1, -1, -1))

            # Placement of bank 0 (bottom right)
            self.bank_pos_0= vector(self.bank_pos_2.x, self.bank_pos_1.y)
            self.bank_inst.append(self.add_bank(0, self.bank_pos_0, -1, 1))

            self.width= self.bank_inst[1].rx() + self.m_pitch("m1")
        
        if self.orien == "V":
            # Placement of bank 0 (lowest)
            x_off= self.v_bus_width + self.bnk_to_bus_gap
            self.bank_pos_0= vector(x_off,self.bank.height)
            self.bank_inst=[self.add_bank(0, self.bank_pos_0, -1, 1)]

            # Placement of bank 1 
            y_off= self.bank.height + 2*(self.data_bus_height+self.bnk_to_bus_gap+self.pow_rail_pitch)
            self.bank_pos_1= vector(self.bank_pos_0.x, y_off)
            self.bank_inst.append(self.add_bank(1, self.bank_pos_1, 1, 1))

            # Placement of bank 2 
            y_off= 3*self.bank.height+2*(self.data_bus_height + \
                   self.bnk_to_bus_gap + self.pow_rail_pitch) + self.bnk_to_bnk_gap
            self.bank_pos_2= vector(self.bank_pos_0.x, y_off)
            self.bank_inst.append(self.add_bank(2, self.bank_pos_2, -1, 1))

            # Placement of bank 3 (topmost)
            y_off= 3*self.bank.height + 4*(self.data_bus_height + \
                    self.bnk_to_bus_gap + self.pow_rail_pitch) + self.bnk_to_bnk_gap
            self.bank_pos_3= vector(self.bank_pos_0.x, y_off)
            self.bank_inst.append(self.add_bank(3, self.bank_pos_3, 1, 1))

            if (self.sp_mrg_ctrl.height >= self.v_bus_width):
                self.width= self.bank_inst[1].rx()+ self.m_pitch("m1")+\
                           (self.sp_mrg_ctrl.height -self.v_bus_width)
            else:
                self.width= self.bank_inst[1].rx() + self.m_pitch("m1")

            if ((2*self.w_size+1)*self.m_pitch("m1")>(self.sp_mrg_ctrl.height-self.v_bus_width)):
                self.width = self.bank_inst[1].rx() + (2*self.w_size+3)*self.m_pitch("m1")
        
        sp_mrg_ctrl_off= vector(self.v_bus_off.x+self.v_bus_width-contact.m1m2.height,
                                self.v_bus_off.y+ self.v_bus_height-self.m1_width)
        self.sp_mrg_ctrl_inst= self.add_inst(name="split_merge_control", 
                                             mod=self.sp_mrg_ctrl, 
                                             offset=sp_mrg_ctrl_off,
                                             mirror= "R0",
                                             rotate= 90)
        temp =[]
        if self.two_level_bank:
            temp.extend(["r_split","w_split","rw_split","ack_merge","rack_merge",
                         "rreq_split","wreq_split","wack_merge"])
        else:
            temp.extend(["r","w","rw","ack","rack","rreq","wreq","wack"])
        for i in range(self.num_banks):
            temp.extend(["ack{0}".format(i), "ack_b{0}".format(i)])
        temp.extend(["pre_ack", "pre_wack", "pre_rack", "rw_merge"])        
        if self.two_level_bank:
            temp.append("ack_b")
            for i in range(int(log(self.num_banks,2))):
                temp.append("addr_split[{0}]".format(self.addr_size-2+i))
        else:
            temp.append("ack_b")
            for i in range(int(log(self.num_banks,2))):
                temp.append("addr[{0}]".format(self.addr_size-2+i))
        for i in range(self.num_banks):
            temp.append("sel[{0}]".format(i))

        if self.two_level_bank:
            temp.extend(["S", "vdd", "gnd"])
        else:
            temp.extend(["vdd", "vdd", "gnd"])
        self.connect_inst(temp)
        
        if self.orien == "H":
            self.height= max(self.bank_inst[1].uy(), self.sp_mrg_ctrl_inst.uy())
        
        if self.orien == "V":
            self.height= max(self.bank_inst[3].uy(), self.sp_mrg_ctrl_inst.uy())
        
    def add_single_bank_pins(self):
        """ Add the ctrl, addr bus, Data_in and Data_out buses and power rails. """

        # Vertical bus
        ctrl_pins= ["reset","r","w","rw","ack","rack","rreq","wreq","wack"]
        for i in range(len(ctrl_pins)):
            self.add_layout_pin(text=ctrl_pins[i],
                                layer= self.m1_pin_layer,
                                offset= self.bank_inst.get_pin(ctrl_pins[i]).ll(),
                                width= self.m1_width,
                                height= self.m1_width)
        for i in range(self.addr_size):
            self.add_layout_pin(text="addr[{0}]".format(i),
                                layer= self.m1_pin_layer,
                                offset= self.bank_inst.get_pin("addr[{0}]".format(i)).ll(),
                                width= self.m1_width,
                                height= self.m1_width)

        for i in range(self.w_size):
            yoff= self.bank_inst.get_pin("din[0][0]").by()-(i+4)*self.m_pitch("m1")
            self.add_rect(layer= "metal1", 
                          offset= (0, yoff), 
                          width= self.bank_inst.width, 
                          height= self.m1_width)
            self.add_layout_pin(text="din[{0}]".format(i),
                                layer= self.m1_pin_layer,
                                offset= (0, yoff),
                                width= self.m1_width,
                                height= self.m1_width)

            for j in range(self.num_subanks):
                pin= self.bank_inst.get_pin("din[{0}][{1}]".format(j, i)).ll()
                offset= vector(pin.x, pin.y-(i+4)*self.m_pitch("m1"))
                self.add_rect(layer= "metal2", 
                              offset= (offset.x, offset.y), 
                              width= self.m2_width, 
                              height= (i+4)*self.m_pitch("m1"))
                self.add_via(self.m1_stack,(offset.x, offset.y-self.via_shift("v1")))
            
        for i in range(self.w_size):
            yoff= self.bank_inst.get_pin("dout[0][0]").by()-(i+4+self.w_size)*self.m_pitch("m1")
            self.add_rect(layer= "metal1", 
                          offset= (0, yoff), 
                          width= self.bank_inst.width, 
                          height= self.m1_width)
            self.add_layout_pin(text="dout[{0}]".format(i),
                                layer= self.m1_pin_layer,
                                offset= (0, yoff),
                                width= self.m1_width,
                                height= self.m1_width)
            for j in range(self.num_subanks):
                pin=self.bank_inst.get_pin("dout[{0}][{1}]".format(j,i)).ll()
                offset= vector(pin.x, pin.y-(i+4+self.w_size)*self.m_pitch("m1"))
                self.add_rect(layer= "metal2", 
                              offset= (offset.x, offset.y), 
                              width= self.m2_width, 
                              height= (i+4+self.w_size)*self.m_pitch("m1"))
                self.add_via(self.m1_stack,(offset.x, offset.y-self.via_shift("v1")))
        
        power_pin= ["vdd", "gnd"]
        for i in range(2):
            yoff = self.bank_inst.get_pins(power_pin[i])[0].by()-(1.5+i)*self.m_pitch("m1")
            self.add_rect(layer= "metal1", 
                          offset= (0, yoff), 
                          width= self.bank_inst.width, 
                          height= self.m1_width)
            self.add_layout_pin(text=power_pin[i],
                                layer= self.m1_pin_layer,
                                offset= (0, yoff),
                                width= self.m1_width,
                                height= self.m1_width)
            for j in range(self.num_subanks+1):
                offset1= self.bank_inst.get_pins(power_pin[i])[j].ll()
                self.add_via(self.m1_stack, (offset1.x, offset1.y-(1.5+i)*self.m_pitch("m1")-self.via_shift("v1")))
                self.add_rect(layer="metal2",
                              offset= (offset1.x, offset1.y-(1.5+i)*self.m_pitch("m1")),
                              width=self.m2_width,
                              height=(1.5+i)*self.m_pitch("m1"))

    def add_busses(self):
        """ Add the horizontal and vertical busses """
        
        # The order of the control signals on the control bus matters
        self.reset_name= ["reset"]
        if self.two_level_bank:
            make_pin= False
        else:
            make_pin= True
        self.v_ctrl_bus_pos= self.create_bus(layer="metal2",
                                             pitch=self.m_pitch("m1"),
                                             offset=self.reset_off,
                                             names=self.reset_name,
                                             length=self.v_bus_height,
                                             vertical=True,
                                             make_pins=make_pin)
        
        if self.two_level_bank:
            addr_bus_names=["addr_split[{0}]".format(i) for i in range(self.bank_addr_size)]
            make_pin= False
        else:
            addr_bus_names=["addr[{0}]".format(i) for i in range(self.bank_addr_size)]
            make_pin= True
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.addr_bus1_off,
                                                   names=addr_bus_names,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=make_pin))
       
        self.select_name= ["S"]
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.S_off,
                                                   names=self.select_name,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=False))


        self.gnd_name= ["gnd"]
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.gnd_off,
                                                   names=self.gnd_name,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=False))

        self.vdd_name= ["vdd"]
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.vdd_off,
                                                   names=self.vdd_name,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=False))

        if self.num_banks == 2:
            sel_bus_names= ["sel[{0}]".format(i) for i in range(self.num_banks)]
        if self.num_banks == 4:
            sel_bus_names= ["sel[{0}]".format(self.num_banks-1-i) for i in range(self.num_banks)]

        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.sel_bus_off,
                                                   names=sel_bus_names,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=False))

        if self.two_level_bank:
            addr_bus_names=["addr_split[{0}]".format(self.addr_size-1-i) for i in range(int(log(self.num_banks,2)))]
            make_pin= False
        else:
            addr_bus_names=["addr[{0}]".format(self.addr_size-1-i) for i in range(int(log(self.num_banks,2)))]
            make_pin= True
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.addr_bus2_off,
                                                   names=addr_bus_names,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=make_pin))
        
        bank_spl_mrg_bus_names= ["pre_wack", "pre_rack", "rw_merge", "pre_ack", "ack_b"]
        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.spl_mrg_ctrl_bus_off,
                                                   names=bank_spl_mrg_bus_names,
                                                   length=self.v_bus_height,
                                                   vertical=True,
                                                   make_pins=False))

        for i in range(self.num_banks):
            self.bank_spl_mrg_input_bus_names= ["ack_b{0}".format(i), "ack{0}".format(i)]
            self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                                       pitch=self.m_pitch("m1"),
                                                       offset=self.spl_mrg_in_off+\
                                                              vector(2*i*self.m_pitch("m1"),0),
                                                       names=self.bank_spl_mrg_input_bus_names,
                                                       length=self.v_bus_height,
                                                       vertical=True,
                                                       make_pins=False))

        if self.two_level_bank:
            ctrl_bus_names=["wack_merge", "wreq_split", "rreq_split", "rack_merge", 
                            "ack_merge", "rw_split", "w_split", "r_split"]
            make_pin= False
        else:
            ctrl_bus_names=["wack", "wreq", "rreq", "rack", "ack", "rw", "w", "r"]
            make_pin= True

        self.v_ctrl_bus_pos.update(self.create_bus(layer="metal2",
                                   pitch=self.m_pitch("m1"),
                                   offset=self.ctrl_bus_off,
                                   names=ctrl_bus_names,
                                   length=self.v_bus_height,
                                   vertical=True,
                                   make_pins=make_pin))

        # Horizontal power rails
        power_rail_names= ["vdd", "gnd"]
        if self.two_level_bank:
            make_pin= False
        else:
            make_pin= True

        power_rail1_pos= self.create_bus(layer="metal1",
                                         pitch=self.m_pitch("m1"),
                                         offset=self.pow_rail_1_off,
                                         names=power_rail_names,
                                         length=self.data_bus_width,
                                         vertical=False,
                                         make_pins=make_pin)
        # Horizontal data bus
        if self.two_level_bank:
            din_bus_names=["din_split[{0}]".format(i) for i in range(self.w_size)]
            make_pin= False
        else:
            din_bus_names=["din[{0}]".format(i) for i in range(self.w_size)]
            make_pin= True

        self.din1_bus_pos= self.create_bus(layer="metal1",
                                           pitch=self.m_pitch("m1"),
                                           offset=self.din1_bus_off,
                                           names=din_bus_names,
                                           length=self.data_bus_width,
                                           vertical=False,
                                           make_pins=make_pin)

        if self.two_level_bank:
            dout_bus_names=["dout_merge[{0}]".format(i) for i in range(self.w_size)]
            make_pin= False
        else:
            dout_bus_names=["dout[{0}]".format(i) for i in range(self.w_size)]
            make_pin= True

        self.dout1_bus_pos= self.create_bus(layer="metal1",
                                            pitch=self.m_pitch("m1"),
                                            offset=self.dout1_bus_off,
                                            names=dout_bus_names,
                                            length=self.data_bus_width,
                                            vertical=False,
                                            make_pins=make_pin)
        if (self.num_banks == 4 and  self.orien == "V"):
            power_rail_names= ["vdd", "gnd"]
            power_rail2_pos= self.create_bus(layer="metal1",
                                             pitch=self.m_pitch("m1"),
                                             offset=self.pow_rail_2_off,
                                             names=power_rail_names,
                                             length=self.data_bus_width,
                                             vertical=False,
                                             make_pins=False)

            if self.two_level_bank:
                din_bus_names=["din_split[{0}]".format(i) for i in range(self.w_size)]
            else:
                din_bus_names=["din[{0}]".format(i) for i in range(self.w_size)]
            self.din2_bus_pos= self.create_bus(layer="metal1",
                                                          pitch=self.m_pitch("m1"),
                                                          offset=self.din2_bus_off,
                                                          names=din_bus_names,
                                                          length=self.data_bus_width,
                                                          vertical=False,
                                                          make_pins=False)
            
            if self.two_level_bank:
                dout_bus_names=["dout_merge[{0}]".format(i) for i in range(self.w_size)]
            else:
                dout_bus_names=["dout[{0}]".format(i) for i in range(self.w_size)]
            self.dout2_bus_pos= self.create_bus(layer="metal1",
                                                pitch=self.m_pitch("m1"),
                                                offset=self.dout2_bus_off,
                                                names=dout_bus_names,
                                                length=self.data_bus_width,
                                                vertical=False,
                                                make_pins=False)

    def route_banks(self):
        """ Connect the inputs and outputs of each bank to horizontal and vertical busses """
        
        # Data Connections
        if (self.num_banks == 2 or self.orien == "H"):
            for k in range(self.num_banks):
                for i in range(self.num_subanks):
                  for j in range(self.w_size):
                      din_off= vector(self.bank_inst[k].get_pin("din[{0}][{1}]".format(i,j)).lx(), 
                                      self.din1_bus_off.y+ j*self.m_pitch("m1") + 0.5*self.m1_width)
                      din_height=  self.bank_inst[k].get_pin("din[{0}][{1}]".format(i,j)).by() -\
                                   self.din1_bus_off.y - j*self.m_pitch("m1")
                      self.add_rect(layer="metal2", 
                                    offset=din_off, 
                                    width=self.m2_width, 
                                    height=din_height)
                      self.add_via(self.m1_stack, (din_off.x, din_off.y-self.via_shift("v1")))
    
                      dout_off= vector(self.bank_inst[k].get_pin("dout[{0}][{1}]".format(i,j)).lx(), 
                                       self.dout1_bus_off.y+ j*self.m_pitch("m1") + 0.5*self.m1_width)
                      dout_height=  self.bank_inst[k].get_pin("dout[{0}][{1}]".format(i,j)).by() -\
                                    self.dout1_bus_off.y - j*self.m_pitch("m1")
                      self.add_rect(layer="metal2", 
                                    offset=dout_off, 
                                    width=self.m2_width, 
                                    height=dout_height)
                      self.add_via(self.m1_stack, (dout_off.x, dout_off.y-self.via_shift("v1")))
        
        if (self.num_banks == 4 and  self.orien == "V"):
            for k in range(self.num_banks):
                for i in range(self.num_subanks):
                  for j in range(self.w_size):
                      self.data_in_bus_off= [self.din1_bus_off.y, self.din2_bus_off.y]
                      self.data_out_bus_off= [self.dout1_bus_off.y, self.dout2_bus_off.y]
                      din_off= vector(self.bank_inst[k].get_pin("din[{0}][{1}]".format(i,j)).lx(), 
                               self.data_in_bus_off[k/2]+ j*self.m_pitch("m1") + 0.5*self.m1_width)
                      din_height=  self.bank_inst[k].get_pin("din[{0}][{1}]".format(i,j)).by() - \
                                   self.data_in_bus_off[k/2] - j*self.m_pitch("m1")
                      self.add_rect(layer="metal2", 
                                    offset=din_off, 
                                    width=self.m2_width, 
                                    height=din_height)
                      self.add_via(self.m1_stack, (din_off.x, din_off.y-self.via_shift("v1")))
    
                      dout_off= vector(self.bank_inst[k].get_pin("dout[{0}][{1}]".format(i,j)).lx(), 
                                self.data_out_bus_off[k/2]+ j*self.m_pitch("m1") + 0.5*self.m1_width)
                      dout_height=  self.bank_inst[k].get_pin("dout[{0}][{1}]".format(i,j)).by() -\
                                    self.data_out_bus_off[k/2] - j*self.m_pitch("m1")
                      self.add_rect(layer="metal2", 
                                    offset=dout_off, 
                                    width=self.m2_width, 
                                    height=dout_height)
                      self.add_via(self.m1_stack, (dout_off.x, dout_off.y-self.via_shift("v1")))
                      
            # Connect second Data_in & Data_out bus to first one
            for j in range(self.w_size):                      
                din_bus_con_off1= vector(self.din1_bus_off.x, 
                                         self.din1_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                din_bus_con_off2= vector(-(j+2)*self.m_pitch("m1"), 
                                         self.din1_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                din_bus_con_off3= vector(-(j+2)*self.m_pitch("m1"), 
                                         self.din2_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                din_bus_con_off4= vector(self.din2_bus_off.x, 
                                         self.din2_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                self.add_wire(self.m1_stack, 
                             [din_bus_con_off1, din_bus_con_off2,din_bus_con_off3, din_bus_con_off4])
                      
            for j in range(self.w_size):                      
                dout_bus_con_off1= vector(self.dout1_bus_off.x, 
                                          self.dout1_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                dout_bus_con_off2= vector(-(j+2+self.w_size)*self.m_pitch("m1"), 
                                          self.dout1_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                dout_bus_con_off3= vector(-(j+2+self.w_size)*self.m_pitch("m1"), 
                                          self.dout2_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                dout_bus_con_off4= vector(self.dout2_bus_off.x, 
                                          self.dout2_bus_off.y + j*self.m_pitch("m1") + self.m1_width)
                self.add_wire(self.m1_stack, 
                              [dout_bus_con_off1, dout_bus_con_off2,dout_bus_con_off3, dout_bus_con_off4])

        # Addr Connections
        for k in range(self.num_banks):
            for i in range(self.bank_addr_size):
                pin= self.bank_inst[k].get_pin("addr[{0}]".format(i))
                if (pin.layer == "metal1" or pin.layer == "m1pin"):
                    layer= "metal1"
                    height= self.m1_width
                    stack= self.m1_stack
                else:
                    layer= "metal3"
                    height= self.m3_width
                    stack= self.m2_stack

                addr_off= vector(self.addr_bus1_off.x+ i*self.m_pitch("m1")- self.metal3_enclosure_via2, 
                                 self.bank_inst[k].get_pin("addr[{0}]".format(i)).uc().y - height)
                addr_width=  self.bank_inst[k].get_pin("addr[{0}]".format(i)).uc().x - \
                             self.addr_bus1_off.x - i*self.m_pitch("m1")

                self.add_rect(layer=layer, 
                              offset=addr_off, 
                              width=addr_width, 
                              height=height)
                self.add_via(stack, (addr_off.x, addr_off.y-self.via_shift("v1")))
        
        # bank_sel Connections
        for k in range(self.num_banks):
            pin= self.bank_inst[k].get_pin("S")
            if (pin.layer == "metal1" or pin.layer == "m1pin"):
                layer= "metal1"
                height= self.m1_width
                stack= self.m1_stack
            else:
                layer= "metal3"
                height= self.m3_width
                stack= self.m2_stack

            bank_sel_off= vector(self.sel_bus_off.x+ k*self.m_pitch("m1"), 
                                 self.bank_inst[k].get_pin("S").uc().y - height)
            bank_sel_width=  self.bank_inst[k].get_pin("S").uc().x - \
                             self.sel_bus_off.x - k*self.m_pitch("m1")
            self.add_rect(layer=layer, 
                          offset=bank_sel_off, 
                          width=bank_sel_width, 
                          height=height)
            self.add_via(stack, (bank_sel_off.x, bank_sel_off.y-self.via_shift("v1")))
    
        # Ctrl Connections
        for k in range(self.num_banks):
            control_pin_list= ["reset", "wack", "wreq", "rreq", "rack", "ack", "rw", "w", "r", 
                               "ack_merge", "rw_en1_S", "rw_en2_S", "Mack", "Mrack", "Mwack"]
            
            if self.two_level_bank:
                split_control_list= ["reset", "pre_wack", "wreq_split", "rreq_split", "pre_rack", 
                                     "pre_ack", "rw_split", "w_split", "r_split", "ack{0}".format(k), 
                                     "ack_b{0}".format(k), "ack_b", "rw_merge", "rreq_split", "wreq_split"]
            else:
                split_control_list= ["reset", "pre_wack", "wreq", "rreq", "pre_rack", "pre_ack",  
                                     "rw", "w", "r", "ack{0}".format(k), "ack_b{0}".format(k),"ack_b", 
                                     "rw_merge", "rreq", "wreq"]
  
            for i in range(len(control_pin_list)):
                pin= self.bank_inst[k].get_pin(control_pin_list[i])
                if (pin.layer == "metal1" or pin.layer == "m1pin"):
                    layer= "metal1"
                    height= self.m1_width
                    stack= self.m1_stack
                else:
                    layer= "metal3"
                    height= self.m3_width
                    stack= self.m2_stack
                    
                ctrl_off= vector(self.v_ctrl_bus_pos[split_control_list[i]][0]- 0.5*height, 
                                 self.bank_inst[k].get_pin(control_pin_list[i]).uc().y- height)
                ctrl_width=  self.bank_inst[k].get_pin(control_pin_list[i]).uc().x - \
                             self.v_ctrl_bus_pos[split_control_list[i]][0]
                self.add_rect(layer=layer, 
                              offset=ctrl_off, 
                              width=ctrl_width, 
                              height=height)
                self.add_via(stack, (ctrl_off.x, ctrl_off.y-self.via_shift("v1")))             
        
        
        # select= vdd Connection
        if not self.two_level_bank:
            sel_pos1=vector(self.v_ctrl_bus_pos["S"].x , self.v_ctrl_bus_pos["S"].y+self.m1_width)
            sel_pos2=vector(self.v_ctrl_bus_pos["vdd"].x, self.v_ctrl_bus_pos["vdd"].y+self.m1_width)
            self.add_path("metal1", [sel_pos1, sel_pos2])
            self.add_via(self.m1_stack, (sel_pos1.x-0.5*self.m2_width, 
                         sel_pos1.y-0.5*self.m1_width-self.via_shift("v1")))
            self.add_via(self.m1_stack, (sel_pos2.x-0.5*self.m2_width, 
                         sel_pos2.y-0.5*self.m1_width-self.via_shift("v1")))
        
        bank
        # vdd and gnd Connections
        if (self.num_banks == 2 or self.orien == "H"):
            for k in range(self.num_banks):
                for vdd_pin in self.bank_inst[k].get_pins("vdd"):
                    vdd_off= vector(vdd_pin.lx(), self.pow_rail_1_off.y + 0.5*self.m1_width)
                    vdd_height=  vdd_pin.by() - self.pow_rail_1_off.y
                    self.add_rect(layer="metal2", 
                                  offset=vdd_off, 
                                  width=self.bank.vdd_rail_width, 
                                  height=vdd_height)
                    self.add_via(self.m1_stack, (vdd_off.x, vdd_off.y-self.via_shift("v1")))
        
                for gnd_pin in self.bank_inst[k].get_pins("gnd"):
                    gnd_off= vector(gnd_pin.lx(), 
                                    self.pow_rail_1_off.y + self.pow_rail_pitch + 0.5*self.m1_width)
                    gnd_height=  gnd_pin.by() - self.pow_rail_1_off.y - self.pow_rail_pitch
                    self.add_rect(layer="metal2", 
                                  offset=gnd_off, 
                                  width=self.bank.gnd_rail_width, 
                                  height=gnd_height)
                    self.add_via(self.m1_stack, gnd_off)

        if (self.num_banks == 4 and  self.orien == "V"):
            self.power_rail_off= [self.pow_rail_1_off.y, self.pow_rail_2_off.y]
            for k in range(self.num_banks):
                for vdd_pin in self.bank_inst[k].get_pins("vdd"):
                    vdd_off= vector(vdd_pin.lx(), self.power_rail_off[k/2] + 0.5*self.m1_width)
                    vdd_height=  vdd_pin.by() - self.power_rail_off[k/2]
                    self.add_rect(layer="metal2", 
                                  offset=vdd_off, 
                                  width=self.bank.vdd_rail_width, 
                                  height=vdd_height)
                    self.add_via(self.m1_stack, vdd_off)
            
                for gnd_pin in self.bank_inst[k].get_pins("gnd"):
                    gnd_off= vector(gnd_pin.lx(), self.power_rail_off[k/2] + \
                                    self.pow_rail_pitch + 0.5*self.m1_width)
                    gnd_height=  gnd_pin.by() - self.power_rail_off[k/2] - self.pow_rail_pitch
                    self.add_rect(layer="metal2", 
                                  offset=gnd_off, 
                                  width=self.bank.gnd_rail_width, 
                                  height=gnd_height)
                    self.add_via(self.m1_stack, gnd_off)

        #Connect vdd & gnd of split_merge_control to horizontal vdd & gnd power rails
        self.add_via(self.m1_stack, (self.vdd_off.x, self.pow_rail_1_off.y+0.5*self.m1_width-\
                     self.via_shift("v1")))
        self.add_via(self.m1_stack, 
                     (self.gnd_off.x,self.pow_rail_1_off.y+self.pow_rail_pitch+0.5*self.m1_width))
        if (self.num_banks == 4 and  self.orien == "V"):
            self.add_via(self.m1_stack, (self.vdd_off.x, self.pow_rail_2_off.y+\
                        0.5*self.m1_width-self.via_shift("v1")))
            self.add_via(self.m1_stack, 
                        (self.gnd_off.x,self.pow_rail_2_off.y+self.pow_rail_pitch+\
                         0.5*self.m1_width-self.via_shift("v1")))


#/////////////////////////////////////////////////////////////////////////////#
#                                                                             #
#  Adding Split and Merge cells and Connection if self.two_level_bank == True #
#                                                                             #
#/////////////////////////////////////////////////////////////////////////////#

    def add_split_merge_cells(self):
        """ Adding the second-level data_split_merge_cells for data, addr and ctrls"""
        
        # Adding data_in_split_cell_array
        x_off= self.bank_pos_0.x + self.bank.width - self.dsplit_ary.width 
        if (self.num_banks == 2 and self.orien=="H"):
            y_off= -(max(self.addr_size,self.control_size)+3)*self.m_pitch("m2")-\
                     self.addr_split_ary.height
        else:
            y_off= -(max(max(self.addr_size,self.control_size), self.w_size)+3)*self.m_pitch("m2")-\
                     self.addr_split_ary.height

        self.dsplit_ary_inst= self.add_inst(name="outter_data_split_array", 
                                            mod=self.dsplit_ary, 
                                            offset=vector(x_off,y_off))
        temp= []
        for i in range(self.w_size):
            temp.append("din[{0}]".format(i))
            temp.append("din_split[{0}]".format(i))
        temp.extend(["rw_en1_S", "rw_en2_S", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)

        for i in range(self.w_size):
            self.add_layout_pin(text="din[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset= self.dsplit_ary_inst.get_pin("D[{0}]".format(i)).ll(),
                                width=self.m2_width, 
                                height=self.m2_width)

        # Adding data_out_merge_cell_array
        if self.orien == "H":
            x_off= self.bank_pos_1.x - self.bank.width + \
                   self.w_per_row*self.ctrl_mrg_cell.width - self.ctrl_mrg_cell.width
            self.dmerge_ary_inst= self.add_inst(name="outter_data_merge_array", 
                                                mod=self.dmerge_ary, 
                                                offset=vector(x_off,y_off))
            temp= []
            for i in range(self.w_size):
                temp.append("dout_merge[{0}]".format(i))
                temp.append("dout[{0}]".format(i))
            temp.extend(["Mrack_S", "rreq_split", "reset", "S", "vdd", "gnd"])
            self.connect_inst(temp)
        
            for i in range(self.w_size):
                self.add_layout_pin(text="dout[{0}]".format(self.w_size-1-i), 
                                    layer=self.m2_pin_layer, 
                                    offset= self.dmerge_ary_inst.get_pin("Q[{0}]".format(i)).ll(),
                                    width=self.m2_width, 
                                    height=self.m2_width)
        
        # Redefining width and height after adding spli and merge arrays
        if self.num_banks == 2:
            self.width= self.bank_inst[1].rx()
            # 8 m1 pitch fo split and merge control signals
            self.height= max(self.bank_inst[1].uy(), self.sp_mrg_ctrl_inst.uy()) -\
                             self.dsplit_ary_inst.by() + 8*self.m_pitch("m1")

        if self.num_banks == 4:
            self.width= self.bank_inst[1].rx() + 2*self.w_size*self.m_pitch("m1")
            # 8 m1 pitch fo split and merge control signals
            self.height= max(self.bank_inst[1].uy(), self.sp_mrg_ctrl_inst.uy()) -\
                             self.dsplit_ary_inst.by() + 8*self.m_pitch("m1")

        if self.orien == "V":
            x_off2= self.bank_pos_0.x + self.bank.width - self.dsplit_ary.width
            if self.num_banks == 2:
                y_off2= self.bank_pos_1.y + self.bank.height +\
                        self.dmerge_ary.height + (self.w_size+2)*self.m_pitch("m1")
            if self.num_banks == 4:
                y_off2= self.bank_pos_3.y + self.bank.height + \
                        self.dmerge_ary.height + (self.w_size+2)*self.m_pitch("m1")
            self.dmerge_ary_inst= self.add_inst(name="outter_data_merge_array", 
                                                 mod=self.dmerge_ary, 
                                                 offset=vector(x_off2,y_off2),
                                                 mirror= "MX")
            temp= []
            for i in range(self.w_size):
                temp.append("dout_merge[{0}]".format(i))
                temp.append("dout[{0}]".format(i))
            temp.extend(["Mrack_S", "rreq_split", "reset", "S", "vdd", "gnd"])
            self.connect_inst(temp)
        
            for i in range(self.w_size):
                self.add_layout_pin(text="dout[{0}]".format(i), 
                                    layer=self.m2_pin_layer, 
                                    offset= (self.dmerge_ary_inst.get_pin("Q[{0}]".format(i)).lx(),
                                             self.dmerge_ary_inst.uy()-self.m2_width),
                                    width=self.m2_width, 
                                    height=self.m2_width)

            self.width= self.bank_inst[1].rx() + (self.sp_mrg_ctrl.height-self.v_bus_width)+\
                        (self.w_size+7)*self.m_pitch("m1")
            self.height= max(self.sp_mrg_ctrl_inst.uy(), self.dmerge_ary_inst.uy()) -\
                         self.dsplit_ary_inst.by() + 8*self.m_pitch("m1")
            
            
            
            if ((2*self.w_size+1)*self.m_pitch("m1")>(self.sp_mrg_ctrl.height-self.v_bus_width)):
                self.width = self.bank_inst[1].rx() + (self.w_size+7)*self.m_pitch("m1") + \
                             (2*self.w_size+1)*self.m_pitch("m1")

        # Adding addr_split_cell_array
        x_off= self.reset_off.x + self.m_pitch("m1")
        self.addr_split_ary_inst=self.add_inst(name="outter_address_split_array", 
                                               mod=self.addr_split_ary,
                                               offset=vector(x_off,y_off))
        temp= []
        for i in range(self.addr_size):
            temp.append("addr[{0}]".format(i))
            temp.append("addr_split[{0}]".format(i))
        temp.extend(["rw_en1_S", "rw_en2_S", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)
        
        for i in range(self.addr_size):
            self.add_layout_pin(text="addr[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset= self.addr_split_ary_inst.get_pin("D[{0}]".format(i)).ll(),
                                width=self.m2_width, 
                                height=self.m2_width)
        
        # Adding rw_split_cell_array
        # 7 m1 pitch gap between ctrl split cells for en1, en2, s, vdd, gnd + two spaces on each side
        self.ctrl_split_gap= 7*self.m_pitch("m1")
        x_off= max(self.sp_mrg_ctrl_inst.rx() + self.ctrl_split_gap, 
                   self.addr_split_ary_inst.rx() + self.ctrl_split_gap)
        self.ctrl_split_ary_inst= self.add_inst(name="outter_ctrl_split_array", 
                                                mod=self.ctrl_split_ary, 
                                                offset=vector(x_off,y_off))
        temp= []
        temp.extend(["r", "r_split", "w", "w_split", "rw", "rw_split"])
        temp.extend(["rreq", "rreq_split", "wreq", "wreq_split"])
        temp.extend(["rw_en1_S", "rw_en2_S", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)

        control_pin_name=["r", "w", "rw", "rreq", "wreq"]
        for i in range(5):
            self.add_layout_pin(text=control_pin_name[i], 
                                layer=self.m2_pin_layer, 
                                offset= self.ctrl_split_ary_inst.get_pin("D[{0}]".format(i)).ll(),
                                width=self.m2_width, 
                                height=self.m2_width)
        
        # Adding ack_merge_cell
        x_off= self.ctrl_split_ary_inst.rx() + self.ctrl_split_gap
        self.ack_mrg_inst=self.add_inst(name="outter_ack_merge_cell", 
                                        mod=self.ctrl_mrg_cell,
                                        offset=vector(x_off,y_off))
        temp= []
        temp.extend(["ack_merge", "ack"])
        temp.extend(["Mack_S", "rw_merge", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)
        self.add_layout_pin(text="ack", 
                            layer=self.m2_pin_layer, 
                            offset= self.ack_mrg_inst.get_pin("Q[0]").ll(),
                            width=self.m2_width, 
                            height=self.m2_width)

        # Adding rack_merge_cell
        x_off= self.ack_mrg_inst.rx() + self.ctrl_split_gap
        self.rack_mrg_inst=self.add_inst(name="outter_rack_merge_cell", 
                                         mod=self.ctrl_mrg_cell,
                                         offset=vector(x_off,y_off))
        temp= []
        temp.extend(["rack_merge", "rack"])
        temp.extend(["Mrack_S", "rreq_split", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)
        self.add_layout_pin(text="rack", 
                            layer=self.m2_pin_layer, 
                            offset= self.rack_mrg_inst.get_pin("Q[0]").ll(),
                            width=self.m2_width, 
                            height=self.m2_width)

        # Adding wack_merge_cell
        x_off= self.rack_mrg_inst.rx() + self.ctrl_split_gap
        self.wack_mrg_inst=self.add_inst(name="outter_wack_merge_cell", 
                                         mod=self.ctrl_mrg_cell,
                                         offset=vector(x_off,y_off))
        temp= []
        temp.extend(["wack_merge", "wack"])
        temp.extend(["Mwack_S", "wreq_split", "reset", "S", "vdd", "gnd"])
        self.connect_inst(temp)
        self.add_layout_pin(text="wack", 
                            layer=self.m2_pin_layer, 
                            offset= self.wack_mrg_inst.get_pin("Q[0]").ll(),
                            width=self.m2_width, 
                            height=self.m2_width)

    def route_data_split_merge(self):
        """ Connecting data_split_merge_cells to horizontal data bus"""
        
        # Adding a horizontal bus to connect datain pins to data_split_cell_array
        # Add +-0.5*self.m1_width for center of bus
        self.din_split_bus_off={}
        if (self.num_banks == 2 and self.orien == "H"):
            for i in range(self.w_size):
                self.din_split_bus_off[i]= vector(self.din1_bus_off.x,self.din1_bus_off.y+\
                                                   i*self.m_pitch("m1")+0.5*self.m1_width)
        else:
            for i in range(self.w_size):
                self.din_split_bus_off[i]= vector(self.bank_pos_0.x+self.bank.width-\
                                                  self.dsplit_ary.width,self.reset_off.y- \
                                                  (i+1)*self.m_pitch("m1")-0.5*self.m1_width)

                offset=(self.din_split_bus_off[i][0]-self.ctrl_mrg_cell.width,self.din_split_bus_off[i][1])
                self.add_rect(layer="metal1", 
                          offset= offset, 
                          width= self.dsplit_ary.width, 
                          height= self.m1_width)
        
                data_in_pos_x= self.din1_bus_pos["din_split[{0}]".format(i)][0]+self.data_bus_width
                data_in_pos_y= self.din1_bus_pos["din_split[{0}]".format(i)][1]
                self.add_wire(self.m1_stack, 
                              [(data_in_pos_x, data_in_pos_y), 
                              (data_in_pos_x+(i+1)*self.m_pitch("m1"),data_in_pos_y),
                              (data_in_pos_x+(i+1)*self.m_pitch("m1"),self.din_split_bus_off[i][1]),
                              (self.din_split_bus_off[i][0],
                               self.din_split_bus_off[i][1]+0.5*self.m1_width)]) 


        # connecting data_in_split_array to data_in_split_bus
        for i in range(self.w_size):
            data_in_pos= self.dsplit_ary_inst.get_pin("Q[{0}]".format(i)).uc()
            x_off= self.bank_inst[self.num_banks-1].get_pin("din[{0}][{1}]".format(self.num_subanks-1,i)).lx()
            y_off= self.din_split_bus_off[i][1]+0.5*self.m2_width-self.via_shift("v1")
            self.add_via(self.m1_stack, (x_off, y_off-0.5*self.m2_width))
            self.add_path("metal2", [data_in_pos, (x_off, y_off)])

        # Adding a horizontal bus to connect dataout pins to data_merge_cell_array
        self.dout_mrg_bus_off={}
        if self.orien == "H":
            if self.num_banks == 2:
                for i in range(self.w_size):
                    self.dout_mrg_bus_off[i]= vector(self.dout1_bus_off.x,self.dout1_bus_off.y+\
                                                    i*self.m_pitch("m1")+0.5*self.m1_width)
            if self.num_banks == 4:
                for i in range(self.w_size):
                    self.dout_mrg_bus_off[i]= vector(self.bank_pos_1.x-self.bank.width, 
                                                     self.reset_off.y- (i+1)*self.m_pitch("m1"))
                    self.add_rect(layer="metal1", 
                                  offset=self.dout_mrg_bus_off[i], 
                                  width= self.dmerge_ary.width+self.ctrl_mrg_cell.width, 
                                  height= self.m1_width)

                    data_out_pos_x= self.dout1_bus_pos["dout_merge[{0}]".format(i)][0]
                    data_out_pos_y= self.dout1_bus_pos["dout_merge[{0}]".format(i)][1]
                    self.add_wire(self.m1_stack, 
                                  [(data_out_pos_x, data_out_pos_y),
                                  (data_out_pos_x-(i+1)*self.m_pitch("m1"), data_out_pos_y),
                                  (data_out_pos_x-(i+1)*self.m_pitch("m1"), self.dout_mrg_bus_off[i][1]),
                                  (self.dout_mrg_bus_off[i][0], 
                                   self.dout_mrg_bus_off[i][1]+0.5*self.m1_width)]) 

        if self.orien == "V":
            for i in range(self.w_size):
                x_off= self.bank_pos_0.x+self.bank.width-self.dmerge_ary.width
                if self.num_banks == 2:
                    y_off= self.bank_pos_1.y + self.bank.height+(i+1)*self.m_pitch("m1")
                if self.num_banks == 4:
                    y_off= self.bank_pos_3.y + self.bank.height+(i+1)*self.m_pitch("m1")
                self.dout_mrg_bus_off[i]= vector(x_off, y_off)
                self.add_rect(layer="metal1", 
                              offset=(self.dout_mrg_bus_off[i][0]-self.ctrl_mrg_cell.width,
                                      self.dout_mrg_bus_off[i][1]), 
                              width= self.dmerge_ary.width, 
                              height= self.m1_width)

            for i in range(self.w_size):
                if self.num_banks == 2:
                    data_out_pos_x= self.dout1_bus_pos["dout_merge[{0}]".format(i)][0]+\
                                    self.data_bus_width
                    data_out_pos_y= self.dout1_bus_pos["dout_merge[{0}]".format(i)][1]
                if self.num_banks == 4:
                    data_out_pos_x= self.dout2_bus_pos["dout_merge[{0}]".format(i)][0]+\
                                    self.data_bus_width
                    data_out_pos_y= self.dout2_bus_pos["dout_merge[{0}]".format(i)][1]
                self.add_wire(self.m1_stack, [(data_out_pos_x, data_out_pos_y),
                             (data_out_pos_x+(i+1)*self.m_pitch("m1"), data_out_pos_y),
                             (data_out_pos_x+(i+1)*self.m_pitch("m1"), self.dout_mrg_bus_off[i][1]),
                             (self.dout_mrg_bus_off[i][0],
                              self.dout_mrg_bus_off[i][1]+0.5*self.m1_width)]) 


        # connecting data_out_merge_array to data_out_merge_bus
        for i in range(self.w_size):
            if self.orien=="V":
                data_out_pos= self.dmerge_ary_inst.get_pin("D[{0}]".format(i)).uc()
            if self.orien=="H":
                data_out_pos= self.dmerge_ary_inst.get_pin("D[{0}]".format(self.w_size-1-i)).uc()
            x_off= self.bank_inst[0].get_pin("dout[{0}][{1}]".format(self.num_subanks-1,i)).lx()
            y_off= self.dout_mrg_bus_off[i][1]
            
            pos1=vector(x_off+0.5*contact.m1m2.width, y_off)
            pos2=vector(data_out_pos.x, data_out_pos.y-0.5*self.m2_width)
            
            if i%2:
                if self.orien=="H":
                    mid_pos1=vector(pos1.x, pos2.y+self.m_pitch("m1"))
                if self.orien=="V":
                    mid_pos1=vector(pos1.x, pos2.y-self.m_pitch("m1"))

            else:
                mid_pos1=vector(pos1.x, pos2.y)
            
            mid_pos2=vector(pos2.x, mid_pos1.y)
            self.add_path("metal2", [pos1, mid_pos1, mid_pos2, pos2], width=contact.m1m2.width)
            self.add_via(self.m1_stack, (x_off+contact.m1m2.height, y_off), rotate=90)


    def route_addr_ctrl_split_merge(self):
        # Connecting addr_split and ctrl_split_merge_cells to vertical addr & ctrl bus
        
        # Connecting vertical addr bus to addr split cells
        for i in range(self.addr_size):
            addr_split_y_off= self.reset_off.y- (i+1)*self.m_pitch("m2")
            addr_bus_pos= self.v_ctrl_bus_pos["addr_split[{0}]".format(self.addr_size-1-i)]
            addr_split_pos= self.addr_split_ary_inst.get_pin("Q[{0}]".format(self.addr_size-1-i)).uc()
            self.add_path("metal3", [addr_split_pos,(addr_split_pos[0],addr_split_y_off),
                         (addr_bus_pos[0],addr_split_y_off) ])
            self.add_via(self.m2_stack, (addr_split_pos[0]-0.5*self.m3_width,
                                         addr_split_pos[1]-0.5*self.m3_width))
            self.add_via(self.m2_stack,(addr_bus_pos[0]-0.5*self.m3_width,
                                        addr_split_y_off-0.5*self.m3_width-self.via_shift("v2")))
            self.add_path("metal2",[(addr_bus_pos[0],addr_split_y_off),addr_bus_pos ])
        
        # Connecting vertical ctrl bus to ctrlr split/merge cells
        control_pin_list= ["r_split", "w_split", "rw_split", "ack_merge", 
                           "rack_merge", "rreq_split", "wreq_split","wack_merge"]
        ctrl_pos= [self.ctrl_split_ary_inst.get_pin("Q[0]").uc(),
                   self.ctrl_split_ary_inst.get_pin("Q[1]").uc(),
                   self.ctrl_split_ary_inst.get_pin("Q[2]").uc(),
                   self.ack_mrg_inst.get_pin("D[0]").uc(),
                   self.rack_mrg_inst.get_pin("D[0]").uc(),
                   self.ctrl_split_ary_inst.get_pin("Q[3]").uc(),
                   self.ctrl_split_ary_inst.get_pin("Q[4]").uc(),
                   self.wack_mrg_inst.get_pin("D[0]").uc()]
        
        for i in range(self.control_size):
            ctrl_split_y_off= self.reset_off.y- (i+1)*self.m_pitch("m1")
            ctrl_bus_pos= self.v_ctrl_bus_pos[control_pin_list[i]]
            self.add_wire(self.m1_stack, [ctrl_pos[i], (ctrl_pos[i][0],ctrl_split_y_off),
                          (ctrl_bus_pos[0],ctrl_split_y_off), ctrl_bus_pos]) 

    def route_split_cells_powers_and_selects(self):
        """ Connecting vdd, gnd, select and enables of split_merge_cells """
        
        power_select_pin= ["vdd", "gnd", "reset", "S"]
        for i in range(4):
            if self.orien == "H":
                x_off= self.bank_pos_1.x - self.bank.width
            if self.orien == "V":
                x_off= self.sp_mrg_ctrl_inst.lx()

            y_off=self.addr_split_ary_inst.by()
            width =self.bank_pos_0.x + self.bank.width - x_off

            self.add_rect(layer= "metal1",
                          offset=vector(x_off, y_off-(i+1)*self.m_pitch("m1")),
                          width= width,
                          height= self.m1_width)
            self.add_layout_pin(text=power_select_pin[i],
                                layer= self.m1_pin_layer,
                                offset=vector(x_off, y_off-(i+1)*self.m_pitch("m1")),
                                width= self.m1_width,
                                height= self.m1_width)
        
        mod_list0=[self.dsplit_ary_inst, self.dmerge_ary_inst]
        mod_list1=[self.dsplit_ary_inst, self.addr_split_ary_inst, self.ctrl_split_ary_inst]
        mod_list2=[self.ack_mrg_inst, self.rack_mrg_inst, self.wack_mrg_inst]
        
        for i in range(3):
            for mod in (mod_list1 + mod_list2):
                power_pos= mod.get_pin(power_select_pin[i])
                self.add_wire(self.m1_stack,[power_pos.lc(), 
                              (power_pos.lx()-(1+i)*self.m_pitch("m1"), power_pos.lc().y), 
                              (power_pos.lx()-(1+i)*self.m_pitch("m1"), y_off-(i+1)*self.m_pitch("m1"))])
                self.add_via(self.m1_stack,(power_pos.lx()-(1+i)*self.m_pitch("m1")-\
                                            0.5*self.m2_width,y_off-(i+1)*self.m_pitch("m1"))) 

        for mod in mod_list1:
            select_pos= mod.get_pin("S")
            self.add_wire(self.m1_stack, [select_pos.lc(),
                          (select_pos.lx()-4*self.m_pitch("m1"), select_pos.lc().y), 
                          (select_pos.lx()-4*self.m_pitch("m1"), y_off-4*self.m_pitch("m1"))])
            self.add_via(self.m1_stack, (select_pos.lx()-4*self.m_pitch("m1")-0.5*self.m2_width,
                                         y_off-4*self.m_pitch("m1"))) 

        for mod in mod_list2:
            select_pos= mod.get_pin("M")
            self.add_wire(self.m1_stack, [select_pos.lc(),(select_pos.lx()-4*self.m_pitch("m1"), 
                          select_pos.lc().y), 
                          (select_pos.lx()-4*self.m_pitch("m1"),y_off-4*self.m_pitch("m1"))])
            self.add_via(self.m1_stack, (select_pos.lx()-4*self.m_pitch("m1")-0.5*self.m2_width,
                                         y_off-4*self.m_pitch("m1"))) 


        select_pin_S= ["en1_S", "en2_S"]
        select_split_pin_name=["rw_en1_S", "rw_en2_S"] 
        mod_list4=self.ctrl_split_ary_inst

        for i in range(2):
            select_pos= mod_list4.get_pin(select_pin_S[i])
            self.add_wire(self.m1_stack, [select_pos.lc(), 
                          (select_pos.lx()-(i+5)*self.m_pitch("m1"), select_pos.lc().y), 
                          (select_pos.lx()-(i+5)*self.m_pitch("m1"), 
                          self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1"))])
            self.add_layout_pin(text=select_split_pin_name[i],
                                layer= self.m2_pin_layer,
                                offset=(select_pos.lx()-(i+5)*self.m_pitch("m1")-0.5*self.m2_width,
                                        self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1")),
                                width= self.m2_width,
                                height= self.m2_width)

        select_merge_pin_name=["Mack_S", "Mrack_S", "Mwack_S"]
        for mod in mod_list2:
            select_pos1= mod.get_pin("en1_M")
            self.add_wire(self.m1_stack, [select_pos1.lc(), 
                          (select_pos1.lx()-5*self.m_pitch("m1"), select_pos1.lc().y), 
                          (select_pos1.lx()-5*self.m_pitch("m1"), 
                           self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1"))])
            self.add_layout_pin(text=select_merge_pin_name[mod_list2.index(mod)],
                                layer= self.m2_pin_layer,
                                offset=(select_pos1.lx()-5*self.m_pitch("m1")-0.5*self.m2_width,
                                        self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1")),
                                width= self.m2_width,
                                height= self.m2_width)
           
        en2_merge=["rreq_split", "wreq_split"]
        mod_list=[self.rack_mrg_inst, self.wack_mrg_inst]
        for mod in mod_list:           
            select_pos2= mod.get_pin("en2_M")
            ctrl_pos= self.ctrl_split_ary_inst.get_pin("Q[{0}]".format(3+mod_list.index(mod))).uc()
            self.add_wire(self.m1_stack, [select_pos2.lc(),
                          (select_pos2.lx()-6*self.m_pitch("m1"), select_pos2.lc().y), 
                          (select_pos2.lx()-6*self.m_pitch("m1"), 
                           self.reset_off.y- (6+mod_list.index(mod))*self.m_pitch("m1")),
                          (ctrl_pos.x, self.reset_off.y- (6+mod_list.index(mod))*self.m_pitch("m1"))])

        Mrw_y_off= self.reset_off.y- 9*self.m_pitch("m1")
        ctrl_bus_pos= self.v_ctrl_bus_pos["rw_merge"]
        ctrl_pos= self.ack_mrg_inst.get_pin("en2_M").lc()
        self.add_wire(self.m1_stack, [ctrl_pos, 
                      (ctrl_pos.x-6*self.m_pitch("m1"), ctrl_pos.y), 
                      (ctrl_pos.x-6*self.m_pitch("m1"),Mrw_y_off), 
                      (ctrl_bus_pos[0],Mrw_y_off), ctrl_bus_pos]) 

        power_select_pins= ["vdd", "gnd", "reset", "M"]
        for i in range(4):
            select_pos= self.dmerge_ary_inst.get_pin(power_select_pins[i])
            
            if self.orien == "H":
                y_off= self.dmerge_ary_inst.by()
                self.add_wire(self.m1_stack, [select_pos.lc(), 
                              (self.dmerge_ary_inst.rx()+(1+i)*self.m_pitch("m1"), 
                                select_pos.lc().y), 
                              (self.dmerge_ary_inst.rx()+(1+i)*self.m_pitch("m1"), 
                                y_off-(1+i)*self.m_pitch("m1"))])
                self.add_via(self.m1_stack, 
                            (select_pos.lx()+self.dmerge_ary.width+(1+i)*self.m_pitch("m1")-\
                            0.5*self.m2_width,y_off-(1+i)*self.m_pitch("m1"))) 
            
            if self.orien == "V":
                y_off= self.dsplit_ary_inst.by()
                self.add_wire(self.m1_stack, [select_pos.lc(), 
                              (self.dmerge_ary_inst.rx()+(1+i+self.w_size)*self.m_pitch("m1"), 
                               select_pos.lc().y), 
                              (self.dmerge_ary_inst.rx()+(1+i+self.w_size)*self.m_pitch("m1"), 
                               y_off-(1+i)*self.m_pitch("m1")),
                              (select_pos.lx(), y_off-(1+i)*self.m_pitch("m1")+0.5*self.m1_width)])

        
        #Connecting "vdd" & "gnd" and "reset" between banks and ctrl_split arrays
        power_pins= ["vdd", "gnd"]
        for i in range(2):
            bank_power= self.sp_mrg_ctrl_inst.get_pin(power_pins[i])
            spl_mrg_power= self.addr_split_ary_inst.get_pin(power_pins[i])
            
            self.add_wire(self.m1_stack, [(spl_mrg_power.lx(), spl_mrg_power.lc().y),
                         (spl_mrg_power.lx()-(i+8)*self.m_pitch("m1"), spl_mrg_power.lc().y),
                         (spl_mrg_power.lx(), self.reset_off.y-(2-i)*self.m_pitch("m1")),
                         (bank_power.uc().x, self.reset_off.y-(2-i)*self.m_pitch("m1")),
                         (bank_power.uc().x, self.reset_off.y+self.m2_width)])

        
        # Connection S pin of split_merge_ctrl to select pin
        sel_pos1=self.v_ctrl_bus_pos["S"]
        sel_pos2=vector(self.reset_off.x-9*self.m_pitch("m1")-0.5*self.m2_width, sel_pos1.y)
        sel_pos3=vector(sel_pos2.x, self.addr_split_ary_inst.by()-4*self.m_pitch("m1"))
        self.add_wire(self.m2_rev_stack, [sel_pos1, sel_pos2, sel_pos3])
        self.add_via_center(self.m1_stack, sel_pos3)
        self.add_via_center(self.m2_stack, sel_pos1)
        
        spl_mrg_reset= self.addr_split_ary_inst.get_pin("reset")
        self.add_wire(self.m1_stack, [(spl_mrg_reset.lx(), spl_mrg_reset.lc().y),
                     (spl_mrg_reset.lx()-3*self.m_pitch("m1"), spl_mrg_reset.lc().y),
                     (spl_mrg_reset.lx()-3*self.m_pitch("m1"),self.reset_off.y-3*self.m_pitch("m1")),
                     (self.reset_off.x, self.reset_off.y-3*self.m_pitch("m1")),
                     (self.reset_off.x, self.reset_off.y+self.m_pitch("m1"))])

        spl_mrg_ack_merge= self.v_ctrl_bus_pos["ack_merge"]
        self.add_wire(self.m1_stack, [(spl_mrg_ack_merge.x, spl_mrg_ack_merge.y),
                     (spl_mrg_ack_merge.x, self.reset_off.y-4*self.m_pitch("m1")),
                     (self.reset_off.x-6*self.m_pitch("m1"), self.reset_off.y-4*self.m_pitch("m1")),
                     (self.reset_off.x-6*self.m_pitch("m1"), 
                      self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1"))])

        self.add_layout_pin(text="ack_merge",
                            layer= self.m2_pin_layer,
                            offset=(self.reset_off.x-6*self.m_pitch("m1")-0.5*self.m2_width, 
                                    self.ctrl_split_ary_inst.by()-6*self.m_pitch("m1")),
                            width= self.m2_width,
                            height= self.m2_width)
        
        #Connecting "rw_en1_sel" & "rw_en2_sel" between datain_spli, addr_spli and rwrw_split arrays
        select_pin_S= ["en1_S", "en2_S"]
        for i in range(2):
            en_data= self.dsplit_ary_inst.get_pin(select_pin_S[i])
            en_addr= self.addr_split_ary_inst.get_pin(select_pin_S[i])
            en_ctrl= self.ctrl_split_ary_inst.get_pin(select_pin_S[i])
            yoff= self.ctrl_split_ary_inst.by()-(5+i)*self.m_pitch("m1")
            self.add_wire(self.m1_stack,
                          [en_addr.lc(), (en_addr.lx()-(i+5)*self.m_pitch("m1"), en_addr.lc().y), 
                          (en_addr.lx()-(i+5)*self.m_pitch("m1"), yoff), 
                          (en_data.lx()-(i+5)*self.m_pitch("m1"), yoff),
                          (en_data.lx()-(i+5)*self.m_pitch("m1"), en_data.lc().y), en_data.lc()])

            self.add_wire(self.m1_stack,
                          [en_addr.lc(), (en_addr.lx()-(i+5)*self.m_pitch("m1"), en_addr.lc().y), 
                          (en_addr.lx()-(i+5)*self.m_pitch("m1"), yoff), 
                          (en_ctrl.lx()-(i+5)*self.m_pitch("m1"), yoff),
                          (en_ctrl.lx()-(i+5)*self.m_pitch("m1"), en_ctrl.lc().y), en_ctrl.lc()])

        #Connecting "Mrack_select" between dataout_merge and rack_merge cell
        en_data= self.dmerge_ary_inst.get_pin("en1_M")
        en_ctrl= self.rack_mrg_inst.get_pin("en1_M")
        yoff= self.ctrl_split_ary_inst.by()-7*self.m_pitch("m1")
        if self.orien == "H":
            self.add_wire(self.m1_stack,
                          [en_ctrl.lc(), (en_ctrl.lx()-5*self.m_pitch("m1"), en_ctrl.lc().y), 
                          (en_ctrl.lx()-5*self.m_pitch("m1"), yoff), 
                          (self.dmerge_ary_inst.rx()+5*self.m_pitch("m1"), yoff),
                          (self.dmerge_ary_inst.rx()+5*self.m_pitch("m1"), en_data.lc().y), 
                           en_data.lc()])

        if self.orien == "V":
            self.add_wire(self.m1_stack,
                          [en_ctrl.lc(), (en_ctrl.lx()-5*self.m_pitch("m1"), en_ctrl.lc().y), 
                          (en_ctrl.lx()-5*self.m_pitch("m1"), yoff), 
                          (self.dmerge_ary_inst.rx()+(5+self.w_size)*self.m_pitch("m1"), yoff),
                          (self.dmerge_ary_inst.rx()+(5+self.w_size)*self.m_pitch("m1"), 
                           en_data.lc().y), en_data.lc()])

        #Connecting "rreq_split" between dataout_merge and rack_merge cell
        en_data= self.dmerge_ary_inst.get_pin("en2_M")
        en_ctrl= self.rack_mrg_inst.get_pin("en2_M")
        yoff= self.ctrl_split_ary_inst.by()-8*self.m_pitch("m1")
        if self.orien == "H":
            self.add_wire(self.m1_stack,
                          [en_ctrl.lc(), (en_ctrl.lx()-6*self.m_pitch("m1"), en_ctrl.lc().y), 
                          (en_ctrl.lx()-6*self.m_pitch("m1"), yoff), 
                          (self.dmerge_ary_inst.rx()+6*self.m_pitch("m1"), yoff),
                          (self.dmerge_ary_inst.rx()+6*self.m_pitch("m1"), en_data.lc().y), 
                           en_data.lc()])

        if self.orien == "V":
            self.add_wire(self.m1_stack,
                          [en_ctrl.lc(), (en_ctrl.lx()-6*self.m_pitch("m1"), en_ctrl.lc().y), 
                          (en_ctrl.lx()-6*self.m_pitch("m1"), yoff), 
                          (self.dmerge_ary_inst.rx()+(6+self.w_size)*self.m_pitch("m1"), yoff),
                          (self.dmerge_ary_inst.rx()+(6+self.w_size)*self.m_pitch("m1"), 
                           en_data.lc().y), en_data.lc()])
