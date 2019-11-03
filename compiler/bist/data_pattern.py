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

class data_pattern(design.design):
    """ Dynamically generated data patterns (nb'1 and nb'0) for input data"""

    def __init__(self, size, name="data_pattern"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.size = size
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.add_modules()
        self.connect_modules()
        self.add_layout_pins()
        
        self.width= self.nmos_inst[self.size-1].rx()-self.nmos_inst[0].lx()+\
                    2*self.shift+self.pin_off+self.m_pitch("m1")
        
        self.height= self.nmos.width+self.pmos.width+self.m_pitch("m1")
        if info["tx_dummy_poly"]:
            self.height= self.height+self.poly_space
            

    def add_pins(self):
        """ Adds all pins of data pattern module """
        
        for i in range(self.size):
            self.add_pin("out{0}".format(i))
        self.add_pin_list(["enable", "vdd", "gnd"])

    def create_modules(self):
        """ construct all the required modules """
        
        self.nmos = ptx(tx_type="nmos", min_area = True)
        self.add_mod(self.nmos)

        self.pmos = ptx(tx_type="pmos", min_area = True)
        self.add_mod(self.pmos)
        
        #This is a offset in x-direction for input pins
        self.pin_off = 3*self.m_pitch("m1")
        self.shift = max(self.nmos.height, self.pmos.height)

        self.space = 0
        if info["tx_dummy_poly"]:
            self.space = self.poly_space

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_ptx()
        self.add_well_contact()
    
    def add_ptx(self):
        """ Place the NMOSes for data0 and PMOSes for data1 """
        
        self.nmos_inst={}
        self.pmos_inst={}
        for i in range(self.size):
            #NMOS
            self.nmos_inst[i]= self.add_inst(name="nmos{0}".format(i),
                                             mod=self.nmos,
                                             offset=(i*self.shift,0),
                                             rotate=90)
            self.connect_inst(["gnd", "enable", "out{0}".format(i), "gnd"])
        
        for i in range(self.size):
            #PMOS
            y_off = self.nmos.width+self.space
            self.pmos_inst[i]= self.add_inst(name="pmos{0}".format(i),
                                             mod=self.pmos,
                                             offset=(i*self.shift,y_off),
                                             rotate=90)
            self.connect_inst(["out{0}".format(i), "enable", "vdd", "vdd"])
    
    def add_well_contact(self):
        """ Add nwell and pwell contacts """

        #nwell contact
        if info["has_pwell"]:
            self.add_rect(layer="pwell",
                          offset=self.nmos_inst[self.size-1].lr(),
                          width=2*self.shift,
                          height=self.nmos.width)
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset=self.nmos_inst[self.size-1].lr(),
                          width=2*self.shift,
                          height=self.pmos_inst[self.size-1].by()+self.implant_space)
                       
        xoff=self.well_enclose_active+contact.well.height
        yoff=self.well_enclose_active
        self.nwell_co_off=self.nmos_inst[self.size-1].lr()+vector(xoff,yoff)
        self.add_contact(("active", "contact", "metal1"), self.nwell_co_off, rotate=90)
        self.add_rect(layer="active",
                      offset=(self.nwell_co_off.x-contact.well.height,self.nwell_co_off.y ),
                      width=ceil(self.active_minarea/contact.well.width),
                      height=contact.well.width)
        #pwell contact
        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                          offset=self.pmos_inst[0].ll()-vector(0, 0.5*self.space),
                          width=self.shift*(self.size+2),
                          height=self.pmos.width+self.space)
        if info["has_nimplant"]:
             self.add_rect(layer="nimplant",
                           offset=self.pmos_inst[self.size-1].lr()+vector(0,self.implant_space),
                           width=2*self.shift,
                           height=self.nmos.width-self.implant_space)
                       
        xoff = self.well_enclose_active+contact.well.height
        yoff = self.well_enclose_active+contact.well.width
        self.pwell_co_off=self.pmos_inst[self.size-1].ur()+vector(xoff, -yoff)
                          
        self.add_contact(("active", "contact", "metal1"), self.pwell_co_off, rotate=90)
        self.add_rect(layer="active",
                      offset=(self.pwell_co_off.x-contact.well.height,self.pwell_co_off.y),
                      width=ceil(self.active_minarea/contact.well.width),
                      height=contact.well.width)

        extra_height = contact.well.width+2*self.extra_enclose
        extra_width = max(ceil(self.active_minarea/contact.well.width)+2*self.extra_enclose, 
                          ceil(self.extra_minarea/extra_height))
        shift=vector(contact.well.height+self.extra_enclose,self.extra_enclose)
        for off in [self.nwell_co_off-shift, self.pwell_co_off-shift]:
            self.add_rect(layer="extra_layer",
                          layer_dataType = layer["extra_layer_dataType"],
                          offset=off,
                          width= extra_width,
                          height= extra_height)

    def connect_modules(self):
        """ Connect NMOS and PMOS terminals to in/out pins """

        
        minx_tx=min(self.pmos_inst[0].lx(),self.nmos_inst[0].lx())
        
        #connect all NMOS gates to data0 pin
        self.add_path("poly",[(self.nmos_inst[0].get_pin("G").lc()-vector(self.pin_off,0)), 
                               self.nmos_inst[self.size-1].get_pin("G").lc()])
        #connect all PMOS gates to data1 pin
        self.add_path("poly",[(self.pmos_inst[0].get_pin("G").lc()-vector(self.pin_off,0)), 
                               self.pmos_inst[self.size-1].get_pin("G").lc()])
        
        #extend implant to cover poly for DRC violation
        if info["has_nimplant"]:
            self.add_rect(layer="nimplant",
                          offset=(minx_tx-self.pin_off,self.nmos_inst[0].by()),
                          width=self.pin_off+self.shift*self.size,
                          height=self.pmos_inst[0].by())
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset=(minx_tx-self.pin_off,self.pmos_inst[0].by()),
                          width=self.pin_off+self.shift*self.size,
                          height=self.pmos.width)

        #connect all NMOS sources to gnd pin
        pos1=self.nmos_inst[0].get_pin("S").lc()-vector(self.pin_off-self.m_pitch("m1"),0)
        pos2=(self.nwell_co_off.x, self.nmos_inst[self.size-1].get_pin("S").lc().y)
        self.add_path("metal1",[pos1,pos2])
        
        #connect all PMOS drains to vdd pin
        pos1=self.pmos_inst[0].get_pin("D").lc()-vector(self.pin_off-self.m_pitch("m1"),0)
        pos2=(self.nwell_co_off.x, self.pmos_inst[self.size-1].get_pin("D").lc().y)
        self.add_path("metal1",[pos1,pos2])

        #connect all NMOS drains to PMOS sources
        for i in range(self.size):
            pos1=self.pmos_inst[i].get_pin("S").uc()
            pos2=self.nmos_inst[i].get_pin("D").uc()
            self.add_path("metal1",[pos1,pos2], width=contact.m1m2.width)
            via_off = vector(pos1.x, self.pmos_inst[0].by())
            self.add_via_center(self.m1_stack, via_off)
            self.add_path("metal2",[via_off, (via_off.x, self.pmos_inst[0].uy()+self.m_pitch("m1"))])

        #connect all dummy polies to avoid min-space poly DRC
        if info["tx_dummy_poly"]:
            shift = vector(self.nmos.dummy_poly_offset1.y,self.nmos.dummy_poly_offset1.x+0.5*self.poly_width)
            self.add_path("poly",[vector(minx_tx, self.nmos_inst[0].by())+shift, self.nmos_inst[self.size-1].lr()+shift])
            self.add_path("poly",[vector(minx_tx, self.pmos_inst[0].by())+shift, self.pmos_inst[self.size-1].lr()+shift])
            
            shift = (self.nmos.dummy_poly_offset2.y,self.nmos.dummy_poly_offset2.x+0.5*self.poly_width)
            self.add_path("poly",[vector(minx_tx, self.nmos_inst[0].by())+shift, self.nmos_inst[self.size-1].lr()+shift])
            self.add_path("poly",[vector(minx_tx, self.pmos_inst[0].by())+shift, self.pmos_inst[self.size-1].lr()+shift])


        #connect all vt layers to avoid min-space vt DRC
        vt_offset=(minx_tx,self.nmos_inst[0].by())
        vt_height = ceil(self.pmos.width) + ceil(self.nmos.width) + self.space
        self.add_rect(layer="vt",
                      offset=vt_offset,
                      layer_dataType = layer["vt_dataType"],
                      width=self.shift*self.size,
                      height=vt_height)

    def add_layout_pins(self):
        """ Adds all input, ouput and power pins"""
        
        #output pins
        for i in range(self.size):
            pin_off=(self.pmos_inst[i].get_pin("S").uc().x-0.5*self.m2_width, 
                     self.pmos_inst[0].uy()+self.m_pitch("m1")-self.m2_width)
            self.add_layout_pin(text="out{0}".format(i),
                                layer=self.m2_pin_layer,
                                offset=pin_off,
                                width=self.m2_width,
                                height=self.m2_width)

        #power pins
        vdd_off=self.pmos_inst[0].get_pin("D").lc()-vector(self.pin_off-2*self.m_pitch("m1"),0)
        gnd_off=self.nmos_inst[0].get_pin("S").lc()-vector(self.pin_off-self.m_pitch("m1"),0)
        height =self.nmos.width+self.pmos.width
        self.add_path("metal2", [(vdd_off.x, 0),(vdd_off.x, height)])
        self.add_path("metal2", [(gnd_off.x, 0),(gnd_off.x, height)])
        self.add_via_center(self.m1_stack, vdd_off, rotate=90)
        self.add_via_center(self.m1_stack, gnd_off, rotate=90)
        
        self.add_layout_pin(text="vdd",
                            layer=self.m2_pin_layer,
                            offset=(vdd_off.x-0.5*self.m2_width, 0),
                            width=self.m2_width,
                            height=self.m2_width)
        self.add_layout_pin(text="gnd",
                            layer=self.m2_pin_layer,
                            offset=(gnd_off.x-0.5*self.m2_width, 0),
                            width=self.m2_width,
                            height=self.m2_width)

        #input pins
        xshift=self.pin_off-contact.poly.height+self.via_shift("co")
        data1_off=self.pmos_inst[0].get_pin("G").lc()- vector(xshift, 0.5*self.poly_width+contact.poly.width)
        data0_off=self.nmos_inst[0].get_pin("G").lc()-vector(xshift,-0.5*self.poly_width)
        self.add_contact(self.poly_stack, data1_off, rotate=90)
        self.add_contact(self.poly_stack, data0_off, rotate=90)
        
        pos1=(data1_off.x-2*self.m_pitch("m1"), data1_off.y)
        pos2=(data1_off.x, data1_off.y)
        self.add_path("metal1", [pos1, pos2])

        pos1=self.pmos_inst[0].get_pin("G").lc()- vector(xshift+0.5*contact.poly.height, contact.poly.width)
        pos2=self.nmos_inst[0].get_pin("G").lc()- vector(xshift+0.5*contact.poly.height, -contact.poly.width)
        self.add_path("metal1", [pos1, pos2])
        
        
        self.add_layout_pin(text="enable",
                            layer=self.m1_pin_layer,
                            offset=(data1_off.x-2*self.m_pitch("m1"),data1_off.y-0.5*self.m1_width ),
                            width=self.m1_width,
                            height=self.m1_width)
