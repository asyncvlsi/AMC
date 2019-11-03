# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
from vector import vector
from column_mux import column_mux
from tech import drc, info 

class column_mux_array(design.design):
    """ Dynamically generated column mux array """

    def __init__(self, columns, word_size, name="columnmux_array"):
        design.design.__init__(self, name)
        debug.info(1, "Creating {0}".format(name))
        
        self.columns = columns
        self.word_size = word_size
        self.name = name
        self.words_per_row = self.columns / self.word_size
        
        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for column_mux_array, order of the pins is important """
        
        for i in range(self.columns):
            self.add_pin("bl[{}]".format(i))
            self.add_pin("br[{}]".format(i))
        for i in range(self.words_per_row):
            self.add_pin("sel[{}]".format(i))
        for i in range(self.word_size):
            self.add_pin("bl_out[{}]".format(i))
            self.add_pin("br_out[{}]".format(i))
        self.add_pin("gnd")

    def create_layout(self):
        
        self.mux = column_mux()
        self.add_mod(self.mux)
        
        self.width = self.columns * self.mux.width
        
        self.create_array()
        self.add_routing()
        # Find the highest shapes to determine height before adding well
        highest = self.find_highest_coords()
        self.height = highest.y 
        self.add_layout_pins()
        self.offset_all_coordinates()
        
    def create_array(self):
        """ For every column, add a column_mux cell"""
        
        # one set of metal1 routes for select signals and bl & br outputs plus space 
        self.route_height = (self.words_per_row + 3) * self.m_pitch("m2")

        self.mux_inst = []
        for col_num in range(self.columns):
            name = "mux{0}".format(col_num)
            off = vector(col_num * self.mux.width, self.route_height)
            if col_num %2:
                mirror="MY"
                off = vector((col_num+1) * self.mux.width, self.route_height)
            else:
                mirror="R0"
            
            
            self.mux_inst.append(self.add_inst(name=name, mod=self.mux, offset=off, mirror=mirror))
            self.connect_inst(["bl[{}]".format(col_num), "br[{}]".format(col_num), 
                               "bl_out[{}]".format(int(col_num/self.words_per_row)),
                               "br_out[{}]".format(int(col_num/self.words_per_row)), 
                               "sel[{}]".format(col_num % self.words_per_row),"gnd"])

    def add_routing(self):
        self.add_horizontal_input_rail()
        self.add_vertical_poly_rail()
        self.route_bitlines()

    def add_horizontal_input_rail(self):
        """ Create select input rails below the column_mux transistors  """
        
        for j in range(self.words_per_row):
            offset = vector(0, self.route_height - (j+1)*self.m_pitch("m2"))
            self.add_rect(layer="metal1", 
                          offset=offset, 
                          width=self.width, 
                          height=self.m1_width)
            self.add_layout_pin(text="sel[{}]".format(j), 
                                layer=self.m1_pin_layer, 
                                offset=offset, 
                                width=self.m1_width, 
                                height=self.m1_width)

    def add_vertical_poly_rail(self):
        """  Connect the poly to the selsect rails """
        
        for col in range(self.columns):
            sel_index = col % self.words_per_row
            gate_offset = self.mux_inst[col].get_pin("sel").bc()
            sel_height = self.get_pin("sel[{}]".format(sel_index)).by()
            offset = (gate_offset.x, self.get_pin("sel[{}]".format(sel_index)).cy())
            
            if (self.mux_inst[0].get_pin("br").lx() - self.mux_inst[0].get_pin("bl").rx()) < 3*self.m2_width:
                self.add_path("poly", [offset, gate_offset])
                self.add_contact_center(self.poly_stack, offset, rotate=90)
            
            else:
                off=self.mux_inst[col].get_pin("sel").cc()
                self.add_contact_center(self.poly_stack,off , rotate=90)
                self.add_contact_center(self.m1_stack, off, rotate=90)
                
                self.add_path("metal2", [offset, gate_offset])
                self.add_contact_center(self.m1_stack, offset, rotate=90)
                
                width = max(contact.poly.second_layer_height, contact.m1m2.first_layer_height)
                self.add_rect_center(layer="metal1", 
                                     offset = off, 
                                     width=width, 
                                     height=1.5 * (self.m1_minarea / width))
            
            # add implant for poly-enclosure drc violation
            implant_offset = (self.mux_inst[0].lx(), self.mux_inst[0].by()-self.route_height)
            implant_width = self.width
            if (info["has_pimplant"] and drc["implant_enclosure_poly"]>0):
                self.add_rect(layer= "pimplant", 
                              offset= implant_offset, 
                              width = implant_width,
                              height= self.route_height)

    def route_bitlines(self):
        """  Connect the output bit-lines to form the appropriate width mux """
        
        for j in range(self.columns):
            bl_offset = self.mux_inst[j].get_pin("bl_out").ll()
            br_offset = self.mux_inst[j].get_pin("br_out").ll()

            bl_out_offset = bl_offset - vector(0,(self.words_per_row+1)*self.m_pitch("m2")+self.m1_space)
            br_out_offset = br_offset - vector(0,(self.words_per_row+2)*self.m_pitch("m2")+self.m1_space)

            if (j % self.words_per_row) == 0:
                width = self.mux_inst[self.words_per_row-1].get_pin("bl_out").rx() -\
                        self.mux_inst[0].get_pin("bl_out").lx()
                self.add_rect(layer="metal1",
                              offset=bl_out_offset,
                              width=width,
                              height=contact.m1m2.width)
                width = self.mux_inst[self.words_per_row-1].get_pin("br_out").rx() -\
                        self.mux_inst[0].get_pin("br_out").lx()
                self.add_rect(layer="metal1",
                              offset=br_out_offset,
                              width=width,
                              height=contact.m1m2.width)

                # Extend the bitline output rails downward on the first bit of each n-way mux
                self.add_rect(layer="metal2", 
                              offset=bl_out_offset.scale(1,0), 
                              width=self.m2_width, 
                              height=self.route_height)
                self.add_layout_pin(text="bl_out[{}]".format(int(j/self.words_per_row)), 
                                    layer=self.m2_pin_layer, 
                                    offset=bl_out_offset.scale(1,0), 
                                    width=self.m2_width, 
                                    height=self.m2_width)

                self.add_rect(layer="metal2", 
                              offset=br_out_offset.scale(1,0), 
                              width=self.m2_width, 
                              height=self.route_height)
                self.add_layout_pin(text="br_out[{}]".format(int(j/self.words_per_row)),
                                    layer=self.m2_pin_layer, 
                                    offset=br_out_offset.scale(1,0), 
                                    width=self.m2_width, 
                                    height=self.m2_width)
            
            else:
                self.add_rect(layer="metal2", 
                              offset=bl_out_offset, 
                              width=self.m2_width, 
                              height=self.route_height-bl_out_offset.y)
                self.add_rect(layer="metal2", 
                              offset=br_out_offset, 
                              width=self.m2_width, 
                              height=self.route_height-br_out_offset.y)
            
            self.add_via(self.m1_stack, bl_out_offset+vector(contact.m1m2.height, 0), rotate=90)
            self.add_via(self.m1_stack, br_out_offset+vector(contact.m1m2.height, 0), rotate=90)

    def add_layout_pins(self):
        """ Add the pins after height is determined """
        
        for col_num in range(self.columns):
            mux_inst = self.mux_inst[col_num]
            
            offset = mux_inst.get_pin("bl").ll()
            self.add_rect(layer="metal2", 
                          offset=offset,
                          width= self.m2_width, 
                          height=self.height-offset.y)
            self.add_layout_pin(text="bl[{}]".format(col_num), 
                                layer=self.m2_pin_layer, 
                                offset=offset,
                                width= self.m2_width, 
                                height=self.m2_width)

            offset = mux_inst.get_pin("br").ll()
            self.add_rect(layer="metal2", 
                          offset=offset,
                          width= self.m2_width, 
                          height=self.height-offset.y)
            self.add_layout_pin(text="br[{}]".format(col_num), 
                                layer=self.m2_pin_layer, 
                                offset=offset,
                                width= self.m2_width, 
                                height=self.m2_width)

            gnd_pin = self.mux_inst[0].get_pin("gnd")
            self.add_layout_pin(text="gnd", 
                                layer=gnd_pin.layer, 
                                offset=gnd_pin.ll(),
                                width = self.m1_width, 
                                height=self.m1_width)
