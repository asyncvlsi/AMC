
""" BSD 3-Clause License
    Copyright (c) 2018-2019 Regents of the University of California and The Board
    of Regents for the Oklahoma Agricultural and Mechanical College
    (acting for and on behalf of Oklahoma State University)
    All rights reserved.
"""

""" Run a regresion test on column_multiplexer_array. """

from testutils import header,AMC_test,unittest
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class column_mux_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import column_mux_array
        
        debug.info(1, "Testing sample for 1-way column_mux_array")
        a = column_mux_array.column_mux_array(columns=8, word_size=1, name="columnmux_array_1")
        self.local_check(a)

        debug.info(1, "Testing sample for 2-way column_mux_array")
        a = column_mux_array.column_mux_array(columns=8, word_size=4, name="columnmux_array_2")
        self.local_check(a)

        debug.info(1, "Testing sample for 4-way column_mux_array")
        a = column_mux_array.column_mux_array(columns=16, word_size=4, name="columnmux_array_4")
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
