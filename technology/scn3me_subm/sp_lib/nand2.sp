
.SUBCKT nand2 A B Z vdd gnd
M1 gnd A net1 gnd n w=2.4u l=0.6u 
M2 net1 B Z gnd n w=2.4u l=0.6u 
M3 vdd A Z vdd p w=2.4u l=0.6u 
M4 Z B vdd vdd p w=2.4u l=0.6u 
.ENDS nand2
