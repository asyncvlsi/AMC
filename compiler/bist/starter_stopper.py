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
import math
from tech import layer, info, drc
from vector import vector
from delay_chain import delay_chain
from nand2 import nand2
from pinv import pinv
from ptx import ptx
from pull_up_pull_down import pull_up_pull_down
from utils import ceil

class starter_stopper(design.design):
    """ Dynamically generated a starter and stopper for ring oscillator. 
        when Test = 1 and Reset = 0, starter enables the oscillation and
        when Finish = 1 stopper (Arbitter) disables the oscillation """

    def __init__(self, name="starter_stopper"):
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
        self.add_layout_pins()
        self.width= self.pmos1.rx()+self.m_pitch("m1")
        self.height= self.inv_inst.uy()+self.m_pitch("m1")+contact.m1m2.width

    def add_pins(self):
        """ Adds pins for starter-stopper module """
        
        self.add_pin_list(["in", "out", "test", "reset", "finish", "vdd", "gnd"])

    def create_modules(self):
        """ construct all the required modules """
        
        self.nand2 = nand2()
        self.add_mod(self.nand2)

        self.inv = pinv(size=1)
        self.add_mod(self.inv)
        
        self.nmos=ptx(tx_type="nmos")
        self.add_mod(self.nmos)
        
        self.pmos=ptx(tx_type="pmos")
        self.add_mod(self.nmos)
        
        self.pull_up_pull_down = pull_up_pull_down(num_nmos=3, num_pmos=1, 
                                                   nmos_size=3, pmos_size=2, 
                                                   vdd_pins=["D0"], gnd_pins=["D2"],
                                                   name="pull_up_pull_down_x")
        self.add_mod(self.pull_up_pull_down)

        #This is a offset in x-direction for input pins
        self.gap = max(self.well_space, self.implant_space, self.m_pitch("m1"))
        

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_starter()
        self.add_stopper()
    
    def connect_modules(self):
        """ Route modules """

        self.starter_connections()
        self.connect_reset_to_sarter()
        self.connect_starter_to_stopper()
        self.cross_couppled_nands_connections()
        self.ptx_connections()
        self.add_well_contact()
    
    def add_starter(self):
        """ Add starter """
        
        #INV for RESET signal
        yoff = max(2*self.nand2.height,self.pull_up_pull_down.height+self.gap)
        self.inv_inst= self.add_inst(name="inv", mod=self.inv,
                                     offset=(0,yoff))
        self.connect_inst(["reset", "reset_b", "vdd", "gnd"])

        #pull_up_pull_down for starter
        self.starter_inst= self.add_inst(name="starter", mod=self.pull_up_pull_down,
                                         offset=(0,-0.5*contact.m1m2.width))
        self.connect_inst(["z", "in", "net1", "reset_b", "net2", "test", "gnd",
                           "z", "in", "vdd", "vdd", "gnd"])
    
    def add_stopper(self):
        """ Add stopper  """

        off = (max(self.inv.width,self.pull_up_pull_down.width)+ 5*self.m_pitch("m1"), 0)
        self.nand1_inst=self.add_inst(name="nand1", mod=self.nand2, offset=off)
        self.connect_inst(["z", "_u", "_v", "vdd", "gnd"])
        
        off = (self.nand1_inst.lx(), 2*self.nand2.height)
        self.nand2_inst=self.add_inst(name="nand2", mod=self.nand2, offset=off, mirror="MX")
        self.connect_inst(["finish", "_v", "_u", "vdd", "gnd"])
        
        off=(self.nand2_inst.rx()+self.nmos.height+ 2*max(self.gap, self.m_pitch("m1")), 0)
        self.nmos1=self.add_inst(name="nmos1", mod=self.nmos, offset=off, rotate=90)
        self.connect_inst(["out", "_v", "gnd", "gnd"])

        off = (self.nmos1.rx()+self.pmos.height+ 2*max(self.gap, self.m_pitch("m1")), 0)
        self.pmos1=self.add_inst(name="pmos1", mod=self.pmos, offset= off, rotate=90)
        self.connect_inst(["out", "_v", "_u", "vdd"])
        
        off = (self.nmos1.rx(), self.nmos.width+2*self.gap)
        self.nmos2=self.add_inst(name="nmos2", mod=self.nmos, offset=off, rotate=90)
        self.connect_inst(["u", "_u", "gnd", "gnd"])

        off = (self.pmos1.rx(), self.nmos.width+2*self.gap)
        self.pmos2=self.add_inst(name="pmos2", mod=self.pmos, offset=off, rotate=90)
        self.connect_inst(["u", "_u", "_v", "vdd"])

    def starter_connections(self): 
        """ Connections in pull_up_pulll_down network of starter gate"""
        
        #connect output of inv1 to input B of nand2
        self.add_path("poly",[self.starter_inst.get_pin("Gp0").lc(), self.starter_inst.get_pin("Gn0").lc()])
        self.add_path("metal1",[self.starter_inst.get_pin("Sp0").lc(), self.starter_inst.get_pin("Sn0").lc()])
        for pin in ["Dn2", "Dn1", "Dn0", "Dp0"]:    
            self.add_rect_center(layer="metal1",
                                 offset=self.starter_inst.get_pin(pin).cc(),
                                 width=ceil(self.m1_minarea/contact.m1m2.width),
                                 height=contact.m1m2.width) 


    def connect_reset_to_sarter(self):
        """ Connect output of reset inverter to input gate of pull_up_pull_down """

        pos1=self.inv_inst.get_pin("Z").lc()
        pos2=vector(self.starter_inst.rx(), pos1.y)
        pos3=vector(pos2.x, self.starter_inst.get_pin("Gn1").lc().y)
        pos4=vector(pos2.x-self.m_pitch("m2"),pos3.y)
        self.add_wire(self.m1_stack,[pos1,pos2,pos3,pos4] )
        self.add_path("poly",[self.starter_inst.get_pin("Gn1").lc(),pos4])
        self.add_contact_center(self.poly_stack, (pos4.x, pos4.y))

        
    def connect_starter_to_stopper(self):
        """ Connect output of starter gate to input B of both nand gates in stopper gate"""
        
        pos1=self.nand1_inst.get_pin("A").lc()
        pos2=vector(pos1.x-3*self.m_pitch("m1"), pos1.y)
        
        pos5=self.starter_inst.get_pin("Sn0").lc()
        pos6=vector(pos2.x, pos5.y)
        pos7=vector(pos6.x, pos1.y)
        self.add_path("metal1", [pos5,pos6, pos7, pos1])
        
        #connect vdd of stopper nand gates to stopper gate
        pos1=(self.starter_inst.rx(), self.starter_inst.get_pin("vdd").uc().y)
        self.add_path("metal1", [pos1, self.nand1_inst.get_pin("vdd").lc()])
        
        #connect gnd(s) of stopper nand gates to stopper gate
        pos1=(self.starter_inst.rx(), self.starter_inst.get_pin("gnd").lc().y)
        self.add_path("metal1", [pos1, self.nand1_inst.get_pin("gnd").lc()], width=contact.m1m2.width)
        
        pos1=(self.inv_inst.rx(), self.inv_inst.get_pin("gnd").lc().y)
        self.add_path("metal1", [pos1, self.nand2_inst.get_pin("gnd").lc()], width=contact.m1m2.width)
        
    def cross_couppled_nands_connections(self):    
        """ Connect output of each nand gate to input A of other nand gate (cross-couppled nands)"""
        
        mod1 = self.nand1_inst
        mod2 = self.nand2_inst

        #first nand
        pos1=vector(mod1.rx()-0.5*self.m2_width, mod1.get_pin("Z").lc().y)
        pos2=vector(pos1.x+self.m2_width, pos1.y)
        pos3=vector(pos2.x, mod1.by()-self.m_pitch("m1"))
        pos4=vector(mod2.get_pin("B").lc().x-2*self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x,mod2.get_pin("B").lc().y)
        pos6=mod2.get_pin("B").lc()
        self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4, pos5, pos6])
        
        #second nand
        pos1=vector(mod2.rx()-0.5*self.m2_width, mod2.get_pin("Z").lc().y)
        pos2=vector(pos1.x+self.m2_width, pos1.y)
        pos3=vector(pos2.x, mod2.uy()+self.m_pitch("m1"))
        pos4=vector(mod1.get_pin("B").lc().x-self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x,mod1.get_pin("B").lc().y)
        pos6=mod1.get_pin("B").lc()
        self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4, pos5, pos6])
    
    
    def ptx_connections(self):    
        """ Connections of NMOS and PMOS  terminals in stopper gate """
        
        #connect gates and source of nmos1 and pmos1
        self.add_path("poly", [self.nmos1.get_pin("G").lc(),self.pmos1.get_pin("G").lc()] )
        self.add_path("metal1", [self.nmos1.get_pin("S").lc(),self.pmos1.get_pin("S").lc()])
        
        #connect gates and drain of nmos2 and pmos2
        self.add_path("poly", [self.nmos2.get_pin("G").lc(),self.pmos2.get_pin("G").lc()] )
        self.add_path("metal1", [self.nmos2.get_pin("D").lc(),self.pmos2.get_pin("D").lc()])
        
        #connect gate of nmos1 to source of pmos2
        pos1=vector(self.nmos1.get_pin("G").lc().x+1.5*self.m_pitch("m1"),self.nmos1.get_pin("G").uy())
        shift = contact.m1m2.width+contact.poly.height
        self.add_contact(self.poly_stack, (pos1.x+shift, pos1.y), rotate=90)
        self.add_via(self.m1_stack, pos1)
        
        pos2=self.pmos2.by()-self.m1_space
        pos3=self.pmos2.get_pin("S").uc()
        self.add_wire(self.m1_stack, [(pos1.x+0.5*self.m2_width, pos1.y), 
                                      (pos1.x, pos2),(pos3.x, pos2), pos3])
        self.add_via_center(self.m1_stack, self.pmos2.get_pin("S").cc(), rotate=90)
        
        width = max(ceil(self.m1_minarea/contact.poly.width),shift)
        self.add_rect(layer="metal1",
                      offset=pos1,
                      width=width,
                      height=contact.poly.width) 
        
        #connect gate of nmos2 to source of pmos1
        pin = self.nmos2.get_pin("G")
        pos1=vector(pin.lc().x+2.5*self.m_pitch("m1"), pin.by()-contact.m1m2.height)
        yoff=pin.by()-contact.poly.width
        self.add_contact(self.poly_stack, (pos1.x+shift, yoff), rotate=90)
        self.add_via(self.m1_stack, pos1)
        pos2=self.pmos1.uy()+self.m1_space
        pos3=self.pmos1.get_pin("D").uc()
        self.add_wire(self.m1_stack, [(pos1.x+0.5*self.m2_width, pos1.y+contact.m1m2.height), 
                                      (pos1.x, pos2), (pos3.x, pos2), pos3])
        self.add_via_center(self.m1_stack, self.pmos1.get_pin("D").cc(), rotate=90)
        self.add_rect(layer="metal1",
                      offset=(pos1.x, yoff),
                      width=width,
                      height=contact.poly.width) 
        
        #connect drain of nmos1 and source of nmos2 together and to gnd of nand1
        self.add_path("metal1", [self.nmos1.get_pin("D").uc(), self.nmos2.get_pin("S").uc()])
        pos1=self.nand1_inst.get_pin("gnd").lc()
        pos2=vector(self.nand1_inst.rx()+2*self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, pos2.y-self.m_pitch("m1"))
        pos5=self.nmos1.get_pin("D").uc()
        pos4=vector(pos5.x, pos3.y)
        
        self.add_wire(self.m1_stack, [pos1,pos2,pos3, pos4])
        self.add_path("metal2", [pos3, pos4, pos5])
        self.add_via_center(self.m1_stack, self.nmos1.get_pin("D").cc(), rotate=90)

        
        #add metal1 in drain of pmos1 and source of pmos2 to avoid min_area violation
        for metal in ["metal1", "metal2"]:
            for off in [self.pmos1.get_pin("D").cc(), self.pmos2.get_pin("S").cc()]:
                self.add_rect_center(layer=metal,
                                     offset=off,
                                     width=ceil(self.m1_minarea/contact.m1m2.width),
                                     height=contact.m1m2.width) 
    
        #connect nand1 out to nmos1 gate
        pin = self.nmos1.get_pin("G")
        pos1=self.nand1_inst.get_pin("Z").lc()
        pos2=vector(self.nmos1.lx()-2*self.m1_space, pos1.y)
        pos3=vector(pos2.x, pin.by())
        self.add_path("metal1", [pos1, pos2, pos3])
        self.add_path("poly", [pin.lc(), (pos2.x,pin.lc().y)])
        self.add_contact_center(self.poly_stack, (pos2.x, pos3.y))

        #connect nand2 out to nmos2 gate
        pin= self.nmos2.get_pin("G")
        pos1=self.nand2_inst.get_pin("Z").lc()
        pos2=vector(self.nmos2.lx()-2*self.m1_space, pos1.y)
        pos3=vector(pos2.x, pin.by())
        self.add_path("metal1", [pos1, pos2, pos3])
        self.add_path("poly", [pin.lc(), (pos2.x,pin.lc().y)])
        self.add_contact_center(self.poly_stack, (pos2.x, pos3.y))

        if info["tx_dummy_poly"]:        
            shift1 = vector(self.pmos.dummy_poly_offset1.y, self.pmos.dummy_poly_offset1.x)
            shift2 = vector(self.pmos.dummy_poly_offset2.y, self.pmos.dummy_poly_offset2.x)
            offset = [self.nmos1.ll(),self.nmos2.ll(), self.pmos1.ll(), self.pmos2.ll()] 
            for off in offset:
                for i in [off + shift1, off + shift2]:
                    self.add_rect(layer="poly", 
                                  offset=i,
                                  width=ceil(drc["minarea_poly_merge"]/self.poly_width),
                                  height=self.poly_width)

    def add_well_contact(self):
        """ Add implant and well layers for substrate connections of NMOSes and PMOSes"""

        #add implants and well to connect body of nmos to gnd and pmos to vdd
        height = max(self.pmos2.uy()-self.pmos1.by()+0.5*contact.m1m2.width, 
                     self.nand2_inst.uy()+contact.m1m2.width)
        yoff = self.nand1_inst.by()-0.5*contact.m1m2.width
        if info["has_pwell"]:
            self.add_rect(layer="pwell",
                          offset=(self.nand1_inst.rx(), yoff) ,
                          width=self.pmos1.lx()-self.nand1_inst.rx(),
                          height=height) 
        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                      offset=(self.pmos1.lx(),yoff) ,
                      width=self.pmos.height+self.well_width,
                      height=height) 

        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                      offset=(self.nand1_inst.rx(),yoff) ,
                      width=self.nmos1.lx()-self.nand1_inst.rx(),
                      height=height) 
            self.add_rect(layer="pimplant",
                      offset=(self.pmos1.lx(),yoff) ,
                      width=self.pmos.height,
                      height=height) 

        if info["has_nimplant"]:
            self.add_rect(layer="nimplant",
                      offset=(self.nmos1.lx(),yoff) ,
                      width=self.pmos1.lx()-self.nmos1.lx(),
                      height=height) 
            self.add_rect(layer="nimplant",
                      offset=(self.pmos1.rx(),yoff) ,
                      width=self.well_width,
                      height=height)
        
        #add nwell contact
        co_xoff = self.pmos1.rx()+self.m1_space+self.implant_enclose_body_active+self.extra_enclose
        co_yoff = self.inv_inst.by()-self.well_enclose_active-contact.well.height
        contact_off=vector(co_xoff, co_yoff)
        self.add_contact(("active", "contact", "metal1"), contact_off)
        height=self.active_minarea/contact.well.width
        self.add_rect(layer="active", 
                      offset=(co_xoff, co_yoff+contact.well.height-height),
                      width=contact.well.width,
                      height=height)
        
        extra_width = self.well_width-self.extra_enclose
        extra_off= (self.pmos1.rx()+self.extra_enclose,yoff)
        self.add_rect(layer="extra_layer",
                      layer_dataType = layer["extra_layer_dataType"],
                      offset=extra_off,
                      width= extra_width,
                      height= 2*self.nand2.height+contact.m1m2.width)
        
        self.add_rect(layer="vt",
                      offset=self.nmos1.ll(),
                      layer_dataType = layer["vt_dataType"],
                      width=self.pmos1.rx()-self.nmos1.lx(),
                      height=self.nmos2.uy()-self.nmos1.by())


        #connect nwell contact to inverter vdd
        self.add_path("metal1", [(co_xoff+0.5*self.m1_width,co_yoff), self.inv_inst.get_pin("vdd").lc()])
                       
    
    def add_layout_pins(self):
        """ Adds all input, ouput and power pins"""
        
        #reset pin to input of inv
        self.add_layout_pin(text="reset",
                            layer=self.m1_pin_layer,
                            offset=self.inv_inst.get_pin("A").ll(),
                            width=self.m1_width,
                            height=self.m1_width)

        #in pin to first gate of starter gate
        pos1=self.starter_inst.get_pin("Gp0").lc()
        self.add_path("poly", [pos1, (self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y)])
        self.add_contact_center(self.poly_stack,(self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y))
        self.add_path("metal1", [(self.starter_inst.lx(), pos1.y), 
                                 (self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y)])
        self.add_layout_pin(text="in",
                            layer=self.m1_pin_layer,
                            offset=(self.starter_inst.lx(), pos1.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #test pin to third gate of starter gate
        pos1=self.starter_inst.get_pin("Gn2").lc()
        self.add_path("poly", [pos1, (self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y)])
        self.add_contact_center(self.poly_stack,(self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y))
        self.add_path("metal1", [(self.starter_inst.lx(), pos1.y), 
                                   (self.starter_inst.lx()+1.5*self.m_pitch("m1"), pos1.y)])
        self.add_layout_pin(text="test",
                            layer=self.m1_pin_layer,
                            offset=(self.starter_inst.lx(), pos1.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #finish pin to input A of nand2 of stopper gate
        pos1=self.nand2_inst.get_pin("A").lc()
        self.add_path("metal1", [(self.starter_inst.lx(), pos1.y), pos1])
        self.add_layout_pin(text="finish",
                            layer=self.m1_pin_layer,
                            offset=(self.starter_inst.lx(), pos1.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #out pin to input A of nand2 of stopper gate
        pos1=self.pmos1.get_pin("S").lc()
        self.add_path("metal1", [pos1, (self.pmos1.rx()+self.m_pitch("m1"), pos1.y)])
        self.add_layout_pin(text="out",
                            layer=self.m1_pin_layer,
                            offset=(self.pmos1.rx()+self.m_pitch("m1")-self.m1_width, 
                                    pos1.y-0.5*self.m1_width),
                            width=self.m1_width,
                            height=self.m1_width)

        #vdd pin to vdd of starter gate 
        pos1=self.starter_inst.get_pin("vdd").lc()
        pos2=self.inv_inst.get_pin("vdd").lc()
        self.add_wire(self.m1_stack, [pos1, (self.starter_inst.rx()+self.m_pitch("m1"), pos1.y),
                                      (self.starter_inst.rx()+self.m_pitch("m1"), pos2.y), pos2])
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=self.starter_inst.get_pin("vdd").ll(),
                            width=self.m2_width,
                            height=self.m2_width)
        
        pos1=self.starter_inst.get_pin("gnd").lc()
        pos2=self.inv_inst.get_pin("gnd").lc()
        self.add_wire(self.m1_stack, [pos1, (self.starter_inst.rx()+2*self.m_pitch("m1"), pos1.y),
                                      (self.starter_inst.rx()+2*self.m_pitch("m1"), pos2.y), pos2])
        self.add_layout_pin(text="gnd",
                            layer=self.m1_pin_layer,
                            offset=self.starter_inst.get_pin("gnd").ll(),
                            width=self.m2_width,
                            height=self.m2_width)
