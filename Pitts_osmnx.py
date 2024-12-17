import osmnx as ox
import requests
import os

# Define the area of interest (Pittsburgh)
place_name = "Pittsburgh, Pennsylvania, USA"

# GitHub raw URL for the GraphML file
graphml_url = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main/pittsburgh_street_network.graphml"

# Local file path
local_graphml_file = "pittsburgh_street_network.graphml"

# Check if the file exists in the repository and download it
if not os.path.exists(local_graphml_file):
    print("Downloading GraphML file from the GitHub repository...")
    response = requests.get(graphml_url)
    if response.status_code == 200:
        with open(local_graphml_file, "wb") as file:
            file.write(response.content)
        print(f"GraphML file downloaded successfully to {local_graphml_file}")
    else:
        print("GraphML file not found in the repository. Generating a new one...")
        # Download the street network if the file doesn't exist
        G = ox.graph_from_place(place_name, network_type='drive')
        ox.save_graphml(G, filepath=local_graphml_file)
        print(f"GraphML file saved locally to {local_graphml_file}")
else:
    print(f"GraphML file already exists locally at {local_graphml_file}")

print("Process completed successfully.")
