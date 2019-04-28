""" Run regression tests on a parameterized inverter. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class pinv_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import pinv

        debug.info(2, "Checking 1x size inverter")
        tx = pinv.pinv(size=1)
        self.local_check(tx)

        debug.info(2, "Checking 2x size inverter")
        tx = pinv.pinv(size=2)
        self.local_check(tx)

        debug.info(2, "Checking 7x size inverter")
        tx = pinv.pinv(size=7)
        self.local_check(tx)
        
        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()        

# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
