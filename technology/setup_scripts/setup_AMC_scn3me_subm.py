# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


""" This is the setup script for scn3me_subm tech """

import sys
import os

TECHNOLOGY = "scn3me_subm"
AMC_TECH=os.path.abspath(os.environ.get("AMC_TECH"))
DRCLVS_HOME=AMC_TECH+"/scn3me_subm/tech"
os.environ["DRCLVS_HOME"] = DRCLVS_HOME
os.environ["SPICE_MODEL_DIR"] = "{0}/scn3me_subm/models/".format(AMC_TECH)
LOCAL = "{0}/..".format(os.path.dirname(__file__)) 
sys.path.append("{0}/{1}".format(LOCAL,TECHNOLOGY))
