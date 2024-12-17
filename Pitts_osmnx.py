import osmnx as ox
import os

# Define the area of interest (Pittsburgh)
place_name = "Pittsburgh, Pennsylvania, USA"

# Download the street network (drivable roads)
G = ox.graph_from_place(place_name, network_type='drive')

# Save the graph to a GraphML file
output_folder = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    
graphml_filepath = os.path.join(output_folder, 'pittsburgh_street_network.graphml')
ox.save_graphml(G, filepath=graphml_filepath)

print(f"GraphML file saved to {graphml_filepath}")
