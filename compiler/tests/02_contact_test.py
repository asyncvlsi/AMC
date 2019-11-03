# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


"Run a regresion test for DRC on basic contacts of different array sizes. "

import unittest
from testutils import header, AMC_test
import sys, os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class contact_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import contact

        for layer_stack in [("active", "contact", "metal1"), ("metal1", "via1", "metal2")]:

            # Check single 1 x 1 contact"
            debug.info(2, "1 x 1 {} test".format(layer_stack))
            c1 = contact.contact(layer_stack, (1, 1))
            #self.local_drc_check(c1)

            # check vertical array with one in the middle and two ends
            debug.info(2, "1 x 3 {} test".format(layer_stack))
            c2 = contact.contact(layer_stack, (1, 3))
            #self.local_drc_check(c2)

            # check horizontal array with one in the middle and two ends
            debug.info(2, "3 x 1 {} test".format(layer_stack))
            c3 = contact.contact(layer_stack, (3, 1))
            #self.local_drc_check(c3)

            # check 3x3 array for all possible neighbors
            debug.info(2, "3 x 3 {} test".format(layer_stack))
            c4 = contact.contact(layer_stack, (3, 3))
            #self.local_drc_check(c4)

        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()


# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
