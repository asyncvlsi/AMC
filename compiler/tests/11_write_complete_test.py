""" Run a regresion test on write complete detection array. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class write_complete_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import write_complete_array

        debug.info(2, "Testing write_complete for columns=4, word_size=1")
        a = write_complete_array.write_complete_array(columns=4, word_size=1, name="write_complete1")
        self.local_check(a)

        debug.info(2, "Testing write_complete for columns=4, word_size=2")
        a = write_complete_array.write_complete_array(columns=4, word_size=2, name="write_complete2")
        self.local_check(a)
        
        debug.info(2, "Testing write_complete for columns=4, word_size=4")
        a = write_complete_array.write_complete_array(columns=4, word_size=4, name="write_complete4")
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
