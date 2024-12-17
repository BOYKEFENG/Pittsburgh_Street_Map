import os
import osmnx as ox
import pandas as pd
import numpy as np
import requests
import time
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ------------------------------
# Configuration Parameters
# ------------------------------
# Define the area of interest
place_name = "Pittsburgh, Pennsylvania, USA"

# Define API key for TessaDEM Elevation API
api_key = ''

# Define raw URLs for saving/loading files from the repository
base_repo_url = "https://raw.githubusercontent.com/BOYKEFENG/Pittsburgh_Street_Map/main"

graphml_url = f"{base_repo_url}/pittsburgh_street_network.graphml"
slope_csv_url = f"{base_repo_url}/pittsburgh_street_slopes.csv"

# ------------------------------
# Step 1: Download and Save Street Network
# ------------------------------
def download_and_save_street_network():
    print("Downloading street network data...")
    # Download the street network (drivable roads) with automatic simplification
    G = ox.graph_from_place(place_name, network_type='drive')

    # Calculate edge lengths explicitly
    G = ox.distance.add_edge_lengths(G)

    # Save the graph locally and push it to the repo if required
    ox.save_graphml(G, filepath="pittsburgh_street_network.graphml")
    print(f"Street network saved locally to GraphML file.\n")
    return G

# ------------------------------
# Step 2: Load Street Network
# ------------------------------
def load_street_network():
    print("Loading street network from raw GitHub repository...")
    try:
        # Download the GraphML file directly from the GitHub raw link
        graphml_file = "pittsburgh_street_network.graphml"
        response = requests.get(graphml_url)
        with open(graphml_file, "wb") as file:
            file.write(response.content)
        print("Street network loaded successfully.\n")
        G = ox.load_graphml(graphml_file)
    except Exception as e:
        print(f"Error loading graph: {e}. Downloading new graph...")
        G = download_and_save_street_network()
    return G

# ------------------------------
# Step 3: Extract Segment Coordinates and Lengths
# ------------------------------
def extract_segment_info(G):
    print("Converting graph to GeoDataFrames...")
    nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

    print("Extracting start and end coordinates for each street segment...")
    edges['start_lon'] = edges['geometry'].apply(lambda x: x.coords[0][0])
    edges['start_lat'] = edges['geometry'].apply(lambda x: x.coords[0][1])
    edges['end_lon'] = edges['geometry'].apply(lambda x: x.coords[-1][0])
    edges['end_lat'] = edges['geometry'].apply(lambda x: x.coords[-1][1])

    if 'length' not in edges.columns:
        edges['length'] = edges['geometry'].length  # Ensure street lengths exist

    print("Street segment information extracted successfully.\n")
    return edges

# ------------------------------
# Step 4: Retrieve Elevation Data
# ------------------------------
def retrieve_elevation_data(edges):
    print("Retrieving elevation data...")
    start_coords = edges[['start_lat', 'start_lon']].values.tolist()
    end_coords = edges[['end_lat', 'end_lon']].values.tolist()
    all_coords = list(set(map(tuple, start_coords + end_coords)))

    def batch_coords(coords, batch_size=512):
        for i in range(0, len(coords), batch_size):
            yield coords[i:i + batch_size]

    elevation_data = {}
    base_url = 'https://tessadem.com/api/elevation'

    for batch_num, batch in enumerate(batch_coords(all_coords), start=1):
        print(f"Processing batch {batch_num}...")
        locations = '|'.join([f"{lat},{lon}" for lat, lon in batch])
        params = {'key': api_key, 'locations': locations, 'format': 'json', 'unit': 'meters'}
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                for result in response.json().get('results', []):
                    coord = (result['latitude'], result['longitude'])
                    elevation_data[coord] = result['elevation']
        except Exception as e:
            print(f"Error in batch {batch_num}: {e}")
        time.sleep(0.2)

    return elevation_data

# ------------------------------
# Step 5: Map Elevation Data to Edges
# ------------------------------
def map_elevation_to_edges(edges, elevation_data):
    def get_elev(lat, lon):
        return elevation_data.get((lat, lon), np.nan)

    edges['start_elev'] = edges.apply(lambda row: get_elev(row['start_lat'], row['start_lon']), axis=1)
    edges['end_elev'] = edges.apply(lambda row: get_elev(row['end_lat'], row['end_lon']), axis=1)
    return edges

# ------------------------------
# Step 6: Calculate Slope
# ------------------------------
def calculate_slope(edges):
    edges['slope_percentage'] = ((edges['end_elev'] - edges['start_elev']) / edges['length']) * 100
    edges['slope_percentage'].replace([np.inf, -np.inf], np.nan, inplace=True)
    edges['abs_slope_percentage'] = edges['slope_percentage'].abs()
    return edges

# ------------------------------
# Step 7: Save Slope Data to CSV (with Geometry)
# ------------------------------
def save_slope_data(edges):
    print("Saving slope data to CSV...")
    edges_reset = edges.reset_index()
    edges_reset['geometry'] = edges_reset['geometry'].apply(lambda geom: geom.wkt)
    edges_reset.to_csv("pittsburgh_street_slopes.csv", index=False)
    print("Slope data saved locally.\n")

# ------------------------------
# Main Execution Flow
# ------------------------------
def main():
    G = load_street_network()
    edges = extract_segment_info(G)
    elevation_data = retrieve_elevation_data(edges)
    edges = map_elevation_to_edges(edges, elevation_data)
    edges = calculate_slope(edges)
    save_slope_data(edges)
    print("All tasks completed successfully.")

if __name__ == "__main__":
    main()
