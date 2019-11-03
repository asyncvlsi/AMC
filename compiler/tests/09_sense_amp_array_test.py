# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" Run a regresion test on a sense amp array. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class sense_amp_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import sense_amp_array

        debug.info(2, "Testing sense_amp_array for word_size=16, words_per_row=1")
        a = sense_amp_array.sense_amp_array(word_size=16, words_per_row=1, name="sa_array1")
        self.local_check(a)

        debug.info(2, "Testing sense_amp_array for word_size=16, words_per_row=2")
        a = sense_amp_array.sense_amp_array(word_size=16, words_per_row=2, name="sa_array2")
        self.local_check(a)

        debug.info(2, "Testing sense_amp_array for word_size=16, words_per_row=4")
        a = sense_amp_array.sense_amp_array(word_size=16, words_per_row=4, name="sa_array4")
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
