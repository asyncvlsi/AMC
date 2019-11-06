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

import sys
import datetime
import getpass
import design
from globals import OPTS, print_time
import debug
import contact
import math
from vector import vector
from fsm import fsm
from lfsr import lfsr
from comparator import comparator
from data_pattern import data_pattern
from oscillator import oscillator
from frequency_divider import frequency_divider
from pinv import pinv
from xor2 import xor2

class bist(design.design):
    """ Dynamically generated bist """

    def __init__(self, addr_size, data_size, delay = 0, async_bist = True, name="bist"):
        """ Constructor """

        design.design.name_map=[]
        start_time = datetime.datetime.now()
        design.design.__init__(self, name)
        debug.info(1, "Creating {}".format(name))

        self.addr_size = addr_size
        self.data_size = data_size
        self.delay = delay
        self.async_bist = async_bist
        
        self.create_layout()
        self.offset_all_coordinates()

    def create_layout(self):
        """ Create layout, route between modules and adding pins """
        
        self.add_pins()
        self.create_modules()
        self.setup_layout_constants()
        self.add_modules()
        self.connect_modules()
        self.add_layout_pins()
        self.width= self.max_xoff - self.min_xoff
        self.height=self.max_yoff - self.min_yoff 

    def add_pins(self):
        """ Adds pins for BIST module """
        
        for i in range(self.addr_size):
            self.add_pin("addr{0}".format(i),"INPUT")
        for i in range(self.data_size):
            self.add_pin("din{0}".format(i),"INPUT")
        for i in range(self.data_size):
            self.add_pin("dout{0}".format(i),"OUTPUT")
        
        self.add_pin_list(["reset", "r", "w", "test"],"INPUT")
        
        if not self.async_bist:
            self.add_pin("external_clk","INPUT")

        self.add_pin_list(["finish", "error"],"OUTPUT")
        
        self.add_pin("vdd","POWER")
        self.add_pin("gnd","GROUND")

    def create_modules(self):
        """ Construct all the required modules """
        
        self.lfsr = lfsr(size=self.addr_size, name="bist_lfsr")
        self.add_mod(self.lfsr)

        self.fsm = fsm()
        self.add_mod(self.fsm)
        
        self.xor2 = xor2()
        self.add_mod(self.xor2)

        self.inv = pinv()
        self.add_mod(self.inv)
        
        if self.async_bist:
            self.osc = oscillator(self.delay)
            self.add_mod(self.osc)
        
        else:
            self.osc = frequency_divider()
            self.add_mod(self.osc)

        self.data_pattern = data_pattern(self.data_size)
        self.add_mod(self.data_pattern)
        
        self.comparator = comparator(self.data_size)
        self.add_mod(self.comparator)
        
    def setup_layout_constants(self):
        """ Setup layout offsets, spaces, etc """

        #This is a gap between neighbor cell to avoid well/implant DRC violation
        self.gap= max(self.implant_space, self.well_space, self.m_pitch("m1"))

    def add_modules(self):
        """ Adds all modules in the following order"""

        self.add_lfsr()
        self.add_oscillator()
        self.add_fsm()
        self.add_data_pattern()
        self.add_comparator()
    
    def connect_modules(self):
        """ Route modules """

        self.connect_data_pattern_to_comparator()
        self.connect_comp_err_to_fsm()
        self.connect_lfsr_done_to_fsm_and_comparator()
        self.connect_data_enable_to_data_pattern()
        self.connect_up_down_to_lfsr()
        self.connect_reset_test()
        self.connect_clk()
        self.connect_vdd_gnd()

    def add_oscillator(self):
        """ Place ring oscillator """
        
        off = (self.osc.width, self.lfsr_inst.uy()+self.gap+9*self.m_pitch("m1"))
        self.osc_inst=self.add_inst(name="oscillator", mod=self.osc,
                                    offset=off, mirror="MY")
        if self.async_bist:
            self.connect_inst(["reset", "test", "finish", "clk", "clk1", "clk2", "clk3", "vdd", "gnd"])
        else:
            self.connect_inst(["external_clk", "clk", "clk1", "clk2", "clk3", "reset", "vdd", "gnd"])

    
    def add_lfsr(self):
        """ Place lfsr """
        
        if self.async_bist:
            x_off = self.osc.width-(self.xor2.width+self.inv.width+(self.addr_size+11)*self.m_pitch("m2")-\
                   (self.lfsr.width-self.osc.width))
        else:
            x_off = -(self.xor2.width+self.inv.width+(self.addr_size+11)*self.m_pitch("m2") -self.lfsr.width)

        self.lfsr_inst=self.add_inst(name="lfsr", mod=self.lfsr,
                                     offset=(x_off,0), mirror="MY")
        temp=[]
        for i in range(self.addr_size):
            temp.append("addr{0}".format(i))
        temp.extend(["up_down", "reset", "test", "lfsr_done", "clk1", "vdd", "gnd"])
        self.connect_inst(temp)
    
    def add_fsm(self):
        """ Place FSM """

        if self.async_bist:
            xoff = max(self.osc_inst.rx(),self.lfsr_inst.rx())+self.gap+12*self.m_pitch("m1")
        else:
            xoff = self.lfsr_inst.rx()+self.gap+10*self.m_pitch("m1")
        
        self.fsm_inst=self.add_inst(name="fsm", mod=self.fsm,
                                    offset=(xoff, self.lfsr_inst.uy()-self.fsm.height))
        self.connect_inst(["lfsr_done", "comp_err", "reset", "finish", "error", "up_down", 
                           "data_enable", "r", "w", "clk", "clk3", "clk2", "vdd", "gnd"])
    
    def add_data_pattern(self):
        """ Place data pattern generator """
        
        off = self.fsm_inst.ul()+ vector(self.m_pitch("m1"), self.gap+9*self.m_pitch("m1"))
        self.data_pattern_inst=self.add_inst(name="data_pattern", mod=self.data_pattern,
                                             offset= off)
        temp=[]
        for i in range(self.data_size):
            temp.append("din{0}".format(i))
        temp.extend(["data_enable", "vdd", "gnd"])
        self.connect_inst(temp)

    def add_comparator(self):
        """ Place comparator """
        
        off = self.data_pattern_inst.ur() +vector(0,(self.data_size+2)*self.m_pitch("m1"))
        self.comparator_inst=self.add_inst(name="comparator", mod=self.comparator,
                                           offset=off)
        temp=[]
        for i in range(self.data_size):
            temp.append("din{0}".format(i))
        for i in range(self.data_size):
            temp.append("dout{0}".format(i))

        temp.extend(["comp_err", "lfsr_done", "reset", "r", "clk1", "vdd", "gnd"])
        self.connect_inst(temp)


    def connect_data_pattern_to_comparator(self):
        """ connect outputs of data pattern to inputs of comparator """
        
        for i in range(self.data_size):
            pos1 = self.data_pattern_inst.get_pin("out{0}".format(i)).uc()
            pos2= vector(pos1.x, pos1.y+(i+1)*self.m_pitch("m1"))
            pos4=self.comparator_inst.get_pin("din{0}".format(i)).uc()
            pos3=vector(pos4.x, pos2.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

    def connect_comp_err_to_fsm(self):
        """ connect output 'err' from comparator to input 'comp_err' of FSM"""
        
        pos1 = self.comparator_inst.get_pin("err").lc()
        pos2= vector(self.comparator_inst.rx() + self.m_pitch("m1"), pos1.y)
        pos3=vector(pos2.x, self.data_pattern_inst.by() - self.m_pitch("m1"))
        pos6= self.fsm_inst.get_pin("comp").lc()
        pos4 = vector(pos6.x-self.m_pitch("m1"), pos3.y)
        pos5= vector(pos4.x, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])


    def connect_data_enable_to_data_pattern(self):
        """ connect output 'data0' and 'data1' from FSM to input of data pattern generator"""
        
        pos1 = self.fsm_inst.get_pin("data_enable").uc()
        pos2= vector(pos1.x, self.fsm_inst.uy()+3*self.m_pitch("m1"))
        pos5= self.data_pattern_inst.get_pin("enable").lc()
        pos3=vector(pos5.x-4*self.m_pitch("m1"),pos2.y)
        pos4=vector(pos3.x, pos5.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4,  pos5])


    def connect_lfsr_done_to_fsm_and_comparator(self):
        """ connect output 'lfsr_done' from lfsr to input 'lfsr' of fsm"""
        
        pos1 = self.lfsr_inst.get_pin("done").lc()
        pos2= vector(pos1.x - self.m_pitch("m1"), pos1.y)
        pos6= self.fsm_inst.get_pin("lfsr").lc()
        pos3=vector(pos2.x, min(self.fsm_inst.by(), self.lfsr_inst.by()-self.m_pitch("m1")))
        pos4=vector(pos6.x-2*self.m_pitch("m1"),pos3.y)
        pos5=vector(pos4.x, pos6.y)
        pos8=self.comparator_inst.get_pin("lfsr_done").lc()
        pos7 = vector(pos5.x, pos8.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4,  pos5, pos6])
        self.add_wire(self.m1_stack, [pos5, pos7, pos8])


    def connect_up_down_to_lfsr(self):
        """ connect output 'up_down' from fsm to input 'up_down' of lfsr"""
        
        pos1 = self.fsm_inst.get_pin("up_down").uc()
        pos2= vector(pos1.x, self.fsm_inst.uy()+2*self.m_pitch("m1"))
        pos4= self.lfsr_inst.get_pin("up_down").uc()
        pos3=vector(pos4.x, pos2.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])

    def connect_reset_test(self):
        """ Add input reset pin and connect it to reset input of all modules"""
        
        self.ctrl_xoff={}
        pin_list = ["reset", "test"]
        pin_yoff = min(self.lfsr_inst.by(),self.fsm_inst.by()) - 2*self.m_pitch("m1")
        
        for i in range(2):
            if self.async_bist:
                self.ctrl_xoff[i]=pin_xoff = max(self.lfsr_inst.rx(),self.osc_inst.rx())+\
                                             (i+1)*self.m_pitch("m1")
                height=max(self.comparator_inst.uy(), self.osc_inst.uy())
            else:
                self.ctrl_xoff[i]=pin_xoff = self.lfsr_inst.rx() + (i+1)*self.m_pitch("m1")
                height=self.comparator_inst.uy()

            self.add_path("metal2", [(pin_xoff, pin_yoff), (pin_xoff,height)])
            self.add_layout_pin(text=pin_list[i],
                                layer=self.m2_pin_layer,
                                offset=(pin_xoff-0.5*self.m2_width, pin_yoff),
                                width=self.m2_width,
                                height = self.m2_width)

        pos1= self.lfsr_inst.get_pin("reset").lc()
        pos2= self.fsm_inst.get_pin("reset").lc()
        mid_pos=vector(self.ctrl_xoff[0], pos1.y)
        
        if abs(pos1.y-pos2.y) < self.m_pitch("m1"):
            self.add_path("metal1", [pos1, mid_pos, pos2], width=contact.m1m2.width)
            self.add_via_center(self.m1_stack, mid_pos)
        else:
            self.add_wire(self.m1_stack, [pos1, mid_pos, pos2])
        
        if self.async_bist:
            
            #connect rest of osc to rest of comparator
            pos1= self.osc_inst.get_pin("reset").lc()
            pos2=vector(self.ctrl_xoff[0], pos1.y)
            pos3=vector(pos2.x, pos2.y-self.m_pitch("m1"))
            pos4=vector(self.ctrl_xoff[1]+7*self.m_pitch("m1"), pos3.y)
            pos6=self.comparator_inst.get_pin("reset").lc()
            pos5=vector(pos4.x, pos6.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5, pos6])
            
            #connect finish of fsm to finish of osc
            pos1 = self.fsm_inst.get_pin("fin").uc()
            pos2= vector(pos1.x, self.fsm_inst.uy()+5*self.m_pitch("m1"))
            pos5= self.osc_inst.get_pin("finish").lc()
            pos3=vector(self.ctrl_xoff[1]+6*self.m_pitch("m1"), pos2.y)
            pos4=vector(pos3.x, pos5.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4, pos5])

        else:
            pos1=self.osc_inst.get_pin("reset").lc()
            self.add_path("metal1", [pos1, (self.ctrl_xoff[0], pos1.y)])
            self.add_via_center(self.m1_stack,(self.ctrl_xoff[0], pos1.y))


            pos1=self.comparator_inst.get_pin("reset").lc()
            self.add_path("metal1", [pos1, (self.ctrl_xoff[0], pos1.y)])
            self.add_via_center(self.m1_stack,(self.ctrl_xoff[0], pos1.y))
        
        modules2=[self.lfsr_inst]
        if self.async_bist:
            modules2.append(self.osc_inst)
        for mod in modules2:
            pos1=mod.get_pin("test").lc()
            pos2=vector(self.ctrl_xoff[1], pos1.y)
            self.add_path("metal1", [pos1, pos2])
            self.add_via_center(self.m1_stack, pos2)

    def connect_clk(self):
        """ Connect clk to 'clk' input of all modules"""

        pin_yoff = min(self.lfsr_inst.by(), self.fsm_inst.by()) - 2*self.m_pitch("m1")
        clk_xoff = self.ctrl_xoff[1]+self.m_pitch("m1")
        if self.async_bist:
            height= max(self.comparator_inst.uy(), self.osc_inst.uy())
        else:
            height= self.comparator_inst.uy()
        self.add_path("metal2", [(clk_xoff, pin_yoff), (clk_xoff, height)])
        
        modules=[self.fsm_inst, self.osc_inst]
        for mod in modules:
            pos1=mod.get_pin("clk").lc()
            pos2=vector(clk_xoff, pos1.y)
            self.add_path("metal1", [pos1, pos2])
            self.add_via_center(self.m1_stack, pos2)

        if not self.async_bist:
            # Add an external clk pin
            external_clk_xoff = clk_xoff+self.m_pitch("m1")
            self.add_path("metal2", [(external_clk_xoff, pin_yoff), (external_clk_xoff, height)])
            
            pos1=self.osc_inst.get_pin("in").uc()
            pos2=vector(pos1.x, pos1.y-self.m2_width-self.m_pitch("m1"))
            pos3=vector(external_clk_xoff, pos2.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_via_center(self.m1_stack, pos3)
            
            self.add_layout_pin(text="external_clk",
                                layer=self.m2_pin_layer,
                                offset=(external_clk_xoff-0.5*self.m2_width, pin_yoff),
                                width=self.m2_width,
                                height = self.m2_width)


        #connect clk3 and clk2 to from oscillator to fsm
        pins=["clk2", "clk3"] 
        for i in range(2):
            xoff = clk_xoff + (i+2) * self.m_pitch("m1")
            pos1=self.fsm_inst.get_pin(pins[i]).lc()
            pos4=self.osc_inst.get_pin(pins[i]).lc()
            pos2=(xoff, pos1.y)
            pos3=(xoff, pos4.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        
        #connect clk1 to from oscillator to lfsr and comparator
        xoff = clk_xoff + 4 * self.m_pitch("m1")
        pos1=self.osc_inst.get_pin("clk1").lc()
        pos4=self.lfsr_inst.get_pin("clk").lc()
        pos6=self.comparator_inst.get_pin("clk").lc()
        pos2=(xoff, pos1.y)
        pos3=(xoff, pos4.y)
        pos5=(xoff, pos6.y)
        self.add_wire(self.m1_stack, [pos1, pos2, pos3, pos4])
        self.add_wire(self.m1_stack, [pos1, pos2, pos5, pos6])
        

    def connect_vdd_gnd(self):
        """ Connect clk to 'clk' input of all modules"""

        self.pow_yoff={}
        pin_list = ["vdd", "gnd"]
        if self.async_bist:
            self.min_xoff = min(self.lfsr_inst.lx(),self.lfsr_inst.lx()) - 2*self.m_pitch("m1")
        else:
            self.min_xoff = self.lfsr_inst.lx() - 2*self.m_pitch("m1")
        
        for i in range(2):
            self.pow_yoff[i] = pin_yoff = self.fsm_inst.uy() + (2*i+6)*self.m_pitch("m1")
            self.add_path("metal1", [(self.min_xoff, pin_yoff), (self.comparator_inst.rx(), pin_yoff)])
            self.add_layout_pin(text=pin_list[i],
                                layer=self.m1_pin_layer,
                                offset=(self.min_xoff, pin_yoff-0.5*self.m1_width),
                                width=self.m1_width,
                                height = self.m1_width)
        
        modules=[self.lfsr_inst, self.comparator_inst, self.fsm_inst, self.data_pattern_inst, self.osc_inst]
        for mod in modules:
            for i in range(2):
                pos1=mod.get_pin(pin_list[i]).uc()
                pos2=vector(pos1.x, self.pow_yoff[i])
                self.add_path("metal2", [pos1, pos2])
                self.add_via_center(self.m1_stack, pos2)

    def add_layout_pins(self):
        """ Add input, output and power pins """
        
        if self.async_bist:
            self.max_yoff = max(self.comparator_inst.uy(), self.osc_inst.uy())+2*self.m_pitch("m2")
        else:
            self.max_yoff = self.comparator_inst.uy()+2*self.m_pitch("m2")
        self.min_yoff = min (self.lfsr_inst.by(), self.fsm_inst.by())
        
        for i in range(self.data_size):
            pos = self.data_pattern_inst.get_pin("out{0}".format(i)).uc()
            self.add_path("metal2", [pos, (pos.x, self.max_yoff)])
            self.add_layout_pin(text="din{0}".format(i),
                                layer=self.m2_pin_layer,
                                offset=(pos.x-0.5*self.m2_width, self.max_yoff-self.m2_width),
                                width=self.m2_width,
                                height = self.m2_width)
        for i in range(self.data_size):
            pos = self.comparator_inst.get_pin("dout{0}".format(i)).uc()-vector(0, self.m2_width)
            self.add_path("metal2", [pos, (pos.x, self.max_yoff)])
            self.add_via_center(self.m2_stack, pos)
            self.add_layout_pin(text="dout{0}".format(i),
                                layer=self.m2_pin_layer,
                                offset=(pos.x-0.5*self.m2_width, self.max_yoff-self.m2_width),
                                width=self.m2_width,
                                height = self.m2_width)

        for i in range(self.addr_size):
            pos = self.lfsr_inst.get_pin("addr{0}".format(i)).uc()
            self.add_path("metal2", [pos, (pos.x, self.max_yoff)])
            self.add_layout_pin(text="addr{0}".format(i),
                                layer=self.m2_pin_layer,
                                offset=(pos.x-0.5*self.m2_width, self.max_yoff-self.m2_width),
                                width=self.m2_width,
                                height = self.m2_width)
        
        pin_list=["r", "w"]
        xoff = max(self.comparator_inst.rx(), self.fsm_inst.rx())
        for i in range(len(pin_list)):
            pos1 = self.fsm_inst.get_pin(pin_list[i]).lc()
            pos2 = vector(xoff+(i+2)*self.m_pitch("m1"), pos1.y)
            pos3 = vector(pos2.x, self.max_yoff)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_layout_pin(text=pin_list[i],
                                layer=self.m2_pin_layer,
                                offset=(pos2.x-0.5*self.m2_width, pos3.y-self.m2_width),
                                width=self.m2_width,
                                height = self.m2_width)


        #connect comparator input "R" to R pin
        pos1=self.comparator_inst.get_pin("r").lc()
        pos2=(xoff+2*self.m_pitch("m1"), pos1.y)
        self.add_path("metal1", [pos1, pos2])
        self.add_via_center(self.m1_stack, pos2)
        
        out_pin_list=["err", "fin"]
        out_pin_name=["error", "finish"]
        self.max_xoff = max(self.comparator_inst.rx(),self.fsm_inst.rx()) +\
                        self.m_pitch("m1")*(len(pin_list)+2)
        for i in range(2):
            pos1 = self.fsm_inst.get_pin(out_pin_list[i]).uc()
            pos2 = vector(pos1.x, self.fsm_inst.uy()+(i+11)*self.m_pitch("m1"))
            pos3 = vector(self.max_xoff, pos2.y)
            self.add_wire(self.m1_stack, [pos1, pos2, pos3])
            self.add_layout_pin(text=out_pin_name[i],
                                layer=self.m1_pin_layer,
                                offset=(pos3.x-self.m1_width, pos3.y-0.5*self.m1_width),
                                width=self.m1_width,
                                height = self.m1_width)

    def sp_write(self, sp_name):
        """ Write the entire spice of the object to the file """
        sp = open(sp_name, 'w')

        sp.write("**************************************************\n")
        sp.write("* AMC generated BIST.\n")
        sp.write("**************************************************\n")        
        usedMODS = list()
        self.sp_write_file(sp, usedMODS)
        del usedMODS
        sp.close()


    def save_output(self):
        """ Save spice, gds and lef files while reporting time to do it as well. """
        
        # Write spice 
        start_time = datetime.datetime.now()
        spname = OPTS.output_path + "AMC_BIST.sp"
        print("\n BIST SP: Writing to {0}".format(spname))
        self.sp_write(spname)
        print_time("BIST Spice writing", datetime.datetime.now(), start_time)

        
        # Write layout
        start_time = datetime.datetime.now()
        gdsname = OPTS.output_path + "AMC_BIST.gds"
        print("\n BIST GDS: Writing to {0}".format(gdsname))
        self.gds_write(gdsname)
        print_time("BIST GDS writing", datetime.datetime.now(), start_time)


        # Write lef 
        start_time = datetime.datetime.now()
        lefname = OPTS.output_path + "AMC_BIST.lef"
        print("\n BIST LEF: Writing to {0}".format(lefname))
        self.lef_write(lefname)
        print_time("LEF", datetime.datetime.now(), start_time)
