""" Run a regresion test on merge cell array. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class merge_array_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import merge_array

        debug.info(2, "Testing merge_array for word_size=8,  words_per_row=1")
        a = merge_array.merge_array(word_size=8,  words_per_row=1, name="merge_array1")
        self.local_check(a)

        debug.info(2, "Testing merge_array for word_size=8,  words_per_row=2")
        a = merge_array.merge_array(word_size=8,  words_per_row=2, name="merge_array2")
        self.local_check(a)

        debug.info(2, "Testing merge_array for word_size=8,  words_per_row=4")
        a = merge_array.merge_array(word_size=8,  words_per_row=4, name="merge_array4")
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
