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


import debug
import design
import contact
import utils
from tech import info, GDS, layer
from vector import vector
from globals import OPTS
from bitcell import bitcell


class bitcell_array(design.design):
    """ Creates a rows x cols array of memory cells. 
        Assumes bitlines and wordlines are connected by abutment. """

    def __init__(self, cols, rows, name="bitcell_array"):
        design.design.__init__(self, name)
        debug.info(1, "Creating {0} {1} x {2}".format(name, rows, cols))

        self.name = name
        self.column_size = cols
        self.row_size = rows

        self.cell = bitcell()
        self.add_mod(self.cell)
                
        self.add_pins()

        if info["foundry_cell"]:
            from endcells_frame import endcells_frame
            
            self.endcell = endcells_frame(self.column_size, self.row_size)
            self.add_mod(self.endcell)
            
            self.xleft_shift = self.endcell.left_width
            self.ybot_shift = self.endcell.bot_width
            self.xright_shift = self.endcell.right_width
            self.ytop_shift = self.endcell.top_width
            self.width = self.column_size*self.cell.width + self.xright_shift + self.xleft_shift
            self.add_endcells_frame()
            
        else:
            
            self.xleft_shift = 0
            self.ybot_shift = 0
            self.xright_shift = 0
            self.ytop_shift = 0
            self.width = self.column_size*self.cell.width

        self.create_layout()
        self.add_layout_pins()
        

        if info["add_well_tap"]:
            # Don't add well-tap to foundary cells and bitcells that already have well tap
            self.add_well_contacts()

        highest = self.find_highest_coords()
        lowest = self.find_lowest_coords()
        self.height = highest.y-lowest.y
        self.width = highest.x-lowest.x
        #self.translate_all(vector(0, lowest.y))
        self.offset_all_coordinates()
        

    def add_pins(self):
        """ Add pins for bitcell_array, order of the pins is important """
        
        for col in range(self.column_size):
            self.add_pin("bl[{0}]".format(col))
            self.add_pin("br[{0}]".format(col))
        for row in range(self.row_size):
            self.add_pin("wl[{0}]".format(row))
        self.add_pin_list(["vdd", "gnd"])
        
        if info["foundry_cell"]:
            self.add_pin("sub")

    def create_layout(self):
        """ Add bitcell in a 2D array, Flip the cells in odd rows to share power rails """

        xoffset = 0.0
        self.cell_inst = {}

        for col in range(self.column_size):
            yoffset = 0.0
            
            if col% 2:
                tempx = xoffset 
            else:
                tempx = xoffset + self.cell.width
            
            for row in range(self.row_size):
                name = "bit_r{0}_c{1}".format(row, col)
                if row % 2:
                    tempy = yoffset 
                else:
                    tempy = yoffset + self.cell.height
                
                if row % 2 and col% 2:
                    mirror = "R0"
                    rotate=0
                if row % 2 and not col% 2:
                    mirror = "MY"
                    rotate=0
                if not row % 2 and col% 2:
                    mirror = "MX"
                    rotate=0
                if not row % 2 and not col% 2:
                    mirror = "R0"
                    rotate=180
                
                pin_list = ["bl[{0}]".format(col),"br[{0}]".format(col), "wl[{0}]".format(row), "vdd", "gnd"]
                if info["foundry_cell"]:
                    pin_list.extend(["gnd", "sub"])
                self.cell_inst[row,col]=self.add_inst(name=name, 
                                                      mod=self.cell, 
                                                      offset=[tempx, tempy], 
                                                      mirror=mirror,
                                                      rotate=rotate)
                self.connect_inst(pin_list)
                yoffset += self.cell.height
            xoffset += self.cell.width

    def add_layout_pins(self):
        """ Add bitline and bitline_bar pins + wordline, vdd and gnd """
        
        # add bl & br pin and label
        for col in range(self.column_size):
            bl_pin = self.cell_inst[0,col].get_pin("bl")
            br_pin = self.cell_inst[0,col].get_pin("br")
            
            self.add_layout_pin(text="bl[{0}]".format(col), 
                                layer=bl_pin.layer, 
                                offset=bl_pin.ll(), 
                                width=bl_pin.width(), 
                                height=bl_pin.height())
            self.add_layout_pin(text="br[{0}]".format(col), 
                                layer=br_pin.layer, 
                                offset=br_pin.ll(), 
                                width=br_pin.width(), 
                                height=br_pin.height())

        # add wl pin and label
        for row in range(self.row_size):
            wl_pin = self.cell_inst[row,0].get_pin("wl")
            self.add_layout_pin(text="wl[{0}]".format(row),
                                layer=wl_pin.layer, 
                                offset=wl_pin.ll(), 
                                width=wl_pin.width(), 
                                height=wl_pin.height())
        
        # add vdd/gnd pin and label
        if self.cell.get_pin("gnd").layer != self.cell.get_pin("vdd").layer:
            # With vdd and gnd on different layer --> vdd and gnd are perpendicular
        
            #Find which pin (vdd/gnd) is vertical
            if self.cell.get_pin("gnd").layer == self.cell.get_pin("bl").layer:
                self.v_pin = "gnd"
                self.h_pin = "vdd"

            else:
                self.v_pin = "vdd"
                self.h_pin = "gnd"

            for row in range(self.row_size):
                # add label for horizontal power rail
                
                h_pins = self.cell_inst[row,0].get_pins(self.h_pin)
                for h_pin in h_pins:
                    self.add_layout_pin(text=self.h_pin, 
                                        layer=h_pin.layer, 
                                        offset=h_pin.ll(), 
                                        width=h_pin.width(), 
                                        height=h_pin.height())

            # Don't add label for vertical power rail; a horizontal 
            # rail at the top of array connects v_pin rails together
            self.add_horiz_power_rail(self.v_pin)


        else:
            # with vdd and gnd on same layer --> vdd and gnd rails are parallel
            
            for row in range(self.row_size):
                vdd_pins = self.cell_inst[row,0].get_pins("vdd")
                gnd_pins = self.cell_inst[row,0].get_pins("gnd")

                # add gnd label
                for gnd_pin in gnd_pins:
                    self.add_layout_pin(text="gnd", 
                                        layer=gnd_pin.layer, 
                                        offset=gnd_pin.ll(), 
                                        width=gnd_pin.width(), 
                                        height=gnd_pin.height())
                
                # add vdd label only to even rows to avoid duplicates
                for vdd_pin in vdd_pins:
                    if row % 2 == 0:
                        self.add_layout_pin(text="vdd", 
                                        layer=vdd_pin.layer, 
                                        offset=vdd_pin.ll(), 
                                        width=vdd_pin.width(), 
                                        height=vdd_pin.height())
    
    def add_horiz_power_rail(self, v_pin):
        """ Adds a horizontal metal3 rail at top of array to connect all vertical power rails"""
        
        
        #y_shift is the height of cell_6t layout outside of its bounding box
        # OR the height of BL endcell (dummy cell) at the top of array        
        
        self.y_shift = 0.5*min(self.cell.height, self.cell.width)
        if info["foundry_cell"]:
            self.y_shift = self.y_shift+self.ytop_shift
        
        height= self.row_size*self.cell.height
        width= self.column_size*self.cell.width
        
        
        h_power_rail_yoff = height+self.y_shift+4*self.m3_width-0.5*contact.m2m3.width
        pos1=(0, h_power_rail_yoff)
        pos2=(width, h_power_rail_yoff)
        self.add_path("metal3", [pos1, pos2], width=contact.m2m3.width)
        
        off = (0, height+self.y_shift+4*self.m3_width-contact.m2m3.width)
        self.add_layout_pin(text=v_pin, 
                            layer=self.m3_pin_layer, 
                            offset=off, 
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)

        bitline_width = self.cell.get_pin("bl").width()
        for col in range(self.column_size):
            for pin in self.cell_inst[0,col].get_pins(v_pin):
                
                xoff = pin.lx()+contact.m2m3.height-self.via_shift("v2")
                yoff =  height+self.y_shift+4*self.m3_width-contact.m2m3.width
                self.add_via(self.m2_stack, (xoff, yoff), rotate=90)
                self.add_rect(layer="metal2",
                              offset=(pin.lx(),height),
                              width=contact.m1m2.width,
                              height=self.y_shift+4*self.m3_width)

            #extend the bitlines from bottom to the top edge
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("bl").lx(),-self.y_shift),
                          width=bitline_width,
                          height=height+2*self.y_shift+4*self.m3_width)
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("br").lx(),-self.y_shift),
                          width=bitline_width,
                          height=height+2*self.y_shift+4*self.m3_width)

        self.ybot_shift = self.y_shift
    
    def add_well_contacts(self):
        """ Add pwell and nwell contacts at the top of each column """
        
        #measure the size of implants and wells in bitcell
        if info["has_nwell"]:
            (nw_width, nw_height) = utils.get_libcell_size("cell_6t", GDS["unit"], layer["nwell"])
        else :
            (nw_width, nw_height) = (0,0)
        
        if info["has_pwell"]:
            (pw_width, pw_height) = utils.get_libcell_size("cell_6t", GDS["unit"], layer["pwell"])
        elif info["has_nimplant"]:
            (pw_width, pw_height) = utils.get_libcell_size("cell_6t", GDS["unit"], layer["nimplant"])
        else:
            (pw_width, pw_height) = (0.5*(self.cell.width-nw_width),self.cell.height)
        
        x_shift = 0.5*(2*pw_width+nw_width-self.cell.width)
        y_shift = 0.5*(nw_height-self.cell.height)
        y_off = self.row_size*self.cell.height+y_shift
        well_height = 2*self.well_enclose_active + 3*contact.active.width
        
        #there is one pwell and one nwell contact for each column
        for col in range(2*self.column_size):
            if col % 2:
                well_xoffset = ((col-1)/2)*self.cell.width - x_shift + pw_width
                well_width = nw_width+self.implant_space
                well_type="nwell"
                implant_type="nimplant"
                implant_offset=(well_xoffset+ self.implant_space, y_off)
                implant_width= well_width + pw_width- 3*self.implant_space
                contact_xoff = well_xoffset+self.well_enclose_active+self.implant_space 
                contact_yoff = y_off+well_height-self.well_enclose_active-contact.active.height

            else:
                well_xoffset = (col/2)*self.cell.width - x_shift
                well_width = pw_width 
                well_type="pwell"
                implant_type="pimplant"
                implant_offset=(well_xoffset, y_off)
                implant_width=well_width + self.implant_space
                contact_xoff = well_xoffset+self.well_enclose_active 
                contact_yoff = y_off+self.well_enclose_active

            self.add_contact(("active", "contact", "metal1"), (contact_xoff, contact_yoff))
            
            self.add_rect(layer= "active",
                          offset= (contact_xoff, contact_yoff),
                          width= self.active_minarea/contact.well.height,
                          height= contact.well.height)
            
            if info["has_{}".format(well_type)]:
                self.add_rect(layer= well_type,
                          offset= (well_xoffset, y_off),
                          width= well_width,
                          height= well_height)
            
            if info["has_{}".format(implant_type)]:
                self.add_rect(layer= implant_type,
                          offset= implant_offset,
                          width= implant_width,
                          height= well_height)

            pin_off =(0,y_off+well_height-self.well_enclose_active-contact.active.height)
            self.add_rect(layer= "metal1",
                          offset= pin_off,
                          width= self.width,
                          height= contact.m1m2.width)

            self.add_layout_pin(text="vdd",
                                layer= self.m1_pin_layer,
                                offset=pin_off,
                                width= self.m1_width,
                                height= self.m1_width)

            self.add_rect(layer= "metal1",
                          offset= (0, y_off+self.well_enclose_active),
                          width= self.width,
                          height= self.m1_width)

            self.add_layout_pin(text="gnd",
                                layer= self.m1_pin_layer,
                                offset=(0, y_off+self.well_enclose_active),
                                width= self.m1_width,
                                height= self.m1_width)
        
        self.y_shift = self.well_enclose_active+0.5*contact.well.width
        if info["has_pwell"]:
            # Add this pwell to avoid DRC violation when connecting arrays in bank
            self.add_rect(layer="pwell",
                          offset=(0,-self.y_shift),
                          width=self.width,
                          height=self.y_shift)
        
        height= self.row_size*self.cell.height+2*self.y_shift+well_height
        for col in range(self.column_size):
            #extend the bitlines from bottom to the top edge
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("bl").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height)
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("br").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height)
        
        self.ybot_shift = 0.5*(nw_height-self.cell.height) 


    def add_endcells_frame(self):
        """ Add endcells frame around the foundry_bitcell_array """
        
        self.frame = self.add_inst(name="endcells_frame1", 
                                   mod=self.endcell, 
                                   offset=(-self.xleft_shift, -self.ybot_shift))
        
        temp = []
        for col in range(self.column_size):
            temp.extend(["bl[{0}]".format(col)])
            temp.extend(["br[{0}]".format(col)])
        for row in range(self.row_size):
            temp.extend(["wl[{0}]".format(row)])
        temp.extend(["vdd", "gnd", "sub"])
        self.connect_inst(temp)

