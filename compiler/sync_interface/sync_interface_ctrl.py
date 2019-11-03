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
from tech import info
from vector import vector
from pinv import pinv
from nand2 import nand2
from pull_up_pull_down import pull_up_pull_down
from utils import ceil

class sync_interface_ctrl(design.design):
    """ Dynamically generated controller for synchronous interface """

    def __init__(self, name="sync_interface_ctrl"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout and route between modules """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_offsets()
        self.add_modules()
        self.route_gates()
        self.add_layout_pins()

    def add_pins(self):
        """ Adds pins, order of the pins is important """
        
        self.add_pin_list(["clk", "clk_b", "en", "ack", "rack", "ctrl_en",  
                           "din_en", "din_en_b", "rack_b", "vdd", "gnd"])

    def create_modules(self):
        """ Create modules for instantiation """

        #ctrl_en gate has 1 NMOS and 2 stacked PMOS
        self.ctrl_en = pull_up_pull_down(num_nmos=1, num_pmos=2, 
                                         nmos_size=1, pmos_size=4, 
                                         vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.ctrl_en)

        #din_en1 gate has 2 stacked NMOS and 2 stacked PMOS
        self.din_en = pull_up_pull_down(num_nmos=2, num_pmos=2, 
                                        nmos_size=1, pmos_size=4, 
                                        vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.din_en)
        
        #din_en2 gate (generates req signal for din_en gate) has 2 stacked NMOS and 1 PMOS
        self.din_en2 = pull_up_pull_down(num_nmos=2, num_pmos=1, 
                                         nmos_size=1, pmos_size=4, 
                                         vdd_pins=["S0"], gnd_pins=["S0"])
        self.add_mod(self.din_en2)

        self.inv = pinv(size=2)
        self.add_mod(self.inv)

    def setup_layout_offsets(self):
        """ Setup layout offsets, spaces, etc """
        
        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.xgap= max(self.implant_space,self.well_space,3*self.m_pitch("m1"))
        self.ygap= max(self.implant_space,self.well_space,4*self.m_pitch("m1"))

        #This is a contact/via shift to avoid DRC violation
        self.via_co_shift= 0.5*abs(contact.poly.width-contact.m1m2.width)
        
        #This is the offset for adding and routing the pins. 
        self.en_xoff= -2*self.m_pitch("m1")
        self.clk_xoff = -self.m_pitch("m1")
        self.ack_xoff= 0
        self.rack_xoff= self.inv.width+self.xgap
        
        #This is width and the height of interface control logic module. 
        self.height= self.ctrl_en.height+self.din_en.height+self.inv.height+self.ygap+4*self.m_pitch("m1")
        self.width = 2*self.inv.width+self.din_en2.width+self.din_en.width+2*self.xgap+5*self.m_pitch("m1")

    def add_modules(self):
        """ Place the gates """

        #ctrl gate for ctrl_latch (ctrl_enable)
        self.ctrl_en_inst=self.add_inst(name="ctrl_en", mod=self.ctrl_en, offset=(0, 0))
        self.connect_inst(["gnd", "ack", "ctrl_en", "vdd", "ack", 
                           "p1", "clk", "ctrl_en", "vdd", "gnd"])
        
        #ctrl gate to generate "req" signal
        offset = vector(0, self.ctrl_en_inst.uy()+self.din_en2.height-contact.m1m2.width)
        self.din_en_inst1=self.add_inst(name="din_en1", mod=self.din_en2, 
                                        offset=offset, mirror="MX")
        self.connect_inst(["gnd", "en", "m1", "clk", "m2", "vdd", "en", "m2", "vdd", "gnd"])
        
        # output of ctrl gate for "req" is drived with an inverter
        offset = offset + vector(self.din_en_inst1.rx(), -0.5*contact.m1m2.width)
        self.din_en_inv=self.add_inst(name="din_en_inv", mod=self.inv, offset=offset, mirror="MX")
        self.connect_inst(["m2", "req", "vdd", "gnd"])
        
        
        #ctrl gate for din_latch (din_enable)
        offset = (self.din_en_inv.rx()+self.din_en2.width+self.xgap, 
                  self.ctrl_en_inst.uy()+self.din_en.height-contact.m1m2.width)
        self.din_en_inst2=self.add_inst(name="din_en2", mod=self.din_en, 
                                       offset= offset, rotate=180)
        self.connect_inst(["gnd", "ack", "o1", "req", "din_en", "vdd", 
                           "ack", "r1", "clk", "din_en", "vdd", "gnd"])
        
        # output of ctrl gate for din_enable is drived with an inverter to generate din_enable_bar
        offset = (self.din_en_inst2.rx()+self.xgap, 
                  self.ctrl_en_inst.uy()+self.din_en2.height-1.5*contact.m1m2.width)
        self.din_en_inv2=self.add_inst(name="din_en_inv2", mod=self.inv, 
                                       offset=offset, mirror="MX")
        self.connect_inst(["din_en", "din_en_b", "vdd", "gnd"])
        
        #inverter for clk_bar
        self.clk_inv=self.add_inst(name="clk_inv", mod=self.inv, 
                                   offset=(0, self.din_en_inst1.uy()+self.ygap))
        self.connect_inst(["clk", "clk_b", "vdd", "gnd"])
        
        #inverter for read_acknowledg_bar
        offset=(self.clk_inv.rx()+self.xgap, self.din_en_inst1.uy()+self.ygap)
        self.rack_inv=self.add_inst(name="rack_inv", mod=self.inv,  offset=offset)
        self.connect_inst(["rack", "rack_b", "vdd", "gnd"])

    def route_gates(self):
        """ Routing inside each gate"""
        
        self.route_ctrl_en_gate()
        self.route_din_en_gate()
        self.route_dout_en_gate()
        self.route_clk_gate()

    def route_ctrl_en_gate(self):
        """ Routing pins to modules input and output"""
        
        #route the "ack" input to ctrl_latch gate
        pos1= (self.ack_xoff+self.via_shift("co"), self.ctrl_en_inst.get_pin("Gn0").lc().y)
        pos2= self.ctrl_en_inst.get_pin("Gn0").lc()
        self.add_path("poly",[pos1, pos2])
        
        pin=self.ctrl_en_inst.get_pin("Gp0")
        self.co_shift = vector(contact.poly.height, -contact.poly.width)
        off=vector(self.ack_xoff, pin.lc().y) + self.co_shift
        self.add_contact(self.poly_stack, off, rotate=90)
        
        self.shift = vector(contact.m1m2.height-self.via_shift("v1"), 
                           -contact.poly.width+self.via_co_shift)
        off=vector(self.ack_xoff, pin.lc().y)+self.shift
        self.add_via(self.m1_stack, off, rotate=90)
        
        self.min_area_shift = 0.5*contact.m1m2.width+self.via_co_shift
        off=(self.ack_xoff, pin.lc().y-self.min_area_shift)
        self.add_metal_minarea("metal1", off)
        
        #route the "clk" input to ctrl_latch gate
        pin=self.ctrl_en_inst.get_pin("Gp1")
        self.add_path("poly",[(self.clk_xoff+self.via_shift("co"), pin.lc().y), pin.lc()])
        
        off=vector(self.clk_xoff, pin.lc().y)+ self.co_shift
        self.add_contact(self.poly_stack, off, rotate=90)
        
        off=vector(self.clk_xoff, pin.lc().y)+self.shift
        self.add_via(self.m1_stack, off, rotate=90)
        
        off=(self.clk_xoff, pin.lc().y-self.min_area_shift)
        self.add_metal_minarea("metal1", off)
        
        self.add_path("metal1",[self.ctrl_en_inst.get_pin("Dn0").uc(),
                                self.ctrl_en_inst.get_pin("Dp1").lc()])


    def route_din_en_gate(self):
        """ Routing pins to modules input and output"""
        
        #route the "enable" input to din_latch gate
        pos1= (self.en_xoff+self.via_shift("co"), self.din_en_inst1.get_pin("Gn0").lc().y)
        pos2= self.din_en_inst1.get_pin("Gn0").lc()
        self.add_path("poly", [pos1, pos2])
        
        pin=self.din_en_inst1.get_pin("Gp0")
        off=vector(self.en_xoff, pin.lc().y)+ self.co_shift
        self.add_contact(self.poly_stack, off, rotate=90)
        
        off=vector(self.en_xoff, pin.lc().y)+self.shift
        self.add_via(self.m1_stack, off, rotate=90)
        
        off = (self.en_xoff, pin.lc().y-self.min_area_shift)
        self.add_metal_minarea("metal1", off)
        
        #route the "clk" input to din_latch gate
        pin=self.din_en_inst1.get_pin("Gn1")
        pos1= vector((self.clk_xoff+self.via_shift("co"), pin.lc().y-self.poly_width))
        pos2= vector(pin.lc().x-contact.active.height, pos1.y)
        pos3= vector(pos2.x, pin.lc().y)
        pos4=pin.lc()
        self.add_path("poly", [pos1, pos2, pos3, pos4])

        off=vector(self.clk_xoff, pin.lc().y+0.5*self.poly_width)+ self.co_shift
        self.add_contact(self.poly_stack, off, rotate=90)
        
        off=vector(self.clk_xoff, pin.lc().y+0.5*self.poly_width)+self.shift
        self.add_via(self.m1_stack, off, rotate=90)
        
        off=(self.clk_xoff, pin.lc().y+0.5*self.poly_width-self.min_area_shift)
        self.add_metal_minarea("metal1", off)
        
        #connect output of din_latch1 gate to input of din_inverter1
        pos1= self.din_en_inst1.get_pin("Dp0").uc()
        pos2= self.din_en_inst1.get_pin("Dn1").lc()
        self.add_path("metal1",[pos1, pos2])
        
        pos1=self.din_en_inv.get_pin("A").ul()-vector(0.5*self.m1_width,0)
        pos2=self.din_en_inst1.get_pin("Dn1").lc()
        self.add_path("metal1",[pos1, pos2])
        
        #connect output of din_inverter1 gate to input of din_latch2
        pos1=self.din_en_inv.get_pin("Z").ul()+vector(0.5*self.m1_width,0)
        pos2=(self.din_en_inst2.lx(),self.din_en_inst2.get_pin("Gn1").lc().y+0.5*contact.poly.width)
        self.add_path("metal1",[pos1, pos2])
        
        #connect ack to din_latch2
        pos1= self.din_en_inst2.get_pin("Gn0").lc()
        xoff=self.din_en_inst2.rx()-self.m_pitch("m1")
        yoff=self.din_en_inst2.get_pin("Gp0").lc().y
        pos2= (xoff-self.via_shift("co"),yoff)
        self.add_path("poly",[pos1, pos2])
        
        pos1=(xoff,yoff)
        self.add_contact(self.poly_stack, pos1,rotate=90)
        pos2= (self.ack_xoff, self.din_en_inst2.uy()+2*self.m_pitch("m1"))
        self.add_wire(self.m1_stack,[pos1, pos2])
        
        off=(xoff,yoff+self.via_co_shift)
        self.add_contact(self.m1_stack, off,rotate=90)
        
        off=(self.ack_xoff+contact.m1m2.height-self.via_shift("v1"), 
             self.din_en_inst1.uy()+2*self.m_pitch("m1")-0.5*contact.m1m2.width)
        self.add_via(self.m1_stack, off, rotate=90)
        
        off=(xoff,yoff+0.5*contact.m1m2.width+self.via_co_shift)
        self.add_metal_minarea("metal1", off)
        
        # req connection (req is the generated by din_latch1)
        pos1= (self.din_en_inst2.lx()+self.via_shift("co"), self.din_en_inst2.get_pin("Gn1").lc().y)
        pos2= self.din_en_inst2.get_pin("Gn1").lc()
        self.add_path("poly",[pos1, pos2])
        
        off=(self.din_en_inst2.lx()+contact.poly.height,
             self.din_en_inst2.get_pin("Gn1").lc().y)
        self.add_contact(self.poly_stack, off, rotate=90)
        
        #connect clk to din_latch2
        pos1= self.din_en_inst2.get_pin("Gp1").lc()
        pos2= (self.din_en_inst2.rx()-self.via_shift("co"), 
               self.din_en_inst2.get_pin("Gp1").lc().y)
        self.add_path("poly",[pos1, pos2])
        
        off=(self.din_en_inst2.rx(), self.din_en_inst2.get_pin("Gp1").uy())
        self.add_contact(self.poly_stack, off, rotate=90)
        
        off=(self.din_en_inst2.rx(), 
             self.din_en_inst2.get_pin("Gp1").uy()+self.via_co_shift)
        self.add_via(self.m1_stack, off, rotate=90)
        
        pos1=(self.din_en_inst2.rx(),self.din_en_inst2.get_pin("Gp1").uy())
        pos2= (self.clk_xoff, self.din_en_inst1.uy()+3*self.m_pitch("m1"))
        self.add_wire(self.m1_stack,[pos1, pos2])
        
        off=(self.clk_xoff+contact.m1m2.height-self.via_shift("v1"), 
             self.din_en_inst1.uy()+3*self.m_pitch("m1")-0.5*contact.m1m2.width)
        self.add_via(self.m1_stack, off, rotate=90)
        
        off=(self.din_en_inst2.rx(), self.din_en_inst2.get_pin("Gp1").uy()+\
             0.5*contact.m1m2.width+self.via_co_shift)
        self.add_metal_minarea("metal1", off)

    def route_dout_en_gate(self):
        """ route clk signal to clk_inverter input"""
        
        pos1= (self.clk_xoff, self.clk_inv.get_pin("A").lc().y)
        pos2= self.clk_inv.get_pin("A").lc()
        self.add_path("metal1",[pos1, pos2])
        
        off=(self.clk_xoff+self.m2_width+self.via_shift("v1"),
             self.clk_inv.get_pin("A").lc().y-0.5*contact.m1m2.width)
        self.add_via(self.m1_stack, off, rotate=90)
    
    def route_clk_gate(self):
        """ route clk_bar signal and add clk_bar pin"""
        
        pos1=self.clk_inv.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.clk_inv.uy()+self.m_pitch("m1"))
        pos4=vector(self.width, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        self.add_layout_pin(text="clk_b", 
                            layer=self.m1_pin_layer, 
                            offset=(self.width-self.m1_width, pos4.y-0.5*self.m1_width), 
                            width=self.m1_width,
                            height=self.m1_width)

    def add_layout_pins(self):
        """ Routing pins to modules' inputs and outputs"""
        
        self.add_input_ctrl_pins()
        self.add_output_ctrl_pins()
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
        
    def add_input_ctrl_pins(self):
        """ Adds input control pins (clk, ack, en, rack) """

        
        #add the final clk, enable and acknowledge pins for this module
        name_list= ["clk", "en", "ack"]
        off_list = [self.clk_xoff, self.en_xoff, self.ack_xoff]
        
        for (name, off) in zip(name_list, off_list):
            i = name_list.index(name)
            yoff = -(i+1)*self.m_pitch("m1")
            self.add_rect(layer="metal1", 
                          offset=(-3*self.m_pitch("m1"), yoff),
                          width=self.width+3*self.m_pitch("m1"),
                          height=self.m1_width)

            offset=(off+self.m2_width+self.via_shift("v1"),yoff)
            self.add_via(self.m1_stack, offset, rotate=90)
            
            self.add_rect(layer="metal2", 
                          offset=(off,yoff),
                          width=self.m2_width,
                          height=self.height-yoff)
            
            self.add_layout_pin(text=name, 
                               layer=self.m1_pin_layer, 
                               offset=(-3*self.m_pitch("m1"),yoff), 
                               width=self.m1_width,
                               height=self.m1_width)

        #add the final rack pin for this module
        pos1= self.rack_inv.get_pin("A").ll()
        pos2=vector(pos1.x, self.height)
        pos3=vector(self.width, pos2.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3])
        
        off=self.rack_inv.get_pin("A").ul()-vector(-self.m2_width,contact.m1m2.width)
        self.add_via(self.m1_stack, off, rotate=90)
        
        self.add_layout_pin(text="rack", 
                            layer=self.m1_pin_layer, 
                            offset=pos3-vector(self.m1_width, 0.5*self.m1_width), 
                            width=self.m1_width,
                            height=self.m1_width)

    def add_output_ctrl_pins(self):
        """ Adds output control pins (ctrl_en, din_en, dout_en) """

        name_list= ["ctrl_en", "rack_b", "din_en_b"]
        
        off_list= [self.ctrl_en_inst.get_pin("Dn0").lc(), 
                   self.rack_inv.get_pin("Z").ll(),
                   self.din_en_inv2.get_pin("Z").ll()]
        
        #adding the final output pins for this module
        for (name, off) in zip(name_list, off_list):
            self.add_rect(layer="metal1", 
                          offset=off,
                          width=self.width-off.x,
                          height=self.m1_width)
            self.add_layout_pin(text=name, 
                               layer=self.m1_pin_layer, 
                               offset=(self.width-self.m1_width, off.y), 
                               width=self.m1_width,
                               height=self.m1_width)
        
        # din_en routing and pin
        mod=self.din_en_inst2
        pos1= mod.get_pin("Dn1").lc()
        pos2= vector(mod.rx()-2*self.m_pitch("m1"),mod.get_pin("Dp1").lc().y)
        pos3= vector(pos2.x, mod.by()-self.m_pitch("m1")+0.5*self.m1_width)
        pos4= vector(self.width, pos3.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        self.add_layout_pin(text="din_en",  
                            layer=self.m1_pin_layer, 
                            offset=(self.width-self.m1_width, pos4.y-0.5*self.m1_width), 
                            width=self.m1_width,
                            height=self.m1_width)

        # din_en_b routing 
        pos1= mod.get_pin("Dn1").lc()
        pos2= vector(mod.rx()-2*self.m_pitch("m1"), mod.get_pin("Dp1").lc().y)
        pos3= vector(pos2.x, mod.by()-self.m_pitch("m1")+0.5*self.m1_width)
        pos4= vector(self.din_en_inv2.lx()-self.m_pitch("m1"), pos3.y)
        pos6= self.din_en_inv2.get_pin("A").lc()
        pos5= vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1,pos2, pos3, pos4, pos5, pos6])

    def add_power_pins(self):
        """ Adds and route the vdd and gnd pins """

        mod_gnd=[self.ctrl_en_inst, self.rack_inv]
        mod_vdd=[self.din_en_inv2, self.rack_inv]
        
        # adding final vdd and gnd pins for this module
        for i in range(len(mod_gnd)):
            pos1= (-3*self.m_pitch("m1"), mod_gnd[i].get_pin("gnd").lc().y)
            pos2= (self.din_en.width, mod_gnd[i].get_pin("gnd").lc().y)
            self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width)
            self.add_layout_pin(text="gnd", 
                                layer=self.m1_pin_layer, 
                                offset=mod_gnd[i].get_pin("gnd").ll(), 
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)
        
        for i in range(len(mod_vdd)):
            self.add_layout_pin(text="vdd", 
                                layer=self.m1_pin_layer, 
                                offset=mod_vdd[i].get_pin("vdd").ll(), 
                                width=contact.m1m2.width,
                                height=contact.m1m2.width)

        #route and connect all vdd and gnd pins together
        pos1= (self.din_en_inst2.lx()+0.5*contact.m1m2.width, 
               self.din_en_inst2.get_pin("vdd").lc().y)
        pos2= (self.din_en_inv.rx(), self.din_en_inv.get_pin("vdd").lc().y)
        self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width) 
        
        yoff=min(self.din_en_inv.get_pin("vdd").by(), 
                self.din_en_inst1.get_pin("vdd").by())
        height= abs(self.din_en_inv.get_pin("vdd").uy()-\
                    self.din_en_inst1.get_pin("vdd").uy())+contact.m1m2.width
        self.add_rect(layer="metal1",
                      offset=(self.din_en_inst1.rx()-self.m1_width, yoff),
                      width=self.m1_width,
                      height=height)

        pos1= (self.din_en_inst2.rx()+0.5*contact.m1m2.width, 
               self.din_en_inst2.get_pin("vdd").lc().y)
        pos2= (self.din_en_inv2.rx(),self.din_en_inv2.get_pin("vdd").lc().y)
        self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width) 
        
        self.add_rect(layer="metal1",
                      offset=(self.din_en_inst2.rx(), yoff),
                      width=contact.m1m2.width,
                      height=height)
        
        pos1= self.din_en_inst1.get_pin("gnd").ul()
        pos2= self.din_en_inv2.get_pin("gnd").lc()
        self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width)
        
        pos1= self.clk_inv.get_pin("vdd").lc()
        pos2= self.rack_inv.get_pin("vdd").lc()
        self.add_path("metal1",[pos1, pos2], width=contact.m1m2.width)
        
        pos1= self.clk_inv.get_pin("gnd").lc()
        pos2= self.rack_inv.get_pin("gnd").lc()
        self.add_path("metal1", [pos1, pos2], width=contact.m1m2.width)
    
    def add_fill_layers(self):
        """ Adds the extra well, implant and metal to avoid DRC violation """
        
        # adding implant layer to avoid poly-enclosed-implant violation
        if info["has_pimplant"]:
            self.add_rect(layer="pimplant",
                          offset=(-3*self.m_pitch("m1"), 0),
                          width=3*self.m_pitch("m1"),
                          height=self.height)
            self.add_rect(layer="pimplant",
                          offset=self.din_en_inst2.ll(),
                          width=-self.implant_enclose_poly,
                          height=self.din_en.height)

        if info["has_nimplant"]:
            self.add_rect(layer="nimplant",
                          offset=self.din_en_inst2.lr(),
                          width=self.m_pitch("m1"),
                          height=self.din_en.height)

        # adding metal1 layer to avoid m1_minarea violation
        for pin in ["Sn0", "Sp0", "Dp0"]:
            off=self.ctrl_en_inst.get_pin(pin).cc()-vector(self.m1_space,0) 
            self.add_metal_minarea("metal1", off)
        
        for pin in ["Sn0", "Sp0", "Dn0"]:
            off=self.din_en_inst1.get_pin(pin).cc()-vector(self.m1_space,0) 
            self.add_metal_minarea("metal1", off)
        
        for pin in ["Sn0", "Sp0", "Dn0", "Dp0"]:
            off=self.din_en_inst2.get_pin(pin).cc()-vector(self.m1_space,0) 
            self.add_metal_minarea("metal1", off)
        
