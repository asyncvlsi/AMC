import os
import debug
from globals import OPTS,find_exe,get_tool

debug.info(2,"Initializing characterizer...")

OPTS.spice_exe = ""


if OPTS.spice_name != "":
    OPTS.spice_exe=find_exe(OPTS.spice_name)
    if OPTS.spice_exe=="":
        debug.error("{0} not found. Unable to perform characterization.".format(OPTS.spice_name),1)
else:
    (OPTS.spice_name, OPTS.spice_exe) = get_tool("spice",["hsim", "vcs"])

# set the input dir for spice files if using ngspice 
if OPTS.spice_name == "ngspice":
    os.environ["NGSPICE_INPUT_DIR"] = "{0}".format(OPTS.AMC_temp)
    
if OPTS.spice_exe == "":
    debug.error("No recognizable spice version found. Unable to perform characterization.",1)



