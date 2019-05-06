""" BSD 3-Clause License
    Copyright (c) 2018-2019 Regents of the University of California and The Board
    of Regents for the Oklahoma Agricultural and Mechanical College
    (acting for and on behalf of Oklahoma State University)
    All rights reserved.
"""


import design
import debug
import contact
from utils import round_to_grid
from vector import vector
from pinv import pinv
from ptx import ptx
from bitcell_array import bitcell_array
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
        self.route()
        self.add_layout_pins()
        self.offset_all_coordinates()

    def calculate_module_offsets(self):
        """ Calculate all the module offsets """
                
        # delay chain and inv will be rotated 90
        self.rbl_inv_offset = vector(self.inv.height, self.inv.width)
        
        # access TX goes right on top of inverter
        self.access_tx_offset = vector(0.5*self.inv.height,self.rbl_inv_offset.y) + \
                                vector(0,0.5*self.inv.height)
        self.delay_chain_offset = self.rbl_inv_offset + vector(-contact.m1m2.width,self.inv.width)

        # Replica bitline is not rotated, it is placed 2 M1 pitch away from the delay chain
        self.bitcell_offset = self.rbl_inv_offset + vector(2*self.m_pitch("m2"), self.bitcell.height)
        self.rbl_offset = self.bitcell_offset+vector(0, -self.rbl.y_shift)
        
        self.height = max(self.rbl_offset.y+self.rbl.height, 
                          self.delay_chain_offset.y+self.delay_chain.width)
        self.width = self.rbl_offset.x + self.bitcell.width + 3*self.m_pitch("m1")


    def create_modules(self):
        """ Create modules for later instantiation """
        
        self.bitcell = self.replica_bitcell = replica_bitcell()
        self.add_mod(self.bitcell)

        # This is the replica bitline load column that is the height of our array
        self.rbl = bitcell_array(name="bitline_load", cols=1, rows=self.bitcell_loads)
        self.add_mod(self.rbl)

        self.delay_chain = delay_chain([self.delay_fanout]*self.delay_stages)
        self.add_mod(self.delay_chain)

        self.inv = pinv(size=5)
        self.add_mod(self.inv)

        self.access_tx = ptx(tx_type="pmos")
        self.add_mod(self.access_tx)

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
                                    offset=self.bitcell_offset,
                                    mirror="MX")
        self.connect_inst(["bl[0]", "br[0]", "delayed_en", "vdd", "gnd"])

        self.rbl_inst=self.add_inst(name="load",
                                    mod=self.rbl,
                                    offset=self.rbl_offset)
        self.connect_inst(["bl[0]", "br[0]"] + ["gnd"]*self.bitcell_loads + ["vdd", "gnd"])
        

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
        
        
        nwell_offset = self.rbl_inv_inst.ll() + vector(-0.5*contact.m1m2.width, self.inv.width)
        nwell_width =  self.inv.height+contact.m1m2.width
        self.add_rect(layer="nwell",
                      offset=nwell_offset,
                      width=nwell_width,
                      height=self.tx_inst.ul().y-nwell_offset.y)
        self.add_rect(layer="pimplant",
                      offset=nwell_offset,
                      width=nwell_width,
                      height=self.tx_inst.ul().y-nwell_offset.y)


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
        mid1 = vector(source_offset.x, self.rbl_inv_inst.get_pin("gnd").ur().y+\
                      self.m1_space+0.5*self.m1_width)
        inv_A_offset = self.rbl_inv_inst.get_pin("A").uc()
        mid2 = vector(inv_A_offset.x, mid1.y)
        self.add_path("metal1", [source_offset, mid1, mid2, inv_A_offset])
        
        # 6. Route the connection of the source route (mid2) to the RBL bitline (left)
        pos1= vector(self.rbc_inst.get_pin("bl").uc().x, self.rbc_inst.ll().y) 
        pos2= vector(pos1.x, pos1.y-self.m_pitch("m1"))
        pos3 = vector(self.rbl_inv_inst.get_pin("gnd").lr().x+self.m_pitch("m1"), pos2.y)
        pos4 = vector(pos3.x, mid1.y)
        pos5 = vector(inv_A_offset.x, pos4.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])
        
    def route_vdd(self):
        """ Adds two vdd pins, one for replica bitline load and one for delay chain """        
        
        # Add first vdd pin to the right of the rbl load
        vdd_start = vector(self.bitcell_offset.x + self.bitcell.width+self.m_pitch("m1") ,0)
        # It is the height of the entire RBL and bitcell
        self.add_rect(layer="metal1",
                      offset=vdd_start,
                      width=contact.m1m2.width,
                      height=self.rbl_inst.uy())
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=vdd_start,
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        # Connect the vdd pins of the bitcell load directly to vdd
        vdd_pins = self.rbl_inst.get_pins("vdd")
        for pin in vdd_pins:
            offset = vector(vdd_start.x, pin.by()) 
            if pin.layer == self.m3_pin_layer:
                layer = "metal3"
                self.add_via(self.m1_stack, (vdd_start.x, offset.y))
                self.add_via(self.m2_stack, (vdd_start.x, offset.y))
            else:
                layer = "metal1"
            self.add_rect(layer=layer,
                          offset=offset,
                          width=self.rbl_offset.x-vdd_start.x,
                          height=contact.m1m2.width)

        # Also connect the replica bitcell vdd pin to vdd
        pin = self.rbc_inst.get_pin("vdd")
        offset = vector(vdd_start.x,pin.by())
        if pin.layer == self.m3_pin_layer:
            layer = "metal3"
            self.add_via(self.m1_stack, offset)
            self.add_via(self.m2_stack, offset)
            self.add_rect(layer="metal2",
                          offset= offset,
                          width=self.m2_width,
                          height=self.rbl.height)
        
        else:
            layer = "metal1"
        self.add_rect(layer=layer,
                      offset=offset,
                      width=self.bitcell_offset.x-vdd_start.x,
                      height=contact.m1m2.width)
        
        # Add a second vdd pin. for delay chain and inverter
        inv_vdd_offset = self.rbl_inv_inst.get_pin("vdd").lc()
        self.add_rect(layer="metal1",
                      offset=inv_vdd_offset.scale(1,0),
                      width=contact.m1m2.width,
                      height=self.dc_inst.get_pin("vdd").ll().y)

        self.add_layout_pin(text="vdd",
                            layer=self.rbl_inv_inst.get_pin("vdd").layer,
                            offset=inv_vdd_offset.scale(1,0),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
    def route_gnd(self):
        """ Route all signals connected to gnd """
        
        gnd_start = self.rbl_inv_inst.get_pin("gnd")
        gnd_end = self.rbl_inst.uy()
        
        self.add_rect(layer="metal2",
                      offset = vector(gnd_start.ll().x, gnd_start.lc().y-contact.m1m2.height),
                      width = contact.m1m2.width,
                      height =max(self.dc_inst.ur().y, gnd_end) - gnd_start.lc().y)

        self.add_rect(layer="metal1",
                      offset=(gnd_start.lc().x,0),
                      width=contact.m1m2.width,
                      height=gnd_start.uc().y)

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
        rbl_gnd = self.rbl_inst.get_pins("gnd")[0].ll().y
        self.add_rect(layer="metal1",
                      offset=(gnd_pin.x,rbl_gnd),
                      width=contact.m1m2.width,
                      height=gnd_end-rbl_gnd)

        # Connect the WL pins directly to gnd
        for row in range(self.bitcell_loads):
            wl = "wl[{}]".format(row)
            pin = self.rbl_inst.get_pin(wl)
            offset = vector(gnd_pin.x,pin.by()) 
            if pin.layer == self.m3_pin_layer:
                layer = "metal3"
                self.add_via(self.m2_stack, offset)
            else:
                layer = "metal1"
                self.add_via(self.m1_stack, offset)
            self.add_rect(layer=layer,
                          offset=offset,
                          width=self.rbl_offset.x-gnd_pin.x,
                          height=contact.m1m2.width)

        # Connect the bitcell gnd pins to the rail
        gnd_pins = self.rbl_inst.get_pins("gnd")
        for pin in gnd_pins:
            offset = vector(gnd_pin.x,pin.by()) 
            if pin.layer == self.m3_pin_layer:
                layer = "metal3"
                self.add_via(self.m2_stack, offset)
            else:
                layer = "metal1"
                self.add_via(self.m1_stack, offset)
            self.add_rect(layer=layer,
                          offset=offset,
                          width=self.rbl_offset.x-gnd_pin.x,
                          height=contact.m1m2.width)

    def add_layout_pins(self):
        """ Route the input and output signal """
        
        en_pin = self.dc_inst.get_pin("in")
        x_off1 = self.rbl_inv_inst.ll().x-self.m_pitch("m1")
        off2 = self.dc_inst.get_pin("in").uc()
        self.add_wire(self.m1_rev_stack, 
                      [(x_off1, 0), (x_off1, self.dc_inst.ll().y-self.m_pitch("m1")),
                       (off2.x, self.dc_inst.ll().y-self.m_pitch("m1")), off2])
        self.add_layout_pin(text="en",
                            layer=en_pin.layer,
                            offset=(x_off1-0.5*self.m1_width, 0),
                            width=en_pin.width(),
                            height=en_pin.height())

        out_pin = self.rbl_inv_inst.get_pin("Z")
        self.add_rect(layer="metal1",
                      offset=(out_pin.lr().x,out_pin.lr().y+self.m1_width) ,
                      width=-1*(self.m1_minarea/contact.m1m2.width),
                      height=contact.m1m2.width)
        self.add_rect(layer="metal1",
                      offset=out_pin.lc().scale(1,0),
                      width=self.m1_width,
                      height=out_pin.lc().y)

        self.add_layout_pin(text="out",
                            layer=self.m1_pin_layer,
                            offset=out_pin.ll().scale(1,0),
                            width=out_pin.width(),
                            height=out_pin.width())
