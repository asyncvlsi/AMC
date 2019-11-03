# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import unittest, warnings
import sys, os, glob
from os import listdir
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class AMC_test(unittest.TestCase):
    """ Base unit test that we have some shared classes in. """
    
    def local_drc_check(self, w):
        """ check only DRC rules for the layout"""

        tempgds = OPTS.AMC_temp + "temp.gds"
        w.gds_write(tempgds)
        
        import calibre
        try:
            self.assertTrue(calibre.run_drc(w.name, tempgds)==0)
        except:
            self.reset()
            # removing density and ESD drc errors for unit tests only
            test=os.listdir(OPTS.AMC_temp)
            self.fail("DRC failed: {}".format(w.name))
    
        if OPTS.purge_temp:
            self.cleanup()
    
    def local_check(self, a, final_verification=False):
        """ check both LVS and DRC rules for the layout"""

        tempspice = OPTS.AMC_temp + "temp.sp"
        tempgds = OPTS.AMC_temp + "temp.gds"
        a.sp_write(tempspice)
        a.gds_write(tempgds)
        
        import calibre
        try:
            self.assertTrue(calibre.run_lvs(a.name, tempgds, tempspice, final_verification)==0)
        except:
            self.reset()
            self.fail("LVS mismatch: {}".format(a.name))

        self.reset()
        try:
            self.assertTrue(calibre.run_drc(a.name, tempgds)==0)
        except:
            self.reset()
            test=os.listdir(OPTS.AMC_temp)
            self.fail("DRC failed: {}".format(a.name))
        
        if OPTS.purge_temp:
            self.cleanup()

    def cleanup(self):
        """ Reset the duplicate checker and cleanup files. """
        
        files = glob.glob(OPTS.AMC_temp + '*')
        for f in files:
            if os.path.isfile(f):
                os.remove(f)        

    def reset(self):
        """ Reset the static duplicate name checker for unit tests """
        
        import design
        design.design.name_map=[]


    def isdiff(self,file1,file2):
        """ This is used to compare two files and display the diff if they are different.. """

        import debug
        import filecmp
        import difflib
        check = filecmp.cmp(file1,file2)
        if not check:
            debug.info(2,"MISMATCH {0} {1}".format(file1,file2))
            f1 = open(file1,"r")
            s1 = f1.readlines()
            f2 = open(file2,"r")
            s2 = f2.readlines()
            for line in difflib.unified_diff(s1, s2):
                debug.info(3,line)
            self.fail("MISMATCH {0} {1}".format(file1,file2))
        else:
            debug.info(2,"MATCH {0} {1}".format(file1,file2))

def header(filename, technology):
    from  globals import OPTS
    tst1 = "Running:"
    tst2 = "For:"
    tst3 = "Outputs:"
    print " ______________________________________________________________________________ "
    print "|==============================================================================|"
    print "|====" + "AMC: Asynchronous Memory Compiler".center(70) + "====|"
    print "|====" + "".center(70) + "====|"
    print "|====" + (tst1+ " " + filename).center(70) + "====|"
    print "|====" + (tst2+ " " + technology).center(70) + "====|"  
    print "|==============================================================================|"
