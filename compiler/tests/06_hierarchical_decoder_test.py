# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" Run a regresion test on a hierarchical_decoder. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class hierarchical_decoder_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import hierarchical_decoder

        # rows=4 and rows=8 Doesn't require hierarchical decoder, 
        # they should be made with only predecoders

        debug.info(1, "Testing 16 row sample for hierarchical_decoder")
        a = hierarchical_decoder.hierarchical_decoder(rows=16, name="hierarchical_decoder_16")
        self.local_check(a)

        debug.info(1, "Testing 32 row sample for hierarchical_decoder")
        a = hierarchical_decoder.hierarchical_decoder(rows=32, name="hierarchical_decoder_32")
        self.local_check(a)

        debug.info(1, "Testing 128 row sample for hierarchical_decoder")
        a = hierarchical_decoder.hierarchical_decoder(rows=128, name="hierarchical_decoder_128")
        self.local_check(a)

        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()
        
# instantiate a copdsay of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
