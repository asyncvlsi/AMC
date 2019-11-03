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
from math import ceil
from tech import spice
from vector import vector
from delay_chain import delay_chain
from nand2 import nand2
from nor2 import nor2
from pinv import pinv
from frequency_divider import frequency_divider
from starter_stopper import starter_stopper


class oscillator(design.design):
    """ Dynamically generated a stopable ring oscillator with variable frequency"""

    def __init__(self, delay, name="oscillator"):
        """ Constructor """

        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.delay = delay
        
        self.create_layout()
        
        self.width= self.dc2_inst[self.stage-1].rx()+9*self.m_pitch("m1")
        self.height=max(self.dc2_inst[self.stage-1].uy(), self.freq_div_inst.uy())-\
                    self.dc1_inst[self.stage-1].by()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.calculate_delay_chain_stages(self.delay)
        self.create_modules()
        self.add_modules()
        self.connect_modules()
        self.add_layout_pins()
        
    def add_pins(self):
        """ Adds pins for oscillator module """
        
        self.add_pin_list(["reset", "test", "finish", "clk", "clk1", "clk2", "clk3", "vdd", "gnd"])

    def calculate_delay_chain_stages(self, delay):
        """ calculate the number of inv in delay_chain based on input access-delay """
        
        num_inv = int(ceil(delay /spice["inv_delay"]))
        #number of inverter stages
        self.stage= int(ceil(num_inv / 10))
        
        self.fanout_list=[]
        self.fanout_list2=[]
        for i in range(10):
            self.fanout_list.append(1)
        
        #odd number of inv for correct polarity
        if self.stage % 2:
            self.fanout_list2=self.fanout_list
        else:
            for i in range(11):
                self.fanout_list2.append(1)
        
        #This is a offset in x-direction for input pins
        self.gap = max(self.well_space, self.implant_space, self.m_pitch("m1"))
        
    def create_modules(self):
        """ construct all the required modules """
        
        self.nand2 = nand2()
        self.add_mod(self.nand2)
        
        self.nor2 = nor2()
        self.add_mod(self.nor2)

        self.inv1 = pinv(size=1)
        self.add_mod(self.inv1)

        self.inv5 = pinv(size=5)
        self.add_mod(self.inv5)
        
        self.freq_div= frequency_divider()
        self.add_mod(self.freq_div)
        
        self.dc=delay_chain(fanout_list=self.fanout_list, name="delay_chain1")
        self.add_mod(self.dc)
        
        self.dc2=delay_chain(fanout_list=self.fanout_list2, name="delay_chain2")
        self.add_mod(self.dc2)
        
        self.start_stop=starter_stopper()
        self.add_mod(self.start_stop)
        

    def add_modules(self):
        """ Adds all modules in the following order"""
        
        self.add_or_gate()
        self.add_pulse_generator()
        self.add_starter_stopper()
        self.add_ring()
        self.add_frequency_divider()
    
    def connect_modules(self):
        """ Route modules """
        
        self.pulse_generator_connections()
        self.connect_stages_of_ring()
        self.connect_pulse_generator_to_starter()
        self.connect_starter_stopper_to_ring()
        self.connect_reset_inputs()
        self.connect_ring_to_or_gate()
        self.connect_vdd_gnd()

    def add_or_gate(self):
        """ Add nor2+inv to gate output of oscillator with reset signal and feedback as input """
        
        self.nor_inst= self.add_inst(name="nor2", mod=self.nor2, offset=(0,0))
        self.connect_inst(["reset", "osc1", "q", "vdd", "gnd"])
        
        self.inv1_inst= self.add_inst(name="inv1", mod=self.inv1, offset=(self.nor2.width,0))
        self.connect_inst(["q", "reset1", "vdd", "gnd"])

    
    def add_pulse_generator(self):
        """ Add nand2+inv and delay chain to generate an edge to pulse generator """
        
        self.inv2_inst= self.add_inst(name="inv2", mod=self.inv1,
                                      offset=self.inv1_inst.lr()+vector(self.gap,0))
        self.connect_inst(["reset1", "reset_b", "vdd", "gnd"])
        
        pos1=self.inv2_inst.get_pin("A").lc()
        pos3=self.inv1_inst.get_pin("Z").lc()
        pos2=vector(pos1.x-self.m1_width, pos1.y)
        self.add_path("metal1", [pos1, pos2, pos3])

        
        # NAND gate to make a pulse from REST signal and delayed-reset
        self.nand_inst= self.add_inst(name="nand2", mod=self.nand2,
                                      offset=(self.inv2_inst.rx(),0))
        self.connect_inst(["delayed_reset", "reset_b", "z", "vdd", "gnd"])
        
        
        self.inv3_inst= self.add_inst(name="inv3", mod=self.inv5,
                                      offset=(self.nand_inst.rx(),0))
        self.connect_inst(["z", "out", "vdd", "gnd"])
        
        #DELAY-CHAIN1 to make the delayed-reset signal
        #DELAY-CHAIN1 is broken to several stages for better floor-panning
        self.dc1_inst={}
        x_off=self.inv2_inst.rx()+4*self.m_pitch("m1")
        for i in range(self.stage-1):
            if i%2:
                mirror="R0"
                y_off=(i+2)*self.inv1.height
            else:
                mirror="MX"
                y_off=(i+1)*self.inv1.height
            self.dc1_inst[i]=self.add_inst(name="dc1{0}".format(i+1),
                                           mod=self.dc,
                                           offset=(x_off, -self.gap-contact.m1m2.width-y_off),
                                           mirror=mirror)
            if i==0:
                self.connect_inst(["reset_b", "w{0}".format(i+1), "vdd", "gnd"])
            else:
                self.connect_inst(["w{0}".format(i), "w{0}".format(i+1), "vdd", "gnd"])


        if self.stage%2:
            mirror="MX"
            y_off=self.stage*self.inv1.height
        else:
            mirror="R0"
            y_off=(self.stage+1)*self.inv1.height

        self.dc1_inst[self.stage-1]=self.add_inst(name="dc1{0}".format(self.stage+1),
                                                  mod=self.dc2,
                                                  offset=(x_off, -self.gap-contact.m1m2.width-y_off),
                                                  mirror=mirror)
        self.connect_inst(["w{0}".format(self.stage-1), "delayed_reset", "vdd", "gnd"])
            
    
    def add_starter_stopper(self):
        """ Add starter_stopper module. Oscillation starts when test=1 and reset=0 and ends when finish=1"""
        
        self.start_stop_inst=self.add_inst(name="start_stop",
                                           mod=self.start_stop,
                                           offset=(0,self.inv1.height+self.gap+self.m_pitch("m1")))
        self.connect_inst(["out", "z0", "test", "reset", "finish", "vdd", "gnd"])

    def add_ring(self):
        """ create ring oscillator with delay chain  """

        self.dc2_inst={}
        x_off=max(self.start_stop_inst.rx(), self.inv3_inst.rx())+4*self.m_pitch("m1")
        for i in range(self.stage-1):
            if i%2:
                mirror="R0"
                y_off=i*self.inv1.height
            else:
                mirror="MX"
                y_off=(i+1)*self.inv1.height
            self.dc2_inst[i]=self.add_inst(name="dc2{0}".format(i+1),
                                           mod=self.dc,
                                           offset=(x_off, self.inv1.height+y_off),
                                           mirror=mirror)
            self.connect_inst(["z{0}".format(i), "z{0}".format(i+1), "vdd", "gnd"])

        if self.stage%2:
            mirror="MX"
            y_off=self.stage*self.inv1.height
        else:
            mirror="R0"
            y_off=(self.stage-1)*self.inv1.height

        self.dc2_inst[self.stage-1]=self.add_inst(name="dc2{0}".format(self.stage+1),
                                                  mod=self.dc2,
                                                  offset=(x_off, self.inv1.height+y_off),
                                                  mirror=mirror)
        self.connect_inst(["z{0}".format(self.stage-1), "osc1", "vdd", "gnd"])

    def add_frequency_divider(self):
        """ Add two frequency dividers to get Fclk2 = Fclk/2 (clk2_b = clk1) and Fclk3=Fclk/2  """
        
        y_off = max(self.dc2_inst[self.stage-1].uy(), self.start_stop_inst.uy())+3*self.m_pitch("m1")
        self.min_xoff = -7*self.m_pitch("m1")
        self.freq_div_inst=self.add_inst(name="freq_div",
                                         mod=self.freq_div,
                                         offset=(self.min_xoff, self.inv1.height+y_off))
        self.connect_inst(["osc1", "clk", "clk1", "clk2", "clk3", "reset", "vdd", "gnd"])
            

    def pulse_generator_connections(self):
        """ Routing of input and output pins of pulse generator"""

        #connect output of inv1 to input B of nand2
        pin = self.nand_inst.get_pin("B").lc()
        self.add_path("metal1",[(pin.x-self.m1_space, pin.y), pin])

        #connect output of inv1 to input of delay-chain1
        pos1=self.dc1_inst[0].get_pin("in").lc()
        pos4=self.inv2_inst.get_pin("Z").lc()
        pos2=vector(pos4.x-2*self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack,[pos1,pos2,pos3])

        #connect output of delay-chain1 to input A of nand2
        pos1=self.dc1_inst[self.stage-1].get_pin("out").lc()
        pos2=vector(self.nand_inst.lx()+0.5*self.m2_width, pos1.y)
        pos3=vector(pos2.x, self.nand_inst.get_pin("A").uc().y)
        self.add_wire(self.m1_stack,[pos1, pos2, pos3])
        
        off = self.nand_inst.get_pin("A").ll()+vector(contact.m1m2.height,0)
        self.add_via(self.m1_stack, off , rotate=90)
       
    def connect_stages_of_ring(self):
        """ Connect output of each stage to input of next stage in delay_chains (dc1 and dc2) """

        for i in range(self.stage-1):
            pos1=self.dc2_inst[i].get_pin("out").lc()
            if i%2:
                pos2=vector(pos1.x-2*self.m_pitch("m1"), pos1.y)
            else:
                pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
            pos4=self.dc2_inst[i+1].get_pin("in").lc()
            pos3=vector(pos2.x, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

        for i in range(self.stage-1):
            pos1=self.dc1_inst[i].get_pin("out").lc()
            if i%2:
                pos2=vector(pos1.x-2*self.m_pitch("m1"), pos1.y)
            else:
                pos2=vector(pos1.x-self.m_pitch("m1"), pos1.y)
            pos4=self.dc1_inst[i+1].get_pin("in").lc()
            pos3=vector(pos2.x, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        

    def connect_pulse_generator_to_starter(self):
        """ Connect output of pulse generator to input of starter_stopper module  """

        pos1=self.inv3_inst.get_pin("Z").lc()
        pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x,self.inv3_inst.uy()+ self.m_pitch("m1"))
        pos5=self.start_stop_inst.get_pin("in").lc()
        pos4=vector(pos5.x-self.m_pitch("m1"), pos3.y)
        self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4, pos5] )

    def connect_starter_stopper_to_ring(self):
        """ Connect output of starter_stopper module to input of delay_chain2 (dc2, first stage)  """

        pos1=self.start_stop_inst.get_pin("out").lc()
        pos3=self.dc2_inst[0].get_pin("in").lc()
        pos2=vector(pos1.x, pos3.y)
        self.add_path("metal1",[pos1, pos2, pos3] )
    
    def connect_reset_inputs(self):
        """ Connect reset input of starter_stopper module to reset input of pulse_generator  """

        pos1=self.start_stop_inst.get_pin("reset").lc()
        pos2=vector(pos1.x-2*self.m_pitch("m1"), pos1.y)
        pos4=self.nor_inst.get_pin("A").lc()
        pos3=vector(pos2.x, pos4.y)
        self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4])
        
        pos1=self.freq_div_inst.get_pin("reset").lc()
        pos2=vector(-4*self.m_pitch("m1"), pos1.y)
        pos4=self.start_stop_inst.get_pin("reset").lc()
        pos4=(pos2.x, pos4.y)
        self.add_wire(self.m1_stack,[pos1, pos2, pos3, pos4])
    
    def connect_ring_to_or_gate(self):
        """ Connect output of buffer to nor gate input B This creates the feedback """

        #connect output of self.dc2_inst[self.stage-1] to input of nor gate
        
        pos1=self.nor_inst.get_pin("B").lc()
        pos2=vector(-3*self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.start_stop_inst.uy()+self.m_pitch("m1"))
        pos6=self.dc2_inst[self.stage-1].get_pin("out").lc()
        pos4=vector(pos6.x-4*self.m_pitch("m1"), pos3.y)
        pos5=vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])


        #connect output of self.dc2_inst[self.stage-1] to input of freq_div
        pos3=self.freq_div_inst.get_pin("in").uc()
        self.add_wire(self.m1_stack, [pos3, pos4, pos5, pos6])
        
    def connect_vdd_gnd(self):
        """ Connect vdd and gnd of all modules together and to power pins"""

        pins=["vdd", "gnd"]

        #connect vdd and gnd of dc1 stages together
        for i in range(self.stage-1,0,-1):
            for j in range(2):
                pos1=vector(self.dc1_inst[self.stage-1].rx(), 
                            self.dc1_inst[i].get_pin(pins[j]).lc().y)
                if j%2:
                    pos2=vector(pos1.x+2*self.m_pitch("m1"), pos1.y)
                else:
                    pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)

                pos4=vector(self.dc1_inst[i-1].lx(), self.dc1_inst[i-1].get_pin(pins[j]).lc().y)
                pos3=vector(pos2.x, pos4.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        #connect vdd and gnd of dc2 stages together
        for i in range(self.stage-1,0,-1):
            for j in range(2):
                pos1=vector(self.dc2_inst[self.stage-1].rx(), 
                            self.dc2_inst[i].get_pin(pins[j]).lc().y)
                if j%2:
                    pos2=vector(pos1.x+2*self.m_pitch("m1"), pos1.y)
                else:
                    pos2=vector(pos1.x+self.m_pitch("m1"), pos1.y)

                pos4=vector(self.dc2_inst[i-1].lx(), self.dc2_inst[i-1].get_pin(pins[j]).lc().y)
                pos3=vector(pos2.x, pos4.y)
                self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        #connect vdd and gnd of dc2[0] stage to dc1[0] vdd and gnd
        for i in range(2):
            pos1=vector(self.dc2_inst[self.stage-1].rx()+(i+1)*self.m_pitch("m1"), 
                        self.dc2_inst[0].get_pin(pins[i]).lc().y)
            pos3=self.dc1_inst[0].get_pin(pins[i]).lc()
            pos2=(pos1.x, pos3.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_via_center(self.m1_stack, pos1, rotate=90)
        
        #connect vdd and gnd of other modules to vdd and gnd pins
        modules=[self.nand_inst, self.start_stop_inst, self.dc1_inst[0]]
        for i in range(2):
            off =vector(-(i+6)*self.m_pitch("m1"), self.dc1_inst[self.stage-1].by())
            self.add_rect(layer="metal2",
                          offset= off,
                          width=self.m2_width,
                          height=self.freq_div_inst.uy() -self.dc1_inst[self.stage-1].by())
            self.add_layout_pin(text=pins[i],
                                layer=self.m2_pin_layer,
                                offset=(off.x, self.dc1_inst[0].by()),
                                width=self.m2_width,
                                height=self.m2_width)

            for mod in modules:
                off=vector(-(i+6)*self.m_pitch("m1"), mod.get_pin(pins[i]).lc().y-0.5*self.m1_width)
                width=mod.get_pin(pins[i]).lc().x-off.x
                self.add_rect(layer="metal1",
                              offset=off,
                              width=width,
                              height=self.m1_width)
                self.add_via(self.m1_stack, off)

    def add_layout_pins(self):
        """ Adds all input and ouput pins"""

        #input pins
        pins=["finish", "test", "reset"]
        for pin in pins:
            off=self.start_stop_inst.get_pin(pin)
            self.add_path("metal1", [(off.lx()+self.min_xoff, off.lc().y), off.lc()])
            self.add_layout_pin(text=pin,
                                layer=self.m1_pin_layer,
                                offset=(off.lx()+self.min_xoff, off.by()),
                                width=self.m1_width,
                                height=self.m1_width)

        #output pins
        pins=["clk", "clk1", "clk2", "clk3"]
        for pin in pins:
            off=self.freq_div_inst.get_pin(pin)
            self.add_path("metal1", [(off.lx(), off.lc().y), off.lc()])
            self.add_layout_pin(text=pin,
                                layer=self.m1_pin_layer,
                                offset=(off.lx(), off.by()),
                                width=self.m1_width,
                                height=self.m1_width)

