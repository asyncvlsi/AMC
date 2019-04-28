
.SUBCKT write_complete bl br en write_complete vdd gnd
M1 net1 bl net2 vdd p w=3.6u l=0.6u
M2 net1 br net2 vdd p w=3.6u l=0.6u
M3 net2 en gnd gnd n w=2.4u l=0.6u
M4 net1 en vdd vdd p w=2.4u l=0.6u
M5 write_complete net1 gnd gnd n w=1.2u l=0.6u
M6 write_complete net1 vdd vdd p w=2.4u l=0.6u
.ENDS write_complete
