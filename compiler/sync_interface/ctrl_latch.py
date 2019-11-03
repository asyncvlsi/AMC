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
from vector import vector
from pinv import pinv
from pull_up_pull_down import pull_up_pull_down

class ctrl_latch(design.design):
    """ Dynamically generated input ctrl latch for synchronous interface """

    def __init__(self, size, name="ctrl_latch_array"):
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
        """ Adds pins, order of the pins is important"""
        
        for i in range(self.size):
            self.add_pin("async_in[{0}]".format(i))
        for i in range(self.size):
            self.add_pin("sync_in[{0}]".format(i))
        self.add_pin_list(["clk", "en", "vdd", "gnd"])

    def create_modules(self):
        """ Create modules for instantiation """

        #each ctrl_latch has 3 stacked NMOS and one PMOS
        self.ctrl_latch = pull_up_pull_down(num_nmos=3, num_pmos=1, 
                                            nmos_size=1, pmos_size=4, 
                                            vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.ctrl_latch)

        self.inv = pinv(size=2)
        self.add_mod(self.inv)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.xgap= max(self.implant_space,self.well_space,3*self.m_pitch("m1"))
        self.ygap= max(self.implant_space,self.well_space,2*self.m_pitch("m1"))

        #This is a contact/via shift to avoid DRC violation
        self.via_co_shift= 0.5*abs(contact.poly.width-contact.m1m2.width)
        
        #This is width and the height of ctrl_latch_array. 
        self.height= self.inv.height + self.ctrl_latch.height + self.ygap + 4* self.m_pitch("m1")
        self.width = self.size* (self.ctrl_latch.width+self.xgap) + self.m1_width

    def add_modules(self):
        """ Place the gates """

        self.ctrl_inst = {}
        for i in range(self.size):
            # adding pull_up_pull_down network for ctrl_latch
            off=(i*(self.ctrl_latch.width+self.xgap), 0)
            self.ctrl_inst[i]=self.add_inst(name="in_latch{}".format(i), 
                                            mod=self.ctrl_latch, offset=off)
            self.connect_inst(["gnd", "en", "n1_{}".format(i), "clk", "n2_{}".format(i), 
                               "async_in[{}]".format(i), "n3_{}".format(i), 
                               "vdd", "en", "n3_{}".format(i), "vdd", "gnd"])

        self.ctrl_inv_inst = {}
        for i in range(self.size):
            # output of ctrl_latch is drived with an inverter
            off=(i*(self.ctrl_latch.width+self.xgap),self.ctrl_latch.height+self.ygap)
            self.ctrl_inv_inst[i]=self.add_inst(name="din_inv{}".format(i), 
                                                mod=self.inv, offset=off)
            self.connect_inst(["n3_{}".format(i), "sync_in[{}]".format(i), "vdd", "gnd"])
        
        #connect the output of latch to input of inverter
        for i in range(self.size):
            pos1= self.ctrl_inst[i].get_pin("Dn2").uc()-vector(0.5*contact.active.height,0)
            pos2=vector(self.ctrl_inst[i].rx(), pos1.y)
            pos3= vector(pos2.x, self.ctrl_inst[i].uy()+self.m_pitch("m1"))
            pos5=self.ctrl_inv_inst[i].get_pin("A").lc()
            pos4=vector(pos5.x, pos3.y)
            pos6=self.ctrl_inst[i].get_pin("Dp0").uc()
            
            self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4, pos5])
            self.add_path("metal1",[pos6, (pos6.x, pos1.y), pos1])
            self.add_via_center(self.m1_stack, (pos5.x, pos5.y), rotate=90)

    def add_layout_pins(self):
        """ Routing pins to modules' input and output"""
        
        self.add_async_din_pins()
        self.add_sync_din_pins()
        self.add_clk_pin()
        self.add_en_pin()
        self.add_power_pins()
        self.add_fill_layers()

    def add_metal_minarea(self, pin):
        """ Adds horizontal metal1 rail to avoid DRC min_area"""
        
        self.add_rect_center(layer="metal1",
                             offset=pin,
                             width=self.m1_minarea/contact.m1m2.first_layer_width,
                             height=contact.m1m2.first_layer_width)
        
    def add_async_din_pins(self):
        """ Adds the input data pins """

        for i in range(self.size):
            xpos = self.ctrl_inst[i].lx()+self.m_pitch("m1")
            pin = self.ctrl_inst[i].get_pin("Gn2")
            
            self.add_path("poly", [(xpos, pin.lc().y), pin.lc()])
            
            off=(xpos+contact.poly.height, pin.by()-contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos+contact.m1m2.height,pin.by()-contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            self.add_metal_minarea(vector(xpos, pin.by()-0.5*contact.m1m2.width-self.via_co_shift))
            
            pos1=(xpos+0.5*self.m2_width, -4*self.m_pitch("m1"))
            pos2=(xpos+0.5*self.m2_width, pin.by()-self.via_co_shift)
            self.add_path("metal2",[pos1, pos2])
        
            # add final async_in pins as inputs (asyn_r, async_w)
            self.add_layout_pin(text="async_in[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset=(xpos, -4*self.m_pitch("m1")), 
                                width=self.m2_width,
                                height=self.m2_width)

    def add_sync_din_pins(self):
        """ Adds the output data pins """

        for i in range(self.size):
            pin = self.ctrl_inv_inst[i].get_pin("Z")
            pos1=(pin.lx()-0.5*self.m2_width, pin.by())
            pos2=(pin.lx()-0.5*self.m2_width, self.ctrl_inv_inst[i].uy()+self.m2_width)
            self.add_path("metal2", [pos1, pos2 ])
        
            # add final syn_input pins as outputs (sync_r, sync_w)
            self.add_layout_pin(text="sync_in[{0}]".format(i), 
                                layer=self.m2_pin_layer, 
                                offset=(pin.lx()-self.m2_width, self.ctrl_inv_inst[i].uy()), 
                                width=self.m2_width,
                                height=self.m2_width)

    def add_clk_pin(self):
        """ Adds the clk pin """

        for i in range(self.size):
            #route the clk to ctrl_latch gates
            xpos=self.ctrl_inst[i].rx()+2*self.m_pitch("m1")
            pin = self.ctrl_inst[i].get_pin("Gn1")
            self.add_path("poly", [pin.lc(), (xpos, pin.lc().y)])
            
            off=(xpos, pin.by()-contact.poly.width)
            self.add_contact(self.poly_stack, off,rotate=90)
            
            off=(xpos, pin.by()-contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off,rotate=90)
            
            xoff=xpos-contact.m1m2.height+self.via_shift("v1")
            yoff=pin.by()-0.5*contact.m1m2.width-self.via_co_shift
            self.add_metal_minarea((xoff, yoff))
            
            pos1=(xpos, pin.by()-self.via_co_shift)
            pos2=(xpos, -self.m_pitch("m1"))
            self.add_path("metal2",[pos1, pos2])
            
            off=(xpos+0.5*self.m2_width+self.via_shift("v1"), -self.m_pitch("m1"))
            self.add_via(self.m1_stack, off, rotate=90)

        pos1=(0,-self.m_pitch("m1")+0.5*self.m1_width)
        pos2=(self.width,-self.m_pitch("m1")+0.5*self.m1_width)
        self.add_path("metal1", [pos1,  pos2])
        
        # add final clk pin
        self.add_layout_pin(text="clk", 
                            layer=self.m1_pin_layer, 
                            offset=(0, -self.m_pitch("m1")), 
                            width=self.m1_width,
                            height=self.m1_width)

    def add_en_pin(self):
        """ Adds the enable pins """

        for i in range(self.size):
            # route en pin to ctrl_latch gates
            xpos=self.ctrl_inst[i].rx()+self.m_pitch("m1")
            pin = self.ctrl_inst[i].get_pin("Gn0")
            self.add_path("poly",[self.ctrl_inst[i].get_pin("Gp0").lc(), (xpos, pin.lc().y)])

            off=(xpos, pin.by()-contact.poly.width)
            self.add_contact(self.poly_stack, off, rotate=90)
            
            off=(xpos, pin.by()-contact.poly.width+self.via_co_shift)
            self.add_via(self.m1_stack, off, rotate=90)
            
            self.add_metal_minarea((xpos, pin.by()-0.5*contact.m1m2.width-self.via_co_shift))
            
            pos1= (xpos, pin.by()-self.via_co_shift)
            pos2= (xpos, -3*self.m_pitch("m1"))
            self.add_path("metal2",[pos1, pos2])
            
            off=(xpos+0.5*self.m2_width+self.via_shift("v1"),-3*self.m_pitch("m1"))
            self.add_via(self.m1_stack, off, rotate=90)
        
        pos1=(0,-3*self.m_pitch("m1")+0.5*self.m1_width)
        pos2=(self.width,-3*self.m_pitch("m1")+0.5*self.m1_width)
        self.add_path("metal1",[pos1, pos2])
        
        #add the final enable pin
        self.add_layout_pin(text="en", 
                            layer=self.m1_pin_layer, 
                            offset=(0, -3*self.m_pitch("m1")), 
                            width=self.m1_width,
                            height=self.m1_width)

    def add_power_pins(self):
        """ Adds the vdd and gnd pins """

        # Route and connect all vdd pins together
        pos1=self.ctrl_inv_inst[0].get_pin("gnd").lc()
        pos2=self.ctrl_inv_inst[self.size-1].get_pin("gnd").lc()
        self.add_path("metal1",[pos1, pos2],width=contact.m1m2.width)
        
        pos1=self.ctrl_inv_inst[0].get_pin("vdd").lc()
        pos2=self.ctrl_inv_inst[self.size-1].get_pin("vdd").lc()
        self.add_path("metal1",[pos1, pos2],width=contact.m1m2.width)
        
        # Route and connect all gnd pins together
        pos1=self.ctrl_inst[0].get_pin("gnd").lc()
        pos2=self.ctrl_inst[self.size-1].get_pin("gnd").lc()
        self.add_path("metal1",[pos1, pos2],width=contact.m1m2.width)
        
        pos1=self.ctrl_inst[0].get_pin("vdd").lc()
        pos2=self.ctrl_inst[self.size-1].get_pin("vdd").lc()
        self.add_path("metal1",[pos1, pos2],width=contact.m1m2.width)
        
        # adding final vdd and gnd pins for this module
        for pin in ["vdd", "gnd"]:
            self.add_layout_pin(text=pin, 
                                layer=self.m1_pin_layer, 
                                offset=self.ctrl_inv_inst[0].get_pin(pin).ll(), 
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)
            self.add_layout_pin(text=pin, 
                                layer=self.m1_pin_layer, 
                                offset=self.ctrl_inst[0].get_pin(pin).ll(), 
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)
    def add_fill_layers(self):
        """ Adds the extra well and implant and metal1 to avoid DRC violation """

        # filling implant and well layers to avoid min_space violation
        height = self.ctrl_inv_inst[0].by() - self.ctrl_inst[0].uy() - 0.5*contact.m1m2.width
        for layer in ("nwell", "pimplant"):
            self.add_rect(layer=layer,
                          offset = (0, self.ctrl_inst[0].uy()),
                          width=self.width,
                          height=height)
        
        # adding implant layer to avoid poly-enclosed-implant violation
        for i in range(self.size):
            self.add_rect(layer="pimplant",
                          offset=((i+1)*self.ctrl_latch.width+i*self.xgap, 
                                  self.ctrl_inst[i].by()),
                          width=self.xgap,
                          height=self.ctrl_inst[i].height)
            
            # adding metal1 layer to avoid m1_minarea violation
            shift = self.m1_minarea/contact.m1m2.first_layer_width
            xoff=self.ctrl_inv_inst[i].get_pin("Z").lx()-contact.m1m2.width+0.5*shift
            yoff=self.ctrl_inv_inst[i].get_pin("Z").lc().y
            self.add_metal_minarea(vector(xoff,yoff))
        
        # adding metal1 layer to avoid m1_minarea violation
        for i in range(self.size):
            for pin in ["Sn0", "Sp0", "Dn0", "Dn1", "Dp0"]:
                off=self.ctrl_inst[i].get_pin(pin).cc()-vector(self.m1_space,0)
                self.add_metal_minarea(off)
