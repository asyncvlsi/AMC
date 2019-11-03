# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" Generate the LEF file for an SRAM. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class lef_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))

        import sram

        debug.info(1, "Testing LEF for a sample sram")
        s = sram.sram(word_size=4,
                      words_per_row=1,
                      num_rows=64,
                      num_subanks=4, 
                      branch_factors=(1,4),
                      bank_orientations=("H", "H"),
                      name="sram3")
                      
        gdsfile = s.name + ".gds"
        leffile = s.name + ".lef"
        gdsname = OPTS.AMC_temp + gdsfile
        lefname = OPTS.AMC_temp + leffile
        s.gds_write(gdsname)
        s.lef_write(lefname)

        globals.end_AMC()

# instantiate a copdsay of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
