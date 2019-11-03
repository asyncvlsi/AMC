# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import contact
import design
import debug
from tech import parameter, info, drc, layer
from ptx import ptx
from vector import vector
from math import ceil
from utils import round_to_grid
from utils import ceil as util_ceil
from nand3 import nand3

class pinv(design.design):
    """ Pinv generates a parametrically sized inverter. The size is specified as the drive size 
       (relative to minimum NMOS) and a beta value for choosing the pmos size. The inverter's cell
        height is the same as the nand3 (nand2, nor2, nor3) cell. """
    
    def __init__(self, size=1, beta=parameter["beta"], height=nand3.height):
        
        name = "pinv_{}".format(size)
        design.design.__init__(self, name)
        debug.info(2, "create inverter with size of {0}".format(size))

        self.nmos_size = size
        self.pmos_size = beta*size
        self.height = height
        self.add_pins()
        self.create_layout()

    def add_pins(self):
        """ Add pins for inverter, order of the pins is important """
        
        self.add_pin_list(["A", "Z", "vdd", "gnd"])

    def create_layout(self):
        """ Calls all functions related to the generation of the layout """

        self.determine_tx_mults()
        self.create_ptx()
        self.add_ptx()
        self.add_supply_rails()
        self.add_well_contacts()
        self.connect_rails()
        self.route_input()
        self.route_output()
        if info["tx_dummy_poly"]:
            self.add_dummy_poly()

        self.translate_all(vector(0,0))

    def determine_tx_mults(self):
        """ Determines the number of fingers for the height constraint. """
        
        min_tx = ptx(width=self.minwidth_tx, mults=1, tx_type="nmos")

        # This is a active-to-active of a flipped cell of active-conatct to power-rail inside cell
        top_bottom_space = max(self.active_to_active, 2*self.m1_space+contact.m1m2.width, self.poly_space)

        # Determine the height left to the transistors for number of fingers calculation
        tx_height_available = self.height - top_bottom_space
        
        #maximum possible num fingers
        tx_width = min_tx.active_width
        if info["tx_dummy_poly"]:
            tx_width = tx_width + 2*self.poly_to_active
        
        max_mults = max(int(ceil(tx_height_available/tx_width)),1)
        if self.nmos_size < max_mults:
            self.tx_mults = self.nmos_size
        else:
            self.tx_mults = max_mults

        # We need to round the width to the grid or we will end up with LVS property mismatch
        # errors when fingers are not a grid length and get rounded in the offset geometry.
        self.nmos_width = round_to_grid((self.nmos_size*self.minwidth_tx) / self.tx_mults)
        self.pmos_width = round_to_grid((self.pmos_size*self.minwidth_tx) / self.tx_mults)
        
    def create_ptx(self):
        """ Create the PMOS and NMOS transistors. """
        
        self.nmos = ptx(width=self.nmos_width,
                        mults=self.tx_mults,
                        tx_type="nmos",
                        connect_poly=True,
                        connect_active=True)
        self.add_mod(self.nmos)
        
        self.pmos = ptx(width=self.pmos_width,
                        mults=self.tx_mults,
                        tx_type="pmos",
                        connect_poly=True,
                        connect_active=True)
        self.add_mod(self.pmos)

    def add_ptx(self):
        """ Add PMOS and NMOS to the layout """
        
        # place PMOS right to nwell contact
        well_width = util_ceil(self.well_minarea/(self.height+contact.m1m2.width))
        if self.tx_mults==1:
            x_off = max(self.well_enclose_active + contact.well.width + \
                        self.implant_enclose_body_active+ self.m1_space+self.pmos.height, well_width)
        else:
            x_off = max(self.well_enclose_active + contact.well.width + \
                        self.implant_enclose_body_active + self.pmos.height+ self.poly_to_active, well_width)
        
        y_off= 0.5*self.height - 0.5*self.pmos.width
        
        pmos_pos = vector(x_off, y_off)
        self.pmos_inst=self.add_inst(name="pinv_pmos",
                                     mod=self.pmos,
                                     offset=pmos_pos,
                                     rotate=90)
        self.connect_inst(["Z", "A", "vdd", "vdd"])

        # place NMOS right to pmos
        x_off = self.pmos_inst.rx()+self.nmos.height

        nmos_pos = vector(x_off, y_off)
        self.nmos_inst=self.add_inst(name="pinv_nmos",
                                     mod=self.nmos,
                                     offset=nmos_pos,
                                     rotate=90)
        self.connect_inst(["Z", "A", "gnd", "gnd"])

        self.nwell_width = max(well_width, self.nmos_inst.lx())
        if info["has_nwell"]:
            # This should be covered nwell-contact and pmos
            nwell_pos = vector(0,-0.5*contact.m1m2.width)
            # This should be covered  only pmos
            self.pimplant_pos = vector(pmos_pos.x-self.pmos.height,-0.5*contact.m1m2.width)
            self.add_rect(layer="nwell", 
                          offset=nwell_pos, 
                          width=self.nwell_width, 
                          height=self.height+contact.m1m2.width)
            self.add_rect(layer="pimplant", 
                          offset=self.pimplant_pos, 
                          width=self.pmos.height, 
                          height=self.height+contact.m1m2.width)
        
        pwell_width= self.nmos_inst.height + contact.well.width + self.well_enclose_active+ \
                     max(self.implant_enclose_body_active, self.m1_space)
        if info["has_pwell"]:
            # This should cover pwell-contact and nmos
            pwell_pos = nimplant_pos= (self.nmos_inst.lx(),-0.5*contact.m1m2.width)
            self.add_rect(layer="pwell", 
                          offset=vector(self.nmos_inst.lx(),-0.5*contact.m1m2.width), 
                          width=pwell_width, 
                          height=self.height+contact.m1m2.width)
        if info["has_nimplant"]:
            self.add_rect(layer="nimplant", 
                          offset=vector(self.nmos_inst.lx(),-0.5*contact.m1m2.width), 
                          width=self.nmos_inst.height, 
                          height=self.height+contact.m1m2.width)

        self.vt_offset = vector(self.pmos_inst.lx(), -0.5*contact.m1m2.width)
        self.vt_width=self.pmos_inst.height + self.nmos_inst.height
        self.add_rect(layer="vt",
                      offset=self.vt_offset,
                      layer_dataType = layer["vt_dataType"],
                      width=self.vt_width,
                      height=self.height+contact.m1m2.width)


        self.width = self.nwell_width + pwell_width              

    def add_supply_rails(self):
        """ Add vdd/gnd rails to the top and bottom. """
        
        self.add_rect(layer="metal1",
                      offset=vector(0,-0.5*contact.m1m2.width),
                      width=self.width,
                      height =contact.m1m2.width)
        self.add_layout_pin(text="gnd",
                            layer=self.m1_pin_layer,
                            pin_dataType=None, 
                            label_dataType=None,  
                            offset=vector(0,-0.5*contact.m1m2.width),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        self.add_rect(layer="metal1",
                      offset=vector(0,self.height-0.5*contact.m1m2.width),
                      width=self.width,
                      height =contact.m1m2.width)
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=vector(0,self.height-0.5*contact.m1m2.width),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
    def add_well_contacts(self):
        """ Add n/p well taps to the layout and connect to supplies """

        layer_stack = ("active", "contact", "metal1")
        
        nwell_contact_offset=vector(self.well_enclose_active, 
                                    self.height+0.5*contact.m1m2.width-max(self.well_enclose_active,self.active_to_active)-contact.well.height)

        pwell_contact_offset= vector(self.nmos_inst.rx()+ \
                                     max(self.implant_enclose_body_active, self.m1_space), 
                                     self.well_enclose_active)
        
        if info["has_nwell"]:
            nwell_type = "n"
        else:
            nwell_type = None
        
        if info["has_nimplant"]:
            nimplant_type = "n"
        else:
            nimplant_type = None
        
        if info["has_pwell"]:
            pwell_type = "p"
        else:
            pwell_type = None
        
        if info["has_pimplant"]:
            pimplant_type = "p"
        else:
            pimplant_type = None

        self.nwell_contact=self.add_contact(layer_stack, nwell_contact_offset,mirror="MX", 
                                            implant_type=nimplant_type, well_type=nwell_type, add_extra_layer=info["well_contact_extra"])
        self.pwell_contact=self.add_contact(layer_stack, pwell_contact_offset, 
                                            implant_type=pimplant_type, well_type=pwell_type, add_extra_layer=info["well_contact_extra"])
        
        self.active_height = self.active_minarea/contact.well.width
        
        
        y_off1 = self.nmos_inst.get_pin("G").uy()+self.poly_to_active
        y_off2 = nwell_contact_offset.y-self.active_height-self.well_enclose_active+self.poly_to_active+contact.well.height
        active_off1 = vector(nwell_contact_offset.x, max(y_off1, y_off2))
        metal_off1= nwell_contact_offset 
        metal_height1 = self.height -  nwell_contact_offset.y
        pimplant_of = vector(0, -0.5*contact.m1m2.width)
        pimplant_width = self.pmos_inst.rx() - self.pmos.height
        
        active_off2 = pwell_contact_offset
        metal_off2= pwell_contact_offset.scale(1,0)
        metal_height2 = pwell_contact_offset.y
        self.nimplant_of = vector(self.nmos_inst.rx(), -0.5*contact.m1m2.width)
        self.nimplant_width = contact.well.width+self.well_enclose_active+\
                        max(self.implant_enclose_body_active, self.m1_space)
        extra_width = contact.well.width+self.extra_enclose+self.well_enclose_active
        extra_height = max(self.active_height+2*self.extra_enclose, 
                           util_ceil(self.extra_minarea/extra_width),
                           self.height+0.5*contact.m1m2.width-active_off1.y+self.extra_enclose)
        extra_off1= vector(0, self.height+0.5*contact.m1m2.width-extra_height)
        extra_off2= vector(active_off2.x-self.extra_enclose, -0.5*contact.m1m2.width)

        if nimplant_type:
            self.add_rect(layer="nimplant",
                          offset=pimplant_of,
                          width=pimplant_width,
                          height=self.height+contact.m1m2.width)

        if pimplant_type:
            self.add_rect(layer="pimplant",
                          offset=self.nimplant_of,
                          width=self.nimplant_width,
                          height=self.height+contact.m1m2.width)

        self.add_active_implant(nwell_contact_offset, active_off1, metal_off1, metal_height1, extra_width, extra_height, extra_off1)
        self.add_active_implant(pwell_contact_offset, active_off2, metal_off2, metal_height2, extra_width, self.height+contact.m1m2.width, extra_off2)


    def add_active_implant(self, well_off, active_off, metal_off, metal_height, extra_width, extra_height, extra_off):
        """ Add active and M1 the layout """
        
        self.add_rect(layer="active",
                      offset=active_off,
                      width=contact.well.width,
                      height=self.active_height)
        
        x_shift = max((self.active_width - self.contact_width)/2, self.active_enclose_contact)
        self.add_rect(layer="metal1",
                      offset=metal_off+vector(x_shift-self.m1_enclose_contact,0),
                      width=contact.well.second_layer_width,
                      height=metal_height)
        
        self.add_rect(layer="extra_layer",
                      layer_dataType = layer["extra_layer_dataType"],
                      offset=extra_off,
                      width= extra_width,
                      height= extra_height)
                      
    def connect_rails(self):
        """ Connect the nmos and pmos to its respective power rails """

        self.add_rect(layer="metal1",
                      offset=(self.nmos_inst.get_pin("S").lx(), 0),
                      width=self.m1_width,
                      height=self.nmos_inst.get_pin("S").by())

        if self.tx_mults==1:
            x_off = self.pmos_inst.get_pin("S").lc().x-self.m1_space-0.5*contact.m1m2.height
            self.add_path("metal1",[self.pmos_inst.get_pin("S").lc(),
                                   (x_off, self.pmos_inst.get_pin("S").lc().y),
                                   (x_off, self.height)])
        else:
            self.add_rect(layer="metal1",
                          offset=self.pmos_inst.get_pin("S").ll(),
                          width=self.m1_width,
                          height=self.height-self.pmos_inst.get_pin("S").by())
    
    def route_input(self):
        """ Route the input (gates) together, routes input to edge. """

        # Pick point on the left of NMOS and connect down to PMOS
        nmos_gate_pos = self.nmos_inst.get_pin("G")
        pmos_gate_pos =self.pmos_inst.get_pin("G")
        self.add_path("poly",[pmos_gate_pos.lc(),nmos_gate_pos.lc()])
        

        # Add the via to the cell midpoint along the gate
        if info["tx_dummy_poly"]:
            shift =  max(self.m1_space, self.poly_space, self.poly_to_active)
        
        else:
            shift =  max(self.m1_space, self.poly_to_active)
        contact_offset = vector(self.pmos_inst.lx()-contact.poly.width - shift,
                                nmos_gate_pos.by()-contact.poly.first_layer_height)


        poly_contact=self.add_contact(self.poly_stack, contact_offset)

        self.add_rect(layer="poly",
                      offset=(contact_offset.x, nmos_gate_pos.by()),
                      width=nmos_gate_pos.lx()-contact_offset.x,
                      height=self.poly_width)

        self.add_layout_pin(text="A",
                            layer=self.m1_pin_layer,
                            offset=(0,(self.height-contact.m1m2.width)/2),
                            width=self.m1_width,
                            height=self.m1_width)
        
        self.add_path("metal1",[(contact_offset.x+0.5*contact.poly.width, contact_offset.y), 
                                (0,(self.height-contact.m1m2.width)/2+0.5*self.m1_width)])

    def route_output(self):
        """ Route the output (drains) together, routes output to edge. """


        # Pick point at right most of NMOS and connect down to PMOS
        nmos_drain_pos = self.nmos_inst.get_pin("D")
        pmos_drain_pos = self.pmos_inst.get_pin("D")
        mid_pos = vector(self.nmos_inst.lx(), nmos_drain_pos.lc().y)
        output_offset = vector(self.width- self.m1_space, nmos_drain_pos.lc().y)
        
        # output pin at the edge of the cell in middle
        output_pin_offset = vector(self.width-self.m1_space-contact.m1m2.width, 
                                   nmos_drain_pos.by())

        
        self.add_path("metal1",[nmos_drain_pos.lc(), mid_pos, pmos_drain_pos.lc()], contact.active.second_layer_width)
        self.add_path("metal2",[(mid_pos.x, nmos_drain_pos.lc().y), output_offset])
        self.add_via_center(self.m1_stack,(mid_pos.x, nmos_drain_pos.lc().y), rotate=90)
        via_off= vector(output_pin_offset.x, nmos_drain_pos.lc().y-0.5*contact.m1m2.width - self.via_shift("v1"))
        self.add_via(self.m1_stack,via_off)
        
        height=util_ceil(self.m1_minarea/contact.m1m2.first_layer_width)
        minarea_yoff = max(self.pwell_contact.uy()+2*self.m1_space, via_off.y-0.5*height)
        self.add_rect(layer="metal1",
                      offset=(via_off.x, minarea_yoff),
                      width=contact.m1m2.first_layer_width,
                      height=height)

        Z_off = (self.width-self.m1_space, nmos_drain_pos.lc().y-0.5*contact.m1m2.width)
        self.add_layout_pin(text="Z",
                            layer=self.m1_pin_layer,
                            offset=Z_off,
                            width=self.m1_space,
                            height=self.m1_width)
        self.add_rect(layer="metal1",
                      offset=Z_off,
                      width=self.m1_space,
                      height=self.m1_width)
    
    def add_dummy_poly(self):
        
        y_off1 = self.pmos_inst.by() + max(self.nmos.dummy_poly_offset1.x, self.pmos.dummy_poly_offset1.x)
        y_off2 = self.pmos_inst.by() + max(self.nmos.dummy_poly_offset2.x, self.pmos.dummy_poly_offset2.x)
        self.add_rect_center(layer="poly",
                             offset=(self.pmos_inst.lx() + (self.pmos.height + self.nmos.height)/2 , y_off1+0.5*self.poly_width),
                             width=self.pmos.height + self.nmos.height,
                             height=self.poly_width)
        self.add_rect_center(layer="poly",
                             offset=(self.pmos_inst.lx() + (self.pmos.height + self.nmos.height)/2 , y_off2+0.5*self.poly_width),
                             width=self.pmos.height + self.nmos.height,
                             height=self.poly_width)
