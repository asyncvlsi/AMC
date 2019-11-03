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

class din_latch(design.design):
    """ Dynamically generated input-data/address latch arrays for synchronous interface """

    def __init__(self, size, name="din_latch_array"):
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
            self.add_pin("async_din[{0}]".format(i))
        for i in range(self.size):
            self.add_pin("sync_din[{0}]".format(i))
        self.add_pin_list(["clk", "en", "clk_b", "en_b", "vdd", "gnd"])

    def create_modules(self):
        """ Create modules for instantiation """

        #each datain_latch has 3 stacked NMOS and 3 stacked PMOS
        self.din_latch = pull_up_pull_down(num_nmos=3, num_pmos=3, 
                                           nmos_size=1, pmos_size=4, 
                                           vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.din_latch)

        self.inv = pinv(size=2)
        self.add_mod(self.inv)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.xgap= max(self.implant_space,self.well_space,3*self.m_pitch("m1"))

        #This is a contact/via shift to avoid DRC violation
        self.via_co_shift= 0.5*abs(contact.poly.width-contact.m1m2.width)
        
        #This is width and the height of din_latch_array. 
        #vdd/gnd rails are shared so their height is deducted from final height.
        self.height= self.size*self.din_latch.height-(self.size-1)*contact.m1m2.width+self.m_pitch("m1")
        self.width = self.din_latch.width+self.inv.width+2*self.xgap + self.m_pitch("m1")

    def add_modules(self):
        """ Place the gates """

        self.din_inst = {}
        self.din_inv_inst = {}
        for i in range(self.size):
            if i%2:
                mirror = "MX"
                yoff=(i+1)*self.din_latch.height-i*contact.m1m2.width
            else:
                mirror = "R0"
                yoff=i*(self.din_latch.height-contact.m1m2.width)

            # adding pull_up_pull_down network for data_in_latch
            self.din_inst[i]=self.add_inst(name="din_latch{}".format(i), 
                                           mod=self.din_latch, 
                                           offset=(self.xgap, yoff),
                                           mirror=mirror)
            self.connect_inst(["gnd", "async_din[{}]".format(i), "n1_{}".format(i), "en", 
                               "n2_{}".format(i), "clk", "n3_{}".format(i), 
                               "vdd", "async_din[{}]".format(i), "p1_{}".format(i), "en_b", 
                               "p2_{}".format(i), "clk_b", "n3_{}".format(i), "vdd", "gnd"])

        for i in range(self.size):
            if i%2:
                mirror = "MX"
                yoff=(i+1)*self.din_latch.height-i*contact.m1m2.width -0.5*contact.m1m2.width
            else:
                mirror = "R0"
                yoff=i*(self.din_latch.height-contact.m1m2.width)+0.5*contact.m1m2.width

            # output of data_in_latch is drived with an inverter
            self.din_inv_inst[i]=self.add_inst(name="din_inv{}".format(i), 
                                               mod=self.inv, 
                                               offset=(self.din_latch.width+2*self.xgap, yoff),
                                               mirror=mirror)
            self.connect_inst(["n3_{}".format(i), "sync_din[{}]".format(i), "vdd", "gnd"])

    def add_layout_pins(self):
        """ Routing pins to modules' inputs and outputs"""
        
        self.add_async_din_pins()
        self.add_sync_din_pins()
        self.add_clk_pin()
        self.add_en_pin()
        self.add_power_pins()
        self.add_fill_layers()

    def add_metal_minarea(self, layer, pin):
        """ Adds horizontal metal rail to avoid DRC min_area"""
        
        if layer == "metal1":
            min_area=self.m1_minarea
        else:
            min_area=self.m2_minarea
        
        self.add_rect_center(layer=layer,
                             offset=pin,
                             width=ceil(min_area/contact.m1m2.first_layer_width),
                             height=contact.m1m2.first_layer_width)

        
    def add_async_din_pins(self):
        """ Adds the input data pins """

        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1
            
            xpos = self.din_inst[i].lx()+self.m_pitch("m1")
            pin=self.din_inst[i].get_pin("Gp0")
            
            #async_din is connected to G0 of pulldown network.
            pos2 =self.din_inst[i].get_pin("Gn0").lc()
            pos1 =(xpos+self.via_shift("co"), pos2.y)
            self.add_path("poly", [pos1,pos2])
            
            off=(xpos+contact.poly.height, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos+contact.m1m2.height,  pin.lc().y- yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            off = vector(xpos, pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            off=vector(xpos, pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal2", off)
            
            # add final async_in pins as inputs (asyn_datain)
            off = (xpos, pin.lc().y-yshift*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_layout_pin(text="async_din[{0}]".format(i), 
                                layer=self.m1_pin_layer, 
                                offset= off, 
                                width=self.m1_width,
                                height=self.m1_width)

    def add_sync_din_pins(self):
        """ Adds the output data pins """
        
        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
                ypin=self.din_inst[i].get_pin("Dp2").cc()-\
                     vector(0.5*contact.active.height,0.5*contact.active.width)
            else:
                yshift=1
                yshift2=1
                ypin=self.din_inst[i].get_pin("Dp2").cc()-\
                     vector(0.5*contact.active.height, -0.5*contact.active.width)

            xpos = self.din_inv_inst[i].lx()-self.m_pitch("m1")
            
            pos1=self.din_inv_inst[i].get_pin("A").lc()
            pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
            pos3=vector(pos2.x, ypin.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, ypin])
        
            width = ceil(self.m1_minarea/contact.m1m2.first_layer_width)
            net=self.din_inv_inst[i].get_pin("Z")
            self.add_metal_minarea("metal1",(net.lx()-contact.m1m2.width+ 0.5*width,net.lc().y))
            
            # add final sync_din pins as outputs (syn_datain)
            self.add_layout_pin(text="sync_din[{0}]".format(i), 
                                layer=self.m1_pin_layer, 
                                offset=net.ll(), 
                                width=self.m1_width,
                                height=self.m1_width)

    def add_clk_pin(self):
        """ Adds the clk pins """

        for i in range(self.size):
            #clk_b
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route the clk_b pin to din_latch gates
            xpos = self.din_inst[i].lx()-self.m_pitch("m2")+contact.m1m2.height
            pin=self.din_inst[i].get_pin("Gp2")
            self.add_path("poly",[pin.lc(), (self.din_inst[i].lx()-self.m_pitch("m2")+self.via_shift("co"),
                                                  pin.lc().y)])
            off=(self.din_inst[i].lx()-self.m_pitch("m2")+contact.poly.height, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            off=(xpos+self.via_shift("v1"), pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m2_stack, off, rotate=90)
            
            off=vector(xpos-contact.m1m2.height,pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            off=vector(xpos-contact.m1m2.height,pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal2", off)
                                 
            
            pos1= (xpos-0.5*self.m3_width, pin.lc().y-self.via_co_shift+contact.m2m3.width)
            pos2= (xpos-0.5*self.m3_width, -self.m_pitch("m1"))
            self.add_path("metal3",[pos1, pos2])
        
        # add final clk_bar pin
        self.add_layout_pin(text="clk_b", 
                            layer=self.m3_pin_layer, 
                            offset=(xpos-self.m3_width, -self.m_pitch("m1")), 
                            width=self.m3_width,
                            height=self.m3_width)
        for i in range(self.size):
            #clk
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route the clk pin to din_latch gates
            xpos=self.din_inst[i].rx()+self.m_pitch("m1")
            pin=self.din_inst[i].get_pin("Gn2")
            self.add_path("poly", [pin.lc(), (xpos-self.via_shift("co"), pin.lc().y)])
            
            off = (xpos, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off , rotate=90)
            
            off = vector(xpos, pin.lc().y-0.5*yshift2*contact.m1m2.width- yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            pos1=(xpos-0.5*self.m2_width, pin.lc().y-self.via_co_shift+contact.m1m2.width)
            pos2= (xpos-0.5*self.m2_width, -self.m_pitch("m1"))
            self.add_path("metal2", [pos1, pos2])
        
        # add final clk pin
        self.add_layout_pin(text="clk", 
                            layer=self.m2_pin_layer, 
                            offset=(xpos-self.m2_width, -self.m_pitch("m1")), 
                            width=self.m1_width,
                            height=self.m1_width)
    def add_en_pin(self):
        """ Adds the enable pins """

        for i in range(self.size):
            #u
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route the en_bar pin to din_latch gates
            xpos = self.din_inst[i].lx() + contact.m1m2.height
            pin=self.din_inst[i].get_pin("Gp1")
            self.add_path("poly", [pin.lc(), (self.din_inst[i].lx()+self.via_shift("co"), pin.lc().y)])

            off=(self.din_inst[i].lx()+contact.poly.height, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off =(xpos, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            off=(xpos+self.via_shift("v1"), pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m2_stack, off, rotate=90)
            
            off=vector(self.din_inst[i].lx(), pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            off=vector(self.din_inst[i].lx(), pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal2", off)
            
            pos1= (xpos-0.5*self.m3_width, pin.lc().y-self.via_co_shift+contact.m2m3.width)
            pos2= (xpos-0.5*self.m3_width, -self.m_pitch("m1"))
            self.add_path("metal3",[pos1, pos2])
        
        # add final en_bar pin
        self.add_layout_pin(text="en_b", 
                            layer=self.m3_pin_layer, 
                            offset=(xpos-self.m3_width, -self.m_pitch("m1")), 
                            width=self.m3_width,
                            height=self.m3_width)
        for i in range(self.size):
            if i%2:
                yshift=0
                yshift2=-1
            else:
                yshift=1
                yshift2=1

            #route the en pin to din_latch gates
            xoff = self.din_inst[i].rx()
            pin=self.din_inst[i].get_pin("Gn1")
            self.add_path("poly",[pin.lc(), (xoff-self.via_shift("co"), pin.lc().y)])

            off = (xoff, pin.lc().y-yshift*contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xoff, pin.lc().y-yshift*contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack,off, rotate=90)
            
            off=vector(xoff, pin.lc().y-0.5*yshift2*contact.m1m2.width-yshift2*self.via_co_shift)
            self.add_metal_minarea("metal1", off)
            
            pos1=(xoff-self.m2_width, pin.lc().y-self.via_co_shift+contact.m1m2.width)
            pos2= (xoff-self.m2_width, -self.m_pitch("m1"))
            self.add_path("metal2",[pos1,pos2])
        
        # add final en pin
        self.add_layout_pin(text="en", 
                            layer=self.m2_pin_layer, 
                            offset=(xoff-1.5*self.m2_width, -self.m_pitch("m1")), 
                            width=self.m2_width,
                            height=self.m2_width)        

    def add_power_pins(self):
        """ Adds the vdd and gnd pins """

        for i in range(self.size):
            
            for pin in ["vdd", "gnd"]:
                if i%2:
                    ypin=self.din_inv_inst[i].get_pin(pin).ul()
                else:
                    ypin=self.din_inv_inst[i].get_pin(pin).ll()
                
                # Route and connect all vdd pins together
                self.add_path("metal1",[ypin, self.din_inst[i].get_pin(pin).lc()], width=contact.m1m2.width)
                
                pos1= (0, self.din_inst[i].get_pin(pin).lc().y)
                pos2= (self.width, self.din_inst[i].get_pin(pin).lc().y)
                self.add_path("metal1",[pos1, pos2],width=contact.m1m2.width)
                
                # adding final vdd and gnd pins for this module
                self.add_layout_pin(text=pin, 
                                layer=self.m1_pin_layer, 
                                offset=self.din_inst[i].get_pin(pin).ll(), 
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)

    def add_fill_layers(self):
        """ Adds the extra well and implant and metal1 to avoid DRC violation """

        if info["has_nwell"]:
            self.add_rect(layer="nwell",
                          offset= (self.din_inv_inst[0].lx(), 0),
                          width=self.inv.nwell_width,
                          height=self.height)
        
        self.add_rect(layer="vt",
                      offset=self.din_inv_inst[0].ll()+self.inv.vt_offset,
                      layer_dataType=layer["vt_dataType"],
                      width=self.inv.vt_width,
                      height=self.height)
        
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset=self.din_inv_inst[0].ll()+self.inv.nimplant_of,
                          width=self.inv.nimplant_width,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset= self.din_inv_inst[0].ll()+self.inv.pimplant_pos,
                          width=self.inv.pmos.height,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset=(0,0),
                          width=self.xgap,
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset=self.din_inst[0].lr(),
                          width=self.xgap,
                          height=self.height)
        
        # adding metal1 layer to avoid m1_minarea violation
        for i in range(self.size):
            for pin in ["Sn0", "Sp0", "Dn0", "Dp0", "Dn1", "Dp1"]:
                off = (self.din_inst[i].get_pin(pin).cc().x-self.m1_space, self.din_inst[i].get_pin(pin).cc().y)
                self.add_metal_minarea("metal1", off)
