import sys
import datetime
import getpass
import design
import debug
import contact
from math import log
from vector import vector
from globals import OPTS, print_time
from multi_bank import multi_bank
from split_merge_control import split_merge_control
from bitcell import bitcell
    
class sram(design.design):
    """ Dynamically generated two level multi-bank asynchronous SRAM. """

    def __init__(self, word_size, words_per_row, num_rows, num_subanks, 
                 branch_factors, bank_orientations, name):
        
        design.design.name_map=[]
        start_time = datetime.datetime.now()
        design.design.__init__(self, name)

        self.word_size = word_size
        self.w_per_row = words_per_row
        self.num_rows = num_rows
        self.num_subanks = num_subanks
        self.num_outbanks = branch_factors[0]
        self.num_inbanks = branch_factors[1]
        self.outbank_orien = bank_orientations[0]
        self.inbank_orien = bank_orientations[1]
        if self.num_outbanks > 1:
            self.two_level_bank = True
        else:
            self.two_level_bank = False
        
        self.compute_sizes()
        self.add_pins()
        self.create_layout()
        self.offset_all_coordinates()

        self.bitcell = bitcell()

        self.total_bits = self.num_rows*self.num_subanks*self.word_size*\
                          self.w_per_row*self.num_inbanks*self.num_outbanks
        efficiency = 100*((self.total_bits*self.bitcell.width*\
                      self.bitcell.height)/(self.width*self.height))
        
    def compute_sizes(self):
        """ Compute the address sizes """
        
        row_addr_size = int(log(self.num_rows, 2))
        subank_addr_size = int(log(self.num_subanks, 2))
        col_mux_addr_size = int(log(self.w_per_row, 2))
        self.inbank_addr_size = subank_addr_size + row_addr_size + col_mux_addr_size +\
                                int(log(self.num_inbanks, 2))
        outbank_addr_size = int(log(self.num_outbanks, 2))
        self.addr_size = self.inbank_addr_size + outbank_addr_size

    def add_pins(self):
        """ Add pins for entire SRAM. """

        for i in range(self.word_size):
                self.add_pin("data_in[{0}]".format(i),"INPUT")
        for i in range(self.word_size):
                self.add_pin("data_out[{0}]".format(i),"OUTPUT")
        for i in range(self.addr_size):
            self.add_pin("addr[{0}]".format(i),"INPUT")
        self.add_pin_list(["reset", "r", "w",  "rw"],"INPUT")
        self.add_pin_list(["ack", "rack"], "OUTPUT")
        self.add_pin_list(["rreq", "wreq"],"INPUT")
        self.add_pin_list(["wack"],"OUTPUT")
        self.add_pin("vdd","POWER")
        self.add_pin("gnd","GROUND")

    def create_layout(self):
        """ Layout creation """
        
        self.create_modules()

        if self.num_outbanks == 1:
            self.add_single_inbank_module()
        elif self.num_outbanks == 2:
            self.add_two_outbank_modules()
        elif self.num_outbanks == 4:
            self.add_four_outbank_modules()
        else:
            debug.error("Invalid number of banks! only 1, 2 and 4 banks are allowed",-1)

    def create_modules(self):
        """ Create all the modules that will be used """
        
        # Create the inbank module (up to four are instantiated)
        self.inbank = multi_bank(word_size=self.word_size, words_per_row=self.w_per_row, 
                                 num_rows=self.num_rows, num_subanks=self.num_subanks, 
                                 num_banks=self.num_inbanks, orientation=self.inbank_orien, 
                                 two_level_bank=self.two_level_bank, name="inbank")
        self.add_mod(self.inbank)

        if self.num_outbanks > 1:
            self.out_split_mrg_ctrl = split_merge_control(num_banks=self.num_outbanks, 
                                                          name="outter_split_merge_ctrl")
            self.add_mod(self.out_split_mrg_ctrl)


    def add_inbanks(self, num, pos, x_flip, y_flip):
        """ Place an inner multi-bank module at the given position with orientations """

        # x_flip ==  1 --> no flip in x_axis
        # x_flip == -1 --> flip in x_axis
        # y_flip ==  1 --> no flip in y_axis
        # y_flip == -1 --> flip in y_axis

        # x_flip and y_flip are used for position translation

        if x_flip == -1 and y_flip == -1:
            inbank_rotation = 180
        else:
            inbank_rotation = 0

        if x_flip == y_flip:
            inbank_mirror = "R0"
        elif x_flip == -1:
            inbank_mirror = "MX"
        elif y_flip == -1:
            inbank_mirror = "MY"
        else:
            inbank_mirror = "R0"
            
        inbank_inst=self.add_inst(name="inbank{0}".format(num),
                                  mod=self.inbank,
                                  offset=pos,
                                  mirror=inbank_mirror,
                                  rotate=inbank_rotation)
        temp = []
        for i in range(self.word_size):
            temp.append("data_in[{0}]".format(i))
        for i in range(self.word_size):
            temp.append("data_out[{0}]".format(i))
        for i in range(self.inbank_addr_size):
            temp.append("addr[{0}]".format(i))
        if self.num_outbanks == 1:
            temp.extend(["reset", "r", "w",  "rw", "ack", "rack", "rreq", "wreq", "wack"])
        else:
            temp.extend(["reset", "r", "w",  "rw", "pre_ack", "pre_rack", "rreq", "wreq", "pre_wack"])
            temp.extend(["sel[{0}]".format(num), "ack{0}".format(num), "ack_b{0}".format(num), 
                         "ack_b", "rw_merge", "rreq", "wreq"])
        temp.extend(["vdd", "gnd"])
        self.connect_inst(temp)

        return inbank_inst

    def compute_bus_sizes(self):
        """ Compute the bus widths shared between two and four bank SRAMs """
        
        
        #"r", "w",  "rw", "ack", "rack", "rreq", "wreq", "wack"
        self.control_size = 8
        self.gap = 5*self.m_pitch("m1")
        
        # horizontal bus size (din, dout, addr, crl, sel, 
        # s/m input (2*num_outbanks), s/m ctrl (5), and reset)
        self.num_h_line = self.addr_size + self.control_size + self.word_size +\
                          self.num_outbanks + 2*self.num_outbanks + 5 + 1
        
        if self.outbank_orien == "H":
            self.data_bus_width = 2*self.inbank.width + 4*self.gap + \
                                  self.out_split_mrg_ctrl.height+self.m1_width
        if self.outbank_orien == "V":
            self.data_bus_width = self.inbank.width + self.gap + self.out_split_mrg_ctrl.height+ \
                                  self.m_pitch("m1")+self.m1_width
        
        self.power_rail_height = self.m1_width
        self.power_pitch = self.m_pitch("m1")
        
        self.h_bus_height = self.m_pitch("m1")*self.num_h_line + 2*self.power_pitch
    
    def add_single_inbank_module(self):
        """ This adds a single bank SRAM (No orientation or offset) """
        
        self.inbank_inst = self.add_inbanks(0, [0, 0], 1, 1)
        self.add_single_inbank_pins()
        self.width = self.inbank_inst.width
        self.height = self.inbank_inst.height

    def add_two_outbank_modules(self):
        """ This adds two inbank SRAM """
        
        self.compute_two_outbank_offsets()
        self.add_two_outbanks()
        self.add_busses()
        self.route_outbanks()
        self.width = self.inbank_inst[1].ur().x+ self.out_split_mrg_ctrl.height+self.m1_width
        self.height = self.inbank_inst[1].ur().y

    def add_four_outbank_modules(self):
        """ This adds four inbank SRAM """

        self.compute_four_outbank_offsets()
        self.add_four_outbanks()
        self.add_busses()
        self.route_outbanks()
        
        if self.outbank_orien == "H":
            self.width = self.inbank_inst[3].ur().x+ self.out_split_mrg_ctrl.height+self.m1_width 
            self.height = self.inbank_inst[3].ur().y
        if self.outbank_orien == "V":
            self.width = self.inbank_inst[3].ur().x+ self.out_split_mrg_ctrl.height+ \
                         self.m1_width+self.m_pitch("m1")*(2*self.word_size+self.inbank_addr_size+1) 
            self.height = self.inbank_inst[3].ur().y

    def compute_two_outbank_offsets(self):
        """ Compute the buses offsets based on orientation of inner banks and outter banks"""

        self.compute_bus_sizes()
        h_off = self.out_split_mrg_ctrl.height
        if self.outbank_orien == "H":
            self.power1_off = vector(-h_off, 0)
            self.din_bus1_off = vector(-h_off, 2*self.power_pitch)
            if self.inbank_orien == "H":
                self.dout_bus1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.reset1_off = vector(-h_off, self.dout_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
            if self.inbank_orien == "V":
                self.dout_bus1_off = vector(-h_off, self.inbank.height+self.h_bus_height+\
                                            2*self.gap+2*self.power_pitch)
                self.reset1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
        
        if self.outbank_orien == "V":
            if self.inbank_orien == "H":
                self.power1_off = vector(-h_off, self.inbank.height + self.gap)
                self.din_bus1_off = vector(-h_off, self.power1_off.y + 2*self.power_pitch)
                self.dout_bus1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.reset1_off = vector(-h_off, self.dout_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
            if self.inbank_orien == "V":
                self.power1_off = vector(-h_off, self.inbank.height + 2*self.gap +\
                                            self.word_size*self.m_pitch("m1"))
                self.din_bus1_off = vector(-h_off, self.power1_off.y + 2*self.power_pitch)
                self.dout_bus1_off = vector(-h_off, 0)
                self.dout_bus2_off = vector(-h_off, self.h_bus_height+2*self.gap +\
                                            self.word_size*self.m_pitch("m1")+ \
                                            2*(self.inbank.height+self.gap+self.power_pitch))
                self.reset1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
        
        self.addr_bus_off = vector(-h_off, self.reset1_off.y + self.m_pitch("m1"))
        self.sel_bus_off = vector(-h_off, self.addr_bus_off.y + \
                                     self.addr_size*self.m_pitch("m1"))
        self.split_merge_input_off = vector(-h_off, self.sel_bus_off.y + \
                                            self.num_outbanks*self.m_pitch("m1"))
        self.split_merge_ctrl_bus_off = vector(-h_off, self.split_merge_input_off.y +\
                                                    (2*self.num_outbanks)*self.m_pitch("m1"))
        self.ctrl_bus_off= vector(-h_off, self.split_merge_ctrl_bus_off.y + \
                                     5*self.m_pitch("m1"))


    def compute_four_outbank_offsets(self):
        """ Compute the buses offsets based on orientation of inner banks and outter banks"""
        
        self.compute_bus_sizes()
        h_off = self.out_split_mrg_ctrl.height
        if self.outbank_orien == "H":
            if self.inbank_orien == "H":
                self.power1_off = vector(-h_off, self.inbank.height + self.gap)
                self.din_bus1_off = vector(-h_off, self.power1_off.y+2*self.power_pitch)
                self.dout_bus1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.reset1_off = vector(-h_off, self.dout_bus1_off.y + \
                                           self.word_size*self.m_pitch("m1"))
            if self.inbank_orien == "V":
                self.power1_off = vector(-h_off, self.inbank.height+2*self.gap+\
                                            self.word_size*self.m_pitch("m1"))
                self.din_bus1_off = vector(-h_off, self.power1_off.y+2*self.power_pitch)
                self.reset1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.dout_bus1_off = vector(-h_off, 0)
                self.dout_bus2_off = vector(-h_off,self.h_bus_height+self.gap+\
                                            self.word_size*self.m_pitch("m1")+2*(self.inbank.height+\
                                            self.gap+2*self.power_pitch))
        if self.outbank_orien == "V":
            if self.inbank_orien == "H":
                self.power1_off = vector(-h_off, self.inbank.height + self.gap)
                self.din_bus1_off = vector(-h_off, self.power1_off.y + 2*self.power_pitch)
                self.dout_bus1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.reset1_off = vector(-h_off, self.dout_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.power2_off = vector(-h_off, 3*(self.inbank.height + self.gap)+ self.gap +\
                                            self.word_size*self.m_pitch("m1")+self.h_bus_height+ \
                                            2*self.power_pitch)
                self.din_bus2_off = vector(-h_off, self.power2_off.y + 2*self.power_pitch)
                self.dout_bus2_off = vector(-h_off, self.din_bus2_off.y + \
                                           self.word_size*self.m_pitch("m1"))
                self.reset2_off = vector(-h_off, self.dout_bus2_off.y + \
                                            self.word_size*self.m_pitch("m1"))

            if self.inbank_orien == "V":
                self.power1_off = vector(-h_off, self.inbank.height + 2*self.gap +\
                                            self.word_size*self.m_pitch("m1"))
                self.din_bus1_off = vector(-h_off, self.power1_off.y + 2*self.power_pitch)
                self.reset1_off = vector(-h_off, self.din_bus1_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.dout_bus1_off = vector(-h_off, 0)
                
                self.power2_off = vector(-h_off, 3*(self.inbank.height +2*self.gap)+\
                                            2*self.word_size*self.m_pitch("m1")+self.h_bus_height)
                self.din_bus2_off = vector(-h_off, self.power2_off.y + 2*self.power_pitch)
                self.reset2_off = vector(-h_off, self.din_bus2_off.y + \
                                            self.word_size*self.m_pitch("m1"))
                self.dout_bus2_off = vector(-h_off, 2*(self.h_bus_height+\
                                             self.word_size*self.m_pitch("m1")) +\
                                            4*(self.inbank.height+2*self.gap+self.power_pitch))
                self.dout_bus3_off = vector(-h_off, self.h_bus_height+\
                                            self.word_size*self.m_pitch("m1") +\
                                            2*(self.inbank.height+2*self.gap+self.power_pitch))

            self.addr_bus2_off = vector(-h_off, self.reset2_off.y + self.m_pitch("m1"))
            self.sel_bus2_off = vector(-h_off, self.addr_bus2_off.y + \
                                          self.addr_size*self.m_pitch("m1"))
            self.split_merge_input2_off = vector(-h_off, self.sel_bus2_off.y + \
                                                 self.num_outbanks*self.m_pitch("m1"))
            self.split_merge_ctrl_bus2_off = vector(-h_off, self.split_merge_input2_off.y +\
                                                    (2*self.num_outbanks)*self.m_pitch("m1"))
            self.ctrl_bus2_off= vector(-h_off, self.split_merge_ctrl_bus2_off.y + \
                                          5*self.m_pitch("m1"))
        
        self.addr_bus_off = vector(-h_off, self.reset1_off.y + self.m_pitch("m1"))
        self.sel_bus_off = vector(-h_off, self.addr_bus_off.y + \
                                     self.addr_size*self.m_pitch("m1"))
        self.split_merge_input_off = vector(-h_off, self.sel_bus_off.y + \
                                            self.num_outbanks*self.m_pitch("m1"))
        self.split_merge_ctrl_bus_off = vector(-h_off, self.split_merge_input_off.y +\
                                                    (2*self.num_outbanks)*self.m_pitch("m1"))
        self.ctrl_bus_off= vector(-h_off, self.split_merge_ctrl_bus_off.y + \
                                     5*self.m_pitch("m1"))


    def add_two_outbanks(self):
        """ Add the two outter banks and control module"""
        
        if self.outbank_orien == "H":
            x_off = self.inbank.width + 2*self.gap
            if self.inbank_orien == "H":
                y_off = self.h_bus_height + self.gap + \
                        self.word_size*self.m_pitch("m1") + 2*self.power_pitch
            if self.inbank_orien == "V":
                y_off = self.h_bus_height + self.gap + 2*self.power_pitch

            # Placement of inbanks 0 (left)
            inbanks_pos_0 = vector(x_off, y_off)
            self.inbank_inst=[self.add_inbanks(0, inbanks_pos_0, 1, -1)]

            # Placement of inbanks 1 (right)
            inbanks_pos_1 = vector(x_off+2*self.gap, y_off)
            self.inbank_inst.append(self.add_inbanks(1, inbanks_pos_1, 1, 1))

        if self.outbank_orien == "V":
            x_off= self.gap
            if self.inbank_orien == "H":
                y_off1 = self.inbank.height
                y_off2= y_off1 + self.h_bus_height + self.word_size*self.m_pitch("m1")+\
                        2*(self.gap + self.power_pitch)
            if self.inbank_orien == "V":
                y_off1 = self.inbank.height + self.gap + self.word_size*self.m_pitch("m1")
                y_off2= y_off1 + self.h_bus_height + 2*(self.gap + self.power_pitch)
            
            # Placement of inbanks 0 (bottom)
            inbanks_pos_0= vector(x_off,y_off1)
            self.inbank_inst= [self.add_inbanks(0, inbanks_pos_0, -1, 1)]

            # Placement of inbanks 1 (top)
            
            inbanks_pos_1= vector(x_off, y_off2)
            self.inbank_inst.append(self.add_inbanks(1, inbanks_pos_1, 1, 1))

        out_split_merge_ctrl_off = vector(0,inbanks_pos_1.y)
        self.out_split_mrg_ctrl_inst = self.add_inst(name="out_split_merge_ctrl", 
                                                     mod=self.out_split_mrg_ctrl, 
                                                     offset=out_split_merge_ctrl_off,
                                                     mirror= "R0",
                                                     rotate = 90)
        temp =[]
        temp.extend(["r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"])
        for i in range(self.num_outbanks):
            temp.append("ack{0}".format(i))
            temp.append("ack_b{0}".format(i))
        temp.extend(["pre_ack", "pre_wack", "pre_rack", "rw_merge"])        
        temp.extend(["ack_b", "addr[{0}]".format(self.addr_size-1), "sel[0]", "sel[1]"])
        temp.extend(["vdd", "vdd","gnd"])
        self.connect_inst(temp)

    def add_four_outbanks(self):
        """ Add the four outter banks and control module"""
        
        if self.outbank_orien == "H":
            x_off = self.inbank.width + 2*self.gap
            if self.inbank_orien == "H":
                y_off1 = self.inbank.height+ self.h_bus_height + 2*self.gap+ \
                        self.word_size*self.m_pitch("m1") + 2*self.power_pitch
                y_off2 = self.inbank.height
            if self.inbank_orien == "V":
                y_off1 = self.inbank.height+ self.h_bus_height + 3*self.gap+ \
                        self.word_size*self.m_pitch("m1") + 2*self.power_pitch
                y_off2 = self.inbank.height+self.word_size*self.m_pitch("m1")+self.gap
                
            # Placement of inbanks 0 (bottom left)
            inbanks_pos_0= vector(x_off,y_off2)
            self.inbank_inst=[self.add_inbanks(0, inbanks_pos_0, -1, -1)]

            # Placement of bank 1 (bottom right)
            inbanks_pos_1= vector(x_off+2*self.gap, y_off2)
            self.inbank_inst.append(self.add_inbanks(1, inbanks_pos_1, -1, 1))

            # Placement of bank 2 (upper left)
            inbanks_pos_2= vector(x_off, y_off1)
            self.inbank_inst.append(self.add_inbanks(2, inbanks_pos_2, 1, -1))

            # Placement of bank 3 (upper right)
            inbanks_pos_3= vector(x_off+2*self.gap, y_off1)
            self.inbank_inst.append(self.add_inbanks(3, inbanks_pos_3, 1, 1))
        
        if self.outbank_orien == "V":
            x_off = self.gap
            if self.inbank_orien == "H":
                y_off1 = self.inbank.height
                y_off2 = y_off1+ self.h_bus_height + 2*self.gap+ \
                        self.word_size*self.m_pitch("m1") + 2*self.power_pitch
                y_off3 = 3*self.inbank.height+ 2*(self.gap+self.power_pitch)+ \
                        self.h_bus_height + self.word_size*self.m_pitch("m1") + self.gap
                y_off4 =  y_off3+ self.h_bus_height +self.word_size*self.m_pitch("m1")+\
                         2*(self.power_pitch+self.gap)
            if self.inbank_orien == "V":
                y_off1 = self.inbank.height +self.word_size*self.m_pitch("m1")+self.gap
                y_off2 = y_off1+ self.h_bus_height + 2*(self.gap+ self.power_pitch)
                y_off3 = 3*self.inbank.height+ 5*self.gap+ 2*self.power_pitch+ \
                        self.h_bus_height + 2*self.word_size*self.m_pitch("m1")
                y_off4 = y_off3+  self.h_bus_height + 2*(self.power_pitch+self.gap)

            # Placement of bank 0 (lowest)
            inbanks_pos_0= vector(x_off,y_off1)
            self.inbank_inst=[self.add_inbanks(0, inbanks_pos_0, -1, 1)]

            # Placement of bank 1 
            inbanks_pos_1= vector(x_off,y_off2)
            self.inbank_inst.append(self.add_inbanks(1, inbanks_pos_1, 1, 1))

            # Placement of bank 2 
            inbanks_pos_2= vector(x_off,y_off3)
            self.inbank_inst.append(self.add_inbanks(2, inbanks_pos_2, -1, 1))

            # Placement of bank 3 (topmost)
            inbanks_pos_3= vector(x_off,y_off4)
            self.inbank_inst.append(self.add_inbanks(3, inbanks_pos_3, 1, 1))

        if self.outbank_orien == "H":
            out_split_merge_ctrl_off = vector(0,inbanks_pos_2.y)
        if self.outbank_orien == "V":
            out_split_merge_ctrl_off = vector(0,inbanks_pos_3.y)
        self.out_split_mrg_ctrl_inst= self.add_inst(name="out_split_merge_ctrl", 
                                                    mod=self.out_split_mrg_ctrl, 
                                                    offset=out_split_merge_ctrl_off,
                                                    mirror= "R0",
                                                    rotate = 90)

        temp =[]
        temp.extend(["r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"])
        for i in range(self.num_outbanks):
            temp.append("ack{0}".format(i))
            temp.append("ack_b{0}".format(i))
        
        temp.extend(["pre_ack", "pre_wack", "pre_rack", "rw_merge", "ack_b"])
        for i in range(int(log(self.num_outbanks,2))):
            temp.append("addr[{0}]".format(self.addr_size-2+i))

        for i in range(self.num_outbanks):
            temp.append("sel[{0}]".format(i))

        temp.extend(["vdd","vdd","gnd"])
        self.connect_inst(temp)


    def add_single_inbank_pins(self):
        """ Add pins for Single outtter bank SRAM """

        ctrl_pins = ["reset", "r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"]
        for i in range(len(ctrl_pins)):
            self.add_layout_pin(text=ctrl_pins[i],
                                layer = self.inbank_inst.get_pin(ctrl_pins[i]).layer,
                                offset = self.inbank_inst.get_pin(ctrl_pins[i]).ll(),
                                width = self.m2_width,
                                height = self.m2_width)
        for i in range(self.addr_size):
            self.add_layout_pin(text="addr[{0}]".format(i),
                                layer = self.inbank_inst.get_pin("addr[{0}]".format(i)).layer,
                                offset = self.inbank_inst.get_pin("addr[{0}]".format(i)).ll(),
                                width = self.m2_width,
                                height = self.m2_width)
        if self.num_inbanks ==1:
            layer = self.m2_pin_layer
        else:
            layer = self.m1_pin_layer
        for i in range(self.word_size):
            self.add_layout_pin(text="data_in[{0}]".format(i),
                                layer = layer,
                                offset = self.inbank_inst.get_pin("din[{0}]".format(i)).ll(),
                                width = self.m1_width,
                                height = self.m1_width)
            self.add_layout_pin(text="data_out[{0}]".format(i),
                                layer = layer,
                                offset = self.inbank_inst.get_pin("dout[{0}]".format(i)).ll(),
                                width = self.m1_width,
                                height = self.m1_width)
        power_pins = ["vdd","gnd"]
        for pin in power_pins:
            self.add_layout_pin(text=pin,
                                layer = self.inbank_inst.get_pin(pin).layer,
                                offset = self.inbank_inst.get_pin(pin).ll(),
                                width = self.m1_width,
                                height = self.m1_width)

    def add_busses(self):
        """ Add the horizontal busses """
        
        power_rail_names = ["vdd" , "gnd"]
        self.power_rail1_pos = self.create_bus(layer="metal1",
                                               pitch=self.m_pitch("m1"),
                                               offset=self.power1_off,
                                               names=power_rail_names,
                                               length=self.data_bus_width,
                                               make_pins=True)
        
        data_in_names=["data_in[{0}]".format(i) for i in range(self.word_size)]
        self.data_in1_bus_pos = self.create_bus(layer="metal1",
                                                pitch=self.m_pitch("m1"),
                                                offset=self.din_bus1_off,
                                                names=data_in_names,
                                                length=self.data_bus_width,
                                                make_pins=True)

        data_out_names=["data_out[{0}]".format(i) for i in range(self.word_size)]
        self.data_out1_bus_pos = self.create_bus(layer="metal1",
                                                 pitch=self.m_pitch("m1"),
                                                 offset=self.dout_bus1_off,
                                                 names=data_out_names,
                                                 length=self.data_bus_width,
                                                 make_pins=True)



        reset_name = ["reset"]
        self.H_ctrl_bus_pos = self.create_bus(layer="metal1",
                                              pitch=self.m_pitch("m1"),
                                              offset=self.reset1_off,
                                              names=reset_name,
                                              length=self.data_bus_width,
                                              make_pins=True)
        
        addr_names=["addr[{0}]".format(i) for i in range(self.addr_size)]
        self.H_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.addr_bus_off,
                                                   names=addr_names,
                                                   length=self.data_bus_width,
                                                   make_pins=True))
        sel_names=["sel[{0}]".format(i) for i in range(self.num_outbanks)]
        self.H_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.sel_bus_off,
                                                   names=sel_names,
                                                   length=self.data_bus_width,
                                                   make_pins=True))

        for i in range(self.num_outbanks):
            self.bank_split_merge_input_names = ["ack{0}".format(i), 
                                                 "ack_b{0}".format(i)]
            self.H_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                       pitch=self.m_pitch("m1"),
                                                       offset=self.split_merge_input_off+\
                                                       vector(0,2*i*self.m_pitch("m1")),
                                                       names=self.bank_split_merge_input_names,
                                                       length=self.data_bus_width,
                                                       make_pins=True))

        bank_split_mrg_bus_names = ["pre_wack", "pre_rack", "rw_merge", "pre_ack", "ack_b"]
        self.H_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.split_merge_ctrl_bus_off,
                                                   names=bank_split_mrg_bus_names,
                                                   length=self.data_bus_width,
                                                   make_pins=True))


        ctrl_names=["wack", "wreq",  "rreq", "rack", "ack", "rw", "w", "r"]
        self.H_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.ctrl_bus_off,
                                                   names=ctrl_names,
                                                   length=self.data_bus_width,
                                                   make_pins=True))


        if (self.outbank_orien == "V" and  self.num_outbanks == 4):
            power_rail_names = ["vdd" , "gnd"]
            self.power_rail2_pos = self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.power2_off,
                                                   names=power_rail_names,
                                                   length=self.data_bus_width)

            data_in_names=["data_in[{0}]".format(i) for i in range(self.word_size)]
            self.data_in2_bus_pos = self.create_bus(layer="metal1",
                                                    pitch=self.m_pitch("m1"),
                                                    offset=self.din_bus2_off,
                                                    names=data_in_names,
                                                    length=self.data_bus_width)
            
            data_out_names=["data_out[{0}]".format(i) for i in range(self.word_size)]
            self.data_out2_bus_pos = self.create_bus(layer="metal1",
                                                     pitch=self.m_pitch("m1"),
                                                     offset=self.dout_bus2_off,
                                                     names=data_out_names,
                                                     length=self.data_bus_width)
           
            reset_name = ["reset"]
            self.H2_ctrl_bus_pos = self.create_bus(layer="metal1",
                                                   pitch=self.m_pitch("m1"),
                                                   offset=self.reset2_off,
                                                   names=reset_name,
                                                   length=self.data_bus_width)
        
            addr_names=["addr[{0}]".format(i) for i in range(self.addr_size)]
            self.H2_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                         pitch=self.m_pitch("m1"),
                                                         offset=self.addr_bus2_off,
                                                         names=addr_names,
                                                         length=self.data_bus_width))

            sel_names=["sel[{0}]".format(i) for i in range(self.num_outbanks)]
            self.H2_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                        pitch=self.m_pitch("m1"),
                                                        offset=self.sel_bus2_off,
                                                        names=sel_names,
                                                        length=self.data_bus_width))

            for i in range(self.num_outbanks):
                self.bank_split_merge_input_names = ["ack{0}".format(i), 
                                                     "ack_b{0}".format(i)]
                self.H2_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                       pitch=self.m_pitch("m1"),
                                                       offset=self.split_merge_input2_off+\
                                                       vector(0,2*i*self.m_pitch("m1")),
                                                       names=self.bank_split_merge_input_names,
                                                       length=self.data_bus_width))

            bank_split_mrg_bus_names = ["pre_wack", "pre_rack", "rw_merge", "pre_ack", "ack_b"]
            self.H2_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                        pitch=self.m_pitch("m1"),
                                                        offset=self.split_merge_ctrl_bus2_off,
                                                        names=bank_split_mrg_bus_names,
                                                        length=self.data_bus_width))


            ctrl_names=["wack", "wreq",  "rreq", "rack", "ack", "rw", "w", "r"]
            self.H2_ctrl_bus_pos.update(self.create_bus(layer="metal1",
                                                         pitch=self.m_pitch("m1"),
                                                         offset=self.ctrl_bus2_off,
                                                         names=ctrl_names,
                                                         length=self.data_bus_width))

    def route_outbanks(self):
        """ Connect the inputs and outputs of each ouuer bank to horizontal busses """
        
        # Data Connections
        if (self.num_outbanks == 2):
            for k in range(self.num_outbanks):
                for i in range(self.word_size):
                    din_off = vector(self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().x, 
                                     self.din_bus1_off.y+ i*self.m_pitch("m1") +0.5*self.m1_width)
                    din_height =  self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().y - \
                                  self.din_bus1_off.y - i*self.m_pitch("m1")
                    self.add_rect(layer="metal2", 
                                  offset=din_off, 
                                  width=self.m2_width, 
                                  height=din_height)
                    self.add_via(self.m1_stack, offset=din_off)
    
                    if (self.outbank_orien == "H" or self.inbank_orien == "H"): 
                        dout_off = vector(self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().x, 
                                          self.dout_bus1_off.y+i*self.m_pitch("m1")+0.5*self.m1_width)
                        dout_height =  self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().y - \
                                       self.dout_bus1_off.y - i*self.m_pitch("m1")
                        self.add_rect(layer="metal2", 
                                      offset=dout_off, 
                                      width=self.m2_width, 
                                      height=dout_height)
                        self.add_via(self.m1_stack, dout_off)

                    else: 
                        dout_off1 = self.inbank_inst[0].get_pin("dout[{0}]".format(i))
                        dout_off2 = self.inbank_inst[1].get_pin("dout[{0}]".format(i))
                        dout_off1_y = self.dout_bus1_off.y+ i*self.m_pitch("m1") +self.m1_width
                        dout_off2_y = self.dout_bus2_off.y+ i*self.m_pitch("m1")
                        x_off = self.inbank_inst[1].lr().x+(i+1)*self.m_pitch("m1") 
                        self.add_wire(self.m1_stack, [(dout_off1.uc().x,dout_off1.ll().y),
                                      (dout_off1.uc().x,dout_off1_y),
                                      (x_off,dout_off1_y), (x_off,dout_off2_y),
                                      (dout_off1.uc().x,dout_off2_y),
                                      (dout_off2.uc().x,dout_off2.ll().y)]) 

        # Data Connections
        if (self.num_outbanks == 4 and self.outbank_orien == "H"):
            for k in range(self.num_outbanks):
                for i in range(self.word_size):
                    din_off = vector(self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().x, 
                                     self.din_bus1_off.y+ i*self.m_pitch("m1") + 0.5*self.m1_width)
                    din_height =  self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().y - \
                                  self.din_bus1_off.y - i*self.m_pitch("m1")
                    self.add_rect(layer="metal2", 
                                  offset=din_off, 
                                  width=self.m2_width, 
                                  height=din_height)
                    self.add_via(self.m1_stack, din_off)
    
                    if (self.inbank_orien == "H"): 
                        dout_off = vector(self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().x, 
                                          self.dout_bus1_off.y+ i*self.m_pitch("m1") + \
                                          0.5*self.m1_width)
                        dout_height =  self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().y - \
                                     self.dout_bus1_off.y - i*self.m_pitch("m1")
                        self.add_rect(layer="metal2", 
                                      offset=dout_off, 
                                      width=self.m2_width, 
                                      height=dout_height)
                        self.add_via(self.m1_stack, dout_off)

                    else: 
                        
                        dout_off0 = self.inbank_inst[0].get_pin("dout[{0}]".format(i))
                        dout_off1 = self.inbank_inst[1].get_pin("dout[{0}]".format(i))
                        dout_off2 = self.inbank_inst[3].get_pin("dout[{0}]".format(i))
                        dout_off1_y = self.dout_bus1_off.y+ i*self.m_pitch("m1") +self.m1_width
                        dout_off2_y = self.dout_bus2_off.y+ i*self.m_pitch("m1")
                        dout_off3 = self.inbank_inst[2].get_pin("dout[{0}]".format(i))
                        self.add_wire(self.m1_stack, [(dout_off0.uc().x,dout_off0.ll().y),
                                      (dout_off0.uc().x,dout_off1_y),(dout_off1.uc().x,dout_off1_y)])

                        x_off = self.inbank_inst[1].lr().x+(i+1)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack,[(dout_off1.uc().x,dout_off1.ll().y),
                                      (dout_off1.uc().x,dout_off1_y),
                                      (x_off,dout_off1_y), (x_off,dout_off2_y),
                                      (dout_off2.uc().x,dout_off2_y),
                                      (dout_off2.uc().x,dout_off2.ll().y)]) 
                        self.add_wire(self.m1_stack, [(dout_off2.uc().x,dout_off2_y),
                                      (dout_off3.uc().x,dout_off2_y),
                                      (dout_off3.uc().x,dout_off3.ll().y)]) 

        if (self.num_outbanks == 4 and self.outbank_orien == "V"):
            for k in range(self.num_outbanks/2):
                for i in range(self.word_size):
                    din_off1 = vector(self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().x, 
                                      self.din_bus1_off.y+ i*self.m_pitch("m1") + 0.5*self.m1_width)
                    din_off2 = vector(self.inbank_inst[k+2].get_pin("din[{0}]".format(i)).ll().x, 
                                      self.din_bus2_off.y+ i*self.m_pitch("m1") + 0.5*self.m1_width)
                    din1_height =  self.inbank_inst[k].get_pin("din[{0}]".format(i)).ll().y - \
                                   self.din_bus1_off.y - i*self.m_pitch("m1")
                    din2_height =  self.inbank_inst[k+2].get_pin("din[{0}]".format(i)).ll().y - \
                                   self.din_bus2_off.y - i*self.m_pitch("m1")

                    self.add_rect(layer="metal2", 
                                  offset=din_off1, 
                                  width=self.m2_width, 
                                  height=din1_height)
                    self.add_via(self.m1_stack, din_off1)
                    self.add_rect(layer="metal2", 
                                  offset=din_off2, 
                                  width=self.m2_width, 
                                  height=din2_height)
                    self.add_via(self.m1_stack, din_off2)
    
                    if (self.inbank_orien == "H"): 
                        dout_off1 = vector(self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().x, 
                                           self.dout_bus1_off.y+ i*self.m_pitch("m1") + \
                                           0.5*self.m1_width)
                        dout_off2 = vector(self.inbank_inst[k+2].get_pin("dout[{0}]".format(i)).ll().x, 
                                           self.dout_bus2_off.y+ i*self.m_pitch("m1") + \
                                           0.5*self.m1_width)
                        dout1_height =  self.inbank_inst[k].get_pin("dout[{0}]".format(i)).ll().y -\
                                       self.dout_bus1_off.y - i*self.m_pitch("m1")
                        dout2_height =  self.inbank_inst[k+2].get_pin("dout[{0}]".format(i)).ll().y-\
                                       self.dout_bus2_off.y - i*self.m_pitch("m1")

                        self.add_rect(layer="metal2", 
                                      offset=dout_off1, 
                                      width=self.m2_width, 
                                      height=dout1_height)
                        self.add_via(self.m1_stack, dout_off1)
                        self.add_rect(layer="metal2", 
                                      offset=dout_off2, 
                                      width=self.m2_width, 
                                      height=dout2_height)
                        self.add_via(self.m1_stack, dout_off2)

                        x_off = self.inbank_inst[1].lr().x+(i+3)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack, 
                                      [(self.inbank_inst[1].lr().x, dout_off1.y+0.5*self.m1_width),
                                      (x_off, dout_off1.y+0.5*self.m1_width),
                                      (x_off, dout_off2.y+0.5*self.m1_width),
                                      (self.inbank_inst[1].lr().x, dout_off2.y+0.5*self.m1_width)])
                    
                        x_off = self.inbank_inst[1].lr().x+(i+self.word_size+3)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack, 
                                      [(self.inbank_inst[1].lr().x, din_off1.y+0.5*self.m1_width),
                                      (x_off, din_off1.y+0.5*self.m1_width),
                                      (x_off, din_off2.y+0.5*self.m1_width),
                                      (self.inbank_inst[1].lr().x, din_off2.y+0.5*self.m1_width)])
                    else: 
                        
                        dout_off0 = self.inbank_inst[0].get_pin("dout[{0}]".format(i))
                        dout_off1 = self.inbank_inst[1].get_pin("dout[{0}]".format(i))
                        dout_off2 = self.inbank_inst[2].get_pin("dout[{0}]".format(i))
                        dout_off3 = self.inbank_inst[3].get_pin("dout[{0}]".format(i))
                        
                        dout_off1_y = self.dout_bus1_off.y+ i*self.m_pitch("m1") +self.m1_width
                        dout_off2_y = self.dout_bus2_off.y+ i*self.m_pitch("m1") +self.m1_width
                        dout_off3_y = self.dout_bus3_off.y+ i*self.m_pitch("m1") 

                        x_off = self.inbank_inst[1].lr().x+(i+3)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack,[(dout_off0.uc().x,dout_off0.ll().y),
                                      (dout_off0.uc().x,dout_off1_y),
                                      (x_off,dout_off1_y), (x_off,dout_off3_y),
                                      (dout_off1.uc().x,dout_off3_y),
                                      (dout_off1.uc().x,dout_off1.ll().y)]) 
                        
                        x_off = self.inbank_inst[1].lr().x+(i+3)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack, [(dout_off3.uc().x,dout_off3.ll().y),
                                      (dout_off3.uc().x,dout_off2_y),
                                      (x_off,dout_off2_y), (x_off,dout_off3_y),
                                      (dout_off2.uc().x,dout_off3_y),
                                      (dout_off2.uc().x,dout_off2.ll().y)]) 

                        x_off = self.inbank_inst[1].lr().x+(i+self.word_size+3)*self.m_pitch("m1")
                        self.add_wire(self.m1_stack, 
                                      [(self.inbank_inst[1].lr().x, din_off1.y+0.5*self.m1_width),
                                      (x_off, din_off1.y+0.5*self.m1_width),
                                      (x_off, din_off2.y+0.5*self.m1_width),
                                      (self.inbank_inst[1].lr().x, din_off2.y+0.5*self.m1_width)])


        if (self.num_outbanks == 2 or self.outbank_orien == "H"):
            # Addr Connections
            for k in range(self.num_outbanks):
                for i in range(self.inbank_addr_size):
                    addr_off = vector(self.inbank_inst[k].get_pin("addr[{0}]".format(i)).ll().x,
                                         self.addr_bus_off.y+ i*self.m_pitch("m1")+ \
                                         0.5*self.m1_width) 
                              
                    addr_height =  self.inbank_inst[k].get_pin("addr[{0}]".format(i)).ll().y - \
                                   self.addr_bus_off.y - i*self.m_pitch("m1")

                    self.add_rect(layer="metal2", 
                                  offset=addr_off, 
                                  width=self.m2_width, 
                                  height=addr_height)
                    self.add_via(self.m1_stack, addr_off)
        
            # sel Connections
            for k in range(self.num_outbanks):
               sel_off = vector(self.inbank_inst[k].get_pin("S").ll().x,
                                   self.H_ctrl_bus_pos["sel[{0}]".format(k)][1] - 0.5*self.m1_width)
               sel_heigh =  self.inbank_inst[k].get_pin("S").lc().y - \
                            self.H_ctrl_bus_pos["sel[{0}]".format(k)][1]
            
               self.add_rect(layer="metal2", 
                             offset=sel_off, 
                             width=self.m2_width, 
                             height=sel_heigh)
               self.add_via(self.m1_stack, sel_off)
               self.add_via(self.m1_stack, (sel_off.x,self.inbank_inst[k].get_pin("S").ll().y ))
            
            # control signal Connections
            for k in range(self.num_outbanks):
                # Connect the split nodes in split_list to nodes in split_ctrl_list (keep the order)
                split_list = ["wack", "wreq",  "rreq", "rack", "ack", "rw",  "w", "r",
                              "ack_merge", "rw_en1_S", "rw_en2_S", "Mack_S", "Mrack_S", "Mwack_S"]
                split_ctrl_list = ["pre_wack", "wreq",  "rreq", "pre_rack", "pre_ack", "rw",  "w",
                                      "r", "ack{0}".format(k), "ack_b{0}".format(k), "ack_b", 
                                      "rw_merge", "rreq", "wreq"]
                for i in range(len(split_list)):
                    split_off = vector(self.inbank_inst[k].get_pin(split_list[i]).ll().x,
                                          self.H_ctrl_bus_pos[split_ctrl_list[i]][1]- \
                                          0.5*self.m1_width)
                    split_heigh =  self.inbank_inst[k].get_pin(split_list[i]).ll().y - \
                               self.H_ctrl_bus_pos[split_ctrl_list[i]][1] + 0.5*self.m1_width
                    self.add_rect(layer="metal2", 
                                  offset=split_off, 
                                  width=self.m2_width, 
                                  height=split_heigh)
                    self.add_via(self.m1_stack, split_off)
        
        
            # vdd and gnd Connections
            power_pin=["vdd", "gnd"]
            for i in range(2):
                for k in range(self.num_outbanks):
                    pow_pin = self.inbank_inst[k].get_pin(power_pin[i])
                    if (k%2 or self.outbank_orien == "V"):
                        pow_off = vector(pow_pin.ll().x-(i+1)*self.m_pitch("m1"), 
                                            self.power1_off.y+i*self.power_pitch+0.5*self.m1_width)
                    else:
                        pow_off = vector(pow_pin.lr().x+(i+1)*self.m_pitch("m1"), 
                                            self.power1_off.y+i*self.power_pitch+0.5*self.m1_width)

                    self.add_wire(self.m1_stack,[pow_off,(pow_off.x,pow_pin.lc().y),
                                                (pow_pin.lr().x,pow_pin.lc().y)]) 
                    self.add_via(self.m1_stack, 
                                 (pow_off.x-0.5*self.m1_width, pow_off.y))
            
            for k in range(self.num_outbanks):
                reset_pin = self.inbank_inst[k].get_pin("reset")
                if (k%2 or self.outbank_orien == "V") :
                    reset_off = vector(reset_pin.ll().x-3*self.m_pitch("m1"), 
                                  self.reset1_off.y + 0.5*self.m1_width)
                else:
                    reset_off = vector(reset_pin.lr().x+3*self.m_pitch("m1"), 
                                  self.reset1_off.y + 0.5*self.m1_width)

                self.add_wire(self.m1_stack, [reset_off,(reset_off.x,reset_pin.lc().y),
                                             (reset_pin.lr().x,reset_pin.lc().y)]) 
                self.add_via(self.m1_stack, (reset_off.x-0.5*self.m1_width, reset_off.y))

            # split_merge_control_inst Connections
            ctrl_pin_list = ["wack", "wreq",  "rreq", "rack", "ack", "rw",  "w", "r", 
                                "ack_b", "rw_merge", "pre_ack", "pre_wack", "pre_rack"]
            for k in range(self.num_outbanks):
                ctrl_pin_list.extend(["ack{0}".format(k), "ack_b{0}".format(k)])
            for i in range(len(ctrl_pin_list)):
                ctrl_off = vector(self.out_split_mrg_ctrl_inst.get_pin(ctrl_pin_list[i]).ll().x,
                                     self.H_ctrl_bus_pos[ctrl_pin_list[i]][1]-0.5*self.m1_width)
                ctrl_heigh =  self.out_split_mrg_ctrl_inst.get_pin(ctrl_pin_list[i]).ll().y - \
                              self.H_ctrl_bus_pos[ctrl_pin_list[i]][1]+ 0.5*self.m1_width
                self.add_rect(layer="metal2", 
                              offset=ctrl_off, 
                              width=self.m2_width, 
                              height=ctrl_heigh)
                self.add_via(self.m1_stack, ctrl_off)        
            
            
            power_pin =["vdd", "gnd"]
            for i in range(2):
                power_off = vector(self.out_split_mrg_ctrl_inst.get_pin(power_pin[i]).ll().x,
                                      self.power1_off.y + i*self.power_pitch + 0.5*self.m1_width)
                power_heigh =  self.out_split_mrg_ctrl_inst.get_pin(power_pin[i]).ll().y - \
                           self.power1_off.y - i*self.power_pitch + 0.5*self.m1_width

                self.add_rect(layer="metal2", 
                          offset=power_off, 
                          width=self.m2_width, 
                          height=power_heigh)
                self.add_via(self.m1_stack, power_off)        

            if self.num_outbanks == 2:
                addr_pin = ["addr[0]","sel[0]", "sel[1]"]
            if self.num_outbanks == 4:
                addr_pin = ["addr[0]","addr[1]", 
                        "sel[0]", "sel[1]", "sel[2]", "sel[3]"]
            for i in range(len(addr_pin)):
                addr_off = vector(self.out_split_mrg_ctrl_inst.get_pin(addr_pin[i]).ll().x,
                                  self.addr_bus_off.y + 0.5*self.m1_width + \
                                  (i+self.inbank_addr_size)*self.m_pitch("m1"))
                addr_heigh =  self.out_split_mrg_ctrl_inst.get_pin(addr_pin[i]).ll().y - \
                              self.addr_bus_off.y - (i+self.inbank_addr_size)*self.m_pitch("m1") +\
                              0.5*self.m1_width
                self.add_rect(layer="metal2", 
                              offset=addr_off, 
                              width=self.m2_width, 
                              height=addr_heigh)
                self.add_via(self.m1_stack, addr_off)        

        if (self.num_outbanks == 4 and self.outbank_orien == "V"):
            # Addr Connections
            for k in range(self.num_outbanks/2):
                for i in range(self.inbank_addr_size):
                    addr1_off = vector(self.inbank_inst[k].get_pin("addr[{0}]".format(i)).ll().x,
                                          self.addr_bus_off.y+ i*self.m_pitch("m1")+ \
                                          0.5*self.m1_width) 
                    addr1_height =  self.inbank_inst[k].get_pin("addr[{0}]".format(i)).ll().y - \
                                    self.addr_bus_off.y - i*self.m_pitch("m1")
                    addr2_off = vector(self.inbank_inst[k+2].get_pin("addr[{0}]".format(i)).ll().x,
                                          self.addr_bus2_off.y+ i*self.m_pitch("m1")+ \
                                          0.5*self.m1_width) 
                    addr2_height =  self.inbank_inst[k+2].get_pin("addr[{0}]".format(i)).ll().y - \
                                    self.addr_bus2_off.y - i*self.m_pitch("m1")

                    self.add_rect(layer="metal2", 
                                  offset=addr1_off, 
                                  width=self.m2_width, 
                                  height=addr1_height)
                    self.add_via(self.m1_stack, addr1_off)
                    self.add_rect(layer="metal2", 
                                  offset=addr2_off, 
                                  width=self.m2_width, 
                                  height=addr2_height)
                    self.add_via(self.m1_stack, addr2_off)
                    
                    x_off = self.inbank_inst[1].lr().x+(i+2*self.word_size+3)*self.m_pitch("m1")
                    self.add_wire(self.m1_stack, 
                                  [(self.inbank_inst[1].lr().x, addr1_off.y+0.5*self.m1_width),
                                  (x_off, addr1_off.y+0.5*self.m1_width),
                                  (x_off, addr2_off.y+0.5*self.m1_width),
                                  (self.inbank_inst[1].lr().x, addr2_off.y+0.5*self.m1_width)])
                    
            # sel Connections
            for k in range(self.num_outbanks/2):
                sel1_off = vector(self.inbank_inst[k].get_pin("S").ll().x,
                                     self.H_ctrl_bus_pos["sel[{0}]".format(k)][1]-0.5*self.m1_width)
                sel1_heigh =  self.inbank_inst[k].get_pin("S").lc().y - \
                                   self.H_ctrl_bus_pos["sel[{0}]".format(k)][1]
                sel2_off = vector(self.inbank_inst[k+2].get_pin("S").ll().x,
                                     self.H2_ctrl_bus_pos["sel[{0}]".format(k+2)][1]-\
                                     0.5*self.m1_width)
                sel2_heigh =  self.inbank_inst[k+2].get_pin("S").lc().y - \
                              self.H2_ctrl_bus_pos["sel[{0}]".format(k+2)][1]
            
                self.add_rect(layer="metal2", 
                              offset=sel1_off, 
                              width=self.m2_width, 
                              height=sel1_heigh)
                self.add_via(self.m1_stack,  sel1_off)
                self.add_via(self.m1_stack, 
                             (sel1_off.x,self.inbank_inst[k].get_pin("S").ll().y ))

                self.add_rect(layer="metal2", 
                              offset=sel2_off, 
                              width=self.m2_width, 
                              height=sel2_heigh)
                self.add_via(self.m1_stack, sel2_off)
                self.add_via(self.m1_stack, 
                             (sel2_off.x,self.inbank_inst[k+2].get_pin("S").ll().y ))

            # control signal Connections
            for k in range(self.num_outbanks/2):
                # Connect the split nodes in split_list to nodes in split_ctrl_list (kepp the order)
                split_list = ["wack", "wreq",  "rreq", "rack", "ack", "rw",  "w", "r",
                              "ack_merge", "rw_en1_S", "rw_en2_S", "Mack_S", "Mrack_S", "Mwack_S"]
                split_ctrl_list1 = ["pre_wack", "wreq",  "rreq", "pre_rack", "pre_ack", "rw",  "w", 
                                    "r", "ack{0}".format(k), "ack_b{0}".format(k), "ack_b", 
                                    "rw_merge", "rreq", "wreq"]
                split_ctrl_list2 = ["pre_wack", "wreq",  "rreq", "pre_rack", "pre_ack", "rw", "w", 
                                    "r", "ack{0}".format(k+2), "ack_b{0}".format(k+2), "ack_b", 
                                    "rw_merge", "rreq", "wreq"]

                for i in range(len(split_list)):
                    split1_off = vector(self.inbank_inst[k].get_pin(split_list[i]).ll().x,
                                           self.H_ctrl_bus_pos[split_ctrl_list1[i]][1]- \
                                           0.5*self.m1_width)
                    split1_heigh =  self.inbank_inst[k].get_pin(split_list[i]).ll().y - \
                                    self.H_ctrl_bus_pos[split_ctrl_list1[i]][1] + 0.5*self.m1_width
                    self.add_rect(layer="metal2", 
                                  offset=split1_off, 
                                  width=self.m2_width, 
                                  height=split1_heigh)
                    self.add_via(self.m1_stack, split1_off)
                    split2_off = vector(self.inbank_inst[k+2].get_pin(split_list[i]).ll().x,
                                           self.H2_ctrl_bus_pos[split_ctrl_list2[i]][1]- \
                                           0.5*self.m1_width)
                    split2_heigh =  self.inbank_inst[k+2].get_pin(split_list[i]).ll().y - \
                                    self.H2_ctrl_bus_pos[split_ctrl_list2[i]][1] + 0.5*self.m1_width
                    self.add_rect(layer="metal2", 
                                  offset=split2_off, 
                                  width=self.m2_width, 
                                  height=split2_heigh)
                    self.add_via(self.m1_stack, split2_off)

        
            # vdd and gnd Connections
            for k in range(self.num_outbanks/2):
                vdd1_pin = self.inbank_inst[k].get_pin("vdd")
                vdd1_off = vector(vdd1_pin.ll().x-self.m_pitch("m1"), 
                                     self.power1_off.y+0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [vdd1_off,(vdd1_off.x, vdd1_pin.lc().y),
                                (vdd1_pin.lr().x, vdd1_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (vdd1_off.x-0.5*self.m1_width, vdd1_off.y))
        
                gnd1_pin = self.inbank_inst[k].get_pin("gnd")
                gnd1_off = vector(gnd1_pin.ll().x-2*self.m_pitch("m1"), 
                                     self.power1_off.y + self.power_pitch + 0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [gnd1_off,(gnd1_off.x, gnd1_pin.lc().y),
                                (gnd1_pin.lr().x, gnd1_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (gnd1_off.x-0.5*self.m1_width, gnd1_off.y))
                
                reset1_pin = self.inbank_inst[k].get_pin("reset")
                reset1_off = vector(reset1_pin.ll().x-3*self.m_pitch("m1"), 
                                     self.reset1_off.y + 0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [reset1_off,(reset1_off.x, reset1_pin.lc().y),
                                (reset1_pin.lr().x, reset1_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (reset1_off.x-0.5*self.m1_width, reset1_off.y))

            
                vdd2_pin = self.inbank_inst[k+2].get_pin("vdd")
                vdd2_off = vector(vdd2_pin.ll().x-self.m_pitch("m1"), 
                                     self.power2_off.y+0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [vdd2_off,(vdd2_off.x, vdd2_pin.lc().y),
                                           (vdd2_pin.lr().x, vdd2_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (vdd2_off.x-0.5*self.m1_width, vdd2_off.y))
        
                gnd2_pin = self.inbank_inst[k+2].get_pin("gnd")
                gnd2_off = vector(gnd2_pin.ll().x-2*self.m_pitch("m1"), 
                                     self.power2_off.y + self.power_pitch + 0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [gnd2_off,(gnd2_off.x, gnd2_pin.lc().y),
                                           (gnd2_pin.lr().x, gnd2_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (gnd2_off.x-0.5*self.m1_width, gnd2_off.y))

                reset2_pin = self.inbank_inst[k+2].get_pin("reset")
                reset2_off = vector(reset2_pin.ll().x-3*self.m_pitch("m1"), 
                                     self.reset2_off.y + 0.5*self.m1_width)
                self.add_wire(self.m1_stack,
                              [reset2_off,(reset2_off.x, reset2_pin.lc().y),
                                          (reset2_pin.lr().x, reset2_pin.lc().y)]) 
                self.add_via(self.m1_stack, 
                             (reset2_off.x-0.5*self.m1_width, reset2_off.y))

            reset_xoff = self.inbank_inst[1].lr().x+\
                         (self.inbank_addr_size+2*self.word_size+3)*self.m_pitch("m1")
            self.add_wire(self.m1_stack, 
                          [(self.inbank_inst[1].lr().x, self.reset1_off.y+self.m1_width),
                          (reset_xoff, self.reset1_off.y+self.m1_width),
                          (reset_xoff, self.reset2_off.y+self.m1_width),
                          (self.inbank_inst[1].lr().x, self.reset2_off.y+self.m1_width)])

            
            
            # split_merge_control_inst Connections
            ctrl_pin_list = ["wack", "wreq",  "rreq", "rack", "ack", "rw",  "w", "r", 
                            "ack_b", "rw_merge", "pre_ack", "pre_wack", "pre_rack"]
            for k in range(self.num_outbanks):
                ctrl_pin_list.extend(["ack{0}".format(k), "ack_b{0}".format(k)])
            for i in range(len(ctrl_pin_list)):
                ctrl_off = vector(self.out_split_mrg_ctrl_inst.get_pin(ctrl_pin_list[i]).ll().x,
                                     self.H_ctrl_bus_pos[ctrl_pin_list[i]][1]- 0.5*self.m1_width)
                ctrl2_off = vector(self.out_split_mrg_ctrl_inst.get_pin(ctrl_pin_list[i]).ll().x,
                                      self.H2_ctrl_bus_pos[ctrl_pin_list[i]][1]- 0.5*self.m1_width)

                ctrl_heigh =  self.out_split_mrg_ctrl_inst.get_pin(ctrl_pin_list[i]).ll().y - \
                              self.H_ctrl_bus_pos[ctrl_pin_list[i]][1]+ 0.5*self.m1_width

                self.add_rect(layer="metal2", 
                              offset=ctrl_off, 
                              width=self.m2_width, 
                              height=ctrl_heigh)
                self.add_via(self.m1_stack, ctrl_off)
                self.add_via(self.m1_stack, ctrl2_off)        
            
            power_pin =["vdd", "gnd"]
            for i in range(2):
                power_off = vector(self.out_split_mrg_ctrl_inst.get_pin(power_pin[i]).ll().x,
                                   self.power1_off.y + i*self.power_pitch + 0.5*self.m1_width)

                power2_off = vector(self.out_split_mrg_ctrl_inst.get_pin(power_pin[i]).ll().x,
                                    self.power2_off.y + i*self.power_pitch + 0.5*self.m1_width)
                power_heigh =  self.out_split_mrg_ctrl_inst.get_pin(power_pin[i]).ll().y - \
                               self.power1_off.y - i*self.power_pitch + 0.5*self.m1_width

                self.add_rect(layer="metal2", 
                              offset=power_off, 
                              width=self.m2_width, 
                              height=power_heigh)
                self.add_via(self.m1_stack, power_off)
                self.add_via(self.m1_stack, power2_off)                

            if self.num_outbanks == 2:
                addr_pin = ["addr[0]","sel[0]", "sel[1]"]
            if self.num_outbanks == 4:
                addr_pin = ["addr[0]","addr[1]", "sel[0]", "sel[1]", "sel[2]", "sel[3]"]
            for i in range(len(addr_pin)):
                addr_off = vector(self.out_split_mrg_ctrl_inst.get_pin(addr_pin[i]).ll().x,
                                     self.addr_bus_off.y + 0.5*self.m1_width + \
                                     (i+self.inbank_addr_size)*self.m_pitch("m1"))
                addr2_off = vector(self.out_split_mrg_ctrl_inst.get_pin(addr_pin[i]).ll().x,
                                      self.addr_bus2_off.y + 0.5*self.m1_width + \
                                      (i+self.inbank_addr_size)*self.m_pitch("m1"))

                addr_heigh =  self.out_split_mrg_ctrl_inst.get_pin(addr_pin[i]).ll().y - \
                              self.addr_bus_off.y - (i+self.inbank_addr_size)*self.m_pitch("m1") +\
                              0.5*self.m1_width
                self.add_rect(layer="metal2", 
                              offset=addr_off, 
                              width=self.m2_width, 
                              height=addr_heigh)
                self.add_via(self.m1_stack, addr_off)
                self.add_via(self.m1_stack, addr2_off)        

        # select= vdd Connection
        sel_pos1=self.out_split_mrg_ctrl_inst.get_pin("S").uc()
        sel_pos2=self.out_split_mrg_ctrl_inst.get_pin("vdd").uc()
        pos1=vector(sel_pos1.x, sel_pos1.y-2*self.m_pitch("m1"))
        pos2=vector(sel_pos2.x, sel_pos1.y-2*self.m_pitch("m1"))
        self.add_wire(self.m1_stack, [sel_pos1, pos1, pos2, sel_pos2])
    
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
