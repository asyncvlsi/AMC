
.SUBCKT single_driver in1 out in0 vdd gnd
M1 gnd in1 net1 gnd n w=2.4u l=0.6u 
M2 net1 in0 z gnd n w=2.4u l=0.6u 
M3 vdd in1 z vdd p w=2.4u l=0.6u 
M4 z in0 vdd vdd p w=2.4u l=0.6u
M5 gnd z out gnd n w=2.4u l=0.6u  
M6 vdd z out vdd p w=4.8u l=0.6u 
.ENDS single_driver
