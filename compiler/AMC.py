""" SRAM Compiler

The output files append the given suffixes to the output name:
a spice (.sp) file for circuit simulation
a GDS2 (.gds) file containing the layout
a Verilog (.v) file for Synthesis
a LEF (.lef) file for preliminary P&R
a Liberty (.lib) file for timing analysis/optimization

"""

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

import sram

print("\n Output files are " + OPTS.output_name + ".(sp|gds|v|lib|lef)")

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
              name=OPTS.name)

OPTS.check_lvsdrc = True

s.save_output()

# Delete temp files etc.
end_AMC()
print_time("End",datetime.datetime.now(), start_time)


