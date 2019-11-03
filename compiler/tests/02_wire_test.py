# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


"Run a regresion test on a basic wire. "

import unittest
from testutils import header,AMC_test
import sys,os
sys.path.append(os.path.join(sys.path[0],".."))
import globals
from globals import OPTS
import debug

class wire_test(AMC_test):

    def runTest(self):
        globals.init_AMC("config_20_{0}".format(OPTS.tech_name))
        global calibre
        import calibre
        OPTS.check_lvsdrc = False

        import wire
        import tech
        import design
        

        min_space = 2 * (tech.drc["minwidth_metal2"] + tech.drc["minwidth_metal1"])
        layer_stack = ("metal1", "via1", "metal2")
        position_list = [[0, 0],
                         [0, 3 * min_space],
                         [1 * min_space, 3 * min_space],
                         [4 * min_space, 3 * min_space],
                         [4 * min_space, 0],
                         [7 * min_space, 0],
                         [7 * min_space, 4 * min_space],
                         [-1 * min_space, 4 * min_space],
                         [-1 * min_space, 0]]
        w = design.design("wire_test1")
        wire.wire(w, layer_stack, position_list)
        self.local_drc_check(w)


        min_space = 2 * (tech.drc["minwidth_metal2"] + tech.drc["minwidth_metal1"])
        layer_stack = ("metal2", "via1", "metal1")
        position_list = [[0, 0],
                         [0, 3 * min_space],
                         [1 * min_space, 3 * min_space],
                         [4 * min_space, 3 * min_space],
                         [4 * min_space, 0],
                         [7 * min_space, 0],
                         [7 * min_space, 4 * min_space],
                         [-1 * min_space, 4 * min_space],
                         [-1 * min_space, 0]]
        w = design.design("wire_test2")
        wire.wire(w, layer_stack, position_list)
        self.local_drc_check(w)

        min_space = 2 * (tech.drc["minwidth_metal2"] + tech.drc["minwidth_metal3"])
        layer_stack = ("metal2", "via2", "metal3")
        position_list = [[0, 0],
                         [0, 3 * min_space],
                         [1 * min_space, 3 * min_space],
                         [4 * min_space, 3 * min_space],
                         [4 * min_space, 0],
                         [7 * min_space, 0],
                         [7 * min_space, 4 * min_space],
                         [-1 * min_space, 4 * min_space],
                         [-1 * min_space, 0]]
        position_list.reverse()
        w = design.design("wire_test3")
        wire.wire(w, layer_stack, position_list)
        self.local_drc_check(w)

        min_space = 2 * (tech.drc["minwidth_metal2"] + tech.drc["minwidth_metal3"])
        layer_stack = ("metal3", "via2", "metal2")
        position_list = [[0, 0],
                         [0, 3 * min_space],
                         [1 * min_space, 3 * min_space],
                         [4 * min_space, 3 * min_space],
                         [4 * min_space, 0],
                         [7 * min_space, 0],
                         [7 * min_space, 4 * min_space],
                         [-1 * min_space, 4 * min_space],
                         [-1 * min_space, 0]]
        position_list.reverse()
        w = design.design("wire_test4")
        wire.wire(w, layer_stack, position_list)
        self.local_drc_check(w)

        # return it back to it's normal state
        OPTS.check_lvsdrc = True
        globals.end_AMC()
        

# instantiate a copy of the class to actually run the test
if __name__ == "__main__":
    (OPTS, args) = globals.parse_args()
    del sys.argv[1:]
    header(__file__, OPTS.tech_name)
    unittest.main()
