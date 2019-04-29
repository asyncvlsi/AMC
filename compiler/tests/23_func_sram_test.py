""" Run a regresion test on SRAM functionality. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class sram_func_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        OPTS.check_lvsdrc = False

        # This is a hack to reload the characterizer __init__ with the spice version
        import characterizer
        reload(characterizer)
        from characterizer import functional_test
        import sram
        import tech

        debug.info(1, "Testing timing for sample 1bit, 16words SRAM with 1 bank")
        s = sram.sram(word_size=2, words_per_row=1, num_rows=32, num_subanks=2, 
                      branch_factors=(1,2), bank_orientations=("H", "H"), name="sram")
                      
        tempspice = OPTS.AMC_temp + "sram.sp"
        s.sp_write(tempspice)
        
        corner = (OPTS.process_corners[0], OPTS.supply_voltages[0], OPTS.temperatures[0])
        size = (s.addr_size, s.word_size)
        
        
        #at least 4 simulation is needed to calculate delays for each operation
        T = functional_test.functional_test(size, corner, name=s.name, 
                                            w_per_row = s.w_per_row, num_rows = s.num_rows, 
                                            load=tech.spice["input_cap"], 
                                            slew=tech.spice["rise_time"])

        globals.end_AMC()
        
# instantiate a copdsay of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()