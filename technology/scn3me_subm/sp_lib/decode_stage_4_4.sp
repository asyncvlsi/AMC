
.SUBCKT decode_stage_4_4 in0 in1 in2 in3 out0 out1 out2 out3 vdd gnd
M00 gnd in3 net01 gnd n w=2.4u l =0.6u
M01 net01 in0 z0 gnd n w=2.4u l =0.6u
M02 gnd z0 out0 gnd n w=1.2u l =0.6u
M03 vdd in3 z0 vdd p w=2.4u l =0.6u
M04 z0 in0 vdd vdd p w=2.4u l =0.6u
M05 vdd z0 out0 vdd p w=2.4u l =0.6u
M10 gnd in2 net11 gnd n w=2.4u l =0.6u
M11 net11 in0 z1 gnd n w=2.4u l =0.6u
M12 gnd z1 out1 gnd n w=1.2u l =0.6u
M13 vdd in2 z1 vdd p w=2.4u l =0.6u
M14 z1 in0 vdd vdd p w=2.4u l =0.6u
M15 vdd z1 out1 vdd p w=2.4u l =0.6u
M20 gnd in2 net21 gnd n w=2.4u l =0.6u
M21 net21 in1 z2 gnd n w=2.4u l =0.6u
M22 gnd z2 out2 gnd n w=1.2u l =0.6u
M23 vdd in1 z2 vdd p w=2.4u l =0.6u
M24 z2 in2 vdd vdd p w=2.4u l =0.6u
M25 vdd z2 out2 vdd p w=2.4u l =0.6u
M30 gnd in3 net31 gnd n w=2.4u l =0.6u
M31 net31 in1 z3 gnd n w=2.4u l =0.6u
M32 gnd z3 out3 gnd n w=1.2u l =0.6u
M33 vdd in3 z3 vdd p w=2.4u l =0.6u
M34 z3 in1 vdd vdd p w=2.4u l =0.6u
M35 vdd z3 out3 vdd p w=2.4u l =0.6u
.ENDS decode_stage_4_4
