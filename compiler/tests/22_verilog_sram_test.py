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


""" Generate the  .v file for an SRAM """

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class verilog_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        OPTS.check_lvsdrc = False

        import sram

        debug.info(1, "Testing Verilog for a sample sram")
        s = sram.sram(word_size=2,
                      words_per_row=1,
                      num_rows=64,
                      num_subanks=4, 
                      branch_factors=(1,4),
                      bank_orientations=("H", "H"),
                      name="sram")

        OPTS.check_lvsdrc = True

        vfile = s.name + ".v"
        vname = OPTS.AMC_temp + vfile
        s.verilog_write(vname)

        globals.end_AMC()
        
# instantiate a copdsay of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
