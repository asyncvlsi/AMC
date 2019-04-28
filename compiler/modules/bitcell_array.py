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
        self.create_layout()
        self.add_layout_pins()

        self.width = self.column_size*self.cell.width 
        if info["name"] == "scn3me_subm":
            # scn3me_subm has a tall 6T_cell layout
            self.add_horiz_gnd_rail()

        if info["name"] != "scn3me_subm":
            # for all other technology nodes use a thin 6T_cell layout
            self.add_well_contacts()
        
        highest = self.find_highest_coords()
        lowest = self.find_lowest_coords()
        self.height = highest.y-lowest.y
        self.translate_all(vector(0, lowest.y))

    def add_pins(self):
        """ Add pins for bitcell_array, order of the pins is important """
        
        for col in range(self.column_size):
            self.add_pin("bl[{0}]".format(col))
            self.add_pin("br[{0}]".format(col))
        for row in range(self.row_size):
            self.add_pin("wl[{0}]".format(row))
        self.add_pin_list(["vdd", "gnd"])

    def create_layout(self):
        """ Add bitcell in a 2D array, Flip the cells in odd rows to share power rails """

        xoffset = 0.0
        self.cell_inst = {}
        
        for col in range(self.column_size):
            yoffset = 0.0
            for row in range(self.row_size):
                name = "bit_r{0}_c{1}".format(row, col)
                if row % 2:
                    tempy = yoffset + self.cell.height
                    mirror = "MX"
                else:
                    tempy = yoffset
                    mirror = "R0"

                self.cell_inst[row,col]=self.add_inst(name=name, 
                                                      mod=self.cell, 
                                                      offset=[xoffset, tempy], 
                                                      mirror=mirror)
                self.connect_inst(["bl[{0}]".format(col),"br[{0}]".format(col), 
                                   "wl[{0}]".format(row), "vdd", "gnd"])
                yoffset += self.cell.height
            xoffset += self.cell.width

    def add_layout_pins(self):
        """ Add bitline and bitline_b pins + wordline, vdd and gnd """
        
        vdd_pin = self.cell.get_pin("vdd")
        gnd_pins = self.cell.get_pins("gnd")
        
        offset = vector(0.0, 0.0)
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
            # increments to the next column width
            offset.x += self.cell.width

        offset.x = 0.0
        for row in range(self.row_size):
            wl_pin = self.cell_inst[row,0].get_pin("wl")
            vdd_pins = self.cell_inst[row,0].get_pins("vdd")
            gnd_pins = self.cell_inst[row,0].get_pins("gnd")

            # add gnd label
            for gnd_pin in gnd_pins:
                if gnd_pin.layer=="m3pin":
                    self.add_layout_pin(text="gnd", 
                                        layer=gnd_pin.layer, 
                                        offset=gnd_pin.ll(), 
                                        width=gnd_pin.width(), 
                                        height=gnd_pin.height())
                
            # add vdd label only add to even rows to avoid duplicates
            for vdd_pin in vdd_pins:
                if row % 2 == 0:
                    self.add_layout_pin(text="vdd", 
                                        layer=vdd_pin.layer, 
                                        offset=vdd_pin.ll(), 
                                        width=vdd_pin.width(), 
                                        height=vdd_pin.height())
                
            # add wl label
            self.add_layout_pin(text="wl[{0}]".format(row),
                                layer=wl_pin.layer, 
                                offset=wl_pin.ll(), 
                                width=wl_pin.width(), 
                                height=wl_pin.height())

            # increments to the next row height
            offset.y += self.cell.height
    
    def add_horiz_gnd_rail(self):
        """ Adds a horizontal M1 rail at top of array to connect all vertical gnd rails"""
        
        
        #y_shift is the height of cell_6t layout outside of its bounding box
        self.y_shift = self.well_enclose_active + 0.5*contact.m1m2.width
        height= self.row_size*self.cell.height
        width= self.column_size*self.cell.width
        
        
        self.add_path("metal1", [(0, height+self.y_shift+self.m1_width-0.5*contact.m1m2.width), 
                                 (width, height+self.y_shift+self.m1_width-0.5*contact.m1m2.width)],
                      width=contact.m1m2.width)
        self.add_layout_pin(text="gnd", 
                            layer=self.m1_pin_layer, 
                            offset=(-0.5*contact.m1m2.width, height+self.y_shift+self.m1_width-contact.m1m2.width), 
                            width=contact.m1m2.width, 
                            height=contact.m1m2.width)

        for col in range(self.column_size):
            self.add_via(self.m1_stack, 
                         (self.cell_inst[0,col].get_pins("gnd")[0].lx(), 
                          height+self.y_shift+self.m1_width-contact.m1m2.width))
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pins("gnd")[0].lx(),height),
                          width=contact.m1m2.width,
                          height=self.y_shift+self.m1_width)

            #extend the bitlines from bottom to the top edge
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("bl").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height+2*self.y_shift+self.m1_width)
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("br").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height+2*self.y_shift+self.m1_width)

        # this is for the last gnd in last column
        self.add_via(self.m1_stack, (self.cell_inst[0,self.column_size-1].get_pins("gnd")[1].lx(), 
                     height+self.y_shift+self.m1_width-contact.m1m2.width))
        self.add_rect(layer="metal2",
                      offset=(self.cell_inst[0,self.column_size-1].get_pins("gnd")[1].lx(),height),
                      width=contact.m1m2.width,
                      height=self.y_shift+self.m1_width)
        
        #extend the well on both ends of array
        if (self.row_size%2 == 0):
            self.add_rect(layer="pwell",
                          offset=(-self.y_shift,self.row_size*self.cell.height+self.y_shift),
                          width=width+2*self.y_shift,
                          height=self.m1_width)
                      
        self.implant_shift = self.y_shift
    
    def add_well_contacts(self):
        """ Add pwell and nwell contacts at the top of each column """
        
        #measure the size of wells in bitcell
        (nw_width, nw_height) = utils.get_libcell_size("cell_6t", GDS["unit"], layer["nwell"])
        (pw_width, pw_height) = utils.get_libcell_size("cell_6t", GDS["unit"], layer["pwell"])
        x_shift = (2*pw_width+nw_width-self.cell.width)/2
        y_shift = (pw_height-self.cell.height)/2
        y_off = self.row_size*self.cell.height+y_shift
        well_height = 2*self.well_enclose_active + 3*contact.active.width
        
        #there is one pwell and one nwell contact for each column
        for col in range(2*self.column_size):
            if col % 2:
                well_xoffset = ((col-1)/2)*self.cell.width - x_shift + pw_width
                well_width = nw_width 
                well_type="nwell"
                implant_type="nimplant"
                implant_offset=(well_xoffset- self.implant_space, y_off)
                implant_width= well_width + pw_width
                contact_offset = (well_xoffset+self.well_enclose_active, 
                                  y_off+well_height-self.well_enclose_active-contact.active.height)

            else:
                well_xoffset = (col/2)*self.cell.width - x_shift
                well_width = pw_width 
                well_type="pwell"
                implant_type="pimplant"
                implant_offset=(well_xoffset, y_off)
                implant_width=well_width- self.implant_space
                contact_offset = (well_xoffset+self.well_enclose_active, 
                                  y_off+self.well_enclose_active)

            self.add_contact(("active", "contact", "metal1"), contact_offset)
            
            self.add_rect(layer= "active",
                          offset= contact_offset,
                          width= self.active_minarea/contact.well.height,
                          height= contact.well.height)
            
            self.add_rect(layer= well_type,
                          offset= (well_xoffset, y_off),
                          width= well_width,
                          height= well_height)
            
            self.add_rect(layer= implant_type,
                          offset= implant_offset,
                          width= implant_width,
                          height= well_height)

            self.add_rect(layer= "metal1",
                          offset= (0, y_off+well_height-self.well_enclose_active-contact.active.height),
                          width= self.width,
                          height= self.m1_width)

            self.add_layout_pin(text="vdd",
                                layer= self.m1_pin_layer,
                                offset=(0, y_off+well_height-self.well_enclose_active-contact.active.height),
                                width= self.m1_width,
                                height= self.m1_width)

            self.add_rect(layer= "metal1",
                          offset= (0,  y_off+self.well_enclose_active),
                          width= self.width,
                          height= self.m1_width)

            self.add_layout_pin(text="gnd",
                                layer= self.m1_pin_layer,
                                offset=(0,  y_off+self.well_enclose_active),
                                width= self.m1_width,
                                height= self.m1_width)
        
        self.y_shift = self.well_enclose_active+0.5*contact.well.width
        height= self.row_size*self.cell.height
        self.add_rect(layer="pwell",
                      offset=(0,-self.y_shift),
                      width=self.width,
                      height=self.y_shift)
        
        for col in range(self.column_size):
            #extend the bitlines from bottom to the top edge
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("bl").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height+2*self.y_shift+well_height)
            self.add_rect(layer="metal2",
                          offset=(self.cell_inst[0,col].get_pin("br").lx(),-self.y_shift),
                          width=contact.m1m2.width,
                          height=height+2*self.y_shift+well_height)
        
        
        self.implant_shift = (nw_height-self.cell.height)/2 
