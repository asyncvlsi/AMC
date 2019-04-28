""" Run a regresion test on a bank_control_logic. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class bank_control_logic_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import bank_control_logic
        import tech

        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=32, num_subanks=1, two_level_bank=False, name="bank_ctrl1")
        self.local_check(a)
        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=64, num_subanks=1, two_level_bank=False, name="bank_ctrl2")
        self.local_check(a)


        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=64, num_subanks=2, two_level_bank=True, name="bank_ctrl3")
        self.local_check(a)
        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=32, num_subanks=2, two_level_bank=False, name="bank_ctrl4")
        self.local_check(a)


        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=32, num_subanks=4, two_level_bank=True, name="bank_ctrl5")
        self.local_check(a)
        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=32, num_subanks=4, two_level_bank=False, name="bank_ctrl6")
        self.local_check(a)


        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=64, num_subanks=8, two_level_bank=True, name="bank_ctrl7")
        self.local_check(a)
        debug.info(1, "Testing sample for bank_control_logic")
        a = bank_control_logic.bank_control_logic(num_rows=32, num_subanks=8, two_level_bank=False, name="bank_ctrl8")
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
