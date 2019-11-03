# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
from ptx import ptx
from vector import vector
from utils import ceil
from bitcell import bitcell
from tech import info, drc, layer

class precharge(design.design):
    """ Creates a single precharge cell used in the design. A precharge cell 
        contains 3 PMOS transistors. """

    def __init__(self):
        design.design.__init__(self, "precharge")
        debug.info(2, "create single precharge cell")

        self.bitcell = bitcell()
        
        self.ptx_width = 2*self.minwidth_tx
        self.add_pin_list(["bl", "br", "en", "vdd"])
        self.width = self.bitcell.width

        self.create_layout()

    def create_layout(self):
        """ Create modules for instantiation and then route"""

        self.create_ptx()
        self.add_ptx()
        self.connect_poly_and_en()
        self.add_vdd_rail()
        self.add_well_and_wellcontact()
        self.add_bitlines()
        self.connect_to_bitlines()
        self.offset_all_coordinates()

    def create_ptx(self):
        """Initializes the pmoses """
           
        self.pmos = ptx(width=self.ptx_width, tx_type="pmos")
        self.add_mod(self.pmos)

        
    def add_ptx(self):
        """Adds transistors"""
        
        # this shift in x-direction avoids DRC violation for pchg cells in array
        if info["has_nimplant"]:
            x_shift = self.implant_enclose_poly

        else:
            x_shift = 0.5*self.poly_space

        y_shift= self.well_enclose_active + contact.well.height
        
        if info["tx_dummy_poly"]:
            y_shift= y_shift + self.well_enclose_active
        
        
        # adding 3 pmoses for precharge cell
        pmos1_pos = vector(self.pmos.height+x_shift, self.pmos.width+y_shift-self.poly_width)
        self.pmos1_inst=self.add_inst(name="pmos1",
                                      mod=self.pmos,
                                      offset=pmos1_pos,
                                      rotate=90)
        self.connect_inst(["bl", "en", "br", "vdd"])

        pmos2_pos = vector(self.width-x_shift, pmos1_pos.y)
        self.pmos2_inst=self.add_inst(name="pmos2",
                                     mod=self.pmos,
                                     offset=pmos2_pos,
                                     rotate=90)
        self.connect_inst(["bl", "en", "vdd", "vdd"])

        pmos3_pos = vector(self.pmos.height+x_shift, y_shift)
        self.pmos3_inst=self.add_inst(name="pmos3",
                                     mod=self.pmos,
                                     offset=pmos3_pos,
                                     rotate=90)
        self.connect_inst(["br", "en", "vdd", "vdd"])

        
        # add a m1_pitch at top for DRC-free abutment connection with write_complete 
        self.height = self.pmos2_inst.uy()+self.m_pitch("m1")

    def connect_poly_and_en(self):

        """Adds the en pin and connect it to pmoses' gate"""
        # connects pmos gates together
        
        self.add_path("poly", [self.pmos1_inst.get_pin("G").lc(), self.pmos2_inst.get_pin("G").lc()])
        self.mid_pos=vector(0.5*self.width, self.pmos1_inst.get_pin("G").lc().y)
        
        if (self.bitcell.get_pin("br").lx() - self.bitcell.get_pin("bl").rx()) < 3*self.m2_width:
            self.add_path("poly", [self.mid_pos,self.pmos3_inst.get_pin("G").lc()])
            
            off=(self.mid_pos.x+0.5*self.poly_width, self.height-contact.poly.height)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            self.add_path( "poly", [(self.mid_pos.x, self.height), self.mid_pos])
        
        else:
            pos1=self.pmos3_inst.get_pin("G").cc()
            pos2=(self.mid_pos.x, self.pmos3_inst.get_pin("G").cc().y)
            self.add_path("poly", [pos1, pos2])
            
            off=(self.mid_pos.x, self.pmos3_inst.get_pin("G").cc().y)
            self.add_contact_center(self.poly_stack, off, rotate=90)
            
            off=(self.mid_pos.x, self.pmos3_inst.get_pin("G").cc().y)
            self.add_contact_center(self.m1_stack, off, rotate=90)

            off=(self.mid_pos.x, self.pmos1_inst.get_pin("G").cc().y)
            self.add_contact_center(self.poly_stack, off, rotate=90)
            
            off=(self.mid_pos.x, self.pmos1_inst.get_pin("G").cc().y)
            self.add_contact_center(self.m1_stack, off, rotate=90)
            
            off=(self.mid_pos.x, self.height-0.5*self.m1_width)
            self.add_contact_center(self.m1_stack, off, rotate=90)
            
            off=(self.mid_pos.x-0.5*self.m2_width,self.pmos3_inst.get_pin("G").cc().y)
            self.add_rect(layer="metal2",
                          offset=off,
                          width = self.m2_width,
                          height= self.height-self.pmos3_inst.get_pin("G").cc().y)
            off=(self.mid_pos.x-0.5*self.m2_width,self.pmos3_inst.get_pin("G").cc().y)
            self.add_rect(layer="metal1",
                          offset=off,
                          width = self.m1_width,
                          height= self.pmos1_inst.get_pin("G").cc().y-self.pmos3_inst.get_pin("G").cc().y)
        
        # Add enable pin and rail
        self.add_rect(layer="metal1",
                      offset=(0,self.height-self.m1_width),
                      width = self.width,
                      height= self.m1_width)
        self.add_layout_pin(text="en",
                            layer=self.m1_pin_layer,
                            offset=(0,self.height-self.m1_width),
                            width = self.m1_width,
                            height = self.m1_width)

        if info["tx_dummy_poly"]:                     
             pos1= (self.pmos1_inst.lx()+self.pmos.dummy_poly_offset1.y, 
                    self.pmos1_inst.by()+self.pmos.dummy_poly_offset1.x)
             pos2= (self.pmos2_inst.lx()+self.pmos.dummy_poly_offset1.y, 
                    self.pmos2_inst.by()+self.pmos.dummy_poly_offset1.x)
             self.add_path("poly", [pos1+vector(0,0.5*self.poly_width), 
                                    pos2+vector(0,0.5*self.poly_width)])
            
             pos1= (self.pmos1_inst.lx()+self.pmos.dummy_poly_offset2.y, 
                    self.pmos1_inst.by()+self.pmos.dummy_poly_offset2.x)
             pos2= (self.pmos2_inst.lx()+self.pmos.dummy_poly_offset2.y, 
                    self.pmos2_inst.by()+self.pmos.dummy_poly_offset2.x)
             self.add_path("poly", [pos1+vector(0,0.5*self.poly_width), 
                                    pos2+vector(0,0.5*self.poly_width)])


             pos1= (self.pmos3_inst.lx()+self.pmos.dummy_poly_offset1.y, 
                    self.pmos3_inst.by()+self.pmos.dummy_poly_offset1.x)
             pos2= (self.pmos2_inst.lx()+self.pmos.dummy_poly_offset1.y, 
                    self.pmos3_inst.by()+self.pmos.dummy_poly_offset1.x)
             self.add_path("poly", [pos1+vector(0,0.5*self.poly_width), 
                                    pos2+vector(0,0.5*self.poly_width)])
    
    def add_vdd_rail(self):
        """Adds a vdd rail across the width of the cell that routes over drains of pmoses"""
        
        self.vdd_position = vector(0,self.pmos1_inst.get_pin("D").uy())
        self.add_rect(layer="metal1",
                      offset=self.vdd_position,
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=self.vdd_position,
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
    def add_well_and_wellcontact(self):
        """Adds a nwell tap to connect to the vdd rail"""

        nwell_contact = vector(self.width-self.well_enclose_active, self.well_enclose_active)
        
        if info["has_nwell"]:
            nwell_type = "n"
        else:
            nwell_type = None

        if info["has_nimplant"]:
            nimplant_type = "n"
        else:
            nimplant_type = None

        
        self.add_contact(layers=("active", "contact", "metal1"),
                         offset=nwell_contact,
                         rotate=90,
                         implant_type=nimplant_type, 
                         well_type=nwell_type, 
                         add_extra_layer=info["well_contact_extra"])
        active_width = self.active_minarea/contact.well.width
        active_off = vector(nwell_contact.x-active_width, nwell_contact.y)
        self.add_rect(layer="active",
                      offset=active_off,
                      width=active_width,
                      height=contact.well.width)
        extra_off = active_off-vector(self.extra_enclose, self.extra_enclose)
        extra_width = self.width-active_off.x+self.extra_enclose
        extra_height = max(contact.well.width + 2*self.extra_enclose, ceil(self.extra_minarea/extra_width))
        self.add_rect(layer="extra_layer",
                      layer_dataType = layer["extra_layer_dataType"],
                      offset= extra_off,
                      width= extra_width,
                      height= extra_height)
        
        pos1=(self.width-0.5*contact.m1m2.width, self.vdd_position.y)
        pos2=(nwell_contact.x-contact.well.height,nwell_contact.y+0.5*contact.well.width)
        self.add_path("metal1", [pos1, pos2], width=contact.m1m2.width)

        #adding nwell to cover all pmoses and nwell contact
        x_off =  self.width-2*self.well_enclose_active-active_width
        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                          offset=vector(0,0),
                          width=self.width,
                          height=self.height)
        
        
        if info["has_pimplant"]:
            # pimplant for pmoses
            self.add_rect(layer="pimplant",
                          offset=vector(0,0),
                          width=x_off,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset=vector(x_off,self.pmos2_inst.by()),
                          width=self.width-x_off,
                          height=self.height-self.pmos2_inst.by())

        if info["has_nimplant"]:
            # nimplant for nwell contact
            self.add_rect(layer="nimplant",
                          offset=vector(x_off,0),
                          width=self.width-x_off,
                          height=self.pmos2_inst.by())


        # pimplant for pmoses
        self.add_rect(layer="vt",
                      offset=vector(0,0),
                      layer_dataType = layer["vt_dataType"],
                      width=x_off,
                      height=self.height)
        self.add_rect(layer="vt",
                      offset=vector(x_off,self.pmos2_inst.by()),
                      layer_dataType = layer["vt_dataType"],
                      width=self.width-x_off,
                      height=self.height-self.pmos2_inst.by())

    def add_bitlines(self):
        """Adds both BL and BR pins to the module"""
        
        offset = vector(self.bitcell.get_pin("bl").cx()-0.5*self.m2_width,0)
        self.add_rect(layer="metal2",
                      offset=offset,
                      width=self.m2_width,
                      height=self.height)
        self.add_layout_pin(text="bl",
                            layer=self.m2_pin_layer,
                            offset=offset,
                            width=self.m2_width,
                            height=self.m2_width)

        offset = vector(self.bitcell.get_pin("br").cx()-0.5*self.m2_width,0)
        self.add_rect(layer="metal2",
                      offset=offset,
                      width=self.m2_width,
                      height=self.height)
        self.add_layout_pin(text="br",
                            layer=self.m2_pin_layer,
                            offset=offset,
                            width=self.m2_width,
                            height=self.m2_width)

    def connect_to_bitlines(self):
        """ Route bitlines to pmoses"""
        
        pmos3_s = self.pmos3_inst.get_pin("S")
        pmos2_s = self.pmos2_inst.get_pin("S")
        pmos1_s = self.pmos1_inst.get_pin("S")
        
        edge = abs(drc["metal1_extend_via1"] - drc["metal2_extend_via1"])
        self.add_path("metal1", [pmos1_s.uc(), self.pmos3_inst.get_pin("D").uc()], 
                      width= contact.m1m2.first_layer_height)
        
        pos1=(pmos3_s.uc().x-0.5*contact.active.height, pmos3_s.by()-0.5*self.m1_width)
        pos2=(pmos2_s.uc().x+0.5*contact.m1m2.height-edge, pmos3_s.by()-0.5*self.m1_width)
        self.add_path("metal1", [pos1, pos2])

        self.add_via_center(self.m1_stack, (pmos2_s.uc().x, pmos2_s.lc().y), rotate=90)
        self.add_via_center(self.m1_stack, (pmos1_s.uc().x, pmos1_s.lc().y), rotate=90)
        self.add_via_center(self.m1_stack, (pmos2_s.uc().x, pmos3_s.by()), rotate=90)
        
        height = ceil(self.m1_minarea/contact.m1m2.first_layer_height)
        self.add_rect_center(layer="metal1", 
                             offset = (pmos2_s.uc().x, pmos2_s.by()-0.5*height),
                             width= contact.m1m2.first_layer_height,
                             height= height)
