import design
import debug
import contact
from ptx import ptx
from vector import vector
from utils import ceil
from bitcell import bitcell

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
        self.connect_poly()
        self.add_en()
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
        x_shift= self.implant_enclose_poly + self.poly_to_active
        
        # adding 3 pmoses for precharge cell
        pmos1_pos = vector(self.pmos.height+x_shift, self.pmos.width-self.well_enclose_active)
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

        pmos3_pos = vector(self.pmos.height+x_shift, 0)
        self.pmos3_inst=self.add_inst(name="pmos3",
                                     mod=self.pmos,
                                     offset=pmos3_pos,
                                     rotate=90)
        self.connect_inst(["br", "en", "vdd", "vdd"])

        
        # add a m1_pitch at top for DRC-free abutment connection with write_complete 
        self.height = self.pmos2_inst.ul().y+self.m_pitch("m1")

    def connect_poly(self):

        # connects pmos gates together
        self.add_path("poly", [self.pmos1_inst.get_pin("G").lc(), self.pmos2_inst.get_pin("G").lc()])

        self.mid_pos=vector(0.5*self.width, self.pmos1_inst.get_pin("G").lc().y)
                
        self.add_path("poly", [self.mid_pos,self.pmos3_inst.get_pin("G").lc()])
   
    def add_en(self):
        """Adds the en pin and connect it to pmoses' gate"""
        
        self.add_contact(self.poly_stack, (self.mid_pos.x+0.5*self.poly_width, self.pmos1_inst.ul().y), rotate=90)
        self.add_path( "poly", [(self.mid_pos.x, self.pmos1_inst.ul().y),
                                 self.mid_pos])

        self.add_rect(layer="metal1",
                      offset=(0,self.pmos1_inst.ul().y),
                      width = self.width,
                      height= self.m1_width)

        self.add_layout_pin(text="en",
                            layer=self.m1_pin_layer,
                            offset=(0,self.pmos1_inst.ul().y),
                            width = self.m1_width,
                            height = self.m1_width)
                     
    def add_vdd_rail(self):
        """Adds a vdd rail across the width of the cell that routes over drains of pmoses"""
        
        self.vdd_position = vector(0,self.pmos1_inst.get_pin("D").ll().y)
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
        self.add_contact(layers=("active", "contact", "metal1"),
                         offset=nwell_contact,
                         rotate=90, implant_type="n", well_type="n")
        active_width = self.active_minarea/contact.well.width
        self.add_rect(layer="active",
                      offset=(nwell_contact.x-active_width, nwell_contact.y),
                      width=active_width,
                      height=contact.well.width)
        self.add_path("metal1", 
                      [(self.width-0.5*contact.m1m2.width, self.vdd_position.y),
                       (nwell_contact.x-contact.well.height,nwell_contact.y+0.5*contact.well.width)],
                      width=contact.m1m2.width)
        

        #adding nwell to cover all pmoses and nwell contact
        x_off =  self.width-2*self.well_enclose_active-active_width
        self.add_rect(layer="nwell",
                      offset=vector(0,0),
                      width=self.width,
                      height=self.height)
        
        
        # pimplant for pmoses
        self.add_rect(layer="pimplant",
                      offset=vector(0,0),
                      width=x_off,
                      height=self.height)
        self.add_rect(layer="pimplant",
                      offset=vector(x_off,self.pmos2_inst.ll().y),
                      width=self.width-x_off,
                      height=self.height-self.pmos2_inst.ll().y)

        # nimplant for nwell contact
        self.add_rect(layer="nimplant",
                      offset=vector(x_off,0),
                      width=self.width-x_off,
                      height=self.pmos2_inst.ll().y)

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
        self.add_path("metal1", [pmos1_s.uc(), self.pmos3_inst.get_pin("D").uc()])
        
        mid_pos1= (pmos3_s.lr().x+2*self.m1_space, pmos2_s.lr().y-0.5*self.m1_width)
        mid_pos2= (pmos3_s.lr().x+2*self.m1_space, pmos3_s.lc().y)
        self.add_path("metal1", [(pmos2_s.ll().x+contact.m1m2.height,
                                  pmos2_s.lr().y-0.5*self.m1_width),
                                  mid_pos1, mid_pos2, pmos3_s.lc()])

        self.add_via_center(self.m1_stack, (pmos2_s.uc().x, pmos2_s.lc().y), rotate=90)
        self.add_via_center(self.m1_stack, (pmos1_s.uc().x, pmos1_s.lc().y), rotate=90)
