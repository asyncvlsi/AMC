
.SUBCKT xor2 A B Z vdd gnd
M1 gnd A net1 gnd n l=0.6u w=2.4u
M2 net1 B Z1 gnd n l=0.6u w=2.4u
M3 vdd A Z1 vdd p l=0.6u w=1.2u
M4 Z1 B vdd vdd p l=0.6u w=1.2u
M5 gnd Z1 net2 gnd n l=0.6u w=2.4u
M6 net2 B Z2 gnd n l=0.6u w=2.4u
M7 vdd Z1 Z2 vdd p l=0.6u w=1.2u
M8 Z2 B vdd vdd p l=0.6u w=1.2u
M9 gnd Z1 net3 gnd n l=0.6u w=2.4u
M10 net3 A Z3 gnd n l=0.6u w=2.4u
M11 vdd Z1 Z3 vdd p l=0.6u w=1.2u
M12 Z3 A vdd vdd p l=0.6u w=1.2u
M13 gnd Z3 net4 gnd n l=0.6u w=2.4u
M14 net4 Z2 Z gnd n l=0.6u w=2.4u
M15 vdd Z2 Z vdd p l=0.6u w=1.2u
M16 Z Z3 vdd vdd p l=0.6u w=1.2u
.ENDS xor2
