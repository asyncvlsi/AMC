import design
import debug
import contact
import math
from vector import vector
from pinv import pinv
from nand2 import nand2
from nand3 import nand3

class hierarchical_predecode(design.design):
    """ Pre 2x4 and 3x8 decoder shared code"""
    
    def __init__(self, input_number):
        self.num_in = input_number
        self.num_out = int(math.pow(2, self.num_in))
        design.design.__init__(self, name="pre{0}x{1}".format(self.num_in,self.num_out))
    
    def add_pins(self):
        """ Add pins for pre_decoder, order of the pins is important """

        for k in range(self.num_in):
            self.add_pin("in[{0}]".format(k))
        for i in range(self.num_out):
            self.add_pin("out[{0}]".format(i))
        self.add_pin_list(["vdd", "gnd"])

    def create_modules(self):
        """ Create the INV and NAND gate """
        
        self.inv = pinv()
        self.add_mod(self.inv)
        
        self.create_nand(self.num_in)
        self.add_mod(self.nand)

    def create_nand(self,inputs):
        """ Create the NAND for the predecode input stage """
        
        if inputs==2:
            self.nand = nand2()
        elif inputs==3:
            self.nand = nand3()
        else:
            debug.error("Invalid number of predecode inputs.",-1)
            
    def setup_constraints(self):
        
        # The rail offsets are indexed by the label
        self.rails = {}

        # Non inverted input rails
        for rail_index in range(self.num_in):
            xoffset = rail_index * self.m_pitch("m2") + 0.5*self.m2_width
            self.rails["in[{}]".format(rail_index)] = xoffset
        # x offset for input inverters
        self.x_off_inv_1 = self.num_in*self.m_pitch("m2") 
        
        # Creating the right hand side metal2 rails for output connections
        for rail_index in range(2 * self.num_in):
            xoffset = self.x_off_inv_1 + self.inv.width+((rail_index+1)*self.m_pitch("m2"))+\
                      0.5*self.m2_width
            if rail_index < self.num_in:
                self.rails["Abar[{}]".format(rail_index)] = xoffset
            else:
                self.rails["A[{}]".format(rail_index-self.num_in)] = xoffset

        # x offset to NAND decoder includes the left rails, mid rails and inverters, plus an extra m2 pitch
        self.x_off_nand = self.x_off_inv_1 + self.inv.width + (1+2*self.num_in) * self.m_pitch("m2")

                       
        # x offset to output inverters
        self.x_off_inv_2 = self.x_off_nand + self.nand.width

        # Height width are computed 
        self.width = self.x_off_inv_2 + self.inv.width
        self.height = self.num_out * self.nand.height

    def create_rails(self):
        """ Create all of the rails for the inputs and vdd/gnd/inputs_bar/inputs """
        
        for label in self.rails.keys():
            if label.startswith("in"):
                self.add_rect(layer="metal2",
                              offset=vector(self.rails[label]-0.5*self.m2_width, 0), 
                              width=self.m2_width,
                              height=self.height - 2*self.m2_space)
                self.add_layout_pin(text=label,
                                    layer=self.m2_pin_layer,
                                    offset=vector(self.rails[label]-0.5*self.m2_width, 0), 
                                    width=self.m2_width,
                                    height=self.m2_width)
            else:
                self.add_rect(layer="metal2",
                              offset=vector(self.rails[label]-0.5*self.m2_width, 0), 
                              width=self.m2_width,
                              height=self.height - 2*self.m2_space)

    def add_input_inverters(self):
        """ Create the input inverters to invert input signals for the decode stage. """

        self.in_inst = []
        for inv_num in range(self.num_in):
            name = "Xpre_inv[{0}]".format(inv_num)
            if (inv_num % 2 == 0):
                y_off = inv_num * (self.inv.height)
                mirror = "R0"
            else:
                y_off = (inv_num + 1) * (self.inv.height)
                mirror="MX"
            
            offset = vector(self.x_off_inv_1, y_off)
            self.in_inst.append(self.add_inst(name=name,
                                              mod=self.inv,
                                              offset=offset,
                                              mirror=mirror))
            self.connect_inst(["in[{0}]".format(inv_num),"inbar[{0}]".format(inv_num), "vdd", "gnd"])
            
    def add_output_inverters(self):
        """ Create inverters for the inverted output decode signals. """
        
        self.inv_inst = []
        for inv_num in range(self.num_out):
            name = "Xpre_nand_inv[{}]".format(inv_num)
            if (inv_num % 2 == 0):
                y_off = inv_num * self.inv.height
                mirror = "R0"
            else:
                y_off =(inv_num + 1)*self.inv.height
                mirror = "MX"
            
            offset = vector(self.x_off_inv_2, y_off)   
            self.inv_inst.append(self.add_inst(name=name,
                                               mod=self.inv,
                                               offset=offset,
                                               mirror=mirror))
            self.connect_inst(["Z[{}]".format(inv_num), "out[{}]".format(inv_num), "vdd", "gnd"])

    def add_nand(self,connections):
        """ Create the NAND stage for the decodes """
        
        self.nand_inst = []        
        for nand_input in range(self.num_out):
            inout = str(self.num_in)+"x"+str(self.num_out)
            name = "Xpre{0}_nand[{1}]".format(inout,nand_input)
            if (nand_input % 2 == 0):
                y_off = nand_input * self.inv.height
                mirror = "R0"
            else:
                y_off = (nand_input + 1) * self.inv.height
                mirror = "MX"
            
            offset = vector(self.x_off_nand, y_off)
            self.nand_inst.append(self.add_inst(name=name,
                                                mod=self.nand,
                                                offset=offset,
                                                mirror=mirror))
            self.connect_inst(connections[nand_input])
            

    def route(self):
        """ Route between inverters and nand gates """
        
        self.route_input_inverters()
        self.route_inputs_to_rails()
        self.route_nand_to_rails()
        self.route_output_inverters()        
        self.route_vdd_gnd()

    def route_inputs_to_rails(self):
        """ Route the uninverted inputs to the second set of rails """
        
        pin = ["A", "B", "C"]
        for num in range(self.num_in):
            y_offset = self.num_out*self.inv.height-self.nand_inst[0].get_pin(pin[num]).lc().y
            in_pin = "in[{}]".format(num)            
            a_pin = "A[{}]".format(num)
            in_pos = vector(self.rails[in_pin],y_offset)
            a_pos = vector(self.rails[a_pin],y_offset)            
            
            self.add_path("metal1",[in_pos, a_pos])
            self.add_via_center(self.m1_stack, [self.rails[in_pin], y_offset], rotate=90)
            self.add_via_center(self.m1_stack,[self.rails[a_pin], y_offset], rotate=90)

    def route_output_inverters(self):
        """ Route all conections of the outputs inverters """
        for num in range(self.num_out):

            # route nand output to output inv input
            zr_pos = self.nand_inst[num].get_pin("Z").lc()
            al_pos = self.inv_inst[num].get_pin("A").rc()
            
            # ensure the bend is in the middle 
            mid1_pos = vector(0.5*(zr_pos.x+al_pos.x), zr_pos.y)
            mid2_pos = vector(0.5*(zr_pos.x+al_pos.x), al_pos.y)
            self.add_path("metal1", [zr_pos, mid1_pos, mid2_pos, al_pos])

            z_pos = self.inv_inst[num].get_pin("Z")
            self.add_layout_pin(text="out[{}]".format(num),
                                layer=self.m1_pin_layer,
                                offset=z_pos.ll(),
                                width=self.m1_width,
                                height=self.m1_width)

    
    def route_input_inverters(self):
        """ Route all conections of the inputs inverters (Inputs, outputs) """
        
        pin = ["A", "B", "C"]
        for inv_num in range(self.num_in):
            out_pin = "Abar[{}]".format(inv_num)
            in_pin = "in[{}]".format(inv_num)
            
            if inv_num%2:
                y_offset = (inv_num+1)*self.inv.height-self.nand_inst[0].get_pin(pin[inv_num]).lc().y
            else:
                y_offset = inv_num*self.inv.height+self.nand_inst[0].get_pin(pin[inv_num]).lc().y

            inv_out_pos = self.in_inst[inv_num].get_pin("Z").ur()
            if y_offset > self.in_inst[inv_num].get_pin("Z").ur().y:
                inv_out_pos = self.in_inst[inv_num].get_pin("Z").lr()
            
            rail_pos = vector(self.rails[out_pin],y_offset)
            self.add_path("metal1", [(inv_out_pos.x+0.5*self.m1_width, inv_out_pos.y), 
                                     (inv_out_pos.x+0.5*self.m1_width, y_offset), rail_pos])
            self.add_via_center(self.m1_stack, rail_pos, rotate=90)
            
            #route input
            inv_in_pos = self.in_inst[inv_num].get_pin("A").lc()
            in_pos = vector(self.rails[in_pin],inv_in_pos.y)
            self.add_path("metal1", [in_pos, inv_in_pos])
            self.add_via_center(self.m1_stack, in_pos, rotate=90)
            

    def route_nand_to_rails(self):
        """ This 2D array defines the connection mapping """ 
        
        nand_input_line_combination = self.get_nand_input_line_combination()
        for k in range(self.num_out):
            # create x offset list         
            index_lst= nand_input_line_combination[k]

            if self.num_in == 2:
                gate_lst = ["A","B"]
            else:
                gate_lst = ["A","B","C"]

            # this will connect pins A,B or A,B,C
            for rail_pin,gate_pin in zip(index_lst,gate_lst):
                pin_pos = self.nand_inst[k].get_pin(gate_pin).lc()
                rail_pos = vector(self.rails[rail_pin], pin_pos.y)
                self.add_path("metal1", [rail_pos, pin_pos])
                self.add_via_center(self.m1_stack, rail_pos, rotate=90)

    def route_vdd_gnd(self):
        """ Add a pin for each row of vdd/gnd which are must-connects next level up. """

        for num in range(0,self.num_out):
            # use the inverter offset even though it will be the nand's too
            
            (gate_offset, y_dir) = self.get_gate_offset(0, self.inv.height, num)

            vdd_offset = self.nand_inst[num].get_pin("vdd")
            self.add_rect(layer="metal1",
                          offset=vdd_offset.ll().scale(0,1),
                          width=self.inv_inst[num].rx(),
                          height = contact.m1m2.width)
            self.add_layout_pin(text="vdd",
                                layer=vdd_offset.layer,
                                offset=vdd_offset.ll().scale(0,1),
                                width=contact.m1m2.width,
                                height = contact.m1m2.width)

            gnd_offset = self.nand_inst[num].get_pin("gnd")
            self.add_rect(layer="metal1",
                          offset=gnd_offset.ll().scale(0,1),
                          width=self.inv_inst[num].rx(),
                          height = contact.m1m2.width)
            self.add_layout_pin(text="gnd",
                                layer=gnd_offset.layer,
                                offset=gnd_offset.ll().scale(0,1),
                                width=contact.m1m2.width,
                                height = contact.m1m2.width)
