# BSD 3-Clause License (See LICENSE.OR for licensing information)
# Copyright (c) 2016-2019 Regents of the University of California 
# and The Board of Regents for the Oklahoma Agricultural and 
# Mechanical College (acting for and on behalf of Oklahoma State University)
# All rights reserved.


import design
import debug
import contact
import utils
from tech import drc
from vector import vector
from pinv import pinv

class delay_chain(design.design):
    """ Generate a delay chain with the given number of stages and fanout.
        This automatically adds an extra inverter with no load on the input.
        Input is a list contains the electrical effort of each stage. """

    def __init__(self, fanout_list, name="delay_chain"):
        design.design.__init__(self, name)

        for f in fanout_list:
            debug.check(f>0,"Must have non-zero fanouts for each stage.")

        # number of inverters including any fanout loads.
        self.fanout_list = fanout_list
        self.num_invs = 1 + sum(fanout_list)
        
        self.inv = pinv()
        self.add_mod(self.inv)

        self.add_pins()
        self.create_module()
        self.route_inv()
        self.add_layout_pins()
        orgin = vector(-self.m1_minarea/contact.m1m2.width, 0)
        self.translate_all(orgin)

    def add_pins(self):
        """ Add pins for delay_chain, order of the pins is important """
        
        self.add_pin_list(["in", "out", "vdd", "gnd"])

    def create_module(self):
        """ Add the inverter logical module """

        self.create_inv_list()
        self.shift = max(self.m1_space, self.implant_space, drc["extra_to_extra"])
        self.width = self.num_invs*self.inv.width + (self.num_invs-1)*self.shift +\
                     self.m1_minarea/contact.m1m2.width
        self.height = self.inv.height
        self.add_inv_list()
        
    def create_inv_list(self):
        """ Generate a list of inverters. Each inverter has a stage number and a flag indicating 
            if it is a dummy load. This is the order that they will get placed too. """
        
        # First stage is always 0 and is not a dummy load
        self.inv_list=[[0,False]]
        for stage_num, fanout_size in zip(range(len(self.fanout_list)), self.fanout_list):
            for i in range(fanout_size-1):
                # Add the dummy loads
                self.inv_list.append([stage_num+1, True])
                
            # Add the gate to drive the next stage
            self.inv_list.append([stage_num+1, False])

    def add_inv_list(self):
        """ Add the inverters and connect them based on the stage list """
        
        dummy_load_counter = 1
        self.inv_inst_list = []
        
        for i in range(self.num_invs):
            inv_offset = vector(i*(self.inv.width+self.shift),0)
            cur_inv=self.add_inst(name="dinv{}".format(i),
                                  mod=self.inv,
                                  offset=inv_offset)
            
            # keep track of the inverter instances so we can use them to get the pins
            self.inv_inst_list.append(cur_inv)

            cur_stage = self.inv_list[i][0]
            next_stage = self.inv_list[i][0]+1
            if i == 0:
                input = "in"
            else:
                input = "s{}".format(cur_stage)
            if i == self.num_invs-1:
                output = "out"
            else:                
                output = "s{}".format(next_stage)

            # if the gate is a dummy load don't connect the output else reset the counter
            if self.inv_list[i][1]: 
                output = output+"n{0}".format(dummy_load_counter)
                dummy_load_counter += 1
            else:
                dummy_load_counter = 1
                    
            self.connect_inst(args=[input, output, "vdd", "gnd"])
            self.add_rect(layer= "metal1", 
                          offset= cur_inv.get_pin("A").ul(),
                          width=(self.m1_minarea/contact.m1m2.first_layer_height),
                          height=-contact.m1m2.first_layer_height)
    
    def route_inv(self):
        """ Add metal routing for each of the fanout stages """
        
        start_inv = end_inv = 0
        yshift = self.via_shift("v1")+contact.m1m2.width+0.5*self.m2_width
        
        for fanout in self.fanout_list:
            # end inv number depends on the fan out number
            
            end_inv = start_inv + fanout
            start_inv_inst = self.inv_inst_list[start_inv]

            # route from output to first load
            start_inv_pin = start_inv_inst.get_pin("Z")
            load_inst = self.inv_inst_list[start_inv+1]
            mid_pos=(start_inv_pin.rx()+self.m1_space, start_inv_pin.lc().y)
            load_pin = load_inst.get_pin("A").lc()+vector(contact.m1m2.height, 0)
            
            self.add_path("metal1", [start_inv_pin.lc(), mid_pos, load_pin], width=self.m1_space)
            
            next_inv = start_inv+2
            while next_inv <= end_inv:
                
                prev_load_inst = self.inv_inst_list[next_inv-1]
                prev_load_pin = vector(prev_load_inst.get_pin("A").lc().x, 
                                       prev_load_inst.get_pin("Z").by()- yshift)
                load_inst = self.inv_inst_list[next_inv]
                
                load_pin = vector(load_inst.get_pin("A").lc().x+contact.m1m2.height,
                                  load_inst.get_pin("Z").by()- yshift)
                self.add_path("metal2", [prev_load_pin, load_pin])
                
                xshift = vector(-contact.m1m2.height, 0.5*contact.m1m2.width)
                self.add_via(self.m1_stack,self.inv_inst_list[next_inv-1].get_pin("A").ll()-xshift, rotate=90)
                
                self.add_via(self.m1_stack, self.inv_inst_list[next_inv].get_pin("A").ll()-xshift, rotate=90)
                next_inv += 1

            # set the start of next one after current end
            start_inv = end_inv

    def add_layout_pins(self):
        """ Add vdd and gnd rails and the input/output. Connect the gnd rails internally on
             the top end with no input/output to obstruct."""

        extra_m1=self.m1_minarea/contact.m1m2.height
        vdd_pin = self.inv_inst_list[0].get_pin("vdd")
        gnd_pin = self.inv_inst_list[0].get_pin("gnd")
        self.add_rect(layer="metal1",
                      offset=vdd_pin.ll(),
                      width=self.width-contact.m1m2.height-extra_m1,
                      height=contact.m1m2.width)

        self.add_layout_pin(text="vdd",
                            layer=vdd_pin.layer,
                            offset=vdd_pin.ll(),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)

        self.add_rect(layer="metal1",
                      offset=gnd_pin.ll(),
                      width=self.width-contact.m1m2.height-extra_m1,
                      height=contact.m1m2.width)

        self.add_layout_pin(text="gnd",
                            layer=gnd_pin.layer,
                            offset=gnd_pin.ll(),
                            width=contact.m1m2.width,
                            height=contact.m1m2.width)
        
        # input is A pin of first inverter
        a_pin = self.inv_inst_list[0].get_pin("A")
        self.add_layout_pin(text="in",
                            layer=a_pin.layer,
                            offset=a_pin.ll(),
                            width=self.m1_width,
                            height=self.m1_width)

        # output is Z pin of last inverter
        z_pin = self.inv_inst_list[-1].get_pin("Z")
        pos1=(z_pin.lx()-0.5*self.m1_width, z_pin.lc().y)
        pos2=(z_pin.lx()-0.5*self.m1_width, 2*contact.m1m2.width)
        pos3=(-extra_m1, 2*contact.m1m2.width)
        self.add_path("metal2", [pos1, pos2, pos3])

       

        out_pin= vector(-contact.m1m2.height-extra_m1, 2*contact.m1m2.width-0.5*contact.m1m2.width)
        self.add_rect(layer="metal1",
                      offset=out_pin,
                      width=self.m1_minarea/contact.m1m2.width,
                      height=contact.m1m2.width)
        
        self.add_via(self.m1_stack,(-extra_m1,out_pin.y),rotate=90)
        
        self.add_layout_pin(text="out",
                            layer=self.m1_pin_layer,
                            offset=out_pin,
                            width=self.m1_width,
                            height=self.m1_width)
