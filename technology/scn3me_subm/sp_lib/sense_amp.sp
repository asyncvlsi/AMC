
.SUBCKT sense_amp bl br dout dout_bar en vdd gnd
M1 dout1 dout_bar vdd vdd p w=5.4u l=0.6u 
M2 dout1 dout_bar net_2 gnd n w=2.7u l=0.6u  
M3 dout_bar dout1 vdd vdd p w=5.4u l=0.6u  
M4 dout_bar dout1 net_2 gnd n w=2.7u l=0.6u  
M5 bl en1 dout1 vdd p w=7.2u l=0.6u  
M6 br en1 dout_bar vdd p w=7.2u l=0.6u  
M7 net_2 en1 gnd gnd n w=5.4u l=0.6u
M8 en_bar en vdd vdd p w=2.4u l=0.6u
M9 en_bar en gnd gnd n w=1.2u l=0.6u
M10 en1 en_bar vdd vdd p w=2.4u l=0.6u
M11 en1 en_bar gnd gnd n w=1.2u l=0.6u
M12 dout en1 1 gnd n w=2.4u l=0.6u
M13 1 dout_bar gnd gnd n w=2.4u l=0.6u
M14 1 dout_bar vdd vdd p w=2.4u l=0.6u  
.ENDS sense_amp

