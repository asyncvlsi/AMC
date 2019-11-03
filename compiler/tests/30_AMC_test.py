"""
AMC SRAm:

The output files append the given suffixes to the output name:
a spice (.sp) file for circuit simulation
a GDS2 (.gds) file containing the layout
a LEF (.lef) file for preliminary P&R (real one should be from layout)
a Liberty (.lib) file for timing analysis/optimization

This tests the top-level executable. It checks that it generates the
appropriate files: .lef, .lib, .sp, .gds, .v. It DOES NOT, however,
check that these files are right.
"""

import unittest
from testutils import header,AMC_test
import sys,os,re,shutil
import datetime
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
from globals import *
import importlib
import debug

class AMC_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        # Only print banner here so it's not in unit tests
        print_banner()

        # Output info about this run
        report_status()

        # Start importing design modules after we have the config file
        import tech
        import sram

        # Keep track of running stats
        start_time = datetime.datetime.now()
        print_time("Start",start_time)

        # import SRAM test generation
        s = sram.sram(word_size=OPTS.word_size,
                      words_per_row=OPTS.words_per_row, 
                      num_rows=OPTS.num_rows, 
                      num_subanks=OPTS.num_subanks, 
                      branch_factors=OPTS.branch_factors, 
                      bank_orientations=OPTS.bank_orientations, 
                      name="sram2")


        # return it back to it's normal state
        self.local_check(s)
        OPTS.check_lvsdrc = True
        print_time("End",datetime.datetime.now(), start_time)

        globals.end_AMC()      

# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
