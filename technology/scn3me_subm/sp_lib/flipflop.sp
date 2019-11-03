
.SUBCKT dlatch din dout dout_bar clk clk_bar vdd gnd
M1 din clk int1 vdd p w=1.2u l=0.6u
M2 din clk_bar int1 gnd n w=1.2u l=0.6u
M3 dout_bar int1 vdd vdd p w=1.2u l=0.6u
M4 dout_bar int1 gnd gnd n w=1.2u l=0.6u
M5 dout dout_bar vdd vdd p w=1.2u l=0.6u
M6 dout dout_bar gnd gnd n w=1.2u l=0.6u
M7 int1 clk_bar dout vdd p w=1.2u l=0.6u
M8 int1 clk dout gnd n w=1.2u l=0.6u
.ENDS dlatch

.SUBCKT flipflop in out out_bar clk vdd gnd
M1 clk_bar clk vdd vdd p w=2.4u l=0.6u
M2 clk_bar clk gnd gnd n w=1.2u l=0.6u 
Xmaster in mout mout_bar clk clk_bar vdd gnd dlatch
Xslave mout_bar out_bar out clk_bar clk vdd gnd dlatch
.ENDS flipflop
