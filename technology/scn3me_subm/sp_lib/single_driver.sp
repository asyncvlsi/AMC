
.SUBCKT single_driver in0 in1 in2 in3 out0 out1 out2 out3 en vdd gnd
M3 gnd en in4 gnd n l=0.6u w=2.4u
M4 in4 in0 z0 gnd n l=0.6u w=2.4u
M5 vdd in0 z0 vdd p l=0.6u w=2.4u
M6 z0 en vdd vdd p l=0.6u w=2.4u
M7 gnd en in5 gnd n l=0.6u w=2.4u
M8 in5 in1 z1 gnd n l=0.6u w=2.4u
M9 vdd in1 z1 vdd p l=0.6u w=2.4u
M10 z1 en vdd vdd p l=0.6u w=2.4u
M11 gnd en in6 gnd n l=0.6u w=2.4u
M12 in6 in2 z2 gnd n l=0.6u w=2.4u
M13 vdd in2 z2 vdd p l=0.6u w=2.4u
M14 z2 en vdd vdd p l=0.6u w=2.4u
M15 gnd en in7 gnd n l=0.6u w=2.4u
M16 in7 in3 z3 gnd n l=0.6u w=2.4u
M17 vdd in3 z3 vdd p l=0.6u w=2.4u
M18 z3 en vdd vdd p l=0.6u w=2.4u
M19 out0 z0 gnd gnd n l=0.6u w=1.2u m=2
M20 out0 z0 vdd vdd p l=0.6u w=2.4u m=2
M21 out1 z1 gnd gnd n l=0.6u w=1.2u m=2
M22 out1 z1 vdd vdd p l=0.6u w=2.4u m=2
M23 out2 z2 gnd gnd n l=0.6u w=1.2u m=2
M24 out2 z2 vdd vdd p l=0.6u w=2.4u m=2
M25 out3 z3 gnd gnd n l=0.6u w=1.2u m=2
M26 out3 z3 vdd vdd p l=0.6u w=2.4u m=2
.ENDS wordline_driver
