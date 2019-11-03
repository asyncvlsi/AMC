# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA. (See LICENSE for licensing information)


import design
import debug
import contact
from tech import info, layer, drc
import math
from vector import vector
from ptx import ptx
from utils import ceil


class tgate(design.design):
    """ Dynamically generates a transmission gate """

    def __init__(self, name="tgate"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.add_modules()
        self.connect_modules()
        self.width= self.nmos.height+self.pmos.height+4*self.m_pitch("m1")+self.poly_space
        self.height= self.pmos.width+ 2*self.nmos_overlap
        self.add_layout_pins()
        
    def add_pins(self):
        """ Adds pins for tgate module """
        
        self.add_pin_list(["in1", "in2", "out", "up_down", "up_down_b", "vdd", "gnd"])

    def create_modules(self):
        """ Construct all the required modules """
        
        self.pmos = ptx(tx_type="pmos", min_area = False, dummy_poly=False)
        self.add_mod(self.pmos)

        self.nmos = ptx(tx_type="nmos", min_area = False, dummy_poly=False)
        self.add_mod(self.nmos)
        
        #Thsi is to share Drain & Source contacts of initializer MOSes
        self.nmos_overlap = self.nmos.get_pin("D").lx() - self.nmos.get_pin("S").lx()

    def add_modules(self):
        """ Adds all 4 transistors"""

        off = (0,0)
        self.nfet1=self.add_inst(name="nfet1", mod=self.nmos, offset=off, rotate=90)
        self.connect_inst(["in1", "up_down_b", "out", "gnd"])
        
        off = (self.pmos.height+self.poly_space,self.nmos_overlap)
        self.pfet1=self.add_inst(name="pfet1", mod=self.pmos, offset=off, rotate=90)
        self.connect_inst(["in1", "up_down", "out", "vdd"])

        off = (0,self.nmos_overlap)
        self.nfet2=self.add_inst(name="nfet2", mod=self.nmos, offset=off, rotate=90)
        self.connect_inst(["in2", "up_down", "out", "gnd"])
        
        off = (self.pmos.height+self.poly_space,2*self.nmos_overlap)
        self.pfet2=self.add_inst(name="pfet2", mod=self.pmos, offset=off, rotate=90)
        self.connect_inst(["in2", "up_down_b", "out", "vdd"])
    
    def connect_modules(self):
        """ connect in and out pins to nfet and pfet terminals modules """

        #output routing
        self.out=vector(self.pfet1.rx()+2*self.m_pitch("m1"), self.pfet1.get_pin("D").lc().y)
        pos1= self.nfet1.get_pin("D").lc()
        mid_pos1 = (self.nfet1.rx()+0.5*self.m1_width, pos1.y)
        mid_pos2 = (self.nfet1.rx()+0.5*self.m1_width, self.out.y)
        self.add_path("metal1", [pos1, mid_pos1, mid_pos2,self.out])

        #input 1 routing        
        self.in1=vector(self.nfet1.lx()-2*self.m_pitch("m1"), self.nfet1.get_pin("S").lc().y)
        self.add_path("metal1", [self.pfet1.get_pin("S").uc(), self.in1 ])

        #input 2 routing
        pos1 = self.pfet2.get_pin("D").lc()
        self.in2=vector(self.nfet2.lx()-2*self.m_pitch("m1"), pos1.y)
        mid_pos2 = self.nfet2.get_pin("D").uc()
        mid_pos1 = (mid_pos2.x, pos1.y)
        mid_pos3 = (mid_pos2.x, pos1.y)
        self.add_path("metal1", [pos1, mid_pos1, mid_pos2, mid_pos3, self.in2])
        
        #connect gates: nmos2 to pmos1
        pos1=vector(self.nfet2.lx()-self.m_pitch("m1"), self.nfet2.get_pin("G").lc().y)
        self.add_path("poly", [pos1, self.pfet1.get_pin("G").lc()])
        
        pos2=vector(pos1.x, self.nfet2.get_pin("G").by()-contact.poly.height)
        self.add_contact(self.poly_stack, (pos2.x, pos2.y+self.via_shift("co")))
        
        self.up_down_off= vector(pos1.x-contact.m1m2.width, pos2.y)
        self.add_via(self.m1_stack, self.up_down_off)
        height1 = max(contact.poly.height, contact.m1m2.height-self.via_shift("v1"))
        width1 =  max(ceil(self.m1_minarea/height1), contact.poly.width+2*contact.m1m2.width)
        self.add_rect(layer= "metal1", 
                      offset= self.up_down_off-(0.5*contact.m1m2.width, 0) , 
                      width= width1, 
                      height= height1)
        
        #connect gates nmos1 to pmos2
        pos1=self.nfet1.get_pin("G").lc()
        pos11=vector(self.nfet1.rx()+self.m1_width, pos1.y)
        pos12=vector(pos11.x, pos1.y-self.poly_to_active)
        pos2= vector(self.pfet2.rx() + 2*self.m_pitch("m1")-self.implant_enclose_poly, pos12.y)
        self.add_path("poly", [pos1, pos11, pos12, pos2])
        pos4= self.pfet2.get_pin("G").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_path("poly", [pos3, pos4])
        
        pos5= vector(pos2.x-contact.poly.width, pos1.y-self.poly_to_active)
        pos6=vector(pos5.x, pos4.y+self.poly_width)
        self.add_rect(layer="poly", 
                      offset=(pos5.x, pos4.y), 
                      width=contact.poly.width, 
                      height=2*self.poly_width)
        
        self.add_contact(self.poly_stack, pos5)
        self.add_contact(self.poly_stack, pos6)
        
        self.add_via(self.m1_stack, (pos2.x-contact.poly.width-contact.m1m2.width, pos5.y))
        self.add_via(self.m1_stack, (pos2.x-contact.poly.width-contact.m1m2.width, pos6.y))
        
        self.updown_boff= vector(pos2.x-contact.poly.width-self.m2_width, pos5.y)
        offset = [self.updown_boff-(contact.m1m2.width,0),(self.updown_boff.x-contact.m1m2.width,pos6.y)]
        for off in offset:
            self.add_rect(layer= "metal1", offset= off, width= width1, height= height1)
        
        layers=[]
        if info["has_nimplant"]:
            layers.append("nimplant")
        if info["has_pwell"]:
            layers.append("pwell")

        for layer in layers:
            self.add_rect(layer= layer, 
                          offset= (self.nfet1.lx()-2*self.m_pitch("m1"), 0), 
                          width= self.nmos.height+2*self.m_pitch("m1") , 
                          height= self.nmos.width+2*self.nmos_overlap)

        layers=[]
        if info["has_pimplant"]:
            layers.append("pimplant")
        if info["has_nwell"]:
            layers.append("nwell")

        for layer in layers:
             self.add_rect(layer=layer, 
                           offset=(self.nfet1.rx(), 0), 
                           width = self.pmos.height+2*self.m_pitch("m1")+self.poly_space , 
                           height = self.pmos.width+2*self.nmos_overlap)


        #connect all vt layers to avoid min-space vt DRC
        vt_width = self.pfet2.rx() - self.nfet1.lx()
        vt_height = self.pfet2.uy() - self.nfet1.by()
        self.add_rect(layer="vt",
                      offset=self.nfet1.ll(),
                      layer_dataType = 164,
                      width=vt_width,
                      height=vt_height)
    
        width = ceil(drc["minarea_poly_merge"]/self.poly_width)
        offset=[self.nfet1.lr()-(width,0), 
                self.nfet2.ur()-(width,0), 
                self.pfet1.ll()-(0, 0.5*self.poly_width), 
                self.pfet2.ul()-(0, self.poly_width)]
        if info["tx_dummy_poly"]:
             for off in offset:
                 self.add_rect(layer="poly", offset=off, width = width, height = self.poly_width)
    
    def add_layout_pins(self):
        """ Add input and output pins """
        
        pos = [(self.up_down_off.x, 0), (self.updown_boff.x, 0)]
        for i in pos:
            self.add_rect(layer="metal2",
                          offset=i,
                          width=self.m2_width,
                           height=self.height)
        
        pins=["in1", "in2", "out"]
        offsets=[self.in1-vector(0,0.5*self.m1_width), self.in2-vector(0,0.5*self.m1_width), 
                (self.out.x-self.m1_width, self.out.y-0.5*self.m1_width)]
        for (pin,off) in zip(pins, offsets):
            self.add_layout_pin(text=pin,
                                layer=self.m1_pin_layer,
                                offset=off,
                                width=self.m1_width,
                                height=self.m1_width)
        
        pins=["up_down", "up_down_b"]
        offsets=[(self.up_down_off.x, 0), (self.updown_boff.x, 0) ]
        for (pin,off) in zip(pins, offsets):
            self.add_layout_pin(text=pin,
                                layer=self.m2_pin_layer,
                                offset=off,
                                width=self.m2_width,
                                height=self.m2_width)
