""" Run a regresion test on a write driver array. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class write_driver_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import write_driver_array

        debug.info(2, "Testing write_driver_array for word_size=16, words_per_row=1")
        a = write_driver_array.write_driver_array(word_size=16, words_per_row=1, name="wd_array1")
        self.local_check(a)

        debug.info(2, "Testing write_driver_array for cword_size=16, words_per_row=2")
        a = write_driver_array.write_driver_array(word_size=16, words_per_row=2, name="wd_array2")
        self.local_check(a)
        
        debug.info(2, "Testing write_driver_array for cword_size=16, words_per_row=4")
        a = write_driver_array.write_driver_array(word_size=16, words_per_row=4, name="wd_array4")
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
