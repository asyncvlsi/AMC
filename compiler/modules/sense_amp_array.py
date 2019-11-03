# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
from vector import vector
from sense_amp import sense_amp

class sense_amp_array(design.design):
    """ Array of dynamically generated sense amplifiers to read the bitlines """

    def __init__(self, word_size, words_per_row, name="sense_amp_array"):
        design.design.__init__(self, name )
        debug.info(1, "Creating {0}".format(name))

        self.amp = sense_amp()
        self.add_mod(self.amp)

        self.word_size = word_size
        self.words_per_row = words_per_row
        self.name = name
        self.row_size = self.word_size * self.words_per_row

        self.height = self.amp.height
        self.width = self.amp.width * self.word_size * self.words_per_row

        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for sense_amp_array, order of the pins is important """

        for i in range(0,self.row_size,self.words_per_row):
            self.add_pin("data[{0}]".format(i/self.words_per_row))
            self.add_pin("data_bar[{0}]".format(i/self.words_per_row))
            self.add_pin("bl[{0}]".format(i))
            self.add_pin("br[{0}]".format(i))
        self.add_pin_list(["en","vdd","gnd"])

    def create_layout(self):
        """ Create modules for instantiation and then route"""

        self.add_sense_amp()
        self.connect_rails()

    def add_sense_amp(self):
        """ Add sense_amp cells """
            
        bl_pin = self.amp.get_pin("bl")            
        br_pin = self.amp.get_pin("br")
        dout_pin = self.amp.get_pin("dout")
        dout_bar_pin = self.amp.get_pin("dout_bar")
        self.sa_inst = {}
        
        for i in range(0,self.row_size,self.words_per_row):

            name = "sense_amp{0}".format(i)
            amp_position = vector(self.amp.width * i, 0)
            
            if (self.words_per_row==1 and i%2):
                mirror = "MY"
                amp_position = vector(i * self.amp.width + self.amp.width,0)
            else:
                mirror = "R0"
            

            self.sa_inst[i] = self.add_inst(name=name, mod=self.amp, offset=amp_position, mirror=mirror)
            self.connect_inst(["bl[{0}]".format(i),"br[{0}]".format(i), 
                               "data[{0}]".format(i/self.words_per_row), 
                               "data_bar[{0}]".format(i/self.words_per_row), 
                               "en", "vdd", "gnd"])

            bl_offset = vector(self.sa_inst[i].get_pin("bl").lx() , self.height-self.m2_width)
            br_offset = vector(self.sa_inst[i].get_pin("br").lx() , self.height-self.m2_width)
            dout_offset = self.sa_inst[i].get_pin("dout").ll()
            dout_bar_offset = self.sa_inst[i].get_pin("dout_bar").ll()


            self.add_layout_pin(text="bl[{0}]".format(i), 
                                layer=bl_pin.layer, 
                                offset=bl_offset, 
                                width=bl_pin.width(), 
                                height=self.m2_width)
            self.add_layout_pin(text="br[{0}]".format(i), 
                                layer=br_pin.layer, 
                                offset=br_offset, 
                                width=br_pin.width(), 
                                height=self.m2_width)
            self.add_layout_pin(text="data[{0}]".format(i/self.words_per_row), 
                                layer=dout_pin.layer, 
                                offset=dout_offset, 
                                width=dout_pin.width(), 
                                height=self.m2_width)
            self.add_layout_pin(text="data_bar[{0}]".format(i/self.words_per_row), 
                                layer=dout_bar_pin.layer, 
                                offset=dout_bar_offset, 
                                width=dout_bar_pin.width(), 
                                height=self.m2_width)

    def connect_rails(self):
        """ Add vdd, gnd and en rails across entire array """
        
        #vdd
        vdd_pin = self.amp.get_pin("vdd")
        self.add_rect(layer="metal1", 
                      offset=vdd_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="vdd", 
                            layer=vdd_pin.layer, 
                            offset=vdd_pin.ll().scale(0,1), 
                            width=self.m1_width, 
                            height=self.m1_width)

        #gnd
        gnd_pin = self.amp.get_pin("gnd")
        self.add_rect(layer="metal1", 
                      offset=gnd_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="gnd", 
                            layer=gnd_pin.layer, 
                            offset=gnd_pin.ll().scale(0,1), 
                            width=self.m1_width, 
                            height=self.m1_width)

        #en
        sen_pin = self.amp.get_pin("en")
        self.add_rect(layer="metal1", 
                      offset=sen_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="en", 
                            layer=sen_pin.layer, 
                            offset=sen_pin.ll().scale(0,1), 
                            width=self.m1_width, 
                            height=self.m1_width)
