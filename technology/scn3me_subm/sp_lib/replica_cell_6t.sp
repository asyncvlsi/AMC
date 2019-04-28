
.SUBCKT replica_cell_6t bl br wl vdd gnd
M1 gnd net_2 vdd vdd p w=0.9u l=1.2u 
M2 net_2 gnd vdd vdd p w=0.9u l=1.2u 
M3 br wl net_2 gnd n w=1.2u l=0.6u 
M4 bl wl gnd gnd n w=1.2u l=0.6u  
M5 net_2 gnd gnd gnd n w=2.4u l=0.6u 
M6 gnd net_2 gnd gnd n w=2.4u l=0.6u  
.ENDS replica_cell_6t
