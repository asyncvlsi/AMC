# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import os,sys,re
import debug
import charutils
import functional_test
import tech
import numpy as np
from globals import OPTS

class lib():
    """ lib file generation."""
    
    def __init__(self, out_dir, sram):
        self.out_dir = out_dir
        self.sram = sram
        self.name=self.sram.name

        self.prepare_tables()
        self.create_corners()
        self.characterize_corners()

    def prepare_tables(self):
        """ Determine the load/slews if they aren't specified in the config file. """
        
        # These are the parameters to determine the table sizes
        #self.load_scales = np.array([0.1, 0.25, 0.5, 1, 2, 4, 8])
        self.load_scales = np.array([0.25, 1, 8])
        
        self.load = tech.spice["input_cap"]
        self.loads = self.load_scales*self.load
        debug.info(1,"Loads: {0}".format(self.loads))
        
        #self.slew_scales = np.array([0.1, 0.25, 0.5, 1, 2, 4, 8])
        self.slew_scales = np.array([0.25, 1, 8])        
        self.slew = tech.spice["rise_time"]        
        self.slews = self.slew_scales*self.slew
        debug.info(1,"Slews: {0}".format(self.slews))

    def create_corners(self):
        """ Create corners for characterization. """
        
        # Get the corners from the options file
        self.temperatures = OPTS.temperatures
        self.supply_voltages = OPTS.supply_voltages
        self.process_corners = OPTS.process_corners

        # Enumerate all possible corners
        self.corners = []
        self.lib_files = []
        for proc in self.process_corners:
            for temp in self.temperatures:
                for volt in self.supply_voltages:
                    self.corner_name = "{0}_{1}_{2}V_{3}C".format(self.sram.name, proc, volt, temp)
                    self.corner_name = self.corner_name.replace(".","p") # Remove decimals (point)
                    lib_name = self.out_dir+"{}.lib".format(self.corner_name)
                    
                    # A corner is a tuple of PVT
                    self.corners.append((proc, volt, temp))
                    self.lib_files.append(lib_name)
        
    def characterize_corners(self):
        """ Characterize the list of corners. """
        for (self.corner,lib_name) in zip(self.corners,self.lib_files):
            debug.info(1,"Corner: " + str(self.corner))
            (self.process, self.voltage, self.temperature) = self.corner
            self.lib = open(lib_name, "w")
            debug.info(1,"Writing to {0}".format(lib_name))
            self.characterize()
            self.lib.close()

    def characterize(self):
        """ Characterize the current corner. """

        self.compute_delay()
        self.write_header()
        self.write_data_in_bus()
        self.write_data_out_bus()
        self.write_addr_bus()
        self.write_control_in_pins()
        self.write_control_out_pins()
        self.write_power()
        self.write_footer()
        
    def write_footer(self):
        """ Write the footer """
        self.lib.write("}\n")

    def write_header(self):
        """ Write the header information """
        self.lib.write("library ({0}_lib)".format(self.corner_name))
        self.lib.write("{\n")
        self.lib.write("    delay_model : \"table_lookup\";\n")
        
        self.write_units()
        self.write_defaults()
        self.write_LUT_templates()

        self.lib.write("    default_operating_conditions : OC; \n")
        
        self.write_bus()

        self.lib.write("cell ({0})".format(self.sram.name))
        self.lib.write("{\n")
        self.lib.write("    memory(){ \n")
        self.lib.write("    type : ram;\n")
        self.lib.write("    address_width : {};\n".format(self.sram.addr_size))
        self.lib.write("    word_width : {};\n".format(self.sram.word_size))
        self.lib.write("    }\n")
        self.lib.write("    interface_timing : true;\n")
        self.lib.write("    dont_use  : true;\n")
        self.lib.write("    map_only   : true;\n")
        self.lib.write("    dont_touch : true;\n")
        self.lib.write("    area : {};\n\n".format(self.sram.width * self.sram.height))

        self.lib.write("    leakage_power () {\n")
        self.lib.write("      when : \"reset\";\n")
        self.lib.write("      value : {};\n".format(self.results["leakage_power"]))
        self.lib.write("    }\n")
        self.lib.write("    cell_leakage_power : {};\n\n".format(0))
        
    
    def write_units(self):
        """ Adds default units for time, voltage, current,..."""
        
        self.lib.write("    time_unit : \"1ns\" ;\n")
        self.lib.write("    voltage_unit : \"1v\" ;\n")
        self.lib.write("    current_unit : \"1mA\" ;\n")
        self.lib.write("    resistance_unit : \"1kohm\" ;\n")
        self.lib.write("    capacitive_load_unit(1 ,fF) ;\n")
        self.lib.write("    leakage_power_unit : \"1mW\" ;\n")
        self.lib.write("    pulling_resistance_unit :\"1kohm\" ;\n")
        self.lib.write("    operating_conditions(OC){\n")
        self.lib.write("    process : {} ;\n".format(1.0)) # degree of process scaling
        self.lib.write("    voltage : {} ;\n".format(self.voltage))
        self.lib.write("    temperature : {};\n".format(self.temperature))
        self.lib.write("    }\n\n")

    def write_defaults(self):
        """ Adds default values for slew and capacitance."""
        
        self.lib.write("    input_threshold_pct_fall       :  50.0 ;\n")
        self.lib.write("    output_threshold_pct_fall      :  50.0 ;\n")
        self.lib.write("    input_threshold_pct_rise       :  50.0 ;\n")
        self.lib.write("    output_threshold_pct_rise      :  50.0 ;\n")
        self.lib.write("    slew_lower_threshold_pct_fall  :  10.0 ;\n")
        self.lib.write("    slew_upper_threshold_pct_fall  :  90.0 ;\n")
        self.lib.write("    slew_lower_threshold_pct_rise  :  10.0 ;\n")
        self.lib.write("    slew_upper_threshold_pct_rise  :  90.0 ;\n\n")

        self.lib.write("    nom_voltage : {};\n".format(tech.spice["nom_supply_voltage"]))
        self.lib.write("    nom_temperature : {};\n".format(tech.spice["nom_temperature"]))
        self.lib.write("    nom_process : {};\n".format(1.0)) # degree of process scaling

        self.lib.write("    default_cell_leakage_power    : 0.0 ;\n")
        self.lib.write("    default_leakage_power_density : 0.0 ;\n")
        self.lib.write("    default_input_pin_cap    : 1.0 ;\n")
        self.lib.write("    default_inout_pin_cap    : 1.0 ;\n")
        self.lib.write("    default_output_pin_cap   : 0.0 ;\n")
        self.lib.write("    default_max_transition   : 0.5 ;\n")
        self.lib.write("    default_fanout_load      : 1.0 ;\n")
        self.lib.write("    default_max_fanout   : 4.0 ;\n")
        self.lib.write("    default_connection_class : universal ;\n\n")

    def create_list(self,values):
        """ Helper function to create quoted, line wrapped list """
        
        list_values = ", ".join(str(v) for v in values)
        return "\"{0}\"".format(list_values)

    def create_array(self,values, length):
        """ Helper function to create quoted, line wrapped array with each row of given length """
        
        # check that the length is a multiple or give an error!
        debug.check(len(values)%length == 0,"Values are not a multiple of the length. Cannot make a full array.")
        rounded_values = map(charutils.round_time,values)
        split_values = [rounded_values[i:i+length] for i in range(0, len(rounded_values), length)]
        formatted_rows = map(self.create_list,split_values)
        formatted_array = ",\\\n".join(formatted_rows)
        return formatted_array
    
    def write_index(self, number, values):
        """ Write the index """
        
        quoted_string = self.create_list(values)
        self.lib.write("        index_{0}({1});\n".format(number,quoted_string))

    def write_values(self, values, row_length, indent):
        """ Write the index """
        quoted_string = self.create_array(values, row_length)
        # indent each newline plus extra spaces for word values
        indented_string = quoted_string.replace('\n', '\n' + indent +"       ")
        self.lib.write("{0}values({1});\n".format(indent, indented_string))
        
    def write_LUT_templates(self):
        """ Adds lookup_table format (A 3x3 lookup_table)."""
        
        Tran = ["CELL_TABLE"]
        for i in Tran:
            self.lib.write("    lu_table_template({0})".format(i))
            self.lib.write("{\n")
            self.lib.write("        variable_1 : input_net_transition;\n")
            self.lib.write("        variable_2 : total_output_net_capacitance;\n")
            self.write_index(1,self.slews)
            self.write_index(2,self.loads)
            self.lib.write("    }\n\n")

        CONS = ["CONSTRAINT_TABLE"]
        for i in CONS:
            self.lib.write("    lu_table_template({0})".format(i))
            self.lib.write("{\n")
            self.lib.write("        variable_1 : related_pin_transition;\n")
            self.lib.write("        variable_2 : constrained_pin_transition;\n")
            self.write_index(1,self.slews)
            self.write_index(2,self.slews)
            self.lib.write("    }\n\n")
    
    def write_bus(self):
        """ Adds format of data and addr bus."""
    
        self.lib.write("\n\n")
        self.lib.write("    type (data_in){\n")
        self.lib.write("    base_type : array;\n")
        self.lib.write("    data_type : bit;\n")
        self.lib.write("    bit_width : {0};\n".format(self.sram.word_size))
        self.lib.write("    bit_from : 0;\n")
        self.lib.write("    bit_to : {0};\n".format(self.sram.word_size - 1))
        self.lib.write("    }\n\n")
        
        self.lib.write("    type (data_out){\n")
        self.lib.write("    base_type : array;\n")
        self.lib.write("    data_type : bit;\n")
        self.lib.write("    bit_width : {0};\n".format(self.sram.word_size))
        self.lib.write("    bit_from : 0;\n")
        self.lib.write("    bit_to : {0};\n".format(self.sram.word_size - 1))
        self.lib.write("    }\n\n")


        self.lib.write("    type (addr){\n")
        self.lib.write("    base_type : array;\n")
        self.lib.write("    data_type : bit;\n")
        self.lib.write("    bit_width : {0};\n".format(self.sram.addr_size))
        self.lib.write("    bit_from : 0;\n")
        self.lib.write("    bit_to : {0};\n".format(self.sram.addr_size - 1))
        self.lib.write("    }\n\n")

    def write_delay(self, related_pin, rise_delay, fall_delay, rise_slew, fall_slew):
        """ Adds Setup and Hold timing results"""

        self.lib.write("        timing(){ \n")
        self.lib.write("            timing_sense : non_unate; \n")
        self.lib.write("            related_pin : \"{0}\"; \n".format(related_pin))
        self.lib.write("            timing_type : falling_edge; \n")
        self.lib.write("            cell_rise(CELL_TABLE) {\n")
        self.write_values(rise_delay,len(self.loads),"            ")
        self.lib.write("            }\n") # rise delay
        self.lib.write("            cell_fall(CELL_TABLE) {\n")
        self.write_values(fall_delay,len(self.loads),"            ")
        self.lib.write("            }\n") # fall delay
        self.lib.write("            rise_transition(CELL_TABLE) {\n")
        self.write_values(rise_slew,len(self.loads),"            ")
        self.lib.write("            }\n") # rise trans
        self.lib.write("            fall_transition(CELL_TABLE) {\n")
        self.write_values(fall_slew,len(self.loads),"            ")
        self.lib.write("            }\n") # fall trans
        self.lib.write("        }\n") # timing

    def write_data_in_bus(self):
        """ Adds data bus timing results."""

        self.lib.write("    bus(data_in){\n")
        self.lib.write("        bus_type  : data_in; \n")
        self.lib.write("        direction  : input; \n")
        # This is conservative, but limit to range that we characterized.
        self.lib.write("        max_capacitance : {0};  \n".format(max(self.loads)))
        self.lib.write("        min_capacitance : {0};  \n".format(min(self.loads)))        
        self.lib.write("        three_state : \"(w |rw )& wreq)\"; \n")
        self.lib.write("        memory_write(){ \n")
        self.lib.write("            address : addr; \n")
        self.lib.write("        }\n")
        self.lib.write("        pin(data_in[{0}:0]){{\n".format(self.sram.word_size - 1))
        self.write_delay("w", self.results["write_delay_lh"], 
                              self.results["write_delay_hl"], 
                              self.results["slew_lh"], 
                              self.results["slew_hl"])
        self.write_delay("rw", self.results["read_write_delay_lh"], 
                               self.results["read_write_delay_hl"], 
                               self.results["slew_lh"], 
                               self.results["slew_hl"])
        self.write_delay("wreq", self.results["write_delay_lh"], 
                                 self.results["write_delay_hl"], 
                                 self.results["slew_lh"], 
                                 self.results["slew_hl"])
        self.lib.write("        }\n")
        self.lib.write("    }\n")

    def write_data_out_bus(self):
        """ Adds data bus timing results."""

        self.lib.write("    bus(data_out){\n")
        self.lib.write("        bus_type  : data_out; \n")
        self.lib.write("        direction  : output; \n")
        # This is conservative, but limit to range that we characterized.
        self.lib.write("        max_capacitance : {0};  \n".format(max(self.loads)))
        self.lib.write("        min_capacitance : {0};  \n".format(min(self.loads)))        
        self.lib.write("        three_state : \"(r |rw )& rreq)\"; \n")
        self.lib.write("        memory_read(){ \n")
        self.lib.write("            address : addr; \n")
        self.lib.write("        }\n")
        self.lib.write("        pin(data_out[{0}:0]){{\n".format(self.sram.word_size - 1))
        self.write_delay("r", self.results["read_delay_lh"], 
                               self.results["read_delay_hl"], 
                               self.results["slew_lh"], 
                               self.results["slew_hl"])
        self.write_delay("rw", self.results["read_write_delay_lh"], 
                               self.results["read_write_delay_hl"], 
                               self.results["slew_lh"], 
                               self.results["slew_hl"])
        self.write_delay("rreq", self.results["read_delay_lh"], 
                                 self.results["read_delay_hl"], 
                                 self.results["slew_lh"], 
                                 self.results["slew_hl"])
        self.lib.write("        }\n")
        self.lib.write("    }\n")
        
    def write_addr_bus(self):
        """ Adds addr bus timing results."""

        self.lib.write("    bus(addr){\n")
        self.lib.write("        bus_type  : addr; \n")
        self.lib.write("        direction  : input; \n")
        self.lib.write("        capacitance : {0};  \n".format(tech.spice["input_cap"]))
        self.lib.write("        max_transition       : {0};\n".format(self.slews[-1]))
        self.lib.write("        pin(addr[{0}:0])".format(self.sram.addr_size - 1))
        self.lib.write("{\n")
        self.lib.write("        }\n")        
        self.lib.write("    }\n\n")

    def write_control_in_pins(self):
        """ Adds control pins timing results."""

        ctrl_pin_names = ["reset", "r", "w", "rw", "wreq", "rreq"]
        for i in ctrl_pin_names:
            self.lib.write("    pin({0})".format(i))
            self.lib.write("{\n")
            self.lib.write("        direction  : input; \n")
            self.lib.write("        capacitance : {0};  \n".format(tech.spice["input_cap"]))
            self.lib.write("    }\n\n")
    
    def write_control_out_pins(self):
        """ Adds control pins timing results."""

        ctrl_pin_names = ["ack", "wack", "rack"]
        for i in ctrl_pin_names:
            self.lib.write("    pin({0})".format(i))
            self.lib.write("{\n")
            self.lib.write("        direction  : output; \n")
            self.lib.write("        capacitance : {0};  \n".format(tech.spice["input_cap"]))
            self.lib.write("    }\n\n")

    def write_power(self):
        """ Adds power results."""

        leakage_power = self.results["leakage_power"]
        read_power = self.results["read_power"]
        write_power = self.results["write_power"]
        read_write_power = self.results["read_write_power"]      

        self.lib.write("    internal_power(){\n")
        self.lib.write("        when : \"r & !w & !rw & !reset\"; \n")
        self.lib.write("        rise_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(read_power))
        self.lib.write("        }\n")
        self.lib.write("        fall_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(read_power))
        self.lib.write("        }\n")
        self.lib.write("    }\n")

        self.lib.write("    internal_power(){\n")
        self.lib.write("        when : \"w & !r & !rw &!reset\"; \n")
        self.lib.write("        rise_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(write_power))
        self.lib.write("        }\n")
        self.lib.write("        fall_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(write_power))
        self.lib.write("        }\n")
        self.lib.write("    }\n")

        self.lib.write("    internal_power(){\n")
        self.lib.write("        when : \"rw & !r & !rw & !reset\"; \n")
        self.lib.write("        rise_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(read_write_power))
        self.lib.write("        }\n")
        self.lib.write("        fall_power(scalar){\n")
        self.lib.write("                values(\"{0}\");\n".format(read_write_power))
        self.lib.write("        }\n")
        self.lib.write("    }\n")
        self.lib.write("}\n")
        
        
    def compute_delay(self):
        """ Do the analysis if we haven't characterized the SRAM yet """

        size = (self.sram.addr_size, self.sram.word_size)
        corner = (OPTS.process_corners[0], OPTS.supply_voltages[0], OPTS.temperatures[0])
        self.results  = self.delay_power(size, corner, self.name, self.loads , self.slews)

    def delay_power(self, size, corner, name, loads , slews):
        """ Measure the delay, slew and power for all slew/load pairs """

        char_data = {}
        for m in ["write_delay_lh", "write_delay_hl", "read_delay_lh", "read_delay_hl", 
                  "read_write_delay_lh", "read_write_delay_hl", "slew_lh", "slew_hl", 
                  "leakage_power", "read_power", "write_power", "read_write_power"]:
            char_data[m]=[]

        for slew in slews:
            for load in loads:
                d = functional_test.functional_test(size, corner, name, self.sram.w_per_row, 
                                                    self.sram.num_rows, load ,slew)
                q = d.result
                for k,v in q.items():
                    char_data[k].append(v)
        return char_data
