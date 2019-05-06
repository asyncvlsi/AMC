""" BSD 3-Clause License
    Copyright (c) 2018-2019 Regents of the University of California and The Board
    of Regents for the Oklahoma Agricultural and Mechanical College
    (acting for and on behalf of Oklahoma State University)
    All rights reserved.
"""


import debug
import re
import os
import math
import verilog

class spice(verilog.verilog):
    """
    This provides a set of useful generic types for hierarchy
    management. If a module is a custom designed cell, it will read from
    the GDS and spice files and perform LVS/DRC. If it is dynamically
    generated, it should implement a constructor to create the
    layout/netlist and perform LVS/DRC.
    Class consisting of a set of modules and instances of these modules
    """

    def __init__(self, name):
        self.name = name

        self.mods = []  # Holds subckts/mods for this module
        self.pins = []  # Holds the pins for this module
        self.pin_type = {} # The type map of each pin: INPUT, OUTPUT, INOUT, POWER, GROUND
        # for each instance, this is the set of nets/nodes that map to the pins for this instance
        # THIS MUST MATCH THE ORDER OF THE PINS (restriction imposed by the Spice format)
        self.conns = []
        self.sp_read()

############################################################
# Spice circuit
############################################################

    def add_pin(self, name, pin_type="INOUT"):
        """ Adds a pin to the pins list. Default type is INOUT signal. """
        
        self.pins.append(name)
        self.pin_type[name]=pin_type

    def add_pin_list(self, pin_list, pin_type_list="INOUT"):
        """ Adds a pin_list to the pins list """
        
        # The type list can be a single type for all pins or a list that is the same length as the pin list.
        if type(pin_type_list)==str:
            for pin in pin_list:
                self.add_pin(pin,pin_type_list)
        elif len(pin_type_list)==len(pin_list):
            for (pin,ptype) in zip(pin_list, pin_type_list):
                self.add_pin(pin,ptype)
        else:
            debug.error("Mismatch in type and pin list lengths.", -1)

    def get_pin_type(self, name):
        """ Returns the type of the signal pin. """
        
        return self.pin_type[name]

    def get_pin_dir(self, name):
        """ Returns the direction of the pin. (Supply/ground are INOUT). """
        
        if self.pin_type[name] in ["POWER","GROUND"]:
            return "INOUT"
        else:
            return self.pin_type[name]
        

    def add_mod(self, mod):
        """Adds a subckt/submodule to the subckt hierarchy"""
        
        self.mods.append(mod)

    def connect_inst(self, args, check=True):
        """Connects the pins of the last instance added. It is preferred to use the 
           function with the check to find if there is a problem. The check option 
           can be set to false where we dynamically generate groups of connections 
           after a group of modules are generated."""
        
        if (check and (len(self.insts[-1].mod.pins) != len(args))):
            debug.error("Number of net connections ({0}) does not match last instance ({1})".format(len(self.insts[-1].mod.pins),
                                                                                                    len(args)), 1)
        
        self.conns.append(args)

        if check and (len(self.insts)!=len(self.conns)):
            debug.error("{0} : Not all instance pins ({1}) are connected ({2}).".format(self.name,
                                                                                        len(self.insts),
                                                                                        len(self.conns)))
            debug.error("Instances: \n"+str(self.insts))
            debug.error("-----")
            debug.error("Connections: \n"+str(self.conns),1)


    def sp_read(self):
        """Reads the sp file (and parse the pins) from the library 
           Otherwise, initialize it to null for dynamic generation"""
        
        if os.path.isfile(self.sp_file):
            debug.info(3, "opening {0}".format(self.sp_file))
            f = open(self.sp_file)
            self.spice = f.readlines()
            for i in range(len(self.spice)):
                self.spice[i] = self.spice[i].rstrip(" \n")

            # find the correct subckt line in the file
            subckt = re.compile("^.subckt {}".format(self.name), re.IGNORECASE)
            subckt_line = filter(subckt.search, self.spice)[0]
            # parses line into ports and remove subckt
            self.pins = subckt_line.split(" ")[2:]
        else:
            self.spice = []

    def contains(self, mod, modlist):
        for x in modlist:
            if x.name == mod.name:
                return True
        return False

    def sp_write_file(self, sp, usedMODS):
        """ Recursive spice subcircuit write;
            Writes the spice subcircuit from the library or the dynamically generated one"""
        
        if not self.spice:
            # recursively write the modules
            for i in self.mods:
                if self.contains(i, usedMODS):
                    continue
                usedMODS.append(i)
                i.sp_write_file(sp, usedMODS)

            if len(self.insts) == 0:
                return
            if self.pins == []:
                return

            
            # write out the first spice line (the subcircuit)
            sp.write("\n.SUBCKT {0} {1}\n".format(self.name,
                                                  " ".join(self.pins)))

            # every instance must have a set of connections, even if it is empty.
            if  len(self.insts)!=len(self.conns):
                debug.error("{0} : Not all instance pins ({1}) are connected ({2}).".format(self.name,
                                                                                            len(self.insts),
                                                                                            len(self.conns)))
                debug.error("Instances: \n"+str(self.insts))
                debug.error("-----")
                debug.error("Connections: \n"+str(self.conns),1)



            for i in range(len(self.insts)):
                # we don't need to output connections of empty instances.
                # these are wires and paths
                if self.conns[i] == []:
                    continue
                if hasattr(self.insts[i].mod,"spice_device"):
                    sp.write(self.insts[i].mod.spice_device.format(self.insts[i].name,
                                                                   " ".join(self.conns[i])))
                    sp.write("\n")

                else:
                    sp.write("X{0} {1} {2}\n".format(self.insts[i].name,
                                                     " ".join(self.conns[i]),
                                                     self.insts[i].mod.name))

            sp.write(".ENDS {0}\n".format(self.name))

        else:
            # write the subcircuit itself
            # Including the file path makes the unit test fail for other users.
            #if os.path.isfile(self.sp_file):
            #    sp.write("\n* {0}\n".format(self.sp_file))
            sp.write("\n".join(self.spice))
            
            sp.write("\n")

    def sp_write(self, spname):
        """Writes the spice to files"""
        debug.info(3, "Writing to {0}".format(spname))
        spfile = open(spname, 'w')
        spfile.write("*FIRST LINE IS A COMMENT\n")
        usedMODS = list()
        self.sp_write_file(spfile, usedMODS)
        del usedMODS
        spfile.close()

