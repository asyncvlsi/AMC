
.SUBCKT cell_6t bl br wl vdd gnd
M1 net_1 net_2 vdd vdd p w=0.9u l=1.2u 
M2 net_2 net_1 vdd vdd p w=0.9u l=1.2u 
M3 br wl net_2 gnd n w=1.2u l=0.6u 
M4 bl wl net_1 gnd n w=1.2u l=0.6u  
M5 net_2 net_1 gnd gnd n w=2.4u l=0.6u 
M6 net_1 net_2 gnd gnd n w=2.4u l=0.6u  
.ENDS cell_6t
