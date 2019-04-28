import os

""" File containing the process technology parameters for SCMOS 3me, subm, 600nm. """

info={}
info["name"]="scn3me_subm"
info["body_tie_down"] = 0
info["has_pwell"] = True
info["has_nwell"] = True

#GDS file info
GDS={}
# gds units
GDS["unit"]=(0.001,1e-6)  
# default label zoom
GDS["zoom"] = 0.5


###################################################
##GDS Layer Map
###################################################

# create the GDS layer map
layer={} 
layer["vtg"]            = -1 
layer["vth"]            = -1 
layer["contact"]        = 47 
layer["pwell"]          = 41 
layer["nwell"]          = 42 
layer["active"]         = 43 
layer["pimplant"]       = 44
layer["nimplant"]       = 45
layer["poly"]           = 46 
layer["active_contact"] = 48
layer["metal1"]         = 49 
layer["via1"]           = 50 
layer["metal2"]         = 51 
layer["via2"]           = 61 
layer["metal3"]         = 62
layer["metal4"]         = -1 
layer["text"]           = 83 
layer["boundary"]       = 83
layer["polypin"]       = 46
layer["m1pin"]          = 49
layer["m2pin"]          = 51
layer["m3pin"]          = 62 
layer["m4pin"]          = -1 


###################################################
##END GDS Layer Map
###################################################

###################################################
##DRC/LVS Rules Setup
###################################################

#technology parameter
parameter={}
parameter["min_tx_size"] = 1.2
parameter["beta"] = 2 

drclvs_home=os.environ.get("DRCLVS_HOME")

drc={}
#grid size is 1/2 a lambda
drc["grid"]=0.15
#DRC/LVS test set_up
drc["drc_rules"]=drclvs_home+"/calibreDRC_scn3me_subm.rul"
drc["lvs_rules"]=drclvs_home+"/calibreLVS_scn3me_subm.rul"
drc["layer_map"]=os.environ.get("AMC_TECH")+"/scn3me_subm/layers.map"

        	      					
# minwidth_tx with contact (no dog bone transistors)
drc["minwidth_tx"] = 1.2
drc["minlength_channel"] = 0.6

# 1.4 Minimum spacing between wells of different type (if both are drawn) 
drc["pwell_to_nwell"] = 0
drc["well_to_well"] = 1.8
# 1.1 Minimum width 
drc["minwidth_well"] = 3.6
drc["minwidth_nwell"] = 3.6
drc["minwidth_pwell"] = 3.6                                                                      
# 3.1 Minimum width 
drc["minwidth_poly"] = 0.6
# 3.2 Minimum spacing over active
drc["poly_to_poly"] = 0.9
# 3.3 Minimum gate extension of active 
drc["poly_extend_active"] = 0.6
# ??
drc["poly_to_polycontact"] = 1.2
# ??
drc["active_enclosure_gate"] = 0.0
# 3.2.a Minimum spacing over field poly
drc["poly_to_field_poly"] = 0.9
# 3.5 Minimum field poly to active 
drc["poly_to_active"] = 0.3
# Not a rule
drc["minarea_poly"] = 0.0

# ??
drc["active_to_body_active"] = 1.2  
# 2.1 Minimum width 
drc["minwidth_active"] = 0.9
# 2.2 Minimum spacing
drc["active_to_active"] = 0.9
# 2.3 Source/drain active to well edge 
drc["well_enclosure_active"] = 1.8
# Reserved for asymmetric enclosures
drc["well_extend_active"] = 1.8
# Not a rule
drc["minarea_active"] = 0.0

# 4.1 Minimum select spacing to channel of transistor 
drc["implant_to_channel"] = 0.9
# 4.2 Minimum select overlap of active
drc["implant_enclosure_active"] = 0.6
# Not a rule
drc["implant_enclosure_body_active"] = 0.6
# 4.3 Minimum select overlap of contact  
drc["implant_enclosure_contact"] = 0.3
# Not a rule
drc["implant_enclosure_poly"] = 0
# Not a rule
drc["implant_to_contact"] = 0
# Not a rule
drc["implant_to_implant"] = 0
# Not a rule
drc["minwidth_implant"] = 0
drc["minwidth_nimplant"] = 0
drc["minwidth_pimplant"] = 0
# Not a rule
drc["minarea_implant"] = 0

# 6.1 Exact contact size
drc["minwidth_contact"] = 0.6
# 5.3 Minimum contact spacing
drc["contact_to_contact"] = 0.9                    
# 6.2.b Minimum active overlap 
drc["active_enclosure_contact"] = 0.3
# Reserved for asymmetric enclosure
drc["active_extend_contact"] = 0.3
# 5.2.b Minimum poly overlap 
drc["poly_enclosure_contact"] = 0.3
# Reserved for asymmetric enclosures
drc["poly_extend_contact"] = 0.3
# Reserved for other technologies
drc["contact_to_gate"] = 0.6
# 5.4 Minimum spacing to gate of transistor
drc["contact_to_poly"] = 0.6
        
# 7.1 Minimum width 
drc["minwidth_metal1"] = 0.9
# 7.2 Minimum spacing 
drc["metal1_to_metal1"] = 0.9
# 7.3 Minimum overlap of any contact 
drc["metal1_enclosure_contact"] = 0.3
# Reserved for asymmetric enclosure
drc["metal1_extend_contact"] = 0.3
# 8.3 Minimum overlap by metal1 
drc["metal1_enclosure_via1"] = 0.3                
# Reserve for asymmetric enclosures
drc["metal1_extend_via1"] = 0.3
# Not a rule
drc["minarea_metal1"] = 0

# 8.1 Exact size 
drc["minwidth_via1"] = 0.6
# 8.2 Minimum via1 spacing 
drc["via1_to_via1"] = 0.6

# 9.1 Minimum width
drc["minwidth_metal2"] = 0.9
# 9.2 Minimum spacing 
drc["metal2_to_metal2"] = 0.9
# 9.3 Minimum overlap of via1 
drc["metal2_extend_via1"] = 0.3
# Reserved for asymmetric enclosures
drc["metal2_enclosure_via1"] = 0.3
# 14.3 Minimum overlap by metal2
drc["metal2_extend_via2"] = 0.3
# Reserved for asymmetric enclosures
drc["metal2_enclosure_via2"] = 0.3
# Not a rule
drc["minarea_metal2"] = 0

# 14.2 Exact size
drc["minwidth_via2"] = 0.6
# 14.2 Minimum spacing
drc["via2_to_via2"] = 0.9    

# 15.1 Minimum width
drc["minwidth_metal3"] = 1.5
# 15.2 Minimum spacing to metal3
drc["metal3_to_metal3"] = 0.9
# 15.3 Minimum overlap of via 2
drc["metal3_extend_via2"] = 0.6
# Reserved for asymmetric enclosures
drc["metal3_enclosure_via2"] = 0.6
# Not a rule
drc["minarea_metal3"] = 0

###################################################
##END DRC/LVS Rules
###################################################

###################################################
##Spice Simulation Parameters
###################################################

# spice model info
spice={}
spice["nmos"]="n"
spice["pmos"]="p"
# This is a map of corners to model files
SPICE_MODEL_DIR=os.environ.get("SPICE_MODEL_DIR")

#spice stimulus related variables
spice["inv_delay"] = 0.5                    # Estimated inverter gate delay [ns]
spice["input_cap"] = 10                     # Input capacitance of split cell (Din,ctrl,addr) [fF] 
spice["feasible_period"] = 5                # estimated feasible period in ns
spice["supply_voltages"] = [4.5, 5.0, 5.5]  # Supply voltage corners in [V]
spice["nom_supply_voltage"] = 5.0           # Nominal supply voltage in [V]
spice["rise_time"] = 0.05                   # Rise time in [ns]
spice["fall_time"] = 0.05                   # Fall time in [ns]
spice["temperatures"] = [0, 25, 100]        # Temperature corners (oC)
spice["nom_temperature"] = 25               # Nominal temperature (oC)

#sram signal names
spice["vdd_name"] = "vdd"
spice["gnd_name"] = "gnd"
spice["control_signals"] = ["reset", "R", "W", "RW", "ACK", "WREQ", "WACK", "RREQ", "RACK"]
spice["data_name"] = "DATA"
spice["addr_name"] = "ADDR"
spice["minwidth_tx"] = drc["minwidth_tx"]
spice["channel"] = drc["minlength_channel"]

###################################################
##END Spice Simulation Parameters
###################################################
