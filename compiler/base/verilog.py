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

class verilog:
    """ Create a behavioral Verilog file for simulation."""

    
    def verilog_write(self,verilog_name):
        """ Write a behavioral Verilog model. """
        
        self.vf = open(verilog_name, "w")

        self.vf.write("// AMC SRAM model\n")
        self.vf.write("// Addr size: {0}\n".format(self.addr_size))
        self.vf.write("// Word size: {0}\n\n".format(self.word_size))
    
        self.vf.write("module {0}(data_in, data_out, addr, ".format(self.name))
        self.vf.write("reset, r, w,  rw, rreq, wreq, ack, rack, wack);\n")
        self.vf.write("\n")
        self.vf.write("  parameter DATA_WIDTH = {0} ;\n".format(self.word_size))
        self.vf.write("  parameter ADDR_WIDTH = {0} ;\n".format(self.addr_size))
        self.vf.write("  parameter RAM_DEPTH = 1 << ADDR_WIDTH;\n")
        self.vf.write("  parameter DELAY = 1 ;\n")
        self.vf.write("\n")    
        self.vf.write("  input [DATA_WIDTH-1:0] data_in;\n")
        self.vf.write("  output [DATA_WIDTH-1:0] data_out;\n")
        self.vf.write("  input [ADDR_WIDTH-1:0] addr;\n")
        self.vf.write("  input reset;            // active low reset\n")
        self.vf.write("  input r;                // active high read enable\n")
        self.vf.write("  input w;                // active high write enable\n")
        self.vf.write("  input rw;               // active high read_modify_write enable\n")
        self.vf.write("  input rreq;             // active high read_request\n")
        self.vf.write("  input wreq;             // active high write_request\n")
        self.vf.write("  output ack;             // address_acknowlede\n")
        self.vf.write("  output rack;            // read_acknowledge\n")
        self.vf.write("  output wack;            // write_acknowledge\n")
        self.vf.write("\n")
        self.vf.write("  reg ack;\n")
        self.vf.write("  reg rack;\n")
        self.vf.write("  reg wack;\n")
        self.vf.write("  reg wreqM;\n")
        self.vf.write("  reg [DATA_WIDTH-1:0] data_out;\n")
        self.vf.write("  reg [DATA_WIDTH-1:0] mem [0:RAM_DEPTH-1];\n")
        self.vf.write("  integer i;\n")
        self.vf.write("\n")
        self.vf.write("\n")    
        
        self.vf.write("  // Memory Reset Block\n")
        self.vf.write("  // Reset Operation : When reset = 1\n")
        self.vf.write("  always @ (posedge reset)\n")
        self.vf.write("  begin : MEM_RESET\n")
        self.vf.write("    for(i=0; i<2**{0}; i=i+1)\n".format(self.addr_size))
        self.vf.write("        mem[i] = {0}'b0;\n".format(self.word_size))
        self.vf.write("    $display($time,\" Reseting MEM\");\n")
        self.vf.write("  end\n\n")
        self.vf.write("\n")    


        self.vf.write("  always @ (posedge ack) begin\n")
        self.vf.write("        rack <= #(DELAY) 1'b0;\n")
        self.vf.write("        wack <= #(DELAY) 1'b0;\n")
        self.vf.write("        ack <= #(DELAY) 1'b0;\n")
        self.vf.write("  end\n\n")


        self.vf.write("  // Memory Write Block\n")
        self.vf.write("  // Write Operation : When wreq = 1\n")
        self.vf.write("  always @ (posedge (w || wreqM))\n")
        self.vf.write("  if (!reset) begin : MEM_WRITE\n")
        self.vf.write("  if ((w && wreq) || (rw && wreqM)) begin\n")
        self.vf.write("    mem[addr] = data_in;\n")
        self.vf.write("    wack <= #(DELAY) 1'b1;\n")
        self.vf.write("    ack <= #(DELAY) 1'b1;\n")
        self.vf.write("    $display($time,\" Writing %m ADDR=%b DATA_IN=%b\",addr,data_in);\n")
        self.vf.write("  end\n")
        self.vf.write("  end\n\n")
        self.vf.write("\n")    
        
        self.vf.write("  // Memory Read Block\n")
        self.vf.write("  // Read Operation : When rreq = 1\n")
        self.vf.write("  always @ (posedge (r || rw))\n")
        self.vf.write("  if (!reset) begin : MEM_READ\n")
        self.vf.write("  if ((r || rw) && rreq) begin\n")
        self.vf.write("    data_out <= #(DELAY) mem[addr];\n")
        self.vf.write("    rack <= #(DELAY) 1'b1;\n")
        self.vf.write("    $display($time,\" reading %m ADDR=%b DATAOUT=%b\",addr,data_out);\n")
        self.vf.write("    if (rw) begin\n")
        self.vf.write("        wreqM <= #(DELAY) 1'b1;\n")
        self.vf.write("    end\n")
        self.vf.write("    if (r) begin\n")
        self.vf.write("        ack <= #(DELAY) 1'b1;\n")
        self.vf.write("    end\n")
        self.vf.write("  end\n")
        self.vf.write("  end\n\n")
        self.vf.write("\n")    
        self.vf.write("\n")    
        self.vf.write("endmodule\n")
        self.vf.close()
