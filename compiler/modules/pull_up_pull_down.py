""" This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1301, USA.
"""


import design
import debug
import contact
from utils import ceil
from vector import vector
from globals import OPTS
from utils import round_to_grid
from ptx import ptx

class pull_up_pull_down(design.design):
    """ This module generates a parametrically sized pull-up-pull-down network. """

    unique_id = 1
    def __init__(self, num_nmos, num_pmos, nmos_size, pmos_size, vdd_pins=[], gnd_pins=[]):
        
        name = "pull_up_pull_down_{0}".format(pull_up_pull_down.unique_id)
        pull_up_pull_down.unique_id += 1
        design.design.__init__(self, name)
        debug.info(2, "create pull_up_pull_down structure {0}".format(name))

        self.num_nmos = num_nmos
        self.num_pmos = num_pmos
        self.nmos_size = nmos_size
        self.pmos_size = pmos_size
        self.nmos_width = self.nmos_size*self.minwidth_tx
        self.pmos_width = self.pmos_size*self.minwidth_tx
        self.vdd_pins = vdd_pins
        self.gnd_pins = gnd_pins
        
        self.add_pins()
        self.create_layout()
        
    def add_pins(self):
        """ Add pins for pull_up_pull_down network, order of the pins is important """
        
        self.add_pin("Sn0")
        for i in range(self.num_nmos):
            self.add_pin("Gn{0}".format(i))
            self.add_pin("Dn{0}".format(i))
        self.add_pin("Sp0")
        for i in range(self.num_pmos):
            self.add_pin("Gp{0}".format(i))
            self.add_pin("Dp{0}".format(i))
        self.add_pin_list(["vdd", "gnd"])

    def create_layout(self):
        """ Calls all functions related to the generation of the layout """

        self.create_ptx()
        self.setup_layout_constants()
        self.add_ptx()
        self.add_supply_rails()
        self.add_well_contacts()
        self.connect_rails()
        self.add_input_output_pins()

    def create_ptx(self):
        """ Create the PMOS and NMOS transistors. """
        
        # Apply the min_arae rule for active (diff) layer only if num_mos and mos_size are both 1
        # This will help to align the gates of pull-up and pull-down
        
        if (self.nmos_size == 1 and self.num_nmos == 1):
            nmos_min_area = True
            pmos_min_area = False
        if (self.pmos_size == 1 and self.num_pmos == 1):
            nmos_min_area = False
            pmos_min_area = True
        else:
            nmos_min_area = False
            pmos_min_area = False
             
        self.nmos = ptx(width=self.nmos_width,
                        mults=1,
                        tx_type="nmos",
                        connect_poly=False,
                        connect_active=False,
                        min_area = nmos_min_area)
        self.add_mod(self.nmos)

        self.pmos = ptx(width=self.pmos_width,
                        mults=1,
                        tx_type="pmos",
                        connect_poly=False,
                        connect_active=False,
                        min_area = pmos_min_area)
        self.add_mod(self.pmos)

    def setup_layout_constants(self):
        """ Pre-compute some handy layout parameters. """
        
        # Compute the overlap of the source and drain pins
        nmos_overlap_offset = self.nmos.get_pin("D").ll().x - self.nmos.get_pin("S").ll().x
        pmos_overlap_offset = self.pmos.get_pin("D").ll().x - self.pmos.get_pin("S").ll().x
        self.overlap_offset = max(nmos_overlap_offset, pmos_overlap_offset)

        # This is for active-to-active of two cell that share the vdd/gnd rail
        self.top_bottom_space = self.m1_space+contact.m1m2.width
        num_mos = max(self.num_nmos, self.num_pmos)
        mos_width= max(self.pmos.width,self.nmos.width)
        self.well_height = 2*self.top_bottom_space + (num_mos-1)*self.overlap_offset+ mos_width
        self.height = self.well_height

    def add_ptx(self):
        """ Add PMOS and NMOS to the layout at the upper-most and lowest position """
        
        # place PMOS right to nwell contact
        x_off = self.well_enclose_active + 1.5*contact.well.height + \
                self.implant_enclose_body_active + self.pmos.height
        y_off= self.top_bottom_space
        
        self.pmos_inst={}
        self.nmos_inst={}
        
        for i in range(self.num_pmos):
            pmos_pos = vector(x_off, y_off+i*self.overlap_offset)
            self.pmos_inst[i]=self.add_inst(name="pullup-down_pmos{0}".format(i),
                                            mod=self.pmos,
                                            offset=pmos_pos,
                                            rotate=90)
            if i == 0:
                self.connect_inst(["Dp{0}".format(i), "Gp{0}".format(i), "Sp0", "vdd"])
            else:
                self.connect_inst(["Dp{0}".format(i), "Gp{0}".format(i), "Dp{0}".format(i-1), "vdd"])

        # place NMOS right to pmos
        x_off = self.pmos_inst[0].lr().x+self.poly_space+self.nmos.height
        for i in range(self.num_nmos):
            nmos_pos = vector(x_off, y_off+i*self.overlap_offset)
            self.nmos_inst[i]=self.add_inst(name="pullup-down_nmos{0}".format(i),
                                            mod=self.nmos,
                                            offset=nmos_pos,
                                            rotate=90)
            if i == 0:
                self.connect_inst(["Dn{0}".format(i), "Gn{0}".format(i), "Sn0", "gnd"])
            else:
                self.connect_inst(["Dn{0}".format(i), "Gn{0}".format(i), "Dn{0}".format(i-1), "gnd"])
        
        # This should be placed at the top of the NMOS well
        nwell_pos = vector(0,0)
        nwell_width=self.nmos_inst[0].ll().x
        pimplant_pos = vector(self.pmos_inst[0].ll().x,0)
        
        # This should be placed below the PMOS well
        pwell_pos = vector(self.nmos_inst[0].ll().x,0)
        pwell_width= self.nmos.height + 1.5*contact.well.height + \
                       self.implant_enclose_body_active+self.well_enclose_active
        nimplant_pos = vector(self.nmos_inst[0].ll().x,0)
        
        self.width = nwell_width + pwell_width
        
        self.add_rect(layer="nwell", 
                      offset=nwell_pos, 
                      width=nwell_width, 
                      height=self.height)
        self.add_rect(layer="pimplant", 
                      offset=pimplant_pos, 
                      width=self.nmos_inst[0].ll().x-pimplant_pos.x, 
                      height=self.height)
        
        # This should cover pwell-contact and nmos
        self.add_rect(layer="pwell", 
                      offset=pwell_pos, 
                      width=pwell_width, 
                      height=self.height)
        self.add_rect(layer="nimplant", 
                      offset=nimplant_pos, 
                      width=self.nmos.height, 
                      height=self.height)

    def add_supply_rails(self):
        """ Add vdd/gnd rails to the top and bottom. """
        self.add_rect(layer="metal1",
                      offset=vector(0,0),
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="gnd",
                            layer=self.m1_pin_layer,
                            offset=vector(0,0),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        self.add_rect(layer="metal1",
                      offset=vector(0,self.height-contact.m1m2.width),
                      width=self.width,
                      height=contact.m1m2.width)
        self.add_layout_pin(text="vdd",
                            layer=self.m1_pin_layer,
                            offset=vector(0,self.height-contact.m1m2.width),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

    def add_well_contacts(self):
        """ Add n/p well taps to the layout and connect to supplies """

        layer_stack = ("active", "contact", "metal1")
        nw_contact_off=vector(self.well_enclose_active, 
                              self.height-contact.well.height-self.well_enclose_active)
        self.add_contact(layers=layer_stack, 
                         offset=(nw_contact_off.x+contact.active.height, nw_contact_off.y),
                         implant_type="n", well_type="n", rotate=90)

        pw_contact_off= vector(self.nmos_inst[0].lr().x+self.implant_enclose_body_active, 
                               self.well_enclose_active)
        self.add_contact(layers=layer_stack, 
                         offset=(pw_contact_off.x+contact.active.height, pw_contact_off.y),
                         implant_type="p", well_type="p", rotate=90)
        
        self.active_height = ceil(self.active_minarea/(1.5*contact.well.height))
        
        active_off1 = nw_contact_off-vector(0, self.active_height-self.well_enclose_active)
        metal_off1= nw_contact_off + vector(0,self.active_enclose_contact)
        metal_height1 = self.height -  nw_contact_off.y - self.active_enclose_contact
        pimplant_off = (0, 0)
        implant_width = self.well_enclose_active+1.5*contact.well.height+\
                        self.implant_enclose_body_active

        active_off2 = pw_contact_off
        metal_off2= (pw_contact_off.x, 0)
        metal_height2 = pw_contact_off.y + self.active_enclose_contact
        nimplant_off = (self.nmos_inst[0].lr().x, 0)


        self.add_active_implant("nimplant", active_off1, metal_off1, metal_height1, 
                                pimplant_off, implant_width)
        self.add_active_implant("pimplant", active_off2, metal_off2, metal_height2, 
                               nimplant_off, implant_width)


    def add_active_implant(self, implant_type, active_off, metal_off, metal_height, 
                           implant_off, implant_width):
        """ Add n/p well and implant to the layout """
        
        self.add_rect(layer="active",
                      offset=active_off,
                      width= (1.5*contact.well.height),
                      height=self.active_height)
        
        self.add_rect(layer="metal1",
                      offset=metal_off,
                      width=contact.well.second_layer_width,
                      height=metal_height)
        
        self.add_rect(layer=implant_type,
                      offset=implant_off,
                      width=implant_width,
                      height=self.height)

    def connect_rails(self):
        """ Connect the nmos and pmos to its respective power rails """

        for i in range(len(self.vdd_pins)):
            n=self.vdd_pins[i][0]
            j=int(self.vdd_pins[i][1:])
            self.add_via_center(self.m1_stack, (self.pmos_inst[j].get_pin(n).uc().x,
                                                self.pmos_inst[j].get_pin(n).lc().y), rotate=90)
        for i in range(len(self.gnd_pins)):
            n=self.gnd_pins[i][0]
            j=int(self.gnd_pins[i][1:])
            self.add_via_center(self.m1_stack, (self.nmos_inst[j].get_pin(n).uc().x,
                                                self.nmos_inst[j].get_pin(n).lc().y), rotate=90)            

        self.add_via_center(self.m1_stack, (self.pmos_inst[0].get_pin("D").uc().x,
                                            self.height-0.5*contact.m1m2.width), rotate=90)
        self.add_path("metal2", [(self.pmos_inst[0].get_pin("D").uc().x,0), 
                                 (self.pmos_inst[0].get_pin("D").uc().x,self.height)])
        
        self.add_via_center(self.m1_stack, (self.nmos_inst[0].get_pin("D").uc().x,
                                            0.5*contact.m1m2.width), rotate=90)
        self.add_path("metal2", [(self.nmos_inst[0].get_pin("D").uc().x,0), 
                                 (self.nmos_inst[0].get_pin("D").uc().x,self.height)])

    def add_input_output_pins(self):
        """ Add pins for all the Source, Drain and Gates """

        for i in range(self.num_pmos):
            pin_offset = self.pmos_inst[i].get_pin("D").ll()
            self.add_layout_pin(text="Dp{0}".format(i),
                                layer=self.m1_pin_layer,
                                offset=pin_offset,
                                width=self.m1_width,
                                height=self.m1_width)

        for i in range(self.num_pmos):
            pin_offset = (self.pmos_inst[i].get_pin("G").ll().x, 
                          self.pmos_inst[i].get_pin("G").ll().y)
            self.add_layout_pin(text="Gp{0}".format(i),
                                layer="poly",
                                offset=pin_offset,
                                width=self.poly_width,
                                height=self.poly_width)

        self.add_layout_pin(text="Sp0",
                            layer=self.m1_pin_layer,
                             offset=self.pmos_inst[0].get_pin("S").ll(),
                             width=self.m1_width,
                             height=self.m1_width)

        #gate_pin_width = self.nmos_width + 2*self.poly_extend_active
        for i in range(self.num_nmos):
            pin_offset = self.nmos_inst[i].get_pin("D").ll()
            self.add_layout_pin(text="Dn{0}".format(i),
                                layer=self.m1_pin_layer,
                                offset=pin_offset,
                                width=self.m1_width,
                                height=self.m1_width)


        for i in range(self.num_nmos):
            pin_offset = self.nmos_inst[i].get_pin("G").ll()
            self.add_layout_pin(text="Gn{0}".format(i),
                                layer="poly",
                                offset=pin_offset,
                                width=self.poly_width,
                                height=self.poly_width)
        
        self.add_layout_pin(text="Sn0",
                            layer=self.m1_pin_layer,
                             offset=self.nmos_inst[0].get_pin("S").ll(),
                             width=self.m1_width,
                             height=self.m1_width)
