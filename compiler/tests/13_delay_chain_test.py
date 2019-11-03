# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" Run a regresion test on a delay chain. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class delay_chain_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import delay_chain

        debug.info(2, "Testing delay_chain, 2 stages with fanout 3")
        a = delay_chain.delay_chain(fanout_list=[2,3], name="delay_chain1")
        self.local_check(a)
        
        debug.info(2, "Testing delay_chain, 3 stage with fanout 4")
        a = delay_chain.delay_chain(fanout_list=[4,4,4], name="delay_chain2")
        self.local_check(a)

        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()
        
# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
