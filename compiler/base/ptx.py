# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
from tech import layer, drc, info, spice
from vector import vector
from contact import contact
import path
import re
from utils import round_to_grid
from utils import ceil

class ptx(design.design):
    """ This module generates gds and spice of a parametrically NMOS or PMOS sized transistor.  
        Pins are accessed as D, G, S, B.  Width is the transistor width. Mults is the number of 
        transistors of the given width. Total width is therefore mults*width.  Options allow you 
        to connect the fingered gates and active for parallel devices. """

    def __init__(self, width=drc["minwidth_tx"], mults=1, tx_type="nmos", connect_active=False, 
                       connect_poly=False, num_contacts=None, min_area=True, dummy_poly=True):
        
        # We need to keep unique names because outputting to GDSII will use the last record with 
        # a given name. I.e., you will over-write a design in GDS if one has and the other doesn't
        # have poly connected, for example.
        
        name = "{0}_m{1}_w{2}_{3}".format(tx_type, mults, width, int(min_area))
        if connect_active:
            name += "_a"
        if connect_poly:
            name += "_p"
        if num_contacts:
            name += "_c{}".format(num_contacts)
        
        # replace periods with underscore for newer spice compatibility
        name=re.sub('\.','_',name)

        design.design.__init__(self, name)
        debug.info(3, "create ptx structure {0}".format(name))

        self.tx_type = tx_type
        self.mults = mults
        self.tx_width = width
        self.connect_active = connect_active
        self.connect_poly = connect_poly
        self.num_contacts = num_contacts
        # If True apply min_area rule for active region
        self.min_area = min_area
        self.dummy_poly = dummy_poly
        self.create_layout()
        self.create_spice()
        self.offset_all_coordinates()
    
    def create_layout(self):
        """Calls all functions related to the generation of the layout"""
        
        self.setup_layout_constants()
        self.add_active()
        self.add_poly()
        if (info["tx_dummy_poly"] and self.dummy_poly):
             self.add_dummy_poly()
        self.add_active_contacts()
        self.add_well_implant()

    def setup_layout_constants(self):
        """ Pre-compute some handy layout parameters. """

        if self.num_contacts==None:
            self.num_contacts=self.calculate_num_contacts()

        # Determine layer types needed
        if self.tx_type == "nmos":
            self.implant_type = "n"
            self.well_type = "p"
        elif self.tx_type == "pmos":
            self.implant_type = "p"
            self.well_type = "n"
        else:
            self.error("Invalid transitor type.",-1)
            
            
        # This is not actually instantiated but used for calculations
        self.active_contact = contact(layer_stack=("active", "contact", "metal1"),
                                      dimensions=(1, self.num_contacts))

        # The contacted poly pitch
        self.poly_pitch = max(2*self.contact_to_gate + self.contact_width + self.poly_width,
                              self.poly_space)

        
        # This is the distance from the edge of poly to the contacted end of active
        self.end_to_poly = max(self.active_enclose_contact + self.contact_width + self.contact_to_gate,
                               self.active_enclose_gate)
        
        # The contacted poly pitch
        self.contact_pitch = 2*self.contact_to_gate + self.contact_width + self.poly_width
        
        # Active height is just the transistor width
        self.active_height = self.tx_width

        # Poly height must include poly extension over active
        self.poly_height = self.active_height + 2*self.poly_extend_active

        # Active width is determined by enclosure on both ends and contacted pitch,
        # at least one poly and n-1 poly pitches
        self.active_width = 2*self.end_to_poly + self.poly_width + (self.mults - 1)*self.poly_pitch


        if ((self.active_width*self.active_height) < drc["minarea_active"] and self.min_area):
            end_to_poly = ceil(drc["minarea_active"] / (2*self.active_height)) - (self.poly_width/2)
            self.active_width = 2*end_to_poly + self.poly_width

        self.active_offset = vector(self.well_enclose_active, self.well_enclose_active)
        # Well enclosure of active, ensure minwidth as well
        if info["has_{}well".format(self.well_type)]:
            self.cell_well_width = max(self.active_width + 2*self.well_enclose_active, self.well_width)
            self.cell_well_height = max(self.poly_height, self.active_height + 2*self.well_enclose_active, self.well_width)
            self.cell_vt_width = self.active_width + 2*drc["vt_extend_active"]
            self.cell_vt_height = self.active_height + 2*drc["vt_extend_active"]
            self.width = max(self.cell_well_width, self.cell_vt_width)
            self.height = max(self.cell_well_height, self.cell_vt_height)

        else:
            # If no well, use the boundary of the active and poly
            self.cell_well_width = self.active_width + 2*self.well_enclose_active
            self.cell_well_height = max(self.poly_height, self.active_height + 2*self.well_enclose_active)
            self.cell_vt_width = self.active_width + 2*drc["vt_extend_active"]
            self.cell_vt_height = self.active_height + 2*drc["vt_extend_active"]
            self.width = max(self.cell_well_width, self.cell_vt_width)
            self.height = max(self.poly_height, self.cell_vt_height)
        
        if info["tx_dummy_poly"]:
            self.height = max(self.height, ceil(self.poly_minarea / self.poly_width))
        
        
        # This is the center of the first active contact offset (centered vertically)
        y_shift = max(self.active_enclose_contact, 
                      self.active_enclose_gate - self.contact_width - self.contact_to_gate)
        self.contact_offset = self.active_offset + vector(y_shift + 0.5*self.contact_width, 
                                                          0.5*self.active_height)
                                     
    def calculate_num_contacts(self):
        """  Calculates the possible number of source/drain contacts in a finger.For now, it is 1. """
        return 1


    def add_active(self):
        """  Adding the diffusion (active region = diffusion region) """
        
        self.active=self.add_rect(layer="active",
                                  offset=self.active_offset,
                                  width=self.active_width,
                                  height=self.active_height)

    def add_poly(self):
        """ Add the poly gates(s) and (optionally) connect them. """
        
        # poly is one contacted spacing from the end and down an extension
        self.poly_offset = self.active_offset + vector(self.poly_width,self.poly_height).scale(0.5,0.5)\
                           + vector(self.end_to_poly, -self.poly_extend_active)

        # poly_positions are the bottom center of the poly gates
        poly_positions = []

        # It is important that these are from left to right, 
        # so that the pins are in the right order for the accessors
        for i in range(0, self.mults):
            # Add this duplicate rectangle in case we remove the pin when joining fingers
            self.add_rect_center(layer="poly",
                                 offset=self.poly_offset,
                                 height=self.poly_height,
                                 width=self.poly_width)
            self.add_layout_pin_center_rect(text="G",
                                            layer=self.poly_pin_layer,
                                            offset=self.poly_offset,
                                            height=self.poly_width,
                                            width=self.poly_width)
            poly_positions.append(self.poly_offset)
            self.poly_offset = self.poly_offset + vector(self.poly_pitch,0)

        if self.connect_poly:
            self.connect_fingered_poly(poly_positions)
    
    
    def add_dummy_poly(self):
        """ Add the dummy poly to tx"""
        
        # dummy poly is added on both side (left & right) of active region
        dummy_poly_width = self.poly_width
        dummy_poly_height = max(ceil(self.poly_minarea / self.poly_width),self.poly_height)
        #SAMIRA  changed 2*self.poly_to_active to 2.5*self.poly_to_active!!
        xoff = max(1.5*self.poly_to_active, self.well_enclose_active)
        #self.dummy_poly_offset1 = self.active_offset - vector(xoff, 0.5*(dummy_poly_height-self.active.height))
        self.dummy_poly_offset1 = self.active_offset - vector(xoff , self.poly_extend_active)

        #dummy poly on left
        self.add_rect(layer="poly",
                      offset=self.dummy_poly_offset1,
                      height=dummy_poly_height,
                      width=dummy_poly_width)

        #dummy poly on right
        #self.dummy_poly_offset2 = self.active_offset + vector(self.active.width+xoff-self.poly_width , -0.5*(dummy_poly_height-self.active.height))
        self.dummy_poly_offset2 = self.active_offset + vector(self.active.width+xoff-self.poly_width , -self.poly_extend_active)
        #SAMIRA  changed 2*self.poly_to_active to 2.5*self.poly_to_active!!
        self.add_rect(layer="poly",
                      offset=self.dummy_poly_offset2,
                      height=dummy_poly_height,
                      width=dummy_poly_width)

    def connect_fingered_poly(self, poly_positions):
        """ Connect together the poly gates and create the single gate pin. The poly positions are 
            the center of the poly gates and we will add a single horizontal connection. Implantation 
            layer is extended to enclose the poly """
        
        # Nothing to do if there's one poly gate
        if len(poly_positions)<2:
            return

        # The width of the poly is from the left-most to right-most poly gate
        poly_width = poly_positions[-1].x - poly_positions[0].x + self.poly_width
        
        if self.tx_type == "pmos":
            # This can be limited by poly to active spacing or the poly extension
            distance_below_active = self.poly_width + max(self.poly_to_active,0.5*self.poly_height)
            self.poly_offset = poly_positions[0] - vector(0.5*self.poly_width, distance_below_active)

        else:
            # This can be limited by poly to active spacing or the poly extension
            distance_above_active = max(self.poly_to_active,0.5*self.poly_height)            
            self.poly_offset = poly_positions[0] + vector(-0.5*self.poly_width, distance_above_active)

        # Remove the old pin and add the new one
        self.remove_layout_pin("G") # only keep the main pin
        self.add_rect(layer="poly",
                      offset=self.poly_offset,
                      width=poly_width,
                      height=drc["minwidth_poly"])
        self.add_layout_pin(text="G",
                            layer=self.poly_pin_layer,
                            offset=self.poly_offset,
                            width=drc["minwidth_poly"],
                            height=drc["minwidth_poly"])

    def add_active_contacts(self):
        """ Add the active contacts to the transistor. """

        [source_positions, drain_positions] = self.get_contact_positions()
        
        if info["has_{}well".format(self.well_type)]:
            well_type = self.well_type
            implant_type = self.implant_type
        else:
            well_type = None
            implant_type = None
        
        pin_width = self.active_contact.second_layer_width
        for pos in source_positions:
            contact=self.add_contact_center(layers=("active", "contact", "metal1"),
                                            offset=pos,
                                            size=(1, self.num_contacts),
                                            implant_type=implant_type,
                                            well_type=well_type)
            self.add_layout_pin_center_rect(text="S",
                                            layer=self.m1_pin_layer,
                                            offset=pos,
                                            width=pin_width,
                                            height=pin_width)
                
        for pos in drain_positions:
            contact=self.add_contact_center(layers=("active", "contact", "metal1"),
                                            offset=pos,
                                            size=(1, self.num_contacts),
                                            implant_type=implant_type,
                                            well_type=well_type)
            self.add_layout_pin_center_rect(text="D",
                                            layer=self.m1_pin_layer,
                                            offset=pos,
                                            width=pin_width,
                                            height=pin_width)
                
        if self.connect_active:
            self.connect_fingered_active(drain_positions, source_positions)


    def get_contact_positions(self):
        """ Create a list of the centers of drain and source contact positions. """
        
        # The first one will always be a source
        source_positions = [self.contact_offset]
        drain_positions = []
        
        # It is important that these are from left to right, so that 
        # the pins are in the right order for the accessors.
        
        for i in range(self.mults):
            if i%2:
                # It's a source... so offset from previous drain.
                source_positions.append(drain_positions[-1] + vector(self.contact_pitch,0))
            else:
                # It's a drain... so offset from previous source.
                drain_positions.append(source_positions[-1] + vector(self.contact_pitch,0))

        return [source_positions,drain_positions]


    def connect_fingered_active(self, drain_positions, source_positions):
        """ Connect each contact  up/down to a source or drain pin """
        
        # This is the distance that we must route up or down from the center
        # of the contacts to avoid DRC violations to the other contacts
        pin_offset = vector(0, 0.5*max(self.active_contact.height, self.active_contact.width) + \
                               self.m1_space + 0.5*self.m1_width)
        
        # This is the width of a m1 extend the ends of the pin
        end_offset = vector(0.5*self.m1_width,0)

        # drains always go to the MIDDLE of the cell, so top of NMOS, bottom of PMOS
        # so reverse the directions for NMOS compared to PMOS.
        if self.tx_type == "pmos":
            drain_dir = -1
            source_dir = 1
        else:
            drain_dir = 1
            source_dir = -1
            
        if len(source_positions)>1: 
            source_offset = pin_offset.scale(source_dir,source_dir)
            self.remove_layout_pin("S") # remove the individual connections
            # Add each vertical segment
            for a in source_positions:
                self.add_path(("metal1"), [a,a+pin_offset.scale(source_dir,source_dir)])
            # Add a single horizontal pin
            self.add_segment_center(layer="metal1",
                                    start=source_positions[0]+source_offset-end_offset,
                                    end=source_positions[-1]+source_offset+end_offset)

            source_pin_offset=source_positions[0]+source_offset
            self.add_layout_pin_center_rect(text="S",
                                            layer=self.m1_pin_layer,
                                            offset=source_pin_offset,
                                            width=self.m1_width,
                                            height=self.m1_width)

        if len(drain_positions)>1:
            drain_offset = pin_offset.scale(drain_dir,drain_dir)
            self.remove_layout_pin("D") # remove the individual connections
            # Add each vertical segment
            for a in drain_positions:
                self.add_path(("metal1"), [a,a+drain_offset])
            # Add a single horizontal pin
            self.add_segment_center(layer="metal1",
                                    start=drain_positions[0]+drain_offset-end_offset,
                                    end=drain_positions[-1]+drain_offset+end_offset)
            
            drain_pin_offset=drain_positions[0]+drain_offset
            self.add_layout_pin_center_rect(text="D",
                                            layer=self.m1_pin_layer,
                                            offset=drain_pin_offset,
                                            width=self.m1_width,
                                            height=self.m1_width)

    def add_well_implant(self):
        """ Add an well and implant for the type of transistor. """
        
        self.well_offset = (0,0)
        if (self.mults>1 and self.connect_poly):
            poly_extend = (self.poly_extend_active+self.poly_width-self.well_enclose_active)
            if poly_extend > 0:
                self.cell_well_height = self.cell_well_height + poly_extend
                # for pmos tx, poly connection is below active
                if self.tx_type == "pmos":
                    self.well_offset=self.well_offset- vector(0, poly_extend)
                # for nmos tx, poly connection is above active
                else:
                    self.well_offset=self.well_offset- vector(0, 0)
            
        if (self.mults>1 and self.connect_active):
            shift = 0.5*(self.active_contact.height-self.active_height)
            m1_extend = shift+self.m1_space+self.m1_width-self.well_enclose_active
            if m1_extend > 0: 
                self.cell_well_height = self.cell_well_height + m1_extend 
                
                # for pmos tx, m1 connection for D contact is above active
                if self.tx_type == "pmos":
                    self.well_offset=self.well_offset - vector(0, 0)
                # for nmos tx, m1 connection for S contact is below active
                else:
                    self.well_offset=self.well_offset- vector(0, m1_extend)

                
                if(m1_extend-poly_extend) > 0 and self.mults>2: 
                    self.cell_well_height = self.cell_well_height + (m1_extend-poly_extend) 

                    # for pmos tx, m1 connection for D contact is above active
                    if self.tx_type == "pmos":
                        self.well_offset=self.well_offset - vector(0, (m1_extend-poly_extend))
                    # for nmos tx, m1 connection for S contact is below active
                    else:
                        self.well_offset=self.well_offset- vector(0, 0)
        
        self.height = max(self.cell_well_height, self.height)
        
        
        if info["has_{}well".format(self.well_type)]:
            self.add_rect(layer="{}well".format(self.well_type),
                          offset=self.well_offset,
                          width=self.cell_well_width,
                          height=self.cell_well_height)
        
        if info["has_{}implant".format(self.implant_type)]:
            self.add_rect(layer="{}implant".format(self.implant_type),
                          offset=self.well_offset,
                          width=self.cell_well_width,
                          height=self.cell_well_height)
        
        vt_offset = self.active_offset+vector(self.cell_vt_width, self.cell_vt_height).scale(0.5, 0.5) - \
                    vector(0.5*(self.cell_vt_width-self.active_width), drc["vt_extend_active"])

        self.add_rect_center(layer="vt",
                             offset=vt_offset,
                             layer_dataType = layer["vt_dataType"],
                             width=self.cell_vt_width,
                             height=self.cell_vt_height)
                      
        
    def create_spice(self):
        self.add_pin_list(["D", "G", "S", "B"])
        
        # Just make a guess since these will actually be decided in the layout later.
        area_sd = 2.5*drc["minwidth_poly"]*self.active_height
        perimeter_sd = 2*drc["minwidth_poly"] + 2*self.active_height
        if (spice["poly_bias"] != -1):
            extra_spice_info = "p_la={}".format(spice["poly_bias"])
        else:
            extra_spice_info = ""
        
        self.spice_device="M{{0}} {{1}} {0} m={1} w={2}u l={3}u pd={4}u ps={4}u as={5}p ad={5}p {6}".format(
                           spice[self.tx_type], self.mults, self.active_height, 
                           drc["minwidth_poly"], perimeter_sd, area_sd, extra_spice_info)

        self.spice.append("\n* ptx " + self.spice_device)
