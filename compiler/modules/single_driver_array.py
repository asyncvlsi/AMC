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
from vector import vector
from single_driver import single_driver

class single_driver_array(design.design):
    """ Creates single_driver_array to drive the wordline signals with Go """

    def __init__(self, rows=1, name = "single_driver_array"):
        design.design.__init__(self, name)
        
        self.single_driver = single_driver()
        self.add_mod(self.single_driver)

        self.rows = rows
        
        self.x_offset0 = 7*self.m1_space
        self.width = self.x_offset0 + self.single_driver.width
        #each single driver cell 4 drivers
        self.height = self.single_driver.height * (self.rows/4)

        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for single_driver_array, order of the pins is important """
        
        for i in range(self.rows):
            self.add_pin("in[{0}]".format(i))
        for i in range(self.rows):
            self.add_pin("out[{0}]".format(i))
        self.add_pin_list(["en", "vdd", "gnd"])

    def create_layout(self):
        """ Add single_driver cells and then route"""
        
        for i in range(self.rows/4):
            name = "single_driver{}".format(i)
            y_offset = self.single_driver.height*i

            if (i % 2):
                y_offset = y_offset+self.single_driver.height
                mirror = "MX"
                pin_list=["in[{0}]".format(4*i+3), "in[{0}]".format(4*i+2),
                          "in[{0}]".format(4*i+1), "in[{0}]".format(4*i),
                          "out[{0}]".format(4*i+3), "out[{0}]".format(4*i+2),
                          "out[{0}]".format(4*i+1),"out[{0}]".format(4*i),
                          "en", "vdd", "gnd"]
            else:
                
                mirror = "R0"
                pin_list=["in[{0}]".format(4*i), "in[{0}]".format(4*i+1),
                          "in[{0}]".format(4*i+2), "in[{0}]".format(4*i+3),
                          "out[{0}]".format(4*i), "out[{0}]".format(4*i+1),
                          "out[{0}]".format(4*i+2),"out[{0}]".format(4*i+3),
                          "en", "vdd", "gnd"]

            # add single_driver
            single_driver_inst=self.add_inst(name=name, 
                                             mod=self.single_driver, 
                                             offset=[self.x_offset0, y_offset], 
                                             mirror=mirror)
            self.connect_inst(pin_list)

            # vdd, gnd connection
            for vdd_pin in single_driver_inst.get_pins("vdd"):
                if (vdd_pin.layer=="metal1" or vdd_pin.layer=="m1pin"):
                    pin_width = contact.m1m2.width
                else:
                    pin_width = contact.m2m3.width

                self.add_layout_pin(text="vdd", 
                                    layer=vdd_pin.layer, 
                                    offset=vdd_pin.ll(), 
                                    width=pin_width, 
                                    height=pin_width)

            for gnd_pin in single_driver_inst.get_pins("gnd"):
                if (gnd_pin.layer=="metal1" or gnd_pin.layer=="m1pin"):
                    pin_width = contact.m1m2.width
                else:
                    pin_width = contact.m2m3.width

                self.add_layout_pin(text="gnd", 
                                    layer=gnd_pin.layer, 
                                    offset=gnd_pin.ll(), 
                                    width=pin_width, 
                                    height=pin_width)

            # en connection
            en_pin = single_driver_inst.get_pin("en")
            if (en_pin.layer=="metal1" or en_pin.layer=="m1pin"):
                pin_layer = "metal1"
                pin_width= self.m1_width
                layer_stack = self.m1_stack
                contact_height= contact.m1m2.height
                
            else:
                pin_width = "metal3"
                pin_width= self.m3_width
                layer_stack = self.m2_stack
                contact_height= contact.m2m3.height

            self.add_rect(layer=pin_layer,
                          offset= vector(2*self.m1_space, en_pin.by()),
                          width=en_pin.lx()-2*self.m1_space,
                          height=pin_width)
            self.add_via(layer_stack,(2*self.m1_space+contact_height, en_pin.by()), rotate=90)


            # output each OUT on the right
            for j in range(4):
                if i%2:
                    text_out = "out[{0}]".format(4*i+(3-j))
                    text_in="in[{0}]".format(4*i+(3-j))
                else:
                    text_out = "out[{0}]".format(4*i+j)
                    text_in="in[{0}]".format(4*i+j)


                out_pin = single_driver_inst.get_pin("out{0}".format(j))
                in_pin = single_driver_inst.get_pin("in{0}".format(j))
                if (out_pin.layer=="metal1" or out_pin.layer=="m1pin"):
                    pin_width = self.m1_width
                else:
                    pin_width = self.m3_width
                self.add_layout_pin(text=text_out, 
                                    layer=out_pin.layer,
                                    offset= (self.width-pin_width, out_pin.by()),
                                    width=pin_width, 
                                    height=pin_width)

                self.add_layout_pin(text=text_in, 
                                    layer=in_pin.layer,
                                    offset= in_pin.ll(),
                                    width=pin_width, 
                                    height=pin_width)

        # Wordline enable connection
        self.add_rect(layer="metal2", 
                      offset=[2*self.m1_space,0], 
                      width=self.m2_width, 
                      height=self.height)
        en_pin=self.add_layout_pin(text="en", 
                                   layer=self.m2_pin_layer, 
                                   offset=[2*self.m1_space,0], 
                                   width=self.m2_width, 
                                   height=self.m2_width)

