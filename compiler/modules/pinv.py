import contact
import design
import debug
from tech import parameter
from ptx import ptx
from vector import vector
from math import ceil
from utils import round_to_grid
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
        self.translate_all(vector(0,0))

    def determine_tx_mults(self):
        """ Determines the number of fingers for the height constraint. """
        
        min_tx = ptx(width=self.minwidth_tx, mults=1, tx_type="nmos")

        # This is a active-to-active of a flipped cell of active-conatct to power-rail inside cell
        top_bottom_space = max(self.active_to_active, 2*self.m1_space+contact.m1m2.width)

        # Determine the height left to the transistors for number of fingers calculation
        tx_height_available = self.height - top_bottom_space
        
        #maximum possible num fingers
        max_mults = max(int(ceil(tx_height_available/min_tx.active_width)),1)
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
        if self.tx_mults==1:
            x_off = self.well_enclose_active + contact.well.width + \
                    2*self.implant_enclose_body_active + self.pmos.height
        else:
            x_off = self.well_enclose_active + contact.well.width + \
                    self.implant_enclose_body_active + self.pmos.height
        
        y_off= 0.5*self.height - 0.5*self.pmos.width
        if self.tx_mults > 1:
            x_off = x_off + self.poly_to_active
        
        pmos_pos = vector(x_off, y_off)
        self.pmos_inst=self.add_inst(name="pinv_pmos",
                                     mod=self.pmos,
                                     offset=pmos_pos,
                                     rotate=90)
        self.connect_inst(["Z", "A", "vdd", "vdd"])

        # place NMOS right to pmos
        x_off = self.pmos_inst.lr().x+self.nmos.height
        nmos_pos = vector(x_off, y_off)
        self.nmos_inst=self.add_inst(name="pinv_nmos",
                                     mod=self.nmos,
                                     offset=nmos_pos,
                                     rotate=90)
        self.connect_inst(["Z", "A", "gnd", "gnd"])

        # This should be covered nwell-contact and pmos
        nwell_pos = vector(0,-0.5*contact.m1m2.width)
        nwell_width = self.nmos_inst.ll().x
        pimplant_pos = vector(self.pmos_inst.ll().x,-0.5*contact.m1m2.width)
        if self.tx_mults > 1:
            pimplant_pos = vector(self.pmos_inst.ll().x-self.poly_to_active,
                                       -0.5*contact.m1m2.width)

        self.add_rect(layer="nwell", 
                      offset=nwell_pos, 
                      width=nwell_width, 
                      height=self.height+contact.m1m2.width)
        self.add_rect(layer="pimplant", 
                      offset=pimplant_pos, 
                      width=self.nmos_inst.ll().x-pimplant_pos.x, 
                      height=self.height+contact.m1m2.width)
        
        # This should cover pwell-contact and nmos
        pwell_pos = nimplant_pos= (self.nmos_inst.ll().x,-0.5*contact.m1m2.width)
        pwell_width= self.nmos_inst.height + contact.well.width + self.well_enclose_active+ \
                     max(self.implant_enclose_body_active, self.m1_space)
        self.add_rect(layer="pwell", 
                      offset=pwell_pos, 
                      width=pwell_width, 
                      height=self.height+contact.m1m2.width)
        self.add_rect(layer="nimplant", 
                      offset=nimplant_pos, 
                      width=self.nmos_inst.height, 
                      height=self.height+contact.m1m2.width)

        self.width = nwell_width + pwell_width              

    def add_supply_rails(self):
        """ Add vdd/gnd rails to the top and bottom. """
        
        self.add_rect(layer="metal1",
                      offset=vector(0,-0.5*contact.m1m2.width),
                      width=self.width,
                      height =contact.m1m2.width)
        self.add_layout_pin(text="gnd",
                            layer=self.m1_pin_layer,
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
                                    self.height-contact.well.height-self.well_enclose_active)

        pwell_contact_offset= vector(self.nmos_inst.lr().x+ \
                                     max(self.implant_enclose_body_active, self.m1_space), 
                                     self.well_enclose_active)
        
        self.nwell_contact=self.add_contact(layer_stack, nwell_contact_offset, 
                                            implant_type="n", well_type="n")
        self.pwell_contact=self.add_contact(layer_stack, pwell_contact_offset, 
                                            implant_type="p", well_type="p")
        
        self.active_height = self.active_minarea/contact.well.width
        
        active_off1 = nwell_contact_offset-\
                         vector(0, self.active_height-contact.well.height-self.poly_to_active)
        
        metal_off1= nwell_contact_offset 
        metal_height1 = self.height -  nwell_contact_offset.y
        pimplant_of = vector(0, -0.5*contact.m1m2.width)
        pimplant_width = self.well_enclose_active+contact.well.width+self.implant_enclose_body_active
        if self.tx_mults == 1: 
            pimplant_width = pimplant_width + self.implant_enclose_body_active
        
        active_off2 = pwell_contact_offset
        metal_off2= pwell_contact_offset.scale(1,0)
        metal_height2 = pwell_contact_offset.y
        nimplant_of = vector(self.nmos_inst.lr().x, -0.5*contact.m1m2.width)
        nimplant_width = contact.well.width+self.well_enclose_active+\
                        max(self.implant_enclose_body_active, self.m1_space)


        self.add_active_implant("nimplant", active_off1, metal_off1, metal_height1,
                                pimplant_of, pimplant_width)
        self.add_active_implant("pimplant", active_off2, metal_off2, metal_height2, 
                                nimplant_of, nimplant_width)


    def add_active_implant(self, implant_type, active_off, metal_off, metal_height, 
                           implant_of, implant_width):
        """ Add n/p well and implant to the layout """
        
        self.add_rect(layer="active",
                      offset=active_off,
                      width=contact.well.width,
                      height=self.active_height)
        
        self.add_rect(layer="metal1",
                      offset=metal_off+vector(self.active_enclose_contact-self.m1_enclose_contact,0),
                      width=contact.well.second_layer_width,
                      height=metal_height)
        
        self.add_rect(layer=implant_type,
                      offset=implant_of,
                      width=implant_width,
                      height=self.height+contact.m1m2.width)


    def connect_rails(self):
        """ Connect the nmos and pmos to its respective power rails """

        self.add_rect(layer="metal1",
                      offset=(self.nmos_inst.get_pin("S").ll().x, 0),
                      width=self.m1_width,
                      height=self.nmos_inst.get_pin("S").ll().y)

        if self.tx_mults==1:
            x_off = self.pmos_inst.get_pin("S").lc().x-self.m1_space-0.5*contact.m1m2.height
            self.add_path("metal1",[self.pmos_inst.get_pin("S").lc(),
                                   (x_off, self.pmos_inst.get_pin("S").lc().y),
                                   (x_off, self.height)])
        else:
            self.add_rect(layer="metal1",
                          offset=self.pmos_inst.get_pin("S").ll(),
                          width=self.m1_width,
                          height=self.height-self.pmos_inst.get_pin("S").ll().y)
    
    def route_input(self):
        """ Route the input (gates) together, routes input to edge. """

        # Pick point on the left of NMOS and connect down to PMOS
        nmos_gate_pos = self.nmos_inst.get_pin("G")
        pmos_gate_pos =self.pmos_inst.get_pin("G")
        self.add_path("poly",[pmos_gate_pos.lc(),nmos_gate_pos.lc()])
        

        # Add the via to the cell midpoint along the gate
        contact_offset = vector(max(self.implant_enclose_poly, self.m1_space),
                                nmos_gate_pos.ll().y-contact.poly.height)

        poly_contact=self.add_contact(self.poly_stack, contact_offset)

        self.add_rect(layer="poly",
                      offset=(contact_offset.x, nmos_gate_pos.ll().y),
                      width=nmos_gate_pos.ll().x-contact_offset.x,
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
        mid_pos = vector(self.nmos_inst.ll().x, nmos_drain_pos.lc().y)
        output_offset = vector(self.width- self.m1_space, nmos_drain_pos.lc().y)
        
        # output pin at the edge of the cell in middle
        output_pin_offset = vector(self.width-self.m1_space-contact.m1m2.width, 
                                   nmos_drain_pos.ll().y)

        
        self.add_path("metal1",[nmos_drain_pos.lc(), mid_pos, pmos_drain_pos.lc()])
        self.add_path("metal2",[(mid_pos.x, nmos_drain_pos.lc().y), output_offset])
        self.add_via_center(self.m1_stack,(mid_pos.x, nmos_drain_pos.lc().y), rotate=90)
        self.add_via(self.m1_stack,(output_pin_offset.x, 
                                    nmos_drain_pos.lc().y-0.5*contact.m1m2.width))

        Z_off = (self.width-self.m1_space, nmos_drain_pos.lc().y-0.5*contact.m1m2.width)
        self.add_layout_pin(text="Z",
                            layer=self.m1_pin_layer,
                            offset=Z_off,
                            width=self.m1_width,
                            height=self.m1_width)
        self.add_rect(layer="metal1",
                      offset=Z_off,
                      width=self.m1_space,
                      height=self.m1_width)
