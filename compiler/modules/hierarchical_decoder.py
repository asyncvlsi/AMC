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
import utils
from vector import vector
from math import log
from hierarchical_predecode2x4 import hierarchical_predecode2x4 as pre2x4
from hierarchical_predecode3x8 import hierarchical_predecode3x8 as pre3x8
from decode_stage_4_4 import decode_stage_4_4
from decode_stage_5_4 import decode_stage_5_4

class hierarchical_decoder(design.design):
    """ Creates a hierarchical_decoder for n rows (n is number of wordlines)"""

    def __init__(self, rows, name="hierarchical_decoder"):
        design.design.__init__(self, name)
        debug.info(1, "Creating {0} {1}".format(name, rows))

        self.pre2x4_inst = []
        self.pre3x8_inst = []

        self.rows = rows
        self.num_inputs = int(log(self.rows, 2))
        
        (self.no_of_pre2x4, self.no_of_pre3x8)=self.determine_predecodes(self.num_inputs)
        (self.no_of_dec4_4, self.no_of_dec5_4)=self.determine_decode_stage(self.rows)
         
        self.create_layout()

    def create_layout(self):
        
        self.add_modules()
        self.setup_layout_constants()
        self.add_pins()
        self.create_pre_decoder()
        self.create_row_decoder()
        self.create_vertical_rail()
        self.route_vdd_gnd()
        gnd = self.decode_stage_inst[0].get_pins("gnd")
        min_gnd=[]
        for i in range(len(gnd)):
            min_gnd.append(gnd[i].lc().y)
        
        orgin_offset =  vector(0, min(min_gnd))
        self.translate_all(orgin_offset)

    def add_modules(self):
        
        self.dec4_4 = decode_stage_4_4()
        self.add_mod(self.dec4_4)

        self.dec5_4 = decode_stage_5_4()
        self.add_mod(self.dec5_4)
        
        self.pre2_4 = pre2x4()
        self.add_mod(self.pre2_4)
        
        self.pre3_8 = pre3x8()
        self.add_mod(self.pre3_8)

    def determine_predecodes(self,num_inputs):
        """Determines the number of 2:4 pre-decoder and 3:8 pre-decoder
        needed based on the number of inputs"""
        
        if (num_inputs == 2):
            return (1,0)
        elif (num_inputs == 3):
            return(0,1)
        elif (num_inputs == 4):
            return(2,0)
        elif (num_inputs == 5):
            return(1,1)
        elif (num_inputs == 6):
            return(3,0)
        elif (num_inputs == 7):
            return(2,1)
        elif (num_inputs == 8):
            return(1,2)
        elif (num_inputs == 9):
            return(0,3)
        else:
            debug.error("Invalid number of inputs for hierarchical decoder",-1)

    def determine_decode_stage(self, row_size):
        """Determines the number of decode_stage_4_4 and decode_stage5_4
        needed based on the number of inputs"""
        
        num_inputs = int(log(row_size, 2))
        if (num_inputs == 2):
            return (0,0)
        elif (num_inputs == 3):
            return(0,0)
        elif (num_inputs == 4):
            return(4,0)
        elif (num_inputs == 5):
            return(8,0)
        elif (num_inputs == 6):
            return(0,16)
        elif (num_inputs == 7):
            return(0,32)
        elif (num_inputs == 8):
            return(0,64)
        elif (num_inputs == 9):
            return(0,128)
        else:
            debug.error("Invalid number of inputs for hierarchical decoder",-1)

    def setup_layout_constants(self):
        
        self.predec_grp = []  # This array is a 2D array of predecoder groups.

        # Distributing vertical rails to different groups. One group belongs to one pre-decoder.
        # For example, for two 2:4 pre-decoder and one 3:8 pre-decoder, we will
        # have total 16 output lines out of these 3 pre-decoders and they will
        # be distributed as [ [0,1,2,3] ,[4,5,6,7], [8,9,10,11,12,13,14,15] ] in self.predec_grp
        
        index = 0
        for i in range(self.no_of_pre2x4):
            lines = []
            for j in range(4):
                lines.append(index)
                index = index + 1
            self.predec_grp.append(lines)

        for i in range(self.no_of_pre3x8):
            lines = []
            for j in range(8):
                lines.append(index)
                index = index + 1
            self.predec_grp.append(lines)

        self.calculate_dimensions()

        
    def add_pins(self):
        """ Add pins for decoder, order of the pins is important """
        
        for i in range(self.num_inputs):
            self.add_pin("A[{0}]".format(i))
        for j in range(self.rows):
            self.add_pin("decode[{0}]".format(j))
        self.add_pin_list(["vdd", "gnd"])

    def calculate_dimensions(self):
        """ Calculate the overal dimensions of the hierarchical decoder """

        # If we have 4 or fewer rows, the predecoder is the decoder itself
        if self.num_inputs >= 4:
            self.num_of_predecoder_out = 4*self.no_of_pre2x4 + 8*self.no_of_pre3x8
        else:
            self.num_of_predecoder_out = 0            
            debug.error("Not enough rows for a hierarchical decoder.",-1)

        # Calculates height and width of pre-decoder,
        if(self.no_of_pre3x8 > 0):
            self.predecoder_width = self.pre3_8.width 
        else:
            self.predecoder_width = self.pre2_4.width
        

        # Calculates height and width of row-decoder 
        self.row_decoder_height = int(self.rows/4)*self.dec4_4.height
        if self.no_of_dec5_4 == 0:
            self.row_decoder_width = self.dec4_4.width 
        else:
            self.row_decoder_width = self.dec5_4.width 

        self.routing_width = self.m_pitch("m1")*self.num_of_predecoder_out
        
        # Calculates height and width of hierarchical decoder 
        if self.no_of_pre2x4>0 and self.no_of_pre3x8>0 :
            self.predecoder_height = self.pre2_4.height*self.no_of_pre2x4 + \
                                     self.pre3_8.height*self.no_of_pre3x8 + \
                                     max(4*self.implant_space, 4*self.well_space)
            self.height = self.predecoder_height + self.row_decoder_height 
        else:
            self.predecoder_height = self.pre2_4.height*self.no_of_pre2x4 + \
                                     self.pre3_8.height*self.no_of_pre3x8 + \
                                     max(2*self.implant_space, 2*self.well_space)
            self.height = self.predecoder_height + self.row_decoder_height 
        
        self.width = self.predecoder_width + self.routing_width

    def create_pre_decoder(self):
        """ Creates pre-decoder and places labels input address [A] """
        
        for i in range(self.no_of_pre2x4):
            self.add_pre2x4(i)
            
        for i in range(self.no_of_pre3x8):
            self.add_pre3x8(i)

    def add_pre2x4(self,num):
        """ Add a 2x4 predecoder """
        
        if (self.num_inputs == 2):
            base = vector(self.routing_width,0)
            mirror = "R0"
            index_off1 = index_off2 = 0
        else:
            base= vector(self.routing_width+self.pre2_4.width, num * self.pre2_4.height)
            mirror = "MY"
            index_off1 = num * 2
            index_off2 = num * 4

        pins = []
        for input_index in range(2):
            pins.append("A[{0}]".format(input_index + index_off1))
        for output_index in range(4):
            pins.append("out[{0}]".format(output_index + index_off2))
        pins.extend(["vdd", "gnd"])

        self.pre2x4_inst.append(self.add_inst(name="pre[{0}]".format(num),
                                              mod=self.pre2_4,
                                              offset=base,
                                              mirror=mirror))
        self.connect_inst(pins)
        
        #Add the input pins to the 2x4 predecoder """
        for i in range(2):
            pin = self.pre2x4_inst[num].get_pin("in[{}]".format(i))
            pin_offset = pin.ll()
            
            pin = self.pre2_4.get_pin("in[{}]".format(i))
            self.add_layout_pin(text="A[{0}]".format(i + 2*num ),
                                layer=pin.layer, 
                                offset=pin_offset,
                                width=pin.width(),
                                height=pin.height())
        
    def add_pre3x8(self,num):
        """ Add 3x8 numbered predecoder """
        
        if (self.num_inputs == 3):
            offset = vector(self.routing_width,0)
            mirror ="R0"
        if self.no_of_pre2x4>0:
                height = self.no_of_pre2x4*self.pre2_4.height + \
                         num*self.pre3_8.height + 2*max(self.implant_space, self.well_space)
        else:
                height = num*self.pre3_8.height
        offset = vector(self.routing_width+self.pre3_8.width, height)
        mirror="MY"

        # If we had 2x4 predecodes, those are used as the lower decode output bits
        in_index_offset = num * 3 + self.no_of_pre2x4 * 2
        out_index_offset = num * 8 + self.no_of_pre2x4 * 4

        pins = []
        for input_index in range(3):
            pins.append("A[{0}]".format(input_index + in_index_offset))
        for output_index in range(8):
            pins.append("out[{0}]".format(output_index + out_index_offset))
        pins.extend(["vdd", "gnd"])

        self.pre3x8_inst.append(self.add_inst(name="pre3x8[{0}]".format(num), 
                                              mod=self.pre3_8,
                                              offset=offset,
                                              mirror=mirror))
        self.connect_inst(pins)

        # The 3x8 predecoders will be stacked, so use yoffset to add the pins
        for i in range(3):            
            pin = self.pre3x8_inst[num].get_pin("in[{}]".format(i))
            pin_offset = pin.ll()
            self.add_layout_pin(text="A[{0}]".format(i + 3*num + 2*self.no_of_pre2x4),
                                layer=pin.layer, 
                                offset=pin_offset,
                                width=pin.width(),
                                height=pin.height())

    def create_row_decoder(self):
        """ Add a column of decode_stage_4_4/decode_stage_5_4 for final decode """
        
        if (self.num_inputs == 4 or self.num_inputs == 5):
            self.add_decode_stage(decode_stage_mod=self.dec4_4)
            for i in range(len(self.predec_grp[0])/2):
                for j in range(len(self.predec_grp[1])/2):
                    pins =["out[{0}]".format(2*i), 
                           "out[{0}]".format(2*i+1),
                           "out[{0}]".format(2*j+len(self.predec_grp[0])), 
                           "out[{0}]".format(2*j+1+len(self.predec_grp[0])),
                           "decode[{0}]".format(len(self.predec_grp[1])*2*i + 4*j),
                           "decode[{0}]".format(len(self.predec_grp[1])*2*i + 4*j+1),
                           "decode[{0}]".format(len(self.predec_grp[1])*2*i + 4*j+2),
                           "decode[{0}]".format(len(self.predec_grp[1])*2*i + 4*j+3),
                           "vdd", "gnd"]
                    self.connect_inst(args=pins, check=False)

        elif (self.num_inputs > 5):
            self.add_decode_stage(decode_stage_mod=self.dec5_4)
            for i in range(len(self.predec_grp[0])):
                for j in range(len(self.predec_grp[1])/2):
                    for k in range(len(self.predec_grp[2])/2):
                        Z_index = len(self.predec_grp[1])*len(self.predec_grp[2]) * i + \
                                  len(self.predec_grp[2])*2*j + 4*k
                        pins = ["out[{0}]".format(2*j+len(self.predec_grp[0])),
                                "out[{0}]".format(2*j+1+len(self.predec_grp[0])),
                                "out[{0}]".format(2*k+len(self.predec_grp[0])+len(self.predec_grp[1])),
                                "out[{0}]".format(2*k+1+len(self.predec_grp[0])+len(self.predec_grp[1])),
                                "out[{0}]".format(i),
                                "decode[{0}]".format(Z_index),
                                "decode[{0}]".format(Z_index+1),
                                "decode[{0}]".format(Z_index+2),
                                "decode[{0}]".format(Z_index+3),
                                "vdd", "gnd"]
                        self.connect_inst(args=pins, check=False)

        for row in range(self.rows/4):
            for i in range(4):
                out_pos = self.decode_stage_inst[row].get_pin("out{0}".format(i))
                self.add_layout_pin(text="decode[{0}]".format(4*row+i),
                                layer=out_pos.layer,
                                offset=out_pos.ll(),
                                width=out_pos.width(),
                                height=out_pos.height())


    def add_decode_stage(self, decode_stage_mod):
        """ Add a column of decode_stages for the decoder above the predecoders."""
        
        self.decode_stage_inst = []
        for row in range(self.rows/4):
            name = "decode_stage[{0}]".format(row)
            if (self.no_of_pre2x4 > 0 and self.no_of_pre3x8 > 0):
                y_off = self.predecoder_height + decode_stage_mod.height*row 
            else:
                y_off = self.predecoder_height + decode_stage_mod.height*row 

            y_dir = 1
            mirror = "R0"
            self.decode_stage_inst.append(self.add_inst(name=name,
                                          mod=decode_stage_mod,
                                          offset=[self.routing_width, y_off]))


    def create_vertical_rail(self):
        """ Creates vertical metal 2 rails to connect predecoder and decoder stages."""

        # Array for saving the X offsets of the vertical rails. These rail
        # offsets are accessed with indices. The offsets go into the negative x 
        # direction assuming the predecodes are placed at (self.routing_width,0)
        self.rail_x_offsets = []
        for i in range(self.num_of_predecoder_out):
            x_offset = self.m_pitch("m1") * i
            self.rail_x_offsets.append(x_offset+0.5*self.m2_width)
            self.add_rect(layer="metal2",
                          offset=vector(x_offset,0),
                          width=self.m2_width,
                          height=self.height)

        self.connect_rails_to_predecodes()
        self.connect_rails_to_decoder()

    def connect_rails_to_predecodes(self):
        """ Iterates through all of the predecodes and connects to the rails including the offsets """

        for pre_num in range(self.no_of_pre2x4):
            for i in range(4):
                index = pre_num * 4 + i
                out_name = "out[{}]".format(i)
                pin = self.pre2x4_inst[pre_num].get_pin(out_name)
                self.connect_rail(index, pin) 

            
        for pre_num in range(self.no_of_pre3x8):
            for i in range(8):
                index = pre_num * 8 + i + self.no_of_pre2x4 * 4
                out_name = "out[{}]".format(i)
                pin = self.pre3x8_inst[pre_num].get_pin(out_name)
                self.connect_rail(index, pin) 

    def connect_rails_to_decoder(self):
        """ Use the self.predec_grp to determine the connections to the decode-stages.
            Inputs of decode_stages come from different groups.
            e.g. for these groups [ [0,1,2,3] ,[4,5,6,7], [8,9,10,11]] 
            the first decode_stage_5_4 inputs are connected to [0,1,4,5,8] and 
            the second decode_stage_5_4 inputs are connected to [2,3,4,5,9] ...and 
            the 16th decode_stage_5_4 inputs are connected to [2,3,6,7,11] """
        row_index = 0
        if (self.num_inputs == 4 or self.num_inputs == 5):
            for a in range(len(self.predec_grp[0])/2):
                for b in range(len(self.predec_grp[1])/2):
                    self.connect_rail(2*a, self.decode_stage_inst[row_index].get_pin("in0"))
                    self.connect_rail(2*a+1, self.decode_stage_inst[row_index].get_pin("in1"))
                    self.connect_rail(2*b+len(self.predec_grp[0]), 
                                      self.decode_stage_inst[row_index].get_pin("in2"))
                    self.connect_rail(2*b+1+len(self.predec_grp[0]), 
                                      self.decode_stage_inst[row_index].get_pin("in3"))
                    row_index = row_index + 1

        elif (self.num_inputs > 5):
            for a in range(len(self.predec_grp[0])):
                for b in range(len(self.predec_grp[1])/2):
                    for c in range(len(self.predec_grp[2])/2):
                        self.connect_rail(a, self.decode_stage_inst[row_index].get_pin("in4"))
                        self.connect_rail(2*b+len(self.predec_grp[0]), 
                                          self.decode_stage_inst[row_index].get_pin("in0"))
                        self.connect_rail(2*b+1+len(self.predec_grp[0]), 
                                          self.decode_stage_inst[row_index].get_pin("in1"))
                        self.connect_rail(2*c+len(self.predec_grp[0])+len(self.predec_grp[1]), 
                                          self.decode_stage_inst[row_index].get_pin("in2"))
                        self.connect_rail(2*c+1+len(self.predec_grp[0])+len(self.predec_grp[1]),
                                          self.decode_stage_inst[row_index].get_pin("in3"))
                        row_index = row_index + 1

    def route_vdd_gnd(self):
        """ Add a pin for each row of vdd/gnd which are must-connects next level up. """

        modules=[self.pre2x4_inst, self.pre3x8_inst, self.decode_stage_inst]
        for mod in modules:
            for num in range(len(mod)):
                vdd_pin = mod[num].get_pins("vdd")
                for pin in vdd_pin:
                    if (pin.layer == "m1pin" or pin.layer == "metal1"):
                        pin_layer = "metal1"
                    if (pin.layer == "m3pin" or pin.layer == "metal3"):
                        pin_layer = "metal3"
                    self.add_rect(layer=pin_layer,
                                  offset=(0, pin.ll().y),
                                  width=self.width,
                                  height=contact.m1m2.width)
                    self.add_layout_pin(text="vdd",
                                        layer=pin.layer,
                                        offset=(0, pin.ll().y),
                                        width=contact.m1m2.width,
                                        height=contact.m1m2.width)

                gnd_pin = mod[num].get_pins("gnd")
                for pin in gnd_pin:
                    if (pin.layer == "m1pin" or pin.layer == "metal1"):
                        pin_layer = "metal1"
                    if (pin.layer == "m3pin" or pin.layer == "metal3"):
                        pin_layer = "metal3"
                    self.add_rect(layer=pin_layer,
                                  offset=(0,pin.ll().y),
                                  width=self.width,
                                  height=contact.m1m2.width)
                    self.add_layout_pin(text="gnd",
                                        layer=pin.layer,
                                        offset=(0, pin.ll().y),
                                        width=contact.m1m2.width,
                                        height=contact.m1m2.width)
        
    def connect_rail(self, rail_index, pin):
        """ Connect the routing rail to the given metal1 pin  """
        rail_pos = vector(self.rail_x_offsets[rail_index],pin.lc().y)
        self.add_path("metal1", [rail_pos, (pin.uc().x, pin.lc().y)])
        self.add_via_center(self.m1_stack, rail_pos, rotate=90)
