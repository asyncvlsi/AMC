# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,


""" Run a regresion test on a asynchronous sram with synchronous interface. """

import unittest
from testutils import header, AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class sync_sram_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import sync_sram

        debug.info(1, "Testing async sram with sync interface")
        """ range of acceptable value:  
            
            word_size in any number greater than 1
            word_per_row in [1, 2, 4] 
            num_rows in [32, 64, 128, 256, 512]   
            num_subanks in [1, 2, 4, 8] 
            
            # In banch_factor, first num is no. of outter_banks and second num is no. of 
              inner_banks, e.g (2, 4) means each one of two outter_bank has 4 inner_banks
              branch_factors in [(1,1), (1,2), (1,4), (2,4), (4,4)]
            
            # In bank_orientations, first value is orientaion of outter_banks 
              and second value is orientaion of inner_banks, e.g ("V", "H") 
              means outter_banks are placed vertically and inner_banks are place horizontally
              bank_orientations in [("H", "H"), ("V", "H"), ("H", "V"), ("V", "V")] """ 

        a = sync_sram.sync_sram(word_size=16, words_per_row=2, num_rows=64, 
                                num_subanks=2, branch_factors=(2,4), 
                                bank_orientations=("H", "H"), name="sync_sram")
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
