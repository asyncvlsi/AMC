""" Run a regresion test on a split_merge_control_logic. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class split_merge_control_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import split_merge_control

        debug.info(1, "Testing sample for split_merge_control for 2 banks")
        a = split_merge_control.split_merge_control(num_banks=2, name="split_merge_ctrl2")
        self.local_check(a)

        debug.info(1, "Testing sample for split_merge_control for 4 banks")
        a = split_merge_control.split_merge_control(num_banks=4, name="split_merge_ctrl4")
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
