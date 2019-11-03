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


import design
import debug
import contact
from tech import info, layer
from vector import vector
from pinv import pinv
from pull_up_pull_down import pull_up_pull_down
from utils import ceil

class dout_latch(design.design):
    """ Dynamically generated output-data latch for synchronous interface """

    def __init__(self, size, name="dout_latch_array"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.size = size
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_offsets()
        self.add_modules()
        self.add_layout_pins()

    def add_pins(self):
        """ Adds pins, order of the pins is important """
        
        for i in range(self.size):
            self.add_pin("async_dout[{0}]".format(i))
        for i in range(self.size):
            self.add_pin("sync_dout[{0}]".format(i))
        self.add_pin_list(["rack", "rack_b", "vdd", "gnd"])

    def create_modules(self):
        """ Create modules for instantiation """

        #each dataout_latch has 3 stacked NMOS and 3 stacked PMOS
        self.dout_latch = pull_up_pull_down(num_nmos=2, num_pmos=2, 
                                            nmos_size=1, pmos_size=4, 
                                            vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.dout_latch)
        
        self.inv = pinv(size=2)
        self.add_mod(self.inv)


    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.xgap= max(self.implant_space,self.well_space,3*self.m_pitch("m2"))

        #This is a contact/via shift to avoid DRC violation
        self.via_co_shift= 0.5*abs(contact.poly.width-contact.m1m2.width)
        
        #This is width and the height of dout_latch_array. 
        #vdd/gnd rails are shared so their height is deducted from final height.
        self.height= self.size* self.dout_latch.height - (self.size-1)*contact.m1m2.width
        self.width = 2*self.dout_latch.width + 3*self.xgap  

    def add_modules(self):
        """ Place the dout latch gates """

        self.dout_inst = {}
        self.dout_inv_inst = {}
        for i in range(self.size):
            if i%2:
                mirror = "MX"
                yoff=(i+1)*self.dout_latch.height-i*contact.m1m2.width
            else:
                mirror = "R0"
                yoff=i*(self.dout_latch.height-contact.m1m2.width)
            
            # adding pull_up_pull_down network for data_out_latch
            self.dout_inst[i]=self.add_inst(name="dout_latch1{}".format(i), 
                                            mod=self.dout_latch, 
                                            offset=(self.xgap, yoff),
                                            mirror=mirror)
            self.connect_inst(["gnd", "async_dout[{}]".format(i), "n1_{}".format(i), "rack", 
                               "x{}".format(i), "vdd", "async_dout[{}]".format(i), "p1_{}".format(i), 
                               "rack_b", "x{}".format(i), "vdd", "gnd"])

        for i in range(self.size):
            if i%2:
                mirror = "MX"
                yoff=(i+1)*self.dout_latch.height-i*contact.m1m2.width -0.5*contact.m1m2.width
            else:
                mirror = "R0"
                yoff=i*(self.dout_latch.height-contact.m1m2.width)+0.5*contact.m1m2.width

            # output of data_out_latch is drived with an inverter
            self.dout_inv_inst[i]=self.add_inst(name="dout_inv{}".format(i), 
                                                mod=self.inv, 
                                                offset=(self.dout_latch.width+2*self.xgap, yoff),
                                                mirror=mirror)
            self.connect_inst(["x{}".format(i), "sync_dout[{}]".format(i),"vdd", "gnd"])
        
    def add_layout_pins(self):
        """ Routing pins to modules input and output"""
        
        self.add_async_dout_pins()
        self.add_sync_dout_pins()
        self.add_rack_pin()
        self.add_power_pins()
        self.add_fill_layers()

    def add_metal_minarea(self, layer, pin):
        """ Adds horizontal metal to avoid DRC min_area"""
        
        if layer == "metal1":
            min_area=self.m1_minarea
        else:
            min_area=self.m2_minarea
        
        self.add_rect_center(layer=layer,
                             offset=pin,
                             width=ceil(min_area/contact.m1m2.first_layer_width),
                             height=contact.m1m2.first_layer_width)
        
    def add_async_dout_pins(self):
        """ Adds the input data pins """

        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1
            
            #async_dout is connected to G0 of pulldown network.
            xpos = self.dout_inst[i].lx()+self.m_pitch("m1")
            pin=self.dout_inst[i].get_pin("Gp0")
            pos1= (xpos+self.via_shift("co"), self.dout_inst[i].get_pin("Gn0").lc().y)
            pos2= self.dout_inst[i].get_pin("Gn0").lc()
            self.add_path("poly",[pos1, pos2])
            
            off=(xpos+contact.poly.height, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos+contact.m1m2.height,pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            off= vector(xpos, pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
             
            off= vector(xpos, pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal2", off)
            
            # add final async_dout pins as inputs (asyn_dataout)
            off = (xpos, pin.lc().y-yshift*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_layout_pin(text="async_dout[{0}]".format(i), 
                                layer=self.m1_pin_layer, 
                                offset= off, 
                                width=self.m1_width,
                                height=self.m1_width)

    def add_sync_dout_pins(self):
        """ Adds the output data pins """

        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
                ypin=self.dout_inst[i].get_pin("Dp1").cc()-\
                     vector(0.5*contact.active.height,0.5*contact.active.width)
            else:
                yshift=1
                yshift2=1
                ypin=self.dout_inst[i].get_pin("Dp1").cc()-\
                     vector(0.5*contact.active.height,-0.5*contact.active.width)

            xpos = self.dout_inv_inst[i].lx()-self.m_pitch("m1")
            
            pos1=self.dout_inv_inst[i].get_pin("A").lc()
            pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
            pos3=vector(pos2.x, ypin.y)
            self.add_path("metal1", [pos1, pos2, pos3, ypin])
        
            width = self.m1_minarea/contact.m1m2.first_layer_width
            off=(self.dout_inv_inst[i].get_pin("Z").lx()-contact.m1m2.width+\
                 0.5*width,self.dout_inv_inst[i].get_pin("Z").lc().y)
            self.add_metal_minarea("metal1", off)
            
            # add final async_dout pins as outputs (asyn_dataout)
            self.add_layout_pin(text="sync_dout[{0}]".format(i), 
                                layer=self.m1_pin_layer, 
                                offset=self.dout_inv_inst[i].get_pin("Z").ll(), 
                                width=self.m1_width,
                                height=self.m1_width)

    def add_rack_pin(self):
        """ Adds the clk pins """

        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route rack_b to dout_latch gates
            xpos = self.dout_inst[i].lx()-self.m_pitch("m2")+contact.m1m2.height
            pin= self.dout_inst[i].get_pin("Gp1")
            pos1= (self.dout_inst[i].lx()-self.m_pitch("m2")+self.via_shift("co"), pin.lc().y)
            self.add_path("poly", [pin.lc(), pos1])
            
            off=(self.dout_inst[i].lx()-self.m_pitch("m2")+contact.poly.height, 
                 pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            
            off = vector(xpos-contact.m1m2.height, 
                  pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            pos1= (xpos-0.5*self.m2_width, pin.lc().y-self.via_co_shift+contact.m1m2.width)
            pos2=(xpos-0.5*self.m2_width, -self.m_pitch("m1"))
            self.add_path("metal2",[pos1, pos2])
            
        #add final rack_b pin (rack_b is an output pin for this module)
        self.add_layout_pin(text="rack_b", 
                            layer=self.m2_pin_layer, 
                            offset=(xpos-self.m3_width, -self.m_pitch("m1")), 
                            width=self.m2_width,
                            height=self.m2_width)
        
        for i in range(self.size):            
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route rack to dout_latch gates
            xpos=self.dout_inst[i].rx()+self.m_pitch("m1")
            pin=self.dout_inst[i].get_pin("Gn1")
            self.add_path("poly",[pin.lc(), (xpos-self.via_shift("co"), pin.lc().y)])
            
            off=(xpos, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack,off, rotate=90)
            
            off=(xpos, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            off=vector(xpos-contact.m1m2.height+self.via_shift("v1"), pin.lc().y-\
                       0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            pos1=(xpos-0.5*self.m2_width, pin.lc().y-self.via_co_shift+contact.poly.width)
            pos2= (xpos-0.5*self.m2_width, -self.m_pitch("m1"))
            self.add_path("metal2",[pos1,pos2])

        #add final rack pin (rack is an input pin to this module)
        self.add_layout_pin(text="rack", 
                            layer=self.m2_pin_layer, 
                            offset=(xpos-self.m2_width, -self.m_pitch("m1")), 
                            width=self.m1_width,
                            height=self.m1_width)

    def add_power_pins(self):
        """ Adds the vdd and gnd pins """

        #route and connect all vdd and gnd pins together
        for i in range(self.size):
            yoff=min(self.dout_inst[i].get_pin("vdd").by(), self.dout_inv_inst[i].get_pin("vdd").by())
            height= abs(self.dout_inv_inst[0].get_pin("vdd").uy()-\
                        self.dout_inst[0].get_pin("vdd").uy())+ contact.m1m2.width
            self.add_rect(layer="metal1",
                          offset=(self.dout_inv_inst[i].lx()-self.m1_width, yoff),
                          width=self.m1_width,
                          height=height)
            
            pos1= (0, self.dout_inst[i].get_pin("gnd").lc().y)
            pos2= (self.dout_inv_inst[i].lx(), self.dout_inst[i].get_pin("gnd").lc().y)
            self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width)
            
            pos1= (0, self.dout_inst[i].get_pin("vdd").lc().y)
            pos2= (self.dout_inv_inst[i].lx(), self.dout_inst[i].get_pin("vdd").lc().y)
            self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width)
            
            # adding final vdd anf gnd pins for this module
            for pin in ["vdd", "gnd"]:
                self.add_layout_pin(text=pin, 
                                    layer=self.m1_pin_layer, 
                                    offset=self.dout_inst[i].get_pin(pin).ll(), 
                                    width=contact.m1m2.width,
                                    height=contact.m1m2.width)

    def add_fill_layers(self):
        """ Adds the extra well and implant and metal1 to avoid DRC violation """

        # filling VT and well layers to avoid min_space violation
        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                          offset = (self.dout_inv_inst[0].lx(), 0),
                          width=self.inv.nwell_width,
                          height=self.height)
        self.add_rect(layer="vt",
                      offset = self.dout_inv_inst[0].ll()+self.inv.vt_offset,
                      layer_dataType = layer["vt_dataType"],
                      width=self.inv.vt_width,
                      height=self.height)
        
        # adding implant layer to avoid poly-enclosed-implant violation
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset =  self.dout_inv_inst[0].ll()+self.inv.nimplant_of,
                          width=self.inv.nimplant_width,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset =  self.dout_inv_inst[0].ll()+self.inv.pimplant_pos,
                          width=self.inv.pmos.height,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset = (0,0),
                          width=self.xgap,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset = self.dout_inst[0].lr(),
                          width=self.xgap,
                          height=self.height)
        
        # adding metal1 layer to avoid m1_minarea violation
        for i in range(self.size):
            for pin in ["Sn0", "Sp0", "Dn0", "Dp0"]:
                off=(self.dout_inst[i].get_pin(pin).cc().x-self.m1_space,self.dout_inst[i].get_pin(pin).cc().y)
                self.add_metal_minarea("metal1", off)
