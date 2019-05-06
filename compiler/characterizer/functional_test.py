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



""" This file generates simple spice cards for simulation.  There are
various functions that can be be used to generate stimulus for other
simulations as well. """

import tech
import debug
import subprocess
import os, sys, shutil
from os import path
import charutils 
import numpy as np
from globals import OPTS, get_tool
import time
import design
import math
import trim_spice


class functional_test():
    """ Class for providing stimuli and decks for functional verification """

    def __init__(self, size, corner, name, w_per_row, num_rows, load=tech.spice["input_cap"], slew=tech.spice["rise_time"]):
        self.vdd_name = tech.spice["vdd_name"]
        self.gnd_name = tech.spice["gnd_name"]
        self.voltage = tech.spice["nom_supply_voltage"]
        self.name = name
        self.w_per_row = w_per_row
        self.num_rows = num_rows

        self.deck_file = "test.sp"
        self.test = open(OPTS.AMC_temp+"test.v", "w")
        self.dut = open(OPTS.AMC_temp+"dut.sp", "w")
        self.deck = open(OPTS.AMC_temp+"test.sp", "w")
        self.source = open(OPTS.AMC_temp+"source.v", "w")
        self.cosim = open(OPTS.AMC_temp+"cosim.cfg", "w")
        self.make = open(OPTS.AMC_temp+"Makefile", "w")
        
        (self.addr_bit, self.data_bit) = size
        (self.process, self.voltage, self.temperature) = corner
        self.device_models = tech.SPICE_MODEL_DIR
        
        self.run_sim(load, slew)
    
    def inst_sram(self, abits, dbits, suffix, sram_name):
        """ Function to instatiate an SRAM subckt. """
        
        self.dut.write("X{0} ".format(sram_name))
        for i in range(dbits):
            self.dut.write("DIN{0}{1} ".format(i, suffix))
        for i in range(dbits):
            self.dut.write("DOUT{0}{1} ".format(i,suffix))
        for i in range(abits):
            self.dut.write("ADDR{0}{1} ".format(i, suffix))
        self.dut.write("reset ")
        for i in ["r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"]:
            self.dut.write("{0}{1} ".format(i, suffix))
        self.dut.write("{0} {1} ".format(self.vdd_name, self.gnd_name))
        self.dut.write("{0}\n".format(sram_name))


    def dut_generator(self, abits, dbits, load, sram_name, w_per_row, num_rows):
        """ Function to write DUT netlist. """
        
        self.pmos_name = tech.spice["pmos"]
        self.nmos_name = tech.spice["nmos"]
        self.minwidth_tx = tech.drc["minwidth_tx"]
        self.minlength_tx = tech.drc["minlength_channel"]
        spice_name=sram_name

        self.dut.write("\n ")

        self.dut.write(".inc {0}.sp\n\n".format(spice_name))
        #self.dut.write("V{0} {0} 0 dc {1}v\n".format("test"+self.vdd_name, self.voltage))
        #self.dut.write("V{0} {0} 0 dc 0.0v\n".format("test"+self.gnd_name))
        self.dut.write("\n")
        self.dut.write(".subckt DUT ")
        for i in range(dbits):
            self.dut.write("DIN{0}_ ".format(i))
        for i in range(dbits):
            self.dut.write("DOUT{0}_ ".format(i))
        for i in range(abits):
            self.dut.write("ADDR{0}_ ".format(i))
        for i in ["reset", "r_", "w_", "rw_", "ack_", "rack_", "rreq_", "wreq_", "wack_"]:
            self.dut.write("{0} ".format(i))
        self.dut.write("{0} {1} ".format(self.vdd_name, self.gnd_name))
        self.dut.write("\n")
        self.inst_sram(abits, dbits, "_", sram_name)
        self.dut.write(".ends\n")

        self.dut.write("\n")
        self.create_buffer()

        self.dut.write(".subckt wrapper ")
        for i in range(dbits):
            self.dut.write("DIN{0} ".format(i))
        for i in range(dbits):
            self.dut.write("DOUT{0} ".format(i))
        for i in range(abits):
            self.dut.write("ADDR{0} ".format(i))
        for i in ["reset", "r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"]:
            self.dut.write("{0} ".format(i))
        self.dut.write("\n")
        
        self.inst_sram(abits, dbits, "_buf", "DUT")
        self.dut.write("\n")

        
        din_list=[]
        for i in range(dbits):
            din_list.append("DIN{0}".format(i))
        addr_list=[]
        for i in range(abits):
            addr_list.append("ADDR{0}".format(i))
        dout_list=[]
        for i in range(dbits):
            dout_list.append("DOUT{0}".format(i))

        ctrl_list1 =["r", "w", "rw", "rreq", "wreq"]
        ctrl_list2 =["ack", "wack", "rack"]
        self.add_in_buffer(din_list)
        self.dut.write("\n")
        self.add_in_buffer(addr_list)
        self.dut.write("\n")
        self.add_in_buffer(ctrl_list1)
        self.dut.write("\n")
        self.add_out_buffer(dout_list)
        self.dut.write("\n")
        self.add_out_buffer(ctrl_list2)
        self.dut.write("\n")

        self.add_cap_load(dout_list, load)
        ctrl_list2 =["ack", "rack", "wack"]
        self.dut.write("\n")
        self.add_cap_load(ctrl_list2, load)
        self.dut.write("\n")
        self.dut.write(".ends\n")

        self.dut.close()

    def spice_deck(self, slew, load):
        """ Function to write the HSIM spice deck. """
        
        self.deck.write("* HSIM SPICE DECK for slew = {0} and load = {1}\n\n".format(slew, load))
        self.deck.write(".param HSIMVDD={0}v\n".format(self.voltage))
        self.deck.write(".param HSIMALLOWEDDV={0}v\n".format(0.1*self.voltage))
        self.deck.write(".param HSIMVHTH={0}v\n".format(0.9*self.voltage))
        self.deck.write(".param HSIMVLTH={0}v\n".format(0.1*self.voltage))
        self.deck.write(".param HSIMPWNAME={0}\n".format(self.vdd_name))
        self.deck.write(".param HSIMPWNAME={0}\n".format(self.gnd_name))
        self.deck.write(".param HSIMOUTPUT=\"fsdb\"\n")
        self.deck.write(".param HSIMNODECAP=\"*\"\n")
        self.deck.write(".param HSIMMODELSTAT=1\n")
        self.deck.write(".param HSIMSPICE=3\n")
        self.deck.write(".param HSIMSPEED=1\n")
        self.deck.write(".param HSIMANALOG=2\n")
        self.deck.write(".param HSIMMEASOUT=0\n")
        self.deck.write(".param HSIMFLAT=1\n")
        self.deck.write(".param HSIMITERMODE=2\n")
        self.deck.write(".param HSIMIGISUB=1\n")
        self.deck.write(".param HSIMCONNCHECK=1\n")
        self.deck.write(".param HSIMCHECKMOSBULK=1\n")
        self.deck.write(".param HSIMRISE={0}ns\n".format(slew))
        self.deck.write(".param HSIMFALL={0}ns\n\n".format(slew))
        self.deck.write(".global {0} {1}\n".format(self.vdd_name, self.gnd_name))
        self.deck.write("vpwr0 {0} 0 dc {1}v\n".format(self.vdd_name, self.voltage))
        self.deck.write("vpwr1 {0} 0 dc {1}v\n\n".format(self.gnd_name, 0))
        if tech.info["name"]=="scn3me_subm":
            self.deck.write(".inc {0}{1}_on_c5n.mod\n".format(self.device_models, self.process))
        else:
            self.deck.write(".lib {0} {1}\n".format(self.device_models, self.process))
        self.deck.write(".inc dut.sp\n\n")
        self.deck.write(".print v(*)\n")
        self.deck.write(".lprint {0} {1} v(*)\n".format(0.1*self.voltage, 0.9*self.voltage))
        self.deck.write(".print in(vdd)\n")
        self.deck.write(".print in(gnd)\n\n")
        
        self.gen_meas_delay("write_delay", "w", "ack", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "RISE", 3, 3, "1n")
        self.gen_meas_delay("read_delay", "r", "ack", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "RISE", 2, 6, "1n")
        self.gen_meas_delay("read_write_delay", "rw", "ack", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "RISE", 2, 9, "1n")
        
        self.gen_meas_delay("slew_hl", "r", "r", 
                           (0.9*self.voltage), (0.1*self.voltage), 
                           "FALL", "FALL", 1, 1, "0.001n")
        self.gen_meas_delay("slew_lh", "r", "r", 
                           (0.1*self.voltage), (0.9*self.voltage), 
                           "RISE", "RISE", 1, 1, "0.001n")

        self.gen_meas_delay("w_intvl", "w", "w", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "FALL", 1, 4, "0.001n")
        self.gen_meas_delay("r_intvl", "r", "r", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "FALL", 1, 3, "0.001n")
        self.gen_meas_delay("rw_intvl", "rw", "rw", 
                           (0.5*self.voltage), (0.5*self.voltage), 
                           "RISE", "FALL", 1, 3, "0.001n")

        self.gen_meas_power("leakage_power", "1n", "4n")
        
        self.gen_meas_current("write_current", "5n", "w_intvl+5n")
        self.gen_meas_current("read_current", "w_intvl+5n", "w_intvl+r_intvl+5n")
        self.gen_meas_current("read_write_current", "w_intvl+r_intvl+5n", "w_intvl+r_intvl+rw_intvl+5n")
        
        self.deck.write(".measure write_power param=vdd*write_current\n")
        self.deck.write(".measure read_power param=vdd*read_current\n")
        self.deck.write(".measure read_write_power param=vdd*read_write_current\n")
        
        self.deck.write(".end\n")
        self.deck.close()
        

    def gen_meas_delay(self, meas_name, trig_name, targ_name, trig_val, targ_val, trig_dir, targ_dir, trig_num, targ_num, trig_td):
        """ Creates the .measure statement for the measurement of delay, setup and hold"""
        
        measure_string=".measure tran {0} TRIG V({1}) VAL={2} {3}={4} TD={5} TARG V({6}) VAL={7} {8}={9}\n"
        self.deck.write(measure_string.format(meas_name, trig_name, trig_val, trig_dir, trig_num, trig_td,
                                              targ_name, targ_val, targ_dir, targ_num))
    
    def gen_meas_power(self, meas_name, start, stop):
        """ Creates the .measure statement for the measurement of power """
        
        power_exp = "par('(-1*V(vdd)*I(vpwr0))')"
        measure_string=".measure tran {0} AVG {1} from={2} to={3}\n"
        self.deck.write(measure_string.format(meas_name, power_exp, start, stop))

    def gen_meas_current(self, meas_name, start, stop):
        """ Creates the .measure statement for the measurement of current """
        
        measure_string=".measure tran {0} integ I(vpwr0) from={1} to={2}\n"
        self.deck.write(measure_string.format(meas_name, start, stop))
    
    def verilog_testbench(self,abits, dbits):
        """ Function to write the Verilog Testbench. """
        
        self.test.write("`timescale 1ns / 100ps;\n")
        self.test.write("`include \"source.v\"\n")
        self.test.write("`define WORD_SIZE {0};\n".format(dbits))
        self.test.write("`define ADDR_SIZE {0};\n\n".format(abits))
        self.test.write("module wrapper( ")
        for i in range(dbits):
            self.test.write("DIN{0}, ".format(i))
        for i in range(dbits):
            self.test.write("DOUT{0}, ".format(i))
        for i in range(abits):
            self.test.write("ADDR{0}, ".format(i))
        for i in ["reset", "r", "w", "rw", "ack", "rack", "rreq", "wreq"]:
            self.test.write("{0}, ".format(i))
        
        self.test.write("wack);\n")
        for i in range(dbits):
            self.test.write("    input DIN{0};\n".format(i))
        for i in range(dbits):
            self.test.write("    output DOUT{0};\n".format(i))
        for i in range(abits):
            self.test.write("    input ADDR{0};\n".format(i))
        for i in ["reset", "r", "w", "rw", "rreq", "wreq"]:
            self.test.write("    input {0};\n".format(i))
        for i in ["ack", "rack", "wack"]:
            self.test.write("    output {0};\n".format(i))
        self.test.write("    initial $nsda_module();\n")
        self.test.write("endmodule\n\n")

        self.test.write("module top;\n")
        self.test.write("    parameter WORD_SIZE = `WORD_SIZE;\n")
        self.test.write("    parameter ADDR_SIZE = `ADDR_SIZE;\n")
        for i in range(dbits):
            self.test.write("    wire DIN{0};\n".format(i))
        for i in range(dbits):
            self.test.write("    wire DOUT{0};\n".format(i))
        for i in range(abits):
            self.test.write("    wire ADDR{0};\n".format(i))
        for i in ["r", "w", "rw", "ack", "rack", "rreq", "wreq", "wack"]:
            self.test.write("    wire {0};\n".format(i))
        self.test.write("    wire [WORD_SIZE-1:0] Data_In;\n")
        self.test.write("    wire [ADDR_SIZE-1:0] Addr_In;\n")
        for i in ["r_In", "w_In", "rw_In", "rreq_In", "wreq_In"]:
            self.test.write("    wire {0};\n".format(i))
        for i in ["reset", "{0}".format(self.vdd_name), "{0}".format(self.gnd_name)]:
            self.test.write("    reg {0};\n".format(i))
        self.test.write("    initial begin\n")
        self.test.write("        $timeformat(-12, 0, \"psec\", 10);\n")
        self.test.write("        {0} = 1;\n".format(self.vdd_name))
        self.test.write("        {0} = 0;\n".format(self.gnd_name))
        self.test.write("        reset = 1;\n")
        self.test.write("        #5 reset = 0;\n")
        self.test.write("        #100 $finish;\n")
        self.test.write("    end\n")
        
        self.test.write("    source inputs(.Reset(reset), .DATA(Data_In), .ADDR(Addr_In), ")
        self.test.write(".R(r_In), .W(w_In), .RW(rw_In), .RREQ(rreq_In), .WREQ(wreq_In), ")
        self.test.write(".RACK(rack), .ACK(ack));\n\n")
        
        self.test.write("    assign{ ")
        for i in range(dbits-1):
            self.test.write("DIN{0}, ".format(i))
        self.test.write("DIN{0}".format(dbits))
        self.test.write("} = Data_In;\n\n")
        self.test.write("    assign{ ")
        for i in range(abits-1):
            self.test.write("ADDR{0}, ".format(i))
        self.test.write("ADDR{0}".format(abits))
        self.test.write("} = Addr_In;\n\n")
        self.test.write("    assign{ ")
        for i in ["r", "w", "rw", "rreq"]:
            self.test.write("{0}, ".format(i))
        self.test.write("wreq} = {r_In, w_In, rw_In, rreq_In, wreq_In};\n\n")
        self.test.write("    wrapper dut(")
        for i in range(dbits):
            self.test.write("DIN{0}, ".format(i))
        for i in range(dbits):
            self.test.write("DOUT{0}, ".format(i))
        for i in range(abits):
            self.test.write("ADDR{0}, ".format(i))
        for i in ["reset", "r", "w", "rw", "ack", "rack", "rreq", "wreq"]:
            self.test.write("{0}, ".format(i))
        self.test.write("wack);\n\n")
        for i in ["reset", "r", "w", "rw", "ack", "rreq", "rack", "wreq", "wack"]:
            self.test.write("    always @(posedge {0}) begin \n".format(i))
            self.test.write("        $display(\"     %t {0} : 1\", $time);\n".format(i))
            self.test.write("    end\n")
            self.test.write("    always @(negedge {0}) begin \n".format(i))
            self.test.write("        $display(\"     %t {0} : 0\", $time);\n".format(i))
            self.test.write("    end\n")
        self.test.write("endmodule")
        self.test.close()

    def source_generator(self,abits, dbits, delay, slew):
        """ Function to write the Verilog input vectors. """
        
        self.source.write("`define WORD_SIZE {0};\n".format(dbits))
        self.source.write("`define ADDR_SIZE {0};\n\n".format(abits))
        self.source.write("module source(Reset, DATA, ADDR, R, W, RW, RREQ, WREQ, RACK, ACK);\n")
        self.source.write("    parameter WORD_SIZE = `WORD_SIZE;\n")
        self.source.write("    parameter ADDR_SIZE = `ADDR_SIZE;\n")
        self.source.write("    input Reset;\n")
        self.source.write("    input ACK;\n")
        self.source.write("    input RACK;\n")
        self.source.write("    output [WORD_SIZE-1:0]DATA;\n")
        self.source.write("    output [ADDR_SIZE-1:0]ADDR;\n")
        self.source.write("    output R;\n")
        self.source.write("    output W;\n")
        self.source.write("    output RW;\n")
        self.source.write("    output RREQ;\n")
        self.source.write("    output WREQ;\n\n")
        self.source.write("    reg [WORD_SIZE-1:0]DATA;\n")
        self.source.write("    reg [ADDR_SIZE-1:0]ADDR;\n")
        self.source.write("    reg R, W, RW, RREQ, WREQ;\n")
        self.source.write("    integer i, j, k;\n\n")
        self.source.write("    initial begin\n")
        self.source.write("        $display(\"Initializing....\", $time);\n")
        self.source.write("        DATA <= #{0} {1}'b0;\n".format(delay+slew, dbits))
        self.source.write("        ADDR <= #{0} {1}'b0;\n".format(delay+slew, abits))
        self.source.write("        R <= #{0} 0;\n".format(delay+slew))
        self.source.write("        W <= #{0} 0;\n".format(delay+slew))
        self.source.write("        RW <= #{0} 0;\n".format(delay+slew))
        self.source.write("        RREQ <= #{0} 0;\n".format(delay+slew))
        self.source.write("        WREQ <= #{0} 0;\n".format(delay+slew))
        self.source.write("    end\n\n")
        self.source.write("    always @(negedge Reset) begin\n")
        self.source.write("        $display(\"Negedge of Reset. Test begins....\", $time);\n")
        self.source.write("        W <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("        WREQ <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("        i <= 0;\n")
        self.source.write("        j <= 0;\n")
        self.source.write("        k <= 0;\n")
        self.source.write("    end\n\n")
        self.source.write("    always @(posedge ACK) begin\n")
        self.source.write("        R <= #{0} 0;\n".format(delay+slew))
        self.source.write("        W <= #{0} 0;\n".format(delay+slew))
        self.source.write("        RW <= #{0} 0;\n".format(delay+slew))
        self.source.write("        RREQ <= #{0} 0;\n".format(delay+slew))
        self.source.write("        WREQ <= #{0} 0;\n".format(delay+slew))
        self.source.write("        if (i < 4) begin\n")
        self.source.write("            i = i+1;\n")
        self.source.write("        end\n")
        self.source.write("        if (i == 4 & j != 4) begin\n")
        self.source.write("            j = j+1;\n")
        self.source.write("        end\n")
        self.source.write("        if (i == 4 & j== 4) begin\n")
        self.source.write("            k = k+1;\n")
        self.source.write("        end\n")
        self.source.write("    end\n\n")
        self.source.write("    always @(posedge RACK) begin\n")
        self.source.write("        if (RW) begin\n")
        self.source.write("            WREQ <= 1'b1;\n")
        self.source.write("        end\n")
        self.source.write("    end\n")
        self.source.write("    always @(negedge ACK) begin\n")
        self.source.write("        if (i<4) begin\n")
        self.source.write("            if (i%2==0) begin\n")
        self.source.write("                DATA <= #{0} {1}'b1;\n".format(delay+slew, dbits))
        self.source.write("                ADDR <= #{0} {1}'b1;\n".format(delay+slew, abits)) 
        self.source.write("            end else if (i%2==1) begin\n")
        self.source.write("                 ADDR <= #{0} {1}'b0;\n".format(delay+slew, abits))
        self.source.write("            end\n")
        self.source.write("            W <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("            WREQ <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("        end\n")
        self.source.write("        if (i == 4) begin\n")
        self.source.write("            if (j < 4) begin\n")
        self.source.write("                ADDR <= #{0} {1}'b1;\n".format(delay+slew, abits))
        self.source.write("                R <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("                RREQ <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("            end\n")
        self.source.write("        end\n")
        self.source.write("        if (i == 4 & j ==4) begin\n")
        self.source.write("            if (k < 4) begin\n")
        self.source.write("                if (k%2==0) begin\n")
        self.source.write("                    DATA <= #{0} {1}'b0;\n".format(delay+slew, dbits))
        self.source.write("                    ADDR <= #{0} {1}'b1;\n".format(delay+slew, abits)) 
        self.source.write("                end else if (k%2==1) begin\n")
        self.source.write("                    ADDR <= #{0} {1}'b0;\n".format(delay+slew, abits)) 
        self.source.write("                end\n")
        self.source.write("                RW <= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("                RREQ<= #{0} 1'b1;\n".format(delay+slew))
        self.source.write("            end\n")
        self.source.write("        end\n")
        self.source.write("    end\n")
        self.source.write("endmodule\n")
        self.source.close()        
        
    def cosim_config(self):
        """ Function to write cosim configuration file. """
        
        self.cosim.write("\n")
        self.cosim.write("    set_args {0}\n".format(self.deck_file))
        self.cosim.write("    analog_cell wrapper\n")
        self.cosim.close()

    def run_sim(self, load, slew):
        """Run hsim & VCS in batch mode and output rawfile to parse."""
        
        self.dut_generator(self.addr_bit, self.data_bit, load, self.name, self.w_per_row, self.num_rows)
        self.spice_deck(slew, load)
        self.verilog_testbench(self.addr_bit, self.data_bit)
        self.source_generator(self.addr_bit, self.data_bit, tech.spice["inv_delay"], slew)
        self.cosim_config()

        self.make.write("\n")
        self.make.write("all:\n")
        self.make.write("\tvcs -full64 +vpi -ad_hsim=cosim.cfg -load libvcshsim.so:cs_vpi_startup +cli+3 test.v\n")
        self.make.write("\t./simv +nsda+cosim.cfg 2>&1 | tee -i simv.log\n")
        self.make.write("clean:\n")
        self.make.write("\trm -rf ucli.key\n")
        self.make.write("\trm -rf simv.log\n")
        self.make.write("\trm -rf simv.daidir\n")
        self.make.write("\trm -rf simv\n")
        self.make.write("\trm -rf nsda_cosim.sp\n")
        self.make.close()
        
        
        for myfile in ["cosim.cfg", "test.sp", "test.v", "source.v", "dut.sp", "Makefile"]:
            filename="{0}{1}".format(OPTS.AMC_temp, myfile)
            while not path.exists(filename):
                time.sleep(1)
            else:
                os.chmod(filename, 0o777)
        
        os.chdir(OPTS.AMC_temp)
        spice_stdout = open("{0}spice_stdout.log".format(OPTS.AMC_temp), 'w')
        spice_stderr = open("{0}spice_stderr.log".format(OPTS.AMC_temp), 'w')


        retcode = subprocess.call("make", shell=True, stdout=spice_stdout, stderr=spice_stderr)
        spice_stdout.close()
        spice_stderr.close()

        if (retcode > 1):
            debug.error("Spice simulation error: " + cmd, -1)


        filename="{0}{1}".format(OPTS.AMC_temp, "hsim.mt")
        while not path.exists(filename):
                time.sleep(1)
        
        #Parse the hsim.mt file to repoert delay and power values.
        write_delay = charutils.parse_output("hsim", "write_delay")
        read_delay = charutils.parse_output("hsim", "read_delay")
        read_write_delay = charutils.parse_output("hsim", "read_write_delay")
        slew_hl = charutils.parse_output("hsim", "slew_hl")
        slew_lh = charutils.parse_output("hsim", "slew_lh")
        leakage_power = charutils.parse_output("hsim", "leakage_power")
        write_power = charutils.parse_output("hsim", "write_power")
        read_power = charutils.parse_output("hsim", "read_power")
        read_write_power = charutils.parse_output("hsim", "read_write_power")
        
        self.result = {"write_delay_lh" : write_delay*(10**9),
                       "write_delay_hl" : write_delay*(10**9),
                       "read_delay_lh" : read_delay*(10**9),
                       "read_delay_hl" : read_delay*(10**9),
                       "read_write_delay_lh" : read_write_delay*(10**9),
                       "read_write_delay_hl" : read_write_delay*(10**9),
                       "slew_hl" : slew_hl*(10**9),
                       "slew_lh" : slew_lh*1e9,
                       "leakage_power" : leakage_power*(10**3),
                       "read_power" : read_power*(10**3),
                       "write_power" : write_power*(10**3),
                       "read_write_power" : read_write_power*(10**3)}
        return self.result
        

    def create_buffer(self, size=[2,2], beta=2):
        """Generates buffer for top level signals (only for sim purposes). 
           Size is pair for PMOS, NMOS width multiple. It includes a beta of 2."""

        self.dut.write(".subckt test_buffer in out {0} {1}\n".format(self.vdd_name, self.gnd_name))
        self.dut.write("mpinv1 out_inv in {0} {0} {1} w={2}u l={3}u\n".format(self.vdd_name,
                                                                               self.pmos_name,
                                                                               beta * size[0] * self.minwidth_tx,
                                                                               self.minlength_tx))
        self.dut.write("mninv1 out_inv in {0} {0} {1} w={2}u l={3}u\n".format(self.gnd_name,
                                                                               self.nmos_name,
                                                                               size[0] * self.minwidth_tx,
                                                                               self.minlength_tx))
        self.dut.write("mpinv2 out out_inv {0} {0} {1} w={2}u l={3}u\n".format(self.vdd_name,
                                                                                self.pmos_name,
                                                                                beta * size[1] * self.minwidth_tx,
                                                                                self.minlength_tx))
        self.dut.write("mninv2 out out_inv {0} {0} {1} w={2}u l={3}u\n".format(self.gnd_name,
                                                                                self.nmos_name,
                                                                                size[1] * self.minwidth_tx,
                                                                                self.minlength_tx))
        self.dut.write(".ends test_buffer\n")


    def add_in_buffer(self, signal_list):
        """Adds buffers to each top level signal that is in signal_list (only for sim purposes)"""
        
        for signal in signal_list:
            self.dut.write("X{0}_buffer {0} {0}_buf {1} {2} test_buffer\n".format(signal,
                                                                                self.vdd_name,
                                                                                self.gnd_name))
    def add_out_buffer(self, signal_list):
        """Adds buffers to each top level signal that is in signal_list (only for sim purposes)"""
        
        for signal in signal_list:
            self.dut.write("X{0}_buffer {0}_buf {0} {1} {2} test_buffer\n".format(signal,
                                                                                self.vdd_name,
                                                                                self.gnd_name))


    def add_cap_load(self, signal_list, load):
        """Adds capacitor load to top level signal that is in signal_list (only for sim purposes)"""
        
        for signal in signal_list:
            self.dut.write("C{0} {0} 0 {1}fF\n".format(signal, load))

