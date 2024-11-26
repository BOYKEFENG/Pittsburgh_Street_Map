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
api_key = 'ed55ae765657e06c1cf40cf1141ce8b9e7129638' 

# Define file paths
output_folder = r'C:\Users\fengy\OneDrive\Desktop\24FALL\Pitts_Street_Bridge_Data'
graphml_filename = 'pittsburgh_street_network.graphml'
graphml_filepath = os.path.join(output_folder, graphml_filename)
slope_csv_filepath = os.path.join(output_folder, 'pittsburgh_street_slopes.csv')
slope_plot_filepath = os.path.join(output_folder, 'pittsburgh_street_network_with_slope.png')

# ------------------------------
# Step 1: Download and Save Street Network
# ------------------------------
def download_and_save_street_network():
    print("Downloading street network data...")
    # Download the street network (drivable roads) with automatic simplification
    G = ox.graph_from_place(place_name, network_type='drive')
    
    # Save the graph to a GraphML file
    ox.save_graphml(G, filepath=graphml_filepath)
    print(f"Street network saved to {graphml_filepath}\n")
    return G

# ------------------------------
# Step 2: Load Street Network
# ------------------------------
def load_street_network():
    if os.path.exists(graphml_filepath):
        print("Loading street network from GraphML file...")
        G = ox.load_graphml(graphml_filepath)
        print("Street network loaded successfully.\n")
    else:
        G = download_and_save_street_network()
    return G

# ------------------------------
# Step 3: Extract Segment Coordinates and Lengths
# ------------------------------
def extract_segment_info(G):
    print("Converting graph to GeoDataFrames...")
    nodes, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
    
    # Extract start and end coordinates from geometry
    print("Extracting start and end coordinates for each street segment...")
    edges['start_lon'] = edges['geometry'].apply(lambda x: x.coords[0][0])
    edges['start_lat'] = edges['geometry'].apply(lambda x: x.coords[0][1])
    edges['end_lon'] = edges['geometry'].apply(lambda x: x.coords[-1][0])
    edges['end_lat'] = edges['geometry'].apply(lambda x: x.coords[-1][1])
    
    # Ensure that the 'length' attribute exists and represents the actual street length in meters
    if 'length' not in edges.columns:
        print("Calculating street lengths...")
        edges['length'] = edges['geometry'].length  # Typically already present in OSMnx edges
    
    return edges

# ------------------------------
# Step 4: Retrieve Elevation Data
# ------------------------------
def retrieve_elevation_data(edges):
    print("Preparing to retrieve elevation data...")
    # Combine start and end points
    start_coords = edges[['start_lat', 'start_lon']].values.tolist()
    end_coords = edges[['end_lat', 'end_lon']].values.tolist()
    all_coords = list(set(map(tuple, start_coords + end_coords)))  # Unique coordinates
    
    print(f"Total unique coordinates to process: {len(all_coords)}\n")
    
    # Function to batch coordinates
    def batch_coords(coords, batch_size=512):
        for i in range(0, len(coords), batch_size):
            yield coords[i:i + batch_size]
    
    # Initialize elevation data dictionary
    elevation_data = {}
    
    # Base URL for TessaDEM Elevation API
    base_url = 'https://tessadem.com/api/elevation'
    
    # Iterate over batches and make API requests
    for batch_num, batch in enumerate(batch_coords(all_coords), start=1):
        print(f"Processing batch {batch_num} with {len(batch)} coordinates...")
        locations = '|'.join([f"{lat},{lon}" for lat, lon in batch])
        params = {
            'key': api_key,
            'locations': locations,
            'format': 'json',
            'unit': 'meters'
        }
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    for result in data['results']:
                        coord = (result['latitude'], result['longitude'])
                        elevation = result['elevation']
                        elevation_data[coord] = elevation
                else:
                    print(f"API Error in batch {batch_num}: {data.get('error', {}).get('message', 'Unknown error')}")
            else:
                print(f"HTTP Error in batch {batch_num}: Status code {response.status_code}")
        except Exception as e:
            print(f"Exception occurred in batch {batch_num}: {e}")
        
        # Respect API rate limits
        time.sleep(0.2)  # Adjust sleep time as needed based on API documentation
    
    print("Elevation data retrieval completed.\n")
    return elevation_data

# ------------------------------
# Step 5: Map Elevation Data to Edges
# ------------------------------
def map_elevation_to_edges(edges, elevation_data):
    print("Mapping elevation data to street segments...")
    
    # Function to get elevation from data
    def get_elev(lat, lon):
        return elevation_data.get((lat, lon), np.nan)
    
    # Apply elevation data to edges
    edges['start_elev'] = edges.apply(lambda row: get_elev(row['start_lat'], row['start_lon']), axis=1)
    edges['end_elev'] = edges.apply(lambda row: get_elev(row['end_lat'], row['end_lon']), axis=1)
    
    print("Elevation data mapped to street segments.\n")
    return edges

# ------------------------------
# Step 6: Calculate Slope
# ------------------------------
def calculate_slope(edges):
    print("Calculating slope for each street segment...")
    
    # Slope calculation: (Elevation Change) / (Street Length) * 100
    edges['slope_percentage'] = ((edges['end_elev'] - edges['start_elev']) / edges['length']) * 100
    
    # Handle cases where length is zero or elevation data is missing
    edges['slope_percentage'] = edges['slope_percentage'].replace([np.inf, -np.inf], np.nan)
    
    # Calculate the absolute value of the slope percentage
    edges['abs_slope_percentage'] = edges['slope_percentage'].abs()
    
    print("Slope calculation completed.\n")
    return edges


# ------------------------------
# Step 7: Save Slope Data to CSV (with Geometry)
# ------------------------------
def save_slope_data(edges):
    print("Saving slope data to CSV file with geometry...")

    # Reset index to include osmid as a column
    edges_reset = edges.reset_index()

    # Select relevant columns, including geometry
    result = edges_reset[['osmid', 'name', 'start_lat', 'start_lon', 'end_lat', 'end_lon', 
                          'slope_percentage', 'abs_slope_percentage', 'geometry']]

    # Rename columns for clarity
    result.rename(columns={
        'name': 'street_name',
        'start_lat': 'start_latitude',
        'start_lon': 'start_longitude',
        'end_lat': 'end_latitude',
        'end_lon': 'end_longitude',
        'slope_percentage': 'slope_percentage',
        'abs_slope_percentage': 'abs_slope_percentage',
        'geometry': 'geometry'
    }, inplace=True)

    # Convert geometry to WKT format for saving in CSV
    result['geometry'] = result['geometry'].apply(lambda geom: geom.wkt)

    # Save to CSV
    result.to_csv(slope_csv_filepath, index=False)
    print(f"Slope data with geometry saved to {slope_csv_filepath}\n")
    return result



# ------------------------------
# Step 8: Visualize with OSMnx and Matplotlib
# ------------------------------
def visualize_with_osmnx(G, edges):
    print("Visualizing street network with slope-based coloring using OSMnx and Matplotlib...")
    
    # Ensure 'slope_percentage' exists
    if 'slope_percentage' not in edges.columns:
        print("Slope data not found in edges. Skipping visualization.")
        return
    
    # Remove edges with missing slope data
    edges_valid = edges.dropna(subset=['slope_percentage'])
    
    # Define colormap
    cmap = plt.cm.viridis
    norm = mcolors.Normalize(vmin=edges_valid['slope_percentage'].min(), vmax=edges_valid['slope_percentage'].max())
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 12))
    edges_valid.plot(ax=ax, linewidth=1, edgecolor=cmap(norm(edges_valid['slope_percentage'])))
    
    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label('Slope Percentage (%)')
    
    # Customize plot
    ax.set_title('Pittsburgh Street Network Colored by Slope', fontsize=15)
    ax.set_axis_off()
    
    # Save plot
    fig.savefig(slope_plot_filepath, dpi=300, bbox_inches='tight')
    print(f"Matplotlib plot saved to {slope_plot_filepath}")
    
    # Show plot
    plt.show()

# ------------------------------
# Main Execution Flow
# ------------------------------
def main():
    # Step 1 & 2: Load or Download Street Network
    G = load_street_network()
    
    # Step 3: Extract Segment Coordinates and Lengths
    edges = extract_segment_info(G)
    
    # Step 4: Retrieve Elevation Data
    elevation_data = retrieve_elevation_data(edges)
    
    # Step 5: Map Elevation Data to Edges
    edges = map_elevation_to_edges(edges, elevation_data)
    
    # Step 6: Calculate Slope
    edges = calculate_slope(edges)
    
    # Step 7: Save Slope Data to CSV
    slope_data = save_slope_data(edges)
    
    # Step 8: Visualize with OSMnx and Matplotlib
    visualize_with_osmnx(G, edges)
    
    print("All tasks completed successfully.")

if __name__ == "__main__":
    main()
