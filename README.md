# AMC :  An Asynchronous Memory (SRAM) Compiler.

<img align="right" width="25%" src="images/test_chip.png">

AMC is an open-source asynchronous pipelined memory compiler. 
AMC generates SRAM modules with a bundled-data datapath and 
quasi-delay-insensitive control. AMC is a Python-base, flexible, user-modifiable and 
technology-independent memory compiler that generates fabricable 
SRAM blocks in a broad range of sizes, configurations and process nodes.

The description of the circuits AMC generates and the compiler
can be found in the following paper:
   * Samira Ataei and Rajit Manohar. AMC: An Asynchronous Memory Compiler. Proceedings of the IEEE International Symposium on Asynchronous Circuits and Systems (ASYNC), May 2019.

AMC generates GDSII layout data, standard SPICE netlists, Verilog models, 
DRC/LVS verification reports, timing and power models (.lib), and placement and 
routing models (.lef). 



More detailed documentation is available here: http://avlsi.csl.yale.edu/act/doku.php?id=amc:start



