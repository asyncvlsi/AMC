
.SUBCKT write_complete bl br en write_complete vdd gnd
M1 net1 bl write_complete vdd p w=3.6u l=0.6u
M2 net1 br write_complete vdd p w=3.6u l=0.6u
M3 write_complete en_b gnd gnd n w=2.4u l=0.6u
M4 net1 en_b vdd vdd p w=2.4u l=0.6u
M5 en_b en gnd gnd n w=1.2u l=0.6u
M6 en_b en vdd vdd p w=2.4u l=0.6u
.ENDS write_complete
