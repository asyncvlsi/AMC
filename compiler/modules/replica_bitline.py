# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
import utils
from utils import round_to_grid
from vector import vector
from pinv import pinv
from ptx import ptx
from tech import info, GDS, layer, drc
from replica_bitcell import replica_bitcell
from bitcell import bitcell
from delay_chain import delay_chain


class replica_bitline(design.design):
    """ Generate a replica bitline that simulates the delay of control logic 
        and bitline charging. Stages is the depth of the delay line and rows 
        is the height of the replica bit loads. """

    def __init__(self, delay_stages, delay_fanout, bitcell_loads, name="replica_bitline"):
        design.design.__init__(self, name)

        self.bitcell_loads = bitcell_loads
        self.delay_stages = delay_stages
        self.delay_fanout = delay_fanout
        
        self.add_pin_list(["en", "out", "vdd", "gnd"])
        self.create_modules()
        self.calculate_module_offsets()
        self.add_modules()
        if info["add_replica_well_tap"]:
            self.add_rbl_well_contacts()
        self.route()
        self.add_layout_pins()
        self.offset_all_coordinates()

    def create_modules(self):
        """ Create modules for later instantiation """
        
        self.replica_bitcell = replica_bitcell()
        self.add_mod(self.replica_bitcell)

        self.delay_chain = delay_chain([self.delay_fanout]*self.delay_stages)
        self.add_mod(self.delay_chain)

        self.inv = pinv(size=5)
        self.add_mod(self.inv)

        self.access_tx = ptx(tx_type="pmos")
        self.add_mod(self.access_tx)


    def calculate_module_offsets(self):
        """ Calculate all the module offsets """
                
        # delay chain and inv will be rotated 90
        self.rbl_inv_offset = vector(self.inv.height, self.inv.width)
        
        # access TX goes above inverter
        self.access_tx_offset = vector(0.5*self.inv.height,self.rbl_inv_offset.y) + \
                                vector(0,0.5*self.inv.height)
        self.delay_chain_offset = self.rbl_inv_offset + vector(-contact.m1m2.width,self.inv.width)

        # Replica bitcell is not rotated, it is placed 2 M1 pitch away from the delay chain
        self.replica_bitcell_offset = vector(self.rbl_inv_offset.x+2*self.m_pitch("m2"), 
                                             self.access_tx_offset.y+self.replica_bitcell.height)
        
        self.height = max(self.replica_bitcell_offset.y + (self.bitcell_loads+1)*self.replica_bitcell.height, 
                          self.delay_chain_offset.y+self.delay_chain.width)
        
        self.width = self.replica_bitcell_offset.x + self.replica_bitcell.width + 3*self.m_pitch("m1")

    def add_modules(self):
        """ Add all of the module instances in the logical netlist """
        
        self.rbl_inv_inst=self.add_inst(name="rbl_inv",
                                        mod=self.inv,
                                        offset=self.rbl_inv_offset+vector(-contact.m1m2.width,0),
                                        rotate=270,
                                        mirror="MX")
        self.connect_inst(["bl[0]", "out", "vdd", "gnd"])

        self.tx_inst=self.add_inst(name="rbl_access_tx",
                                   mod=self.access_tx,
                                   offset=self.access_tx_offset,
                                   rotate=90)
        # D, G, S, B
        self.connect_inst(["vdd", "delayed_en", "bl[0]", "vdd"])

        self.dc_inst=self.add_inst(name="delay_chain",
                                   mod=self.delay_chain,
                                   offset=self.delay_chain_offset,
                                   rotate=90)
        self.connect_inst(["en", "delayed_en", "vdd", "gnd"])

        self.rbc_inst=self.add_inst(name="bitcell",
                                    mod=self.replica_bitcell,
                                    offset=self.replica_bitcell_offset,
                                    mirror="MX")
        self.connect_inst(["bl[0]", "br[0]", "delayed_en", "vdd", "gnd"])

        self.dbc_inst={}
        for i in range(self.bitcell_loads):
            if i%2:
                mirror="MX"
                dbc_offset=self.rbc_inst.ul()+vector(0, self.replica_bitcell.height*(i+1))
            else:
                mirror="R0"
                dbc_offset=self.rbc_inst.ul()+vector(0, self.replica_bitcell.height*i)
            
            self.dbc_inst[i]=self.add_inst(name="dummy_cell{}".format(i),
                                           mod=self.replica_bitcell,
                                           offset=dbc_offset,
                                           mirror=mirror)
            self.connect_inst(["bl[0]", "br[0]", "gnd","vdd", "gnd"])

    def add_rbl_well_contacts(self):
        """ Add pwell and nwell contacts at the top of rbl column """
        
        #measure the size of implant(s) and well(s)in replica_bitcell
        if info["has_nwell"]:
            (nw_width, nw_height) = utils.get_libcell_size("replica_cell_6t", GDS["unit"], layer["nwell"])
        elif info["has_pimplant"]:
            (nw_width, nw_height) = utils.get_libcell_size("replica_cell_6t", GDS["unit"], layer["pimplant"])
        else :
            (nw_width, nw_height) = (0,0)
        
        if info["has_pwell"]:
            (pw_width, pw_height) = utils.get_libcell_size("replica_cell_6t", GDS["unit"], layer["pwell"])
        elif info["has_nimplant"]:
            (pw_width, pw_height) = utils.get_libcell_size("replica_cell_6t", GDS["unit"], layer["nimplant"])
        else:
            (pw_width, pw_height) = (0.5*(self.replica_bitcell.width-nw_width),self.replica_bitcell.height)
        
        if info["has_nwell"]:
            nwell_type="nwell"
        else:
            nwell_type=None
        
        if info["has_nimplant"]:
            nimplant_type="nimplant"
        else :
            nimplant_type=None
        
        if info["has_pwell"]:
            pwell_type="pwell"
        else:
            pwell_type=None
        
        if info["has_pimplant"]:
            pimplant_type="pimplant"
        else:
            pimplant_type=None


        xshift = (2*pw_width+nw_width-self.replica_bitcell.width)/2
        yshift = (max(nw_height, pw_height)-self.replica_bitcell.height)/2
        well_height = 2*self.well_enclose_active + 3*contact.active.width
        
        #add one pwell and one nwell contact at top of array
        pwell_contact_offset = vector(-xshift+self.well_enclose_active, 
                                      yshift+well_height-self.well_enclose_active-contact.active.height)
        pwell_offset=vector(-xshift, yshift)
        pimplant_offset=vector(-xshift, yshift)
        pimplant_width= pw_width-self.implant_space

        nwell_offset=vector(-xshift+pw_width, yshift)
        nwell_contact_offset = vector(nwell_offset.x+self.well_enclose_active, yshift+self.well_enclose_active)
        nimplant_offset=vector(nwell_offset.x-self.implant_space, yshift)
        nimplant_width=nw_width
        
        self.add_well_contact(nwell_contact_offset, nwell_offset, nimplant_offset, 
                              nwell_type, nimplant_type, nw_width, nimplant_width)
        self.add_well_contact(pwell_contact_offset, pwell_offset, pimplant_offset, 
                              pwell_type, pimplant_type, pw_width, pimplant_width)


        vdd_start = self.replica_bitcell_offset.x + self.replica_bitcell.width+\
                    self.m_pitch("m1")+0.5*contact.m1m2.width
        self.add_rect(layer= "metal1",
                      offset= self.dbc_inst[self.bitcell_loads-1].ul()+vector(0, nwell_contact_offset.y),
                      width= vdd_start-self.dbc_inst[self.bitcell_loads-1].lx(),
                      height= self.m1_width)

        off=self.dbc_inst[self.bitcell_loads-1].ul()+ pwell_contact_offset+(self.m1_width, 0)
        width=self.rbl_inv_inst.get_pin("gnd").lx()-pwell_contact_offset.x-\
              self.dbc_inst[self.bitcell_loads-1].lx()
        
        self.add_rect(layer= "metal1",
                      offset= off,
                      width= width,
                      height= self.m1_width)

    def add_well_contact(self, contact_offset, well_offset, implant_offset, 
                         well_type, implant_type, well_width, implant_width):

            self.well_height = max(drc["minarea_implant"]/implant_width, 
                         2*self.well_enclose_active + 3*contact.active.height,
                         2*self.well_enclose_active + self.active_minarea/contact.well.height)
            self.add_contact(("active", "contact", "metal1"), 
                              self.dbc_inst[self.bitcell_loads-1].ul()+contact_offset, 
                              add_extra_layer=info["well_contact_extra"])
            
            self.add_rect(layer= "active",
                          offset= self.dbc_inst[self.bitcell_loads-1].ul()+contact_offset,
                          width= contact.well.height,
                          height= self.active_minarea/contact.well.height)
            
            self.add_rect(layer="extra_layer",
                      layer_dataType = layer["extra_layer_dataType"],
                      offset=self.dbc_inst[self.bitcell_loads-1].ul()+well_offset,
                      width= well_width,
                      height=self.well_height)
            
            self.add_rect(layer= well_type,
                          offset= self.dbc_inst[self.bitcell_loads-1].ul()+well_offset,
                          width= well_width,
                          height=self.well_height)
            
            self.add_rect(layer= implant_type,
                          offset= self.dbc_inst[self.bitcell_loads-1].ul()+implant_offset,
                          width= implant_width,
                          height=self.well_height)

    def route(self):
        """ Connect all the signals together """
        
        self.route_access_tx()
        self.route_gnd()
        self.route_vdd()

    def route_access_tx(self):
        """ Route S, D and G of access transistor to delay-chain, inv and biline load """
        
        # 1. GATE ROUTE: Add the poly contact and nwell enclosure
        poly_offset = self.tx_inst.get_pin("G").rc()
        contact_offset = vector(self.dc_inst.get_pin("out").bc().x, poly_offset.y)
        self.add_contact_center(self.poly_stack, contact_offset)
        self.add_rect(layer="poly",
                      offset=self.tx_inst.get_pin("G").lr(),
                      width=contact_offset.x-poly_offset.x,
                      height=self.poly_width)
        
        if info["tx_dummy_poly"]:                     
             pos={}
             pos[0]= (self.tx_inst.lx()+self.access_tx.dummy_poly_offset1.y, 
                      self.tx_inst.by()+self.access_tx.dummy_poly_offset1.x)
             pos[1]= (self.tx_inst.lx()+self.access_tx.dummy_poly_offset2.y, 
                      self.tx_inst.by()+self.access_tx.dummy_poly_offset2.x)
             for i in range(2):
                 self.add_rect_center(layer="poly", 
                                      offset=pos[i]+vector(0, 0.5*self.poly_width), 
                                      width=drc["minarea_poly_merge"]/self.poly_width, 
                                      height=self.poly_width)
        
        nwell_offset = self.rbl_inv_inst.ll() + vector(-0.5*contact.m1m2.width, self.inv.width)
        nwell_width =  self.inv.height+contact.m1m2.width
        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                          offset=nwell_offset,
                          width=nwell_width,
                          height=self.tx_inst.uy()-nwell_offset.y+contact.m1m2.height)
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset=nwell_offset,
                          width=nwell_width,
                          height=self.tx_inst.uy()-nwell_offset.y+contact.m1m2.height)

        self.add_rect(layer="vt",
                      offset=self.tx_inst.ll(),
                      layer_dataType = layer["vt_dataType"],
                      width=drc["minarea_vt"]/self.access_tx.width,
                      height=self.access_tx.width)

        # 2. Route delay chain output to access tx gate
        delay_en_offset = self.dc_inst.get_pin("out").bc()
        self.add_path("metal1", [delay_en_offset,contact_offset])

        # 3. Route the mid-point of previous route to the bitcell WL
        wl_offset = self.rbc_inst.get_pin("wl").lc()
        wl_mid = vector(contact_offset.x, contact_offset.y)
        self.add_path("metal1", [contact_offset, wl_mid, (wl_offset.x+self.m1_width,wl_offset.y)])

        # 4. DRAIN ROUTE : Route the drain to the vdd rail
        drain_offset = self.tx_inst.get_pin("D").lc()
        vdd_offset = (self.rbl_inv_inst.get_pin("vdd").uc().x, drain_offset.y) 
        self.add_path("metal1", [drain_offset, vdd_offset])
        
        # 5. SOURCE ROUTE: Route the source to the RBL inverter input
        source_offset = self.tx_inst.get_pin("S").bc()
        mid1 = vector(source_offset.x, self.rbl_inv_inst.get_pin("gnd").uy()+\
                      self.m1_space+0.5*self.m1_width)
        inv_A_offset = self.rbl_inv_inst.get_pin("A").uc()
        mid2 = vector(inv_A_offset.x, mid1.y)
        self.add_path("metal1", [source_offset, mid1, mid2, inv_A_offset])
        
        # 6. Route the connection of the source route (mid2) to the RBL bitline (left)
        pos1= vector(self.rbc_inst.get_pin("bl").uc().x, self.rbc_inst.by()) 
        pos2= vector(pos1.x, pos1.y-self.m_pitch("m1"))
        pos5 = vector(inv_A_offset.x, mid1.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos5])
        
    def route_vdd(self):
        """ Adds two vdd pins, one for replica bitline load and one for delay chain """        
        
        # Add first vdd pin to the right of the rbc 
        vdd_start = vector(self.replica_bitcell_offset.x + self.replica_bitcell.width+self.m_pitch("m1") ,0)
        
        # It is the height of the entire RBL and bitcell
        self.add_rect(layer="metal1",
                      offset=vdd_start,
                      width=contact.m1m2.width,
                      height=self.dbc_inst[self.bitcell_loads-1].uy()+self.replica_bitcell.height)
        
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=vdd_start,
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        # Connect the vdd pins of the bitcell load directly to vdd
        for i in range(self.bitcell_loads):
            for dbc_vdd in self.dbc_inst[i].get_pins("vdd"):
                offset = vector(vdd_start.x, dbc_vdd.by())
                if dbc_vdd.layer == "m3pin":
                    layer = "metal3"
                    self.add_via(self.m2_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                elif dbc_vdd.layer == "m2pin":
                    layer = None

                else:
                    layer = "metal1"
                    self.add_via(self.m1_stack, offset)
                self.add_rect(layer=layer,
                              offset=offset,
                              width=self.replica_bitcell_offset.x-vdd_start.x,
                              height=contact.m1m2.width)

        # Also connect the replica bitcell vdd pin to vdd
        for rbc_vdd in self.rbc_inst.get_pins("vdd"):
            offset = vector(vdd_start.x, rbc_vdd.by())
            if rbc_vdd.layer == "m3pin":
                layer = "metal3"
                self.add_via(self.m2_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                self.add_via(self.m1_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                self.add_rect(layer="metal2",
                              offset= offset,
                              width=self.m2_width,
                              height=(self.bitcell_loads+1)*self.replica_bitcell.height)
            elif rbc_vdd.layer == "m2pin":
                layer = None
                self.add_wire(self.m1_stack, [rbc_vdd.bc(), 
                                             (rbc_vdd.bc().x, rbc_vdd.bc().y-2*self.m_pitch("m1")),
                                             (vdd_start.x, rbc_vdd.bc().y-2*self.m_pitch("m1"))])

            else:
                layer = "metal1"
                
            self.add_rect(layer=layer,
                          offset=offset,
                          width=self.replica_bitcell_offset.x-vdd_start.x,
                          height=contact.m1m2.width)

        # Add a second vdd pin. for delay chain and inverter
        inv_vdd_offset = self.rbl_inv_inst.get_pin("vdd").lc()
        self.add_rect(layer="metal1",
                      offset=inv_vdd_offset.scale(1,0),
                      width=contact.m1m2.width,
                      height=self.dc_inst.get_pin("vdd").by())

        self.add_layout_pin(text="vdd",
                            layer=self.rbl_inv_inst.get_pin("vdd").layer,
                            offset=inv_vdd_offset.scale(1,0),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
    def route_gnd(self):
        """ Route all signals connected to gnd """
        
        gnd_start = self.rbl_inv_inst.get_pin("gnd")
        gnd_end = self.dbc_inst[self.bitcell_loads-1].uy()
        if info["add_replica_well_tap"]:
            gnd_end = gnd_end+self.well_height
        
        self.add_rect(layer="metal2",
                      offset = vector(gnd_start.lx(), gnd_start.lc().y-contact.m1m2.height),
                      width = contact.m1m2.width,
                      height =max(self.dc_inst.uy(), gnd_end) - gnd_start.lc().y)

        self.add_rect(layer="metal1",
                      offset=(gnd_start.lc().x,0),
                      width=contact.m1m2.width,
                      height=gnd_start.uc().y)
        
        yoff=self.rbc_inst.get_pin("wl").lc().y+self.m_pitch("m1")
        self.add_rect(layer="metal1",
                      offset=(gnd_start.lc().x,yoff),
                      width=contact.m1m2.width,
                      height=max(self.dc_inst.uy(), gnd_end)-yoff)


        # Add via for the inverter
        offset = gnd_start.lc() + vector(0.5*contact.m1m2.width,-0.5*contact.m1m2.height)
        self.add_via_center(self.m1_stack, offset=offset)

        # Add pin from bottom to RBL inverter
        self.add_layout_pin(text="gnd",
                            layer=gnd_start.layer,
                            offset=gnd_start.lc().scale(1,0),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        gnd_pin = self.get_pin("gnd").lc()
        
        
        # Connect the gnd pins of dummy cells
        for i in range(self.bitcell_loads):
            for dbc_gnd in self.dbc_inst[i].get_pins("gnd"):
                offset = vector(gnd_pin.x, dbc_gnd.by())
                if dbc_gnd.layer == "m3pin":
                    layer = "metal3"
                    self.add_via(self.m2_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                    self.add_via(self.m1_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                elif dbc_gnd.layer == "m2pin":
                    layer = None

                else:
                    layer = "metal1"
                    self.add_via(self.m1_stack, offset)
                self.add_rect(layer=layer,
                              offset=(gnd_pin.x, dbc_gnd.by()),
                              width=dbc_gnd.lx()-gnd_pin.x,
                              height=contact.m1m2.width)

        # Connect the gnd pins of replica cell
        for rbc_gnd in self.rbc_inst.get_pins("gnd"):
            offset = vector(gnd_pin.x, rbc_gnd.by())
            if rbc_gnd.layer == "m3pin":
                layer = "metal3"
                self.add_via(self.m2_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                self.add_via(self.m1_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                self.add_rect(layer="metal1",
                              offset=offset+vector(self.m2_width, 0),
                              width=self.m1_minarea/contact.m1m2.width,
                              height=contact.m1m2.width)
            elif rbc_gnd.layer == "m2pin":
                layer = None
                self.add_wire(self.m1_stack, [rbc_gnd.bc(), 
                                             (rbc_gnd.bc().x, rbc_gnd.bc().y-3*self.m_pitch("m1")),
                                             (gnd_pin.x, rbc_gnd.bc().y-3*self.m_pitch("m1"))])

            else:
                layer = "metal1"
                self.add_via(self.m1_stack, offset)
            self.add_rect(layer=layer,
                          offset=(gnd_pin.x, rbc_gnd.by()),
                          width=rbc_gnd.lx()-gnd_pin.x,
                          height=contact.m1m2.width)


        # Connect the WL pins directly to gnd
        for i in range(self.bitcell_loads):
            pin = self.dbc_inst[i].get_pin("wl")
            offset = vector(gnd_pin.x,pin.by()) 
            if pin.layer == "m3pin":
                layer = "metal3"
                self.add_via(self.m2_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
                self.add_via(self.m1_stack, offset+vector(contact.m2m3.height, 0), rotate=90)
            else:
                layer = "metal1"
                self.add_via(self.m1_stack, offset)
            self.add_rect(layer=layer,
                          offset=offset,
                          width=self.dbc_inst[0].lx()-gnd_pin.x,
                          height=contact.m1m2.width)


    def add_layout_pins(self):
        """ Route the input and output signal """
        
        en_pin = self.dc_inst.get_pin("in")
        x_off1 = self.rbl_inv_inst.lx()-self.m_pitch("m1")
        off2 = self.dc_inst.get_pin("in").uc()
        self.add_wire(self.m1_rev_stack, 
                      [(x_off1, 0), (x_off1, self.dc_inst.by()-self.m_pitch("m1")),
                       (off2.x, self.dc_inst.by()-self.m_pitch("m1")), off2])
        self.add_layout_pin(text="en",
                            layer=en_pin.layer,
                            offset=(x_off1-0.5*self.m1_width, 0),
                            width=en_pin.width(),
                            height=en_pin.height())

        out_pin = self.rbl_inv_inst.get_pin("Z")
        self.add_layout_pin(text="out",
                            layer=self.m1_pin_layer,
                            offset=out_pin.ll().scale(1,0),
                            width=out_pin.width(),
                            height=out_pin.width())
