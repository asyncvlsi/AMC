
.SUBCKT nor3 A B C Z vdd gnd
M1 gnd A Z gnd n w=1.2u l=0.6u 
M2 Z B gnd gnd n w=1.2u l=0.6u 
M3 gnd C Z gnd n w=1.2u l=0.6u 
M4 vdd C net1 vdd p w=3.6u l=0.6u 
M5 net1 B net2 vdd p w=3.6u l=0.6u 
M6 net2 A Z vdd p w=3.6u l=0.6u 
.ENDS nor3
