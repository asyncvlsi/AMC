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
# Boston, MA  02110-1301, USA. (See LICENSE for licensing information)


""" Run a regresion test on a multi-bank_SRAM. """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class multi_bank_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import multi_bank
 
        debug.info(1, "Multi Bank SRAM Test")
        
        """ range of acceptable value: 
        word_size in any number greater than 1
        word_per_row in [1, 2, 4] 
        num_rows in [32, 64, 128, 256, 512]
        num_subanks in [1, 2, 4, 8]
        num_banks in [1, 2, 4] 
        orientation in ["H","V"]: Horizontal or Verical
        two_level_bank in [False, True]: if true split and merge cell will be added
        """ 

        a = multi_bank.multi_bank(word_size=16, words_per_row=1, num_rows=64, num_subanks=4, 
                                  num_banks=4, orientation="H", two_level_bank=True, 
                                  name="multi_bank")
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
