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
        
        self.x_offset0 = 6*self.m1_space
        self.width = self.x_offset0 + self.single_driver.width
        self.height = self.single_driver.height * self.rows

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
        
        power_layer = self.single_driver.get_pin("vdd").layer
        if (power_layer=="metal1" or power_layer=="m1pin"):
            self.power_layer = "metal1"
            self.power_pin_layer = self.m1_pin_layer
            self.pin_width= contact.m1m2.width
        else:
            self.power_layer = "metal3"
            self.power_pin_layer = self.m3_pin_layer
            self.pin_width= contact.m2m3.width
        
        self.add_layout_pin(text="gnd", 
                            layer=self.power_pin_layer, 
                            offset=[self.x_offset0, -0.5*self.pin_width], 
                            width=self.pin_width, 
                            height=self.pin_width)

        for row in range(self.rows):
            name = "single_driver{}".format(row)

            if (row % 2):
                y_offset = self.single_driver.height*(row + 1)
                mirror = "MX"
                pin_name = "gnd"
            else:
                y_offset = self.single_driver.height*row
                mirror = "R0"
                pin_name = "vdd"

            offset=[self.x_offset0, y_offset]
            
            # add single_driver
            single_driver_inst=self.add_inst(name=name, 
                                             mod=self.single_driver, 
                                             offset=offset, 
                                             mirror=mirror)
            self.connect_inst(["in[{0}]".format(row), "out[{0}]".format(row), "en", "vdd", "gnd"])

            # vdd, gnd connection
            yoffset = (row + 1) * self.single_driver.height -0.5*self.pin_width
            self.add_layout_pin(text=pin_name, 
                                layer=self.power_pin_layer, 
                                offset=[self.x_offset0, yoffset], 
                                width=self.pin_width, 
                                height=self.pin_width)

            # en connection
            en_pin = single_driver_inst.get_pin("in0")
            en_pos = en_pin.lc()
            en_offset = vector(2*self.m1_space, en_pos.y)
            self.add_segment_center(layer="metal1",  start=en_offset,  end=en_pos)
            self.add_via(self.m1_stack,(en_offset.x+contact.m1m2.height, en_offset.y-0.5*self.m1_width), 
                         rotate=90)

            # output pins on the right
            out_pin = single_driver_inst.get_pin("out")
            self.add_layout_pin_center_segment(text="out[{0}]".format(row), 
                                               layer=self.m1_pin_layer, 
                                               start=out_pin.rc(), 
                                               end=out_pin.rc()-vector(self.m1_width,0))

            # input pins on the left
            in_pin=single_driver_inst.get_pin("in1").ll()
            self.add_layout_pin(text="in[{0}]".format(row), 
                                layer=self.m1_pin_layer,
                                offset=in_pin,
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)
        
        #connect en connections of all drivers togrther
        self.add_rect(layer="metal2", 
                      offset=[2*self.m1_space,0], 
                      width=self.m2_width, 
                      height=self.height)
        en_pin=self.add_layout_pin(text="en", 
                                   layer=self.m2_pin_layer, 
                                   offset=[2*self.m1_space,0], 
                                   width=self.m2_width, 
                                   height=self.m2_width)
