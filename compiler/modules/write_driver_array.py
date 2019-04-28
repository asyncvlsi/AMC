import design
import debug
from vector import vector
from write_driver import write_driver

class write_driver_array(design.design):
    """ Array of dynamically generated write drivers to drive input data to the bitlines.  """

    def __init__(self, word_size, words_per_row, name = "write_driver_array"):
        design.design.__init__(self, name)
        debug.info(1, "Creating {0}".format(name))

        self.write_driver = write_driver()
        self.add_mod(self.write_driver)

        self.word_size = word_size
        self.words_per_row = words_per_row
        self.name = name
        self.row_size = self.word_size * self.words_per_row

        self.width = self.word_size * self.words_per_row * self.write_driver.width
        self.height = self.write_driver.height
        
        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for write_driver_array, order of the pins is important """
        
        for i in range(0, self.row_size, self.words_per_row):
            self.add_pin("data[{0}]".format(i/self.words_per_row))
            self.add_pin_list(["bl[{0}]".format(i), "br[{0}]".format(i)])
        self.add_pin_list(["en","vdd","gnd"])

    def create_layout(self):
        """ Create modules for instantiation and then route"""

        self.add_write_driver()
        self.connect_rails()

    def add_write_driver(self):
        """ Add write driver cells"""
        
        bl_pin = self.write_driver.get_pin("bl")            
        br_pin = self.write_driver.get_pin("br")
        din_pin = self.write_driver.get_pin("din")

        for i in range(0, self.row_size, self.words_per_row):
            name = "write_driver{}".format(i)
            wd_position = vector(i * self.write_driver.width,0)
            bl_offset = wd_position + bl_pin.ll()
            br_offset = wd_position + br_pin.ll()
            din_offset = wd_position + din_pin.ll()
            
            self.add_inst(name=name, mod=self.write_driver, offset=wd_position)
            self.connect_inst(["data[{0}]".format(i/self.words_per_row), 
                               "bl[{0}]".format(i),"br[{0}]".format(i), "en", "vdd", "gnd"])
            
            self.add_layout_pin(text="data[{0}]".format(i/self.words_per_row),
                                layer=din_pin.layer, 
                                offset=din_offset, 
                                width=din_pin.width(), 
                                height=din_pin.height())
                       
            self.add_layout_pin(text="bl[{0}]".format(i), 
                                layer=bl_pin.layer, 
                                offset=bl_offset, 
                                width=bl_pin.width(), 
                                height=bl_pin.height())
            
            self.add_layout_pin(text="br[{0}]".format(i), 
                                layer=br_pin.layer, 
                                offset=br_offset, 
                                width=br_pin.width(), 
                                height=br_pin.height())

    def connect_rails(self):
        """ Add vdd, gnd and en rails across entire array """
        
        #vdd
        vdd_pin=self.write_driver.get_pin("vdd")
        self.add_rect(layer="metal1", 
                      offset=vdd_pin.ll().scale(0,1),
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="vdd", 
                            layer=vdd_pin.layer, 
                            offset=vdd_pin.ll().scale(0,1),
                            width=vdd_pin.width(), 
                            height=vdd_pin.height())
                       
        #gnd
        gnd_pin=self.write_driver.get_pin("gnd")
        self.add_rect(layer="metal1", 
                      offset=gnd_pin.ll().scale(0,1),
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="gnd", 
                            layer=gnd_pin.layer, 
                            offset=gnd_pin.ll().scale(0,1),
                            width=gnd_pin.width(), 
                            height=gnd_pin.height())

        #en
        wen_pin=self.write_driver.get_pin("en")
        self.add_rect(layer="metal1", 
                      offset=wen_pin.ll().scale(0,1),
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="en", 
                            layer=wen_pin.layer, 
                            offset=wen_pin.ll().scale(0,1),
                            width=wen_pin.width(), 
                            height=wen_pin.height())
