import debug
from math import log

class trim_spice():
    """ A utility to trim redundant parts of an SRAM spice netlist. 
        Input is an SRAM spice file. Output is an equivalent netlist
        that works for a single address and range of data bits. """

    def __init__(self, spfile, reduced_spfile, word_size, w_per_row, num_rows, 
                 addr1, addr2):
        self.sp_file = spfile
        self.reduced_spfile = reduced_spfile        

        debug.info(1,"Trimming non-critical cells to speed-up characterization")
        
        # Load the file into a buffer for performance
        sp = open(self.sp_file, "r")
        self.spice = sp.readlines()
        for i in range(len(self.spice)):
            self.spice[i] = self.spice[i].rstrip(" \n")
        self.sp_buffer = self.spice

        #Set the configuration of SRAM sizes that we are simulating.
        self.word_size = word_size
        self.num_rows = num_rows
        self.w_per_row = w_per_row

        self.row_addr_size = int(log(self.num_rows, 2))
        self.col_addr_size = int(log(self.w_per_row, 2))
        self.trim(addr1, addr2)

    def trim(self, addr1, addr2):
        """ Reduce the spice netlist but KEEP the given bits at the
            address (and things that will add capacitive load!)"""

        # Always start fresh if we do multiple reductions
        self.sp_buffer = self.spice

        # Split up the address and convert to an int
        wl_addr1 = int(addr1[0:self.row_addr_size],2)
        wl_addr2 = int(addr2[0:self.row_addr_size],2)
        if self.w_per_row>1:
            col_addr1 = int(addr1[self.row_addr_size:self.row_addr_size+int(log(self.w_per_row,2))],2)
            col_addr2 = int(addr2[self.row_addr_size:self.row_addr_size+int(log(self.w_per_row,2))],2)
        else:
            col_addr1 = 0
            col_addr2 = 0

        # 1. Keep cells in the bitcell array based on WL and BL (first BL from each word for write_complete)
        bl_name1 = "bl[{0}]".format(col_addr1*self.word_size)
        bl_name2 = "bl[{0}]".format(col_addr2*self.word_size)
        wl_name1 = "wl[{0}]".format(wl_addr1)
        wl_name2 = "wl[{0}]".format(wl_addr2)


        # Prepend info about the trimming
        addr_msg = "Keeping {} address".format(addr1)
        self.sp_buffer.insert(0, "* "+addr_msg)
        debug.info(1,addr_msg)
        addr_msg = "Keeping {} address".format(addr2)
        self.sp_buffer.insert(0, "* "+addr_msg)
        debug.info(1,addr_msg)
        
        bl_msg = "Keeping {} (trimming other BLs)".format(bl_name1)
        self.sp_buffer.insert(0, "* "+bl_msg)
        debug.info(1,bl_msg)
        bl_msg = "Keeping {} (trimming other BLs)".format(bl_name2)
        self.sp_buffer.insert(0, "* "+bl_msg)
        debug.info(1,bl_msg)

        wl_msg = "Keeping {} (trimming other WLs)".format(wl_name1)
        self.sp_buffer.insert(0, "* "+wl_msg)
        debug.info(1,wl_msg)
        wl_msg = "Keeping {} (trimming other WLs)".format(wl_name2)
        self.sp_buffer.insert(0, "* "+wl_msg)
        debug.info(1,wl_msg)

        self.sp_buffer.insert(0, "* It should NOT be used for LVS!!")
        self.sp_buffer.insert(0, "* WARNING: This is a TRIMMED NETLIST.")
        
        self.remove_insts("bitcell_ary",[wl_name1, bl_name1])
        self.remove_insts("bitcell_ary",[wl_name2, bl_name2])

        # Everything else isn't worth removing. :)
        
        # Finally, write out the buffer as the new reduced file
        sp = open(self.reduced_spfile, "w")
        sp.write("\n".join(self.sp_buffer))

        
    def remove_insts(self, subckt_name, keep_inst_list):
        """This will remove all of the instances in the list from the named subckt that DO NOT contain 
           a term in the list. It just does a match of the line with a term so you can search for a 
           single net connection, the instance name, anything."""
        
        start_name = ".SUBCKT {}".format(subckt_name)
        end_name = ".ENDS {}".format(subckt_name)

        in_subckt=False
        new_buffer=[]
        for line in self.sp_buffer:
            if start_name in line:
                new_buffer.append(line)
                in_subckt=True
            elif end_name in line:
                new_buffer.append(line)
                in_subckt=False
            elif in_subckt:
                for k in keep_inst_list:
                    if k in line:
                        new_buffer.append(line)
                        break
            else:
                new_buffer.append(line)

        self.sp_buffer = new_buffer
