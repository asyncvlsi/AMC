
.SUBCKT merge D Q en1_M en2_M reset M vdd gnd
M1 net_1 M gnd gnd n w=1.2u l=0.6u 
M2 net_2 D net_1 gnd n w=1.2u l=0.6u  
M3 net_3 en2_M net_2 gnd n w=1.2u l=0.6u  
M4 Q en1_M net_3 gnd n w=1.2u l=0.6u  
M5 Q en1_M net_5 vdd p w=1.2u l=0.6u
M6 vdd en2_M net_5 vdd p w=1.2u l=0.6u    
M7 reset_bar reset vdd vdd p w=1.2u l=0.6u
M8 reset_bar reset gnd gnd n w=1.2u l=0.6u
M9 Q reset_bar vdd vdd p w=1.2u l=0.6u
.ENDS merge

