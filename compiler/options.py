# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
#All rights reserved.

import optparse
import getpass 
import os

class options(optparse.Values):
    """ Class for holding all of the AMC options. 
        All of these options can be over-riden in a configuration file
        that is the sole required command-line positional argument for AMC.py. """

    # This is the technology directory.
    AMC_tech = ""
    
    # This is the name of the technology.
    tech_name = "scn3me_subm"
    
    # This is the temp directory where all intermediate results are stored.
    AMC_temp = os.path.abspath(os.environ.get("AMC_HOME")) + "/tmp/"
    
    # This is the verbosity level to control debug information. 0 is none, 1 is minimal, etc.
    debug_level = 0
    
    # This determines whether  LVS and DRC is checked for each submodule.
    check_lvsdrc = True
    
    # Variable to select the variant of spice
    spice_name = "hsim"
    
    # Should we print out the banner at startup
    print_banner = True
    
    # The DRC/LVS/PEX executable being used which is derived from the user PATH.
    #lvsdrc_exe = "path_to_calibre"

    # The spice executable being used which is derived from the user PATH.
    #spice_exe = "path_to_spice"
    
    # Run with extracted parasitics
    use_pex = False
    
    # Remove noncritical memory cells for characterization speed-up
    trim_netlist = False
    
    # Define the output file paths
    output_path = "tmp"
    
    # Define the output file base name
    output_name = ""
    
    # Purge the temp directory after a successful run (doesn't purge on errors, anyhow)
    purge_temp = True
    
    #run the charactrizer
    characterize = False




