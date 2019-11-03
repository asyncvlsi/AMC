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


import design
import debug
import contact
import math
from vector import vector
from pinv import pinv
from nand2 import nand2
from nand3 import nand3
from nor2 import nor2
from nor3 import nor3

class and_or_gate(design.design):
    """ Generating AND/OR gates  
        with NAND2, NAND3, NOR2 or NOR3 gates plus inverter"""

    def __init__(self, gate="AND2", name="AND2"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))
        self.gate=gate
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.add_layout_pins()
        self.height=self.inv.height

    def add_pins(self):
        """ Adds all pins of data pattern module """
        
        if (self.gate=="AND2" or self.gate=="OR2"):
            self.add_pin_list(["A", "B", "Z", "vdd", "gnd"])
        if (self.gate=="AND3" or self.gate=="OR3"):
            self.add_pin_list(["A", "B", "C", "Z", "vdd", "gnd"])

    def create_modules(self):
        """ construct all the required modules """
        
        self.inv = pinv()
        self.add_mod(self.inv)

        if self.gate=="AND2":
            self.nand2 = nand2()
            self.add_mod(self.nand2)
            self.add_in2(gate=self.nand2)
        
        if self.gate=="AND3":
            self.nand3 = nand3()
            self.add_mod(self.nand3)
            self.add_in3(gate=self.nand3)
        
        if self.gate=="OR2":
            self.nor2 = nor2()
            self.add_mod(self.nor2)
            self.add_in2(gate=self.nor2)
        
        if self.gate=="OR3":
            self.nor3 = nor3()
            self.add_mod(self.nor3)
            self.add_in3(gate=self.nor3)

    def add_in2(self, gate):
        """ Creating 2 input gate"""

        self.gate_inst = self.add_inst(name="2in_gate",mod=gate,
                                      offset=(0,0))
        self.connect_inst(["A", "B", "Z_b","vdd","gnd"])
        
        self.inv_inst = self.add_inst(name="inv",mod=self.inv,
                                      offset=(gate.width,0))
        self.connect_inst(["Z_b", "Z", "vdd","gnd"])
        
        self.width=gate.width+self.inv.width
    
    def add_in3(self, gate):
        """ Creating 3 input gate"""

        self.gate_inst = self.add_inst(name="3in_gate",mod=gate,
                                       offset=(0,0))
        self.connect_inst(["A", "B", "C", "Z_b","vdd","gnd"])
        
        self.inv_inst = self.add_inst(name="inv",mod=self.inv,
                                      offset=(gate.width,0))
        self.connect_inst(["Z_b", "Z", "vdd","gnd"])
        
        self.width=gate.width+self.inv.width
        

    def add_layout_pins(self):
        """ Adding input, output and power pins"""

        if (self.gate=="AND2" or self.gate=="OR2"):
            pins = ["A", "B", "vdd", "gnd"]
            for pin in pins:
                self.add_layout_pin(text=pin, 
                                    layer=self.m1_pin_layer, 
                                    offset=self.gate_inst.get_pin(pin).ll(), 
                                    width=self.m1_width, 
                                    height=self.m1_width)

        if (self.gate=="AND3" or self.gate=="OR3"):
            pins = ["A", "B", "C", "vdd", "gnd"]
            for pin in pins:
                self.add_layout_pin(text=pin, 
                                    layer=self.m1_pin_layer, 
                                    offset=self.gate_inst.get_pin(pin).ll(), 
                                    width=self.m1_width, 
                                    height=self.m1_width)
        self.add_layout_pin(text="Z", 
                            layer=self.m1_pin_layer, 
                            offset=self.inv_inst.get_pin(pin).ll(), 
                            width=self.m1_width, 
                            height=self.m1_width)
