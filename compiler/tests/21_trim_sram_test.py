# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" Run a regresion test on a two-level_SRAM. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug
from os import path

class sram_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        import sram
        from characterizer import trim_spice
 
        debug.info(1, "SRAM Test")
        a = sram.sram(word_size=16, words_per_row=1, num_rows=64, 
                      num_subanks=4, branch_factors=(1,4), 
                      bank_orientations=("H", "H"), name="sram")
        
        tempspice = OPTS.AMC_temp + "sram.sp"
        a.sp_write(tempspice)

        filename="{0}{1}".format(OPTS.AMC_temp, "sram.sp")
        while not path.exists(filename):
            time.sleep(1)
        else:
            os.chmod(filename, 0o777)
        
        address1="1"*a.addr_size
        address2="0"*a.addr_size
        
        reduced_file="{0}{1}".format(OPTS.AMC_temp, "reduced.sp")
        trim_spice.trim_spice(filename, reduced_file, a.word_size, a.w_per_row, a.num_rows, 
                              address1, address2)
        globals.end_AMC()
        
# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
