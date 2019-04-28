
.SUBCKT nor2 A B Z vdd gnd
M1 gnd A Z gnd n w=1.2u l=0.6u 
M2 Z B gnd gnd n w=1.2u l=0.6u 
M3 vdd A net1 vdd p w=2.4u l=0.6u 
M4 net1 B Z vdd p w=2.4u l=0.6u 
.ENDS nor2
