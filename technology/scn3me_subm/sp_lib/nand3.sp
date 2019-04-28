
.SUBCKT nand3 A B C Z vdd gnd
M1 gnd A net1 gnd n w=2.4u l=0.6u 
M2 net1 B net2 gnd n w=2.4u l=0.6u 
M3 net2 C Z gnd n w=2.4u l=0.6u 
M4 vdd A Z vdd p w=2.4u l=0.6u 
M5 Z B vdd vdd p w=2.4u l=0.6u 
M6 vdd C Z vdd p w=2.4u l=0.6u 
.ENDS nand3
