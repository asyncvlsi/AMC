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


""" SRAM Compiler
The output files append the given suffixes to the output name:
a spice (.sp) file for circuit simulation
a GDS2 (.gds) file containing the layout
a Verilog (.v) file for Synthesis
a LEF (.lef) file for preliminary P&R
a Liberty (.lib) file for timing analysis/optimization
"""
#!/usr/bin/env python2

import sys, os
import datetime
import re
from globals import *

(OPTS, args) = parse_args()

# Check that we are left with a single configuration file as argument.
if len(args) != 1:
    print(USAGE)
    sys.exit(2)


# These depend on arguments, so don't load them until now.
import debug


init_AMC(config_file=args[0], is_unit_test=False)

# Only print banner here so it's not in unit tests
print_banner()

# Output info about this run
report_status()

# Start importing design modules after we have the config file



print("\n Output files are " + OPTS.output_name + ".(sp|gds|v|lef)")

# Characterizer is slow and deactivated by default
print("For .lib file: set the \"characterize = True\" in options.py, invoke Synopsys HSIM and VCS tools and rerun.\n")

# Keep track of running stats
start_time = datetime.datetime.now()
print_time("Start",start_time)

# import SRAM test generation
if OPTS.add_sync_interface:
    import sync_sram
    s = sync_sram.sync_sram(word_size=OPTS.word_size,
                            words_per_row=OPTS.words_per_row, 
                            num_rows=OPTS.num_rows, 
                            num_subanks=OPTS.num_subanks, 
                            branch_factors=OPTS.branch_factors, 
                            bank_orientations=OPTS.bank_orientations, 
                            name=OPTS.name)

else:
    import sram
    s = sram.sram(word_size=OPTS.word_size,
                  words_per_row=OPTS.words_per_row, 
                  num_rows=OPTS.num_rows, 
                  num_subanks=OPTS.num_subanks, 
                  branch_factors=OPTS.branch_factors, 
                  bank_orientations=OPTS.bank_orientations, 
                  name=OPTS.name)
OPTS.check_lvsdrc = True

s.save_output()

# Delete temp files etc.
end_AMC()
print_time("End",datetime.datetime.now(), start_time)


