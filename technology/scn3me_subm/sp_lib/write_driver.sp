
.SUBCKT write_driver din bl br en vdd gnd
M1 din_bar din gnd gnd n w=1.2u l=0.6u
M2 din_bar din vdd vdd p w=2.1u l=0.6u
M3 en_bar en gnd gnd n w=1.2u l=0.6u 
M4 en_bar en vdd vdd p w=2.1u l=0.6u 
M5 en1 en_bar gnd gnd n w=1.2u l=0.6u 
M6 en1 en_bar vdd vdd p w=2.1u l=0.6u 
M7 vdd din net_1 vdd p w=7.8u l=0.6u 
M8 net_1 en_bar br vdd p w=7.8u l=0.6u  
M9 br en1 net_2 gnd n w=3.9u l=0.6u 
M10 net_2 din gnd gnd n w=3.9u l=0.6u 
M11 vdd din_bar net_3 vdd p w=7.8u l=0.6u
M12 net_3 en_bar bl vdd p w=7.8u l=0.6u  
M13 bl en1 net_4 gnd n w=3.9u l=0.6u
M14 net_4 din_bar gnd gnd n w=3.9u l=0.6u 
.ENDS	write_driver

