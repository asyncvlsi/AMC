# AMC :  An Asynchronous Memory (SRAM) Compiler.

<img align="right" width="25%" src="images/test_chp.png">

AMC is an open-source asynchronous pipelined memory compiler. 
AMC generates SRAM modules with a bundled-data datapath and 
quasi-delay-insensitive control. AMC is a Python-base, flexible, user-modifiable and 
technology-independent memory compiler that generates fabricable 
SRAM blocks in a broad range of sizes, configurations and process nodes.

AMC generates GDSII layout data, standard SPICE netlists, Verilog models, 
DRC/LVS verification reports, timing and power models (.lib), and placement and 
routing models (.lef). 


# Basic Setup

## Environment

You must set two environment to your .bashrc:

```
  export AMC_HOME="$HOME/AMC/compiler"
  export AMC_TECH="$HOME/AMC/technology"
```

## Dependencies

+ Python 2.7 or higher
+ Python numpy

If you want to perform DRC and LVS, you will need:
+ Calibre 
+ [Magic] and [Netgen] (for [SCMOS])

For characterization and functional verification test you will need:
+ HSIM & VCS for a Spice-Verilog co-simulation


# Usage

You can run AMC from the command line using a single configuration file. 

```
python3 $AMC_HOME/AMC.py example_config.py
```

In *example_config.py* file you can specify the following parameters:

```
# Data word size
word_size = 16

#Number of rows in each memory bank
num_rows = 64

# Number of words in each memory row (num_columns = word_size * words_per_row)
words_per_row = 2

#Number of sub-banks in each bank
num_subanks = 8

#Branch factors (number of inner-banks and outer-banks)
branch_factors = (2,4)

#Bank orientations (orientation of inner-banks and outer-banks)
bank_orientation = ("V", "H")

# Output directory for the results
output_path = "path_to_AMC_output_files"

# Output file name
output_name = "AMC_sram"

# Technology name
tech_name = "scn3me_subm"

# Process corners to characterize
process_corners = ["TT", "SF"]

# Voltage corners to characterize
supply_voltages = [ 5.0, 4.5 ]

# Temperature corners to characterize
temperatures = [ 25, 125 ]

```
You can set  more options for the configuration file in $AMC\_HOME/options.py

AMC has been written so that its core is technology-independent. 
All reference implementation for SCN3ME_SUBM 0.5um technology is included in this release.

