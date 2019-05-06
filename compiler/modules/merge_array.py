""" This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301, USA.
"""


import design
import debug
from vector import vector
from merge import merge

class merge_array(design.design):
    """ Array of dynamically generated merge cells for multi bank SRAM. """

    def __init__(self, word_size, words_per_row, name=""):
        
        if name=="":
            name = "merge_array_{0}_{1}".format(word_size, words_per_row)
        design.design.__init__(self, name )
        debug.info(1, "Creating {0}".format(name))

        self.merge = merge()
        self.add_mod(self.merge)

        self.word_size = word_size
        self.words_per_row = words_per_row
        self.name = name
        self.row_size = self.word_size * self.words_per_row

        self.height = self.merge.height
        self.width = self.merge.width * self.word_size * self.words_per_row

        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for merge_array, order of the pins is important """

        for i in range(0,self.row_size,self.words_per_row):
            self.add_pin("D[{0}]".format(i/self.words_per_row))
            self.add_pin("Q[{0}]".format(i/self.words_per_row))
        self.add_pin_list(["en1_M", "en2_M", "reset" ,"M" ,"vdd" ,"gnd"])

    def create_layout(self):
        """ Create modules for instantiation and then route"""

        self.add_merge()
        self.connect_rails()

    def add_merge(self):
        """ Add merge cells """
            
        D_pin = self.merge.get_pin("D")
        Q_pin = self.merge.get_pin("Q")
        
        for i in range(0,self.row_size,self.words_per_row):

            name = "merge{0}".format(i)
            merge_position = vector(self.merge.width * i, 0)
            
            D_offset = merge_position + vector(D_pin.ll().x, D_pin.ul().y-D_pin.height())
            Q_offset = merge_position + vector(Q_pin.ll().x, Q_pin.ll().y)
            
            self.add_inst(name=name, mod=self.merge, offset=merge_position)
            self.connect_inst(["D[{0}]".format(i/self.words_per_row), 
                               "Q[{0}]".format(i/self.words_per_row), 
                               "en1_M", "en2_M", "reset", "M", "vdd", "gnd"])

            self.add_layout_pin(text="D[{0}]".format(i/self.words_per_row), 
                                layer=D_pin.layer, 
                                offset=D_offset, 
                                width=D_pin.width(), 
                                height=D_pin.height())
            self.add_layout_pin(text="Q[{0}]".format(i/self.words_per_row), 
                                layer=Q_pin.layer, 
                                offset=Q_offset, 
                                width=Q_pin.width(), 
                                height=Q_pin.height())

    def connect_rails(self):
        """ Add vdd, gnd, en1_M, en2_M, reset and select rails across entire array """
        
        #vdd
        vdd_pin = self.merge.get_pin("vdd")
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
        gnd_pin = self.merge.get_pin("gnd")
        self.add_rect(layer="metal1", 
                      offset=gnd_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="gnd", 
                            layer=gnd_pin.layer, 
                            offset=gnd_pin.ll().scale(0,1), 
                            width=gnd_pin.width(), 
                            height=gnd_pin.height())

        #en1_M
        en1_pin = self.merge.get_pin("en1_M")
        self.add_rect(layer="metal1", 
                      offset=en1_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="en1_M", 
                            layer=en1_pin.layer, 
                            offset=en1_pin.ll().scale(0,1), 
                            width=en1_pin.width(), 
                            height=en1_pin.height())

        #en2_M
        en2_pin = self.merge.get_pin("en2_M")
        self.add_rect(layer="metal1", 
                      offset=en2_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="en2_M", 
                            layer=en2_pin.layer, 
                            offset=en2_pin.ll().scale(0,1), 
                            width=en2_pin.width(), 
                            height=en2_pin.height())

        #reset
        reset_pin = self.merge.get_pin("reset")
        self.add_rect(layer="metal1", 
                      offset=reset_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="reset", 
                            layer=reset_pin.layer, 
                            offset=reset_pin.ll().scale(0,1), 
                            width=reset_pin.width(), 
                            height=reset_pin.height())

        #M
        M_pin = self.merge.get_pin("M")
        self.add_rect(layer="metal1", 
                      offset=M_pin.ll().scale(0,1), 
                      width=self.width, 
                      height=self.m1_width)
        self.add_layout_pin(text="M", 
                            layer=M_pin.layer, 
                            offset=M_pin.ll().scale(0,1), 
                            width=M_pin.width(), 
                            height=M_pin.height())
