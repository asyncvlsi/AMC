# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA  02110-1301, USA. (See LICENSE for licensing information)


word_size = 32
words_per_row = 1
num_rows = 64
num_subanks = 4
branch_factors = (1,4)
bank_orientations = ("V", "H")
name = "AMC_SRAM"

add_sync_interface = True

create_bist = True
#define sram access time (ns) for asynchronous BIST only
bist_delay = 5


output_path = "amc_scn3me_subm"


tech_name = "scn3me_subm"
process_corners = ["TT"]
supply_voltages = [ 5.0 ]
temperatures = [ 25 ]


