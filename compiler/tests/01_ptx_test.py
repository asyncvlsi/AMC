"Run a regresion test on a basic parameterized transistors. "

import unittest
from testutils import header, AMC_test
import sys, os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class ptx_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import ptx
        import tech

        debug.info(2, "Checking single finger NMOS")
        fet1 = ptx.ptx(width= tech.drc["minwidth_tx"],
                       mults=1, tx_type="nmos", connect_active=False, connect_poly=False)
        self.local_drc_check(fet1)

        debug.info(2, "Checking single finger PMOS")
        fet2 = ptx.ptx(width= 2*tech.drc["minwidth_tx"],
                       mults=1, tx_type="pmos", connect_active=False, connect_poly=False)
        self.local_drc_check(fet2)

        debug.info(2, "Checking three fingers NMOS")
        fet3 = ptx.ptx(width=3*tech.drc["minwidth_tx"],
                       mults=3, tx_type="nmos", connect_active=False, connect_poly=False)
        self.local_drc_check(fet3)

        debug.info(2, "Checking foure fingers PMOS")
        fet4 = ptx.ptx(width=2*tech.drc["minwidth_tx"],
                       mults=4, tx_type="pmos", connect_active=True, connect_poly=True)
        self.local_drc_check(fet4)

        debug.info(2, "Checking three fingers NMOS")
        fet5 = ptx.ptx(width=3*tech.drc["minwidth_tx"],
                       mults=4, tx_type="nmos", connect_active=True, connect_poly=False)
        self.local_drc_check(fet5)

        debug.info(2, "Checking foure fingers PMOS")
        fet6 = ptx.ptx(width=2*tech.drc["minwidth_tx"],
                       mults=3, tx_type="pmos", connect_active=False, connect_poly=True)
        self.local_drc_check(fet6)

        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()

# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
