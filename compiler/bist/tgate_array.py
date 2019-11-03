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
from tech import drc, layer, info
from vector import vector
from tgate import tgate


class tgate_array(design.design):
    """ Dynamically generated an array of transmission gates """

    def __init__(self, size, name="tgate_array"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))
        
        self.size = size
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        
        self.tgate = tgate()
        self.add_mod(self.tgate)
        self.add_modules()
        self.add_well_contacts()
        self.add_layout_pins()
        self.width= self.tgate.width 
        self.height= self.tgate.height* self.size + 0.5*self.tgate.width
        
    def add_pins(self):
        """ Adds pins for tgate array module """
        
        for i in range(self.size):
            self.add_pin_list(["in1{0}".format(i), "in2{0}".format(i), "out{0}".format(i)])
        self.add_pin_list(["up_down", "up_down_b", "vdd", "gnd"])

    def add_modules(self):
        """ Adds tgates in a column"""

        self.tgate_off = {}
        for i in range(self.size):
            off=(0, i*self.tgate.height)
            self.tgate_off[i] = self.add_inst(name="tgate{0}".format(i), mod=self.tgate,
                                              offset=off)
            self.connect_inst(["in1{0}".format(i), "in2{0}".format(i), "out{0}".format(i), 
                               "up_down", "up_down_b", "vdd", "gnd"])

    def add_well_contacts(self):
        """ Add pwell and nwell contact"""
        well_xoff=self.tgate.nmos.height+2*self.m_pitch("m1") - self.implant_space
        well_yoff=self.tgate.height* self.size
        
        layers=[]
        if info["has_pimplant"]:
            layers.append("pimplant")
        if info["has_pwell"]:
            layers.append("pwell")

        width=self.tgate.nmos.height+2*self.m_pitch("m1") - self.implant_space
        for layer in layers:
            self.add_rect(layer=layer,
                          offset=(0, well_yoff),
                          width=width,
                          height=0.5*self.tgate.width)

        layers=[]
        if info["has_nimplant"]:
            layers.append("nimplant")
        if info["has_nwell"]:
            layers.append("nwell")

        width=self.tgate.pmos.height+2*self.m_pitch("m1") + self.implant_space +self.poly_space
        for layer in layers:
            self.add_rect(layer=layer,
                          offset=(well_xoff, well_yoff),
                          width=width,
                          height=0.5*self.tgate.width)

        pin=["gnd", "vdd"]
        for i in range(2):
            x_off = self.well_enclose_active + i*well_xoff
            y_off = well_yoff + self.well_enclose_active + i*self.m_pitch("m2")
            self.add_contact(("active", "contact", "metal1") , (x_off, y_off))
            
            self.add_rect(layer="metal1",
                          offset=(0, y_off),
                          width=self.tgate.width,
                          height=contact.m1m2.width)
            
            self.add_rect(layer="active",
                          offset=(x_off, y_off),
                          width=self.active_minarea/contact.well.height,
                          height=contact.well.height)
                          
            self.add_layout_pin(text=pin[i],
                                layer=self.m1_pin_layer,
                                offset=(self.tgate.width/2,y_off),
                                width=self.m1_width,
                                height=self.m1_width)
                          
        extra_off= (0, well_yoff)+(0,drc["extra_to_poly"])
        self.add_rect(layer="extra_layer",
                      layer_dataType = 122,
                      offset=extra_off,
                      width= self.tgate.width,
                      height= self.tgate.width/2-drc["extra_to_poly"])

    def add_layout_pins(self):
        """ Add all input, output and power pins"""
        
        for i in range(self.size):
            self.add_layout_pin(text="in1{0}".format(i),
                                layer=self.m1_pin_layer,
                                offset=self.tgate_off[i].get_pin("in1").ll(),
                                width=self.m1_width,
                                height=self.m1_width)
            self.add_layout_pin(text="in2{0}".format(i),
                                layer=self.m1_pin_layer,
                                offset=self.tgate_off[i].get_pin("in2").ll(),
                                width=self.m1_width,
                                height=self.m1_width)
            self.add_layout_pin(text="out{0}".format(i),
                                layer=self.m1_pin_layer,
                                offset=self.tgate_off[i].get_pin("out").ll(),
                                width=self.m1_width,
                                height=self.m1_width)
        
        pins=["up_down", "up_down_b"]
        
        for i in range(2):
            off=self.tgate_off[0].get_pin(pins[i]).uc()
            y_off=self.tgate_off[self.size-1].uy() + self.tgate.width/2
            self.add_path("metal2", [off, (off.x, y_off)])
            self.add_layout_pin(text=pins[i],
                            layer=self.m2_pin_layer,
                            offset=(off.x-0.5*self.m2_width, y_off-self.m2_width),
                            width=self.m2_width,
                            height=self.m2_width)
