# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
import math
from vector import vector
from utils import round_to_grid
from ptx import ptx
from tech import info, drc, layer
from bitcell import bitcell
from utils import ceil as util_ceil

class column_mux(design.design):
    """ This module Creates a single column muxltiplexer cell. A column mux cell contains 2 NMOS. """

    def __init__(self):
        name="column_mux"
        design.design.__init__(self, name)
        debug.info(2, "create single column mux cell: {0}".format(name))

        self.bitcell = bitcell()
        
        # This is to avoid DRC violation with arrays above and below column_mux
        self.pin_height = 5*self.m1_width
        self.width = self.bitcell.width

        self.ptx_width = 2*self.minwidth_tx
        self.add_pin_list(["bl", "br", "bl_out", "br_out", "sel", "gnd"])
        
        self.create_layout()

    def create_layout(self):
        """ Create modules for instantiation and then route"""

        self.add_ptx()
        self.connect_poly()
        self.add_bitline_pins()
        self.connect_bitlines()
        self.add_gnd_rail()
        self.add_well_contact()
        self.offset_all_coordinates()
        
    def add_ptx(self):
        """ Create the two pass gate NMOS transistors to switch the bitlines.
            Width of column_mux cell is equal to bitcell' width for abutment. 
            first NMOS at left and second NMOS at right"""
        
        # If NMOS size if bigger than bicell_width use multi finger NMOS
        n = int(math.floor((0.5* (self.bitcell.width-6*self.m1_space)) / self.minwidth_tx))
        m = (self.ptx_width/n)
        if m > self.minwidth_tx:
            num_fing = int(math.ceil(self.ptx_width/n))
        else:
            num_fing = 1
        self.nmos = ptx(width= round_to_grid(self.ptx_width/num_fing), 
                        mults= num_fing, 
                        tx_type="nmos", 
                        connect_active=True, 
                        connect_poly=True)
        self.add_mod(self.nmos)
        if info["has_nimplant"]:
            shift = self.implant_enclose_poly

        else:
            shift = 0.5*self.poly_space
        
        # Add nmos1 and nmos2 with a pace it in the center
        self.nmos1_position = vector(self.nmos.height+shift, 
                                     -self.nmos.active_offset.x)
        self.nmos1=self.add_inst(name="mux_tx1", 
                                 mod=self.nmos, 
                                 offset=self.nmos1_position, 
                                 rotate=90)
        self.connect_inst(["bl", "sel", "bl_out", "gnd"])

        # nmos2 in same y_offset as nmos1 for gate abutting
        self.nmos2_position = vector(self.bitcell.width-shift, 
                                     self.nmos1_position.y)
        self.nmos2=self.add_inst(name="mux_tx2", 
                                 mod=self.nmos, 
                                 offset=self.nmos2_position, 
                                 rotate=90)
        self.connect_inst(["br", "sel", "br_out", "gnd"])
        
        self.top = self.nmos2.uy() + self.pin_height
        self.height = self.top+contact.well.height+self.pin_height

    def connect_poly(self):
        """ Connect the poly gate of the two pass transistors """
        
        x_off =0.5*(self.nmos2.get_pin("G").lc().x-self.nmos1.get_pin("G").lc().x)
        offset = (self.nmos1.get_pin("G").lc().x+ x_off, self.nmos1.get_pin("G").by())
        self.add_path("poly", [self.nmos1.get_pin("G").lc(), self.nmos2.get_pin("G").lc()])        
        self.add_layout_pin(text="sel", 
                            layer=self.poly_pin_layer, 
                            offset=offset, 
                            width=self.poly_width,
                            height=self.poly_width)

    def add_bitline_pins(self):
        """ Add the BL and BR pins to column_mux cell """

        bl_pos = vector(self.bitcell.get_pin("bl").lx(), 0)
        br_pos = vector(self.bitcell.get_pin("br").lx(), 0)

        # bl and br
        self.add_layout_pin(text="bl", 
                            layer=self.m2_pin_layer, 
                            offset=bl_pos + vector(0,self.top-contact.m1m2.width),
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)
        self.add_layout_pin(text="br", 
                            layer=self.m2_pin_layer, 
                            offset=br_pos + vector(0,self.top-contact.m1m2.width),
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)
        
        # bl_out and br_out
        self.add_layout_pin(text="bl_out", 
                            layer=self.m2_pin_layer, 
                            offset=bl_pos+ vector(0,-contact.well.height-self.pin_height),
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)
        self.add_layout_pin(text="br_out", 
                            layer=self.m2_pin_layer, 
                            offset=br_pos+ vector(0,-contact.well.height-self.pin_height),
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)

    def add_m1_minarea(self, pin):
        """ add metal1 in active contact area to avoid min_area vioalation """
        
        self.add_rect_center(layer="metal1", 
                             offset=pin, 
                             width=self.m1_minarea/contact.m1m2.width, 
                             height=contact.m1m2.width)
    
    def connect_bitlines(self):
        """ Connect the bitlines to the mux transistors """
        
        bl_pin = self.get_pin("bl")
        br_pin = self.get_pin("br")

        nmos1_s_pin = vector(self.nmos1.get_pin("S").uc().x, self.nmos1.get_pin("S").lc().y)
        nmos1_d_pin = vector(self.nmos1.get_pin("D").uc().x, self.nmos1.get_pin("D").lc().y)
        nmos2_s_pin = vector(self.nmos2.get_pin("S").uc().x, self.nmos2.get_pin("S").lc().y)
        nmos2_d_pin = vector(self.nmos2.get_pin("D").uc().x, self.nmos2.get_pin("D").lc().y)
        
        self.add_via_center(self.m1_stack, nmos1_s_pin, rotate=90)
        self.add_via_center(self.m1_stack, nmos1_d_pin+vector(0, contact.m1m2.width), rotate=90)
        self.add_via_center(self.m1_stack, nmos2_s_pin, rotate=90)
        self.add_via_center(self.m1_stack, nmos2_d_pin+vector(0, contact.m1m2.width), rotate=90)
        
        shift=0.5*(self.m1_minarea/contact.m1m2.width)
        self.add_m1_minarea(vector(self.nmos1.lx()+shift, nmos1_s_pin.y))
        self.add_m1_minarea(vector(self.nmos1.lx()+shift, nmos1_d_pin.y))
        self.add_m1_minarea(vector(self.nmos2.rx()-shift, nmos2_s_pin.y))
        self.add_m1_minarea(vector(self.nmos2.rx()-shift, nmos2_d_pin.y))
        
        self.add_path("metal2",[(bl_pin.uc().x, -contact.well.height-self.pin_height),nmos1_s_pin], 
                      width=contact.m1m2.width)
        self.add_path("metal2", [(bl_pin.uc().x,self.top),(nmos1_d_pin.x, nmos1_d_pin.y+contact.m1m2.width)], 
                      width=contact.m1m2.width)
        self.add_path("metal2",[(br_pin.uc().x, -contact.well.height-self.pin_height),nmos2_s_pin], 
                      width=contact.m1m2.width)
        self.add_path("metal2",[(br_pin.uc().x,self.top), (nmos2_d_pin.x, nmos2_d_pin.y+contact.m1m2.width)], 
                      width=contact.m1m2.width)

    def add_gnd_rail(self):
        """ Add the gnd rails that span the whole cell"""

        self.gnd_position = vector(0, self.nmos1.by()-self.m1_width)
        self.add_rect(layer="metal1", 
                       offset=self.gnd_position, 
                       width = self.width,
                       height=self.m1_width)
        self.add_layout_pin(text="gnd", 
                            layer=self.m1_pin_layer, 
                            offset=self.gnd_position,
                            width = self.m1_width, 
                            height=self.m1_width)
        
    def add_well_contact(self):
        """ Add a well and implant over the whole cell. Also, add the pwell contact"""
        
        well_contact_offset = vector(self.well_enclose_active + contact.well.width, 
                                     self.nmos1.by() - self.m1_width - contact.well.height)
        if info["has_pimplant"]:
            implant_type="p"
        else:
            implant_type=None
        
        if info["has_pwell"]:
            well_type="p"
        else:
            well_type=None
        
        self.add_contact(layers=("active", "contact", "metal1"), 
                         offset=well_contact_offset, 
                         implant_type=implant_type, 
                         well_type=well_type, 
                         add_extra_layer=info["well_contact_extra"])
        
        active_width= self.active_minarea/contact.well.first_layer_height
        active_height = contact.well.first_layer_height
        active_offse= vector(self.well_enclose_active,  well_contact_offset.y+ \
                      self.m1_extend_contact-self.active_extend_contact)
        self.add_rect(layer="active", 
                      offset=active_offse, 
                      width = active_width,
                      height= active_height)

        if info["has_pimplant"]:
            self.add_rect(layer="pimplant", 
                          offset=(0,-contact.well.height-self.pin_height), 
                          width = self.width,
                          height= self.nmos1.by()+contact.well.height+self.pin_height)

        if info["has_nimplant"]:
            self.add_rect(layer="nimplant", 
                          offset=(0, self.nmos1.by()), 
                          width =self.width ,
                          height= self.top-self.nmos1.by())

        if info["has_pwell"]:
            self.add_rect(layer="pwell", 
                          offset=(0,-contact.well.height-self.pin_height), 
                          width =self.width ,
                          height= self.top+contact.well.height+self.pin_height)


        vt_offset = vector(0, self.nmos1.by())
        self.add_rect(layer="vt",
                      offset=vt_offset,
                      layer_dataType = layer["vt_dataType"],
                      width=self.width,
                      height=self.nmos.width)


        extra_height = active_height+2*self.extra_enclose
        #extra_width = self.extra_minarea/ extra_height
        extra_width = self.width
        extra_off= vector(0, active_offse[1]-self.extra_enclose)
        self.add_rect(layer="extra_layer",
                      layer_dataType = layer["extra_layer_dataType"],
                      offset=extra_off,
                      width= extra_width,
                      height= extra_height)

